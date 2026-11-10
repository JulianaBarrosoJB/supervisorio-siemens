"""Agente de telemetria: lê CSV existente, persiste SQLite e sincroniza PostgreSQL.

Instalação: pip install "psycopg[binary]>=3.2,<4"
Configuração por variáveis de ambiente; nunca salvar senha no Git.
"""
import csv
import hashlib
import io
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

LOG = logging.getLogger("telemetria")
CSV_FILE = Path(os.getenv("MOTORES_CSV_PATH", "dados_motores.csv"))
SQLITE_FILE = Path(os.getenv("TELEMETRIA_SQLITE_PATH", "telemetria.sqlite3"))
STATION = os.getenv("TELEMETRIA_STATION_ID", "betim")
POSTGRES_URL = os.getenv("DATABASE_URL", "")
INTERVAL = max(1.0, float(os.getenv("TELEMETRIA_INTERVAL", "1")))
BATCH = max(1, min(500, int(os.getenv("TELEMETRIA_BATCH", "100"))))
RETENTION_DAYS = 30  # Retenção máxima fixa, inclusive para registros pendentes.


def init_local(db):
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY, station_id TEXT NOT NULL,
        captured_at TEXT NOT NULL, measurements TEXT NOT NULL,
        sent_at TEXT
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_events_pending ON events(sent_at)")
    db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.commit()


def meta(db, key, default=""):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def put_meta(db, key, value):
    db.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def parse_timestamp(value):
    # Logger legado usa horário local da fábrica; configurar TELEMETRIA_TZ.
    from zoneinfo import ZoneInfo
    local = ZoneInfo(os.getenv("TELEMETRIA_TZ", "America/Sao_Paulo"))
    dt = datetime.fromisoformat(value.strip())
    return (dt.replace(tzinfo=local) if dt.tzinfo is None else dt).astimezone(timezone.utc).isoformat()


def ingest(db):
    if not CSV_FILE.exists():
        return 0
    stat = CSV_FILE.stat()
    offset = int(meta(db, "offset", "0"))
    header = meta(db, "header")
    # Reinício/rotação do arquivo ou substituição pelo logger.
    identity = f"{stat.st_dev}:{stat.st_ino}"
    if identity != meta(db, "identity") or stat.st_size < offset:
        offset, header = 0, ""
    count = 0
    with CSV_FILE.open("rb") as fh:
        fh.seek(offset)
        while True:
            start = fh.tell()
            raw = fh.readline()
            if not raw or not raw.endswith(b"\n"):
                break  # Nunca avançar sobre linha incompleta.
            offset = fh.tell()
            line = raw.decode("utf-8-sig", errors="replace").strip()
            if not line:
                continue
            if line.startswith("timestamp;"):
                header = line
                continue
            if not header:
                continue
            try:
                cols = next(csv.DictReader(io.StringIO(header + "\n" + line), delimiter=";"))
                captured = parse_timestamp(cols["timestamp"])
                motors = {}
                for key, value in cols.items():
                    if not value or not key or "_" not in key:
                        continue
                    motor, field = key.split("_", 1)
                    if field not in ("corrente", "velocidade"):
                        continue
                    try:
                        number = float(value.replace(",", "."))
                    except ValueError:
                        continue
                    motors.setdefault(motor, {})[field] = number
                if not motors:
                    continue
                payload = json.dumps(motors, sort_keys=True, separators=(",", ":"))
                # Idempotente entre reprocessamentos do mesmo CSV.
                event_id = hashlib.sha256(f"{STATION}|{captured}|{payload}".encode()).hexdigest()
                db.execute("INSERT OR IGNORE INTO events(event_id,station_id,captured_at,measurements) VALUES(?,?,?,?)",
                           (event_id, STATION, captured, payload))
                count += 1
            except (ValueError, KeyError, csv.Error, TypeError) as exc:
                LOG.warning("Linha CSV inválida no byte %s: %s", start, exc)
    put_meta(db, "identity", identity)
    put_meta(db, "offset", offset)
    put_meta(db, "header", header)
    db.commit()
    return count


def sync(db):
    if not POSTGRES_URL:
        return 0
    from zoneinfo import ZoneInfo
    # O PostgreSQL guarda somente o dia atual em Brasilia.
    # Pendencias de dias anteriores continuam no SQLite por ate 30 dias,
    # mas nao sao reenviadas para a nuvem apos a virada.
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo"))
    inicio_dia_utc = hoje.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
    rows = db.execute("""SELECT event_id, station_id, captured_at, measurements
                         FROM events WHERE sent_at IS NULL AND captured_at >= ?
                         ORDER BY rowid LIMIT ?""", (inicio_dia_utc, BATCH)).fetchall()
    if not rows:
        return 0
    # Confirmação somente após commit remoto; em caso de falha os eventos permanecem pendentes.
    with psycopg.connect(POSTGRES_URL, connect_timeout=8, autocommit=False) as pg:
        with pg.cursor() as cur:
            cur.executemany("""INSERT INTO motor_snapshots
                (event_id, station_id, captured_at, measurements)
                VALUES (%s,%s,%s,%s) ON CONFLICT (event_id) DO NOTHING""",
                [(eid, station, captured, Jsonb(json.loads(payload)))
                 for eid, station, captured, payload in rows])
        pg.commit()
    db.executemany("UPDATE events SET sent_at=? WHERE event_id=?",
                   [(datetime.now(timezone.utc).isoformat(), row[0]) for row in rows])
    db.commit()
    return len(rows)


def cleanup(db):
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    # Limite por data de aquisição, não por data de envio.
    # Registros pendentes antigos também expiram: registrar a perda no log.
    pending = db.execute(
        "SELECT COUNT(*) FROM events WHERE captured_at < ? AND sent_at IS NULL",
        (cutoff,)
    ).fetchone()[0]
    if pending:
        LOG.error("RETENÇÃO 30 DIAS: excluindo %s registros não transmitidos; dados perdidos.", pending)
    removed = db.execute("DELETE FROM events WHERE captured_at < ?", (cutoff,)).rowcount
    db.commit()
    if removed:
        LOG.info("Limpeza SQLite: %s registros com mais de 30 dias removidos.", removed)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    SQLITE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQLITE_FILE) as db:
        init_local(db)
        last_cleanup = 0
        failures = 0
        next_sync = 0.0
        while True:
            # A coleta local continua a cada segundo, mesmo se a nuvem estiver indisponível.
            try:
                n = ingest(db)
                if n:
                    LOG.info("Gravados localmente: %s", n)
            except (OSError, sqlite3.Error, ValueError) as exc:
                LOG.error("Erro ao persistir CSV local: %s", exc)
            if time.monotonic() >= next_sync:
                try:
                    sent = sync(db)
                    if sent:
                        pending = db.execute("SELECT COUNT(*) FROM events WHERE sent_at IS NULL").fetchone()[0]
                        LOG.info("Enviados: %s; pendentes: %s", sent, pending)
                    failures = 0
                    next_sync = time.monotonic() + INTERVAL
                except (psycopg.Error, OSError, sqlite3.Error) as exc:
                    failures += 1
                    delay = min(60.0, INTERVAL * 2 ** min(failures, 6))
                    next_sync = time.monotonic() + delay
                    LOG.warning("PostgreSQL indisponível; nova tentativa em %.0fs: %s", delay, exc)
            if time.monotonic() - last_cleanup > 3600:
                try:
                    cleanup(db)
                except sqlite3.Error as exc:
                    LOG.error("Falha na limpeza: %s", exc)
                last_cleanup = time.monotonic()
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

"""Fontes de dados do supervisório: CSV local ou demonstração."""
import os
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

MOTORES = [f"M{i:02d}" for i in range(1, 86)] + ["M102", "M103"]
CSV_PATH = os.environ.get("MOTORES_CSV_PATH", "dados_motores.csv")

@st.cache_data(ttl=2)
def carregar_csv():
    if not os.path.isfile(CSV_PATH):
        return None
    try:
        df = pd.read_csv(CSV_PATH, sep=";", decimal=",", encoding="utf-8-sig", on_bad_lines="skip")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df.dropna(subset=["timestamp"]).tail(1200)
    except (OSError, ValueError, pd.errors.ParserError):
        return None

def serie_demo(motor):
    numero = int(motor[1:])
    t = pd.date_range(end=datetime.now(), periods=180, freq="s")
    x = np.arange(180)
    return pd.DataFrame({
        "timestamp": t,
        "corrente": np.maximum(0, 3.6 + numero * .045 + .05 * np.sin(x / 16 + numero * .21)),
        "velocidade": np.clip(72 + (numero % 13) * .55 + .12 * np.sin(x / 15 + numero * .3), 0, 100),
    })

def dados_motor(df, motor):
    if df is not None and f"{motor}_corrente" in df and f"{motor}_velocidade" in df:
        dados = df[["timestamp", f"{motor}_corrente", f"{motor}_velocidade"]].copy()
        dados.columns = ["timestamp", "corrente", "velocidade"]
        dados["corrente"] = pd.to_numeric(dados["corrente"], errors="coerce")
        dados["velocidade"] = pd.to_numeric(dados["velocidade"], errors="coerce")
        dados = dados.dropna().tail(120)
        if not dados.empty:
            return dados, False
    if df is not None:
        return pd.DataFrame(columns=["timestamp", "corrente", "velocidade"]), False
    return serie_demo(motor).tail(120), True

def segredo(nome, default=""):
    try:
        return st.secrets.get(nome, os.getenv(nome, default))
    except (FileNotFoundError, RuntimeError):
        return os.getenv(nome, default)

@st.cache_data(ttl=1, show_spinner=False)
def carregar_postgres():
    """Consulta últimos snapshots; credenciais apenas nos Secrets do Streamlit."""
    import psycopg
    import json
    from datetime import timezone
    url = segredo("DATABASE_URL")
    station = segredo("TELEMETRIA_STATION_ID", "betim")
    if not url:
        return None
    with psycopg.connect(url, connect_timeout=5) as pg:
        with pg.cursor() as cur:
            cur.execute("""SELECT captured_at, measurements FROM motor_snapshots
                           WHERE station_id=%s ORDER BY captured_at DESC LIMIT 120""", (station,))
            rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=["timestamp"])
    out = []
    for ts, payload in reversed(rows):
        record = {"timestamp": ts.astimezone(timezone.utc)}
        if isinstance(payload, str):
            payload = json.loads(payload)
        for motor, metrics in payload.items():
            for field in ("corrente", "velocidade"):
                if field in metrics:
                    record[f"{motor}_{field}"] = metrics[field]
        out.append(record)
    return pd.DataFrame(out)

def carregar_dados():
    """Prioriza banco externo configurado; sem fallback fictício em caso de falha."""
    if segredo("DATABASE_URL"):
        return carregar_postgres(), "PostgreSQL"
    df = carregar_csv()
    return df, "CSV local" if df is not None else "Demonstração"

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

@st.cache_data(ttl=2, show_spinner=False)
def carregar_postgres(access_token):
    """Leitura via Data API e JWT do usuário. RLS aplicada pelo PostgreSQL."""
    import requests
    from datetime import timezone

    url = segredo("SUPABASE_URL").rstrip("/")
    chave = segredo("SUPABASE_ANON_KEY")
    station = segredo("TELEMETRIA_STATION_ID", "betim")
    if not url or not chave or not access_token:
        raise RuntimeError("Autenticação do Supabase não configurada.")
    try:
        response = requests.get(
            url + "/rest/v1/motor_snapshots",
            headers={"apikey": chave, "Authorization": "Bearer " + access_token},
            params={
                "select": "captured_at,measurements",
                "station_id": "eq." + station,
                "order": "captured_at.desc",
                "limit": "120",
            },
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError("Consulta protegida ao PostgreSQL falhou.") from exc

    rows = response.json()
    if not rows:
        return pd.DataFrame(columns=["timestamp"])
    out = []
    for item in reversed(rows):
        record = {"timestamp": pd.to_datetime(item["captured_at"], utc=True)}
        payload = item["measurements"]
        for motor, metrics in payload.items():
            for field in ("corrente", "velocidade"):
                if field in metrics:
                    record[f"{motor}_{field}"] = metrics[field]
        out.append(record)
    return pd.DataFrame(out)


def carregar_dados(access_token):
    """A consulta exige login; jamais retornar dados locais ou fictícios ao visitante."""
    return carregar_postgres(access_token), "PostgreSQL"

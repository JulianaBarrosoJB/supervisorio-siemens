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
        "corrente": np.maximum(0, 6 + numero * .045 + 1.2 * np.sin(x / 14 + numero)),
        "velocidade": np.clip(76 + 10 * np.sin(x / 25 + numero / 9), 0, 100),
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
    return serie_demo(motor).tail(120), True

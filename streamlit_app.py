import os
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Gráficos dos motores", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.stApp {background-color:#ffffff;color:#202a36}
[data-testid="stSidebar"] {background-color:#f6f8fb}
.block-container {padding-top:1.5rem;max-width:1600px}
h1 {font-size:1.65rem!important;font-weight:650!important}
[data-testid="stVerticalBlockBorderWrapper"] {background:#fff}
</style>""", unsafe_allow_html=True)

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

with st.sidebar:
    st.title("Motores")
    pesquisa = st.text_input("Filtrar motor", placeholder="Ex.: M07")
    encontrados = [m for m in MOTORES if pesquisa.strip().upper() in m]
    selecionar_todos = st.checkbox("Mostrar todos", value=not bool(pesquisa.strip()))
    padrao = encontrados if selecionar_todos else encontrados[:1]
    escolhidos = st.multiselect("Selecionar motores", encontrados, default=padrao)
    st.caption(f"{len(escolhidos)} motor(es) selecionado(s)")

logo_a, logo_b = st.columns([3, 2], vertical_alignment="center")
with logo_a:
    if os.path.isfile("assets/logo_nacional.png"):
        st.image("assets/logo_nacional.png", width=285)
with logo_b:
    if os.path.isfile("assets/logo_vlatecn.png"):
        st.image("assets/logo_vlatecn.png", width=215)
st.title("Gráficos dos motores")

@st.fragment(run_every="2s")
def exibir():
    if not escolhidos:
        st.info("Selecione pelo menos um motor na barra lateral.")
        return
    df = carregar_csv()
    simulado = df is None
    if simulado:
        st.caption("Demonstração • dados simulados")
    else:
        st.caption("Leituras do arquivo CSV local")
    for inicio in range(0, len(escolhidos), 2):
        colunas = st.columns(2, gap="medium")
        for coluna, motor in zip(colunas, escolhidos[inicio:inicio+2]):
            with coluna:
                if df is not None and f"{motor}_corrente" in df and f"{motor}_velocidade" in df:
                    dados = df[["timestamp", f"{motor}_corrente", f"{motor}_velocidade"]].copy()
                    dados.columns = ["timestamp", "corrente", "velocidade"]
                    dados["corrente"] = pd.to_numeric(dados["corrente"], errors="coerce")
                    dados["velocidade"] = pd.to_numeric(dados["velocidade"], errors="coerce")
                    dados = dados.dropna().tail(120)
                else:
                    dados = serie_demo(motor).tail(120)
                st.markdown(f"### {motor}")
                velocidade = float(dados["velocidade"].iloc[-1]) if not dados.empty else float("nan")
                corrente = float(dados["corrente"].iloc[-1]) if not dados.empty else float("nan")
                card_vel, card_status, card_corr = st.columns(3)
                card_vel.metric("Velocidade", f"{velocidade:.1f} %" if np.isfinite(velocidade) else "—")
                card_status.metric("Status", "Não mapeado")
                card_corr.metric("Corrente", f"{corrente:.2f} A" if np.isfinite(corrente) else "—")
                fig = go.Figure(go.Scatter(
                    x=dados["timestamp"], y=dados["corrente"], mode="lines",
                    line=dict(color="#2878b8", width=2),
                    hovertemplate="%{x|%H:%M:%S}<br>%{y:.2f} A<extra></extra>",
                ))
                fig.update_layout(
                    template="plotly_white", height=245,
                    margin=dict(l=5,r=10,t=8,b=5),
                    paper_bgcolor="white", plot_bgcolor="white",
                    xaxis=dict(title=None,showgrid=False),
                    yaxis=dict(title="A",gridcolor="#edf1f5",rangemode="tozero"),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, key=f"grafico_{motor}")
exibir()

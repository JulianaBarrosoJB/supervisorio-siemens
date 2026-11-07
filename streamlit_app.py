import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Supervisório Siemens", page_icon="📈", layout="wide")
st.markdown("""<style>
.stApp {background:#0b1220;color:#e2e8f0}
[data-testid="stSidebar"] {background:#111c2e}
h1,h2,h3 {color:#f8fafc}
[data-testid="stMetric"] {background:#172438;padding:15px;border-radius:12px;border:1px solid #304056}
</style>""", unsafe_allow_html=True)

MOTORES = [f"M{i:02d}" for i in range(1,86)] + ["M102","M103"]
CSV_PATH = os.environ.get("MOTORES_CSV_PATH", "dados_motores.csv")

@st.cache_data(ttl=2)
def ler_csv():
    if not os.path.isfile(CSV_PATH):
        return None
    try:
        df = pd.read_csv(CSV_PATH, sep=";", decimal=",", encoding="utf-8-sig", on_bad_lines="skip")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df.dropna(subset=["timestamp"]).tail(1800)
    except (OSError, ValueError, pd.errors.ParserError):
        return None

def simular(motor):
    n = int(motor[1:])
    t = pd.date_range(end=datetime.now(), periods=240, freq="s")
    x = np.arange(240)
    corrente = np.maximum(0, 7 + n*.045 + 1.3*np.sin(x/11+n) + .4*np.sin(x/3))
    velocidade = np.clip(76 + 12*np.sin(x/23+n/7), 0, 100)
    return pd.DataFrame({"timestamp":t, "corrente":corrente, "velocidade":velocidade})

with st.sidebar:
    st.title("◈ SUPERVISÓRIO")
    st.caption("MONITORAMENTO INDUSTRIAL")
    busca = st.text_input("Pesquisar motor", placeholder="M07")
    filtrados = [m for m in MOTORES if busca.upper() in m]
    if not filtrados:
        st.warning("Motor não encontrado")
        st.stop()
    motor = st.selectbox("Motor", filtrados)
    variavel = st.radio("Tendência", ["Corrente (A)", "Velocidade (%)"])
    janela = st.select_slider("Janela (segundos)", options=[30,60,120,240], value=120)
    st.divider()
    st.caption("SOMENTE LEITURA • Sem comandos de acionamento")

st.title(f"Monitoramento • {motor}")
st.caption("Tendências de corrente e velocidade — projeto Siemens")
@st.fragment(run_every="2s")
def painel():
    fonte = ler_csv()
    col_c = f"{motor}_corrente"
    col_v = f"{motor}_velocidade"
    if fonte is not None and col_c in fonte and col_v in fonte:
        dados = fonte[["timestamp",col_c,col_v]].rename(columns={col_c:"corrente",col_v:"velocidade"}).copy()
        dados["corrente"] = pd.to_numeric(dados["corrente"], errors="coerce")
        dados["velocidade"] = pd.to_numeric(dados["velocidade"], errors="coerce")
        dados = dados.dropna().tail(janela)
        status = "CSV local"
        if dados.empty:
            st.warning("Sem leituras válidas no CSV")
            return
        atraso = (datetime.now() - dados["timestamp"].iloc[-1]).total_seconds()
        if atraso > 10:
            st.warning(f"Dados desatualizados há {int(atraso)} segundos")
    else:
        dados = simular(motor).tail(janela)
        status = "DEMONSTRAÇÃO — dados simulados"
    ultimo = dados.iloc[-1]
    a,b,c = st.columns(3)
    a.metric("Corrente", f"{ultimo['corrente']:.2f} A")
    b.metric("Velocidade", f"{ultimo['velocidade']:.2f} %")
    c.metric("Amostras", len(dados))
    eixo = "corrente" if variavel.startswith("Corrente") else "velocidade"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dados["timestamp"],y=dados[eixo],mode="lines",line=dict(color="#38bdf8",width=2),fill="tozeroy",fillcolor="rgba(56,189,248,.09)",name=variavel))
    fig.update_layout(template="plotly_dark",height=400,margin=dict(l=15,r=15,t=20,b=15),paper_bgcolor="#111c2e",plot_bgcolor="#111c2e",xaxis_title="Horário",yaxis_title=variavel)
    st.plotly_chart(fig,use_container_width=True)
    st.caption(f"Fonte: {status} | Última leitura: {ultimo['timestamp']:%d/%m/%Y %H:%M:%S} | Atualização visual: 2 s")
    st.info("Status ligado/desligado e falhas: não mapeados. Não inferimos estados a partir da corrente.")
    with st.expander("Histórico de medições"):
        st.dataframe(dados.sort_values("timestamp",ascending=False),use_container_width=True,hide_index=True)
    if status.startswith("DEMONSTRAÇÃO"):
        st.warning("Valores simulados. A hospedagem Streamlit Cloud não se conecta diretamente ao CLP da fábrica.")
painel()

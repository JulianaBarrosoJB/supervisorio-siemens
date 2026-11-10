"""Tema, logos e filtros do menu lateral."""
from pathlib import Path
import streamlit as st
from .dados import MOTORES

ASSETS = Path(__file__).resolve().parent.parent / "assets"

def aplicar_estilo():
    st.markdown("""<style>
.stApp {background-color:#ffffff;color:#243449}
[data-testid="stSidebar"] {background-color:#f7f9fc;border-right:1px solid #e4eaf1}
.block-container {padding-top:1.25rem;max-width:1500px}
h1 {font-size:1.25rem!important;font-weight:600!important}
h2 {font-size:1.1rem!important}
h3 {font-size:1rem!important;font-weight:650!important;color:#173b67!important}
[data-testid="stMetric"] {background:#f8fafc;border:1px solid #e8eef5;border-radius:9px;padding:.45rem .6rem!important}
[data-testid="stMetricValue"] {white-space:normal!important;overflow-wrap:break-word!important}
[data-testid="stSidebar"] [data-testid="stImage"] {margin-bottom:.2rem}
[data-testid="stSidebar"] hr {border-color:#e8eef5}
[data-testid="stPlotlyChart"] {border:1px solid #eef2f6;border-radius:9px;padding:0 .25rem}
[data-testid="stMetricLabel"] {font-size:.72rem!important}
[data-testid="stMetricValue"] {font-size:1.15rem!important;line-height:1.3!important}

[data-testid="stSidebar"] h1 {font-size:1.1rem!important}
</style>""", unsafe_allow_html=True)

def filtros_laterais():
    with st.sidebar:
        # As duas marcas ficam acima do título e não aparecem na área principal.
        nacional = ASSETS / "logo_nacional.png"
        vlatec = ASSETS / "logo_vlatecn.png"
        col_nacional, col_vlatec = st.columns([1, 1], gap="small", vertical_alignment="center")
        with col_nacional:
            if nacional.is_file():
                st.image(str(nacional), width="stretch")
        with col_vlatec:
            if vlatec.is_file():
                st.image(str(vlatec), use_container_width=True)
        st.title("Motores")
        pesquisa = st.text_input("Filtrar motor", placeholder="Ex.: M07")
        encontrados = [m for m in MOTORES if pesquisa.strip().upper() in m]
        selecionar_todos = st.checkbox("Mostrar todos", value=False)
        padrao = encontrados if selecionar_todos else encontrados[:2]
        escolhidos = st.multiselect("Selecionar motores", encontrados, default=padrao)
        st.caption(f"{len(escolhidos)} motor(es) selecionado(s)")
    return escolhidos

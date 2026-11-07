"""Tema, logos e filtros do menu lateral."""
from pathlib import Path
import streamlit as st
from .dados import MOTORES

ASSETS = Path(__file__).resolve().parent.parent / "assets"

def aplicar_estilo():
    st.markdown("""<style>
.stApp {background-color:#ffffff;color:#202a36}
[data-testid="stSidebar"] {background-color:#f6f8fb}
.block-container {padding-top:1.5rem;max-width:1600px}
h1 {font-size:1.25rem!important;font-weight:600!important}
h2 {font-size:1.1rem!important}
h3 {font-size:1rem!important;font-weight:600!important}
[data-testid="stMetricLabel"] {font-size:.72rem!important}
[data-testid="stMetricValue"] {font-size:1.15rem!important;line-height:1.3!important}
[data-testid="stMetric"] {padding:.25rem .4rem!important}
[data-testid="stSidebar"] h1 {font-size:1.1rem!important}
</style>""", unsafe_allow_html=True)

def filtros_laterais():
    with st.sidebar:
        # As duas marcas ficam acima do título e não aparecem na área principal.
        nacional = ASSETS / "logo_nacional.png"
        vlatec = ASSETS / "logo_vlatecn.png"
        if nacional.is_file():
            st.image(str(nacional), width=235)
        if vlatec.is_file():
            st.image(str(vlatec), width=195)
        st.title("Motores")
        pesquisa = st.text_input("Filtrar motor", placeholder="Ex.: M07")
        encontrados = [m for m in MOTORES if pesquisa.strip().upper() in m]
        selecionar_todos = st.checkbox("Mostrar todos", value=not bool(pesquisa.strip()))
        padrao = encontrados if selecionar_todos else encontrados[:1]
        escolhidos = st.multiselect("Selecionar motores", encontrados, default=padrao)
        st.caption(f"{len(escolhidos)} motor(es) selecionado(s)")
    return escolhidos

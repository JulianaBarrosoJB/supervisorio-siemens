"""Ponto de entrada do aplicativo Streamlit."""
import streamlit as st
from supervisorio.dados import carregar_csv
from supervisorio.interface import aplicar_estilo, filtros_laterais
from supervisorio.graficos import mostrar_motor

st.set_page_config(page_title="Gráficos dos motores", layout="wide", initial_sidebar_state="expanded")
aplicar_estilo()
escolhidos = filtros_laterais()
st.title("Gráficos dos motores")

@st.fragment(run_every="2s")
def exibir():
    if not escolhidos:
        st.info("Selecione pelo menos um motor na barra lateral.")
        return
    df = carregar_csv()
    st.caption("Demonstração • dados simulados" if df is None else "Leituras do arquivo CSV local")
    for inicio in range(0, len(escolhidos), 2):
        colunas = st.columns(2, gap="medium")
        for coluna, motor in zip(colunas, escolhidos[inicio:inicio+2]):
            with coluna:
                mostrar_motor(motor, df)

exibir()

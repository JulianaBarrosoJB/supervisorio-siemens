"""Ponto de entrada do aplicativo Streamlit."""
from datetime import datetime, timezone
import streamlit as st
from supervisorio.dados import carregar_dados
from supervisorio.interface import aplicar_estilo, filtros_laterais, mostrar_cabecalho
from supervisorio.graficos import mostrar_motor

st.set_page_config(page_title="Gráficos dos motores", layout="wide", initial_sidebar_state="expanded")
aplicar_estilo()
escolhidos = filtros_laterais()
mostrar_cabecalho()

@st.fragment(run_every="1s")
def exibir():
    if not escolhidos:
        st.info("Selecione pelo menos um motor na barra lateral.")
        return
    try:
        df, fonte = carregar_dados()
    except Exception as exc:
        st.error(f"Falha ao consultar a fonte de dados: {type(exc).__name__}. Verifique a conexão e os Secrets.")
        return
    st.caption(f"Fonte: {fonte}")
    if fonte != "Demonstração":
        if df is None or df.empty:
            st.warning("Nenhuma leitura recebida do banco de dados.")
        else:
            ultima = df["timestamp"].max()
            instante = ultima.to_pydatetime() if hasattr(ultima, "to_pydatetime") else ultima
            if instante.tzinfo is None:
                from zoneinfo import ZoneInfo
                instante = instante.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
            idade = max(0, (datetime.now(timezone.utc) - instante.astimezone(timezone.utc)).total_seconds())
            horario = instante.astimezone(__import__("zoneinfo").ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
            if idade > 10:
                st.warning(f"Última leitura: {horario} (Brasília) • desatualizada há {idade:.0f} s")
            else:
                st.caption(f"Última leitura: {horario} (Brasília) • atualizada há {idade:.0f} s")
    else:
        st.caption("Demonstração • dados simulados, sem comunicação com a fábrica.")
    for inicio in range(0, len(escolhidos), 2):
        colunas = st.columns(2, gap="medium")
        for coluna, motor in zip(colunas, escolhidos[inicio:inicio+2]):
            with coluna:
                mostrar_motor(motor, df)

exibir()

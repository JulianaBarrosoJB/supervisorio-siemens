"""Supervisorio protegido: autenticação e permissões antes de consultar telemetria."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from supervisorio.acesso import exigir_login, validar_sessao, sair, autorizado, atualizar_nome_exibicao, AuthError
from supervisorio.administracao import exibir_administracao
from supervisorio.dados import carregar_dados
from supervisorio.interface import aplicar_estilo, filtros_laterais, mostrar_cabecalho, mostrar_perfil
from supervisorio.graficos import mostrar_motor

st.set_page_config(
    page_title="Monitoramento de Motores - NG Betim/MG",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo()
sessao = exigir_login()
perfil = sessao["profile"]

with st.sidebar:
    mostrar_perfil(perfil)
    with st.popover("Minha conta ▾", width="stretch"):
        st.caption(perfil.get("email", ""))
        with st.expander("Editar meu nome"):
            with st.form("editar_meu_nome"):
                nome_exibicao = st.text_input(
                    "Nome de exibição",
                    value=perfil.get("display_name") or "",
                    max_chars=80,
                    placeholder="Como deseja aparecer no supervisório",
                )
                salvar_nome = st.form_submit_button("Salvar nome", width="stretch")
            if salvar_nome:
                try:
                    atualizar_nome_exibicao(nome_exibicao)
                    st.rerun()
                except AuthError as exc:
                    st.error(str(exc))
        if st.button("Monitoramento", width="stretch", key="menu_monitoramento"):
            st.session_state["pagina_atual"] = "Monitoramento"
            st.rerun()
        if autorizado(sessao, "users.manage"):
            if st.button("Administração", width="stretch", key="menu_admin"):
                st.session_state["pagina_atual"] = "Administração"
                st.rerun()
        st.divider()
        if st.button("Sair da conta", width="stretch", key="menu_sair"):
            sair()
            st.session_state.pop("pagina_atual", None)
            st.rerun()

pagina = st.session_state.get("pagina_atual", "Monitoramento")
if pagina == "Administração" and not autorizado(sessao, "users.manage"):
    pagina = "Monitoramento"
    st.session_state["pagina_atual"] = pagina

if pagina == "Administração":
    exibir_administracao()
    st.stop()

if not autorizado(sessao, "motors.view"):
    st.error("Seu perfil não tem permissão para acessar o monitoramento.")
    st.stop()

escolhidos = filtros_laterais()
mostrar_cabecalho()


@st.fragment(run_every="1s")
def exibir():
    atual = validar_sessao()
    if not atual:
        st.rerun()
    permissoes = atual["profile"]["permissions"]
    if "motors.view" not in permissoes:
        st.warning("Permissão de monitoramento removida.")
        return
    if not escolhidos:
        st.info("Selecione pelo menos um motor na barra lateral.")
        return
    try:
        df, _ = carregar_dados(atual["access_token"])
    except Exception:
        st.error("Falha ao consultar a telemetria. Verifique a conexão e o acesso ao banco.")
        return
    if "telemetry.latest" in permissoes:
        if df is None or df.empty:
            st.warning("Nenhuma leitura recebida do PostgreSQL.")
        else:
            instante = df["timestamp"].max()
            instante = instante.to_pydatetime() if hasattr(instante, "to_pydatetime") else instante
            if instante.tzinfo is None:
                instante = instante.replace(tzinfo=timezone.utc)
            idade = max(0, (datetime.now(timezone.utc) - instante.astimezone(timezone.utc)).total_seconds())
            horario = instante.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
            if idade > 10:
                st.warning(f"Última leitura: {horario} (Brasília) • desatualizada há {idade:.0f} s")
            else:
                st.caption(f"Última leitura: {horario} (Brasília) • atualizada há {idade:.0f} s")
    if "motors.metrics" not in permissoes and "motors.charts" not in permissoes:
        st.info("Seu perfil não tem permissão para visualizar os indicadores e gráficos.")
        return
    for inicio in range(0, len(escolhidos), 2):
        colunas = st.columns(2, gap="medium")
        for coluna, motor in zip(colunas, escolhidos[inicio:inicio + 2]):
            with coluna:
                mostrar_motor(motor, df, permissoes)


exibir()

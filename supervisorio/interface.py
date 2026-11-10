"""Estilo, cabeçalho com logos e filtros laterais do supervisório."""
import base64
from io import BytesIO
from pathlib import Path
from html import escape

import streamlit as st
from PIL import Image

from .dados import MOTORES

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def aplicar_estilo():
    st.markdown("""<style>
.stApp {background-color:#ffffff;color:#243449}
[data-testid="stSidebar"] {background-color:#f7f9fc;border-right:1px solid #e4eaf1}
/* Oculta a barra de ferramentas padrão do Streamlit e seus controles. */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
footer {display:none!important}
.block-container {padding-top:1.25rem;max-width:1500px}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:1.25rem}
.login-brand {background:#103a72;
border-radius:12px 12px 0 0;padding:22px 18px;color:white;text-align:center;margin:0 -18px 16px}
.login-brand .login-title {font-size:1.15rem;font-weight:750;letter-spacing:.04em}
.login-brand .login-subtitle {font-size:.77rem;opacity:.94;margin-top:5px}
.st-key-login_panel {background:#fff;border:1px solid #e2e8f0;border-radius:14px;
box-shadow:0 10px 35px rgba(17,45,83,.08);padding:0 18px 20px;box-sizing:border-box;width:100%;min-width:0;overflow:hidden}
.st-key-login_panel [data-testid="stForm"] {margin:0;border:0;padding:0;width:100%;min-width:0;box-sizing:border-box}
.st-key-login_panel [data-testid="stTextInput"],.st-key-login_panel [data-testid="stFormSubmitButton"] {width:100%;min-width:0}
.st-key-login_panel input {box-sizing:border-box;width:100%}
.st-key-login_panel [data-testid="stMarkdownContainer"] p {margin:0}
.profile-identity {display:flex;align-items:center;gap:10px;min-width:0;padding:8px 0 3px}
.profile-avatar {height:37px;width:37px;border-radius:50%;background:#103a72;color:#fff;
display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:700;flex-shrink:0}
.profile-name {font-weight:650;font-size:.86rem;color:#243449;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.profile-role {font-size:.72rem;color:#66778a}

h1 {font-size:1.25rem!important;font-weight:600!important}
h2 {font-size:1.1rem!important}
h3 {font-size:1rem!important;font-weight:650!important;color:#173b67!important}
[data-testid="stMetric"] {background:#f8fafc;border:1px solid #e8eef5;border-radius:9px;padding:.45rem .6rem!important}
[data-testid="stMetricValue"] {white-space:normal!important;overflow-wrap:break-word!important}
[data-testid="stPlotlyChart"] {border:1px solid #eef2f6;border-radius:9px;padding:0 .25rem}
[data-testid="stMetricLabel"] {font-size:.72rem!important}
[data-testid="stMetricValue"] {font-size:1.15rem!important;line-height:1.3!important}
[data-testid="stSidebar"] h1 {font-size:1.1rem!important}
.header-ng {display:flex;align-items:center;min-height:64px;width:100%;background:#103a72;overflow:hidden;border-radius:3px;margin-bottom:1.1rem}
.header-ng-red {background:#ed1c24;min-height:64px;display:flex;align-items:center;gap:1.2rem;padding:9px 16px;flex:0 1 80%;min-width:0}
.header-ng-logos {display:flex;align-items:center;gap:12px;flex-shrink:0}
.header-ng-logos img {height:auto;max-height:34px;width:auto;max-width:118px;object-fit:contain}
.header-ng-title {font-size:clamp(10px,1.05vw,15px);font-weight:700;letter-spacing:.015em;color:white;line-height:1.25;text-align:center;flex:1;white-space:normal}
.header-ng-blue {flex:1;min-width:40px}
@media(max-width:920px) {
 .header-ng-red {gap:.6rem;padding:8px;flex-basis:88%}
 .header-ng-logos {gap:6px}
 .header-ng-logos img {max-width:64px;max-height:25px}
 .header-ng-title {font-size:10px}
 .header-ng-blue {min-width:12px}
}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _logo_base64(nome):
    caminho = ASSETS / nome
    if not caminho.is_file():
        return ""
    # Miniatura em memória: evita inserir arquivos pesados no HTML a cada atualização.
    with Image.open(caminho) as original:
        imagem = original.convert("RGBA")
        imagem.thumbnail((260, 90))
        buffer = BytesIO()
        imagem.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def mostrar_cabecalho():
    nacional = _logo_base64("logo_nacional.png")
    vlatec = _logo_base64("logo_vlatecn.png")
    logos = "".join(
        f'<img src="data:image/png;base64,{dados}" alt="{nome}">'
        for dados, nome in ((nacional, "Nacional Gás"), (vlatec, "Vlatec"))
        if dados
    )
    st.markdown(
        '<div class="header-ng">'
        '<div class="header-ng-red">'
        f'<div class="header-ng-logos">{logos}</div>'
        '<div class="header-ng-title">SISTEMA DE MONITORAMENTO DE MOTORES - NG BETIM/MG</div>'
        '</div><div class="header-ng-blue"></div></div>',
        unsafe_allow_html=True,
    )


def iniciais_usuario(perfil):
    nome = perfil.get("display_name") or perfil.get("email", "").split("@")[0]
    partes = [p for p in nome.replace(".", " ").replace("_", " ").split() if p]
    return (partes[0][0] + partes[-1][0]).upper() if len(partes) > 1 else (nome[:2].upper() or "NG")


def mostrar_perfil(perfil):
    """Cartão compacto com avatar; navegação fica no menu suspenso."""
    nome = perfil.get("display_name") or perfil.get("email", "Usuário").split("@")[0].replace(".", " ").title()
    nivel = perfil.get("role_key", "visualizador").capitalize()
    st.markdown(
        '<div class="profile-identity">'
        f'<div class="profile-avatar">{escape(iniciais_usuario(perfil))}</div>'
        '<div style="min-width:0">'
        f'<div class="profile-name">{escape(nome)}</div>'
        f'<div class="profile-role">{escape(nivel)}</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def filtros_laterais():
    with st.sidebar:
        st.title("Motores")
        pesquisa = st.text_input("Filtrar motor", placeholder="Ex.: M07")
        encontrados = [m for m in MOTORES if pesquisa.strip().upper() in m]
        selecionar_todos = st.checkbox("Mostrar todos", value=False)
        padrao = encontrados if selecionar_todos else encontrados[:2]
        escolhidos = st.multiselect("Selecionar motores", encontrados, default=padrao)
        st.caption(f"{len(escolhidos)} motor(es) selecionado(s)")
    return escolhidos

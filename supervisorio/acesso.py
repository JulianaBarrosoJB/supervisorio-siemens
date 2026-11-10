"""Autenticação Supabase Auth e autorização RBAC em Streamlit.

Nenhuma senha de usuário é guardada na aplicação. Tokens são mantidos somente
na sessão de navegador (st.session_state) e descartados ao recarregar a página.
"""
import time

import requests
import streamlit as st

IDLE_SECONDS = 30 * 60
ABSOLUTE_SECONDS = 8 * 60 * 60
RECHECK_SECONDS = 30


class AuthError(Exception):
    pass


def config(nome):
    try:
        return st.secrets.get(nome, "")
    except (FileNotFoundError, RuntimeError):
        return ""


def api(method, path, token=None, data=None, params=None, admin=False):
    url = config("SUPABASE_URL").rstrip("/")
    key = config("SUPABASE_SERVICE_ROLE_KEY") if admin else config("SUPABASE_ANON_KEY")
    if not url or not key:
        raise AuthError("Configure SUPABASE_URL e as chaves nos Secrets do Streamlit.")
    headers = {"apikey": key, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif admin and not key.startswith("sb_secret_"):
        # Chaves novas sb_secret_ vão apenas no cabeçalho apikey;
        # chaves legacy service_role são JWTs e podem ser Bearer.
        headers["Authorization"] = f"Bearer {key}"
    try:
        response = requests.request(
            method, url + path, headers=headers, json=data, params=params, timeout=12
        )
    except requests.RequestException as exc:
        raise AuthError("Não foi possível alcançar o servidor de autenticação.") from exc
    if not response.ok:
        if response.status_code in (400, 401, 403):
            raise AuthError("Credenciais inválidas, sessão expirada ou acesso não autorizado.")
        raise AuthError(f"Falha no Supabase (HTTP {response.status_code}).")
    if not response.content:
        return None
    return response.json()


def perfil(token, usuario_id):
    registros = api(
        "GET", "/rest/v1/app_profiles", token=token,
        params={"select": "id,email,display_name,role_key,enabled", "id": f"eq.{usuario_id}", "limit": 1}
    )
    if not registros or not registros[0]["enabled"]:
        raise AuthError("Usuário sem autorização para acessar o supervisório.")
    info = registros[0]
    regras = api(
        "GET", "/rest/v1/app_role_permissions", token=token,
        params={"select": "permission_key", "role_key": f"eq.{info['role_key']}"}
    )
    info["permissions"] = {item["permission_key"] for item in regras}
    return info


def sair():
    sessao = st.session_state.pop("_auth", None)
    if sessao:
        try:
            api("POST", "/auth/v1/logout", token=sessao["access_token"])
        except AuthError:
            pass
    st.session_state.pop("_auth", None)


def entrar(email, senha):
    info = api(
        "POST", "/auth/v1/token?grant_type=password",
        data={"email": email.strip().lower(), "password": senha}
    )
    token = info["access_token"]
    usuario = api("GET", "/auth/v1/user", token=token)
    acesso = perfil(token, usuario["id"])
    instante = time.time()
    st.session_state["_auth"] = {
        "access_token": token,
        "refresh_token": info["refresh_token"],
        "expires_at": instante + int(info["expires_in"]),
        "login_at": instante,
        "last_action_at": instante,
        "verified_at": instante,
        "user_id": usuario["id"],
        "profile": acesso,
    }


def validar_sessao(force=False):
    sessao = st.session_state.get("_auth")
    if not sessao:
        return None
    instante = time.time()
    if (instante - sessao["last_action_at"] > IDLE_SECONDS
            or instante - sessao["login_at"] > ABSOLUTE_SECONDS):
        sair()
        return None
    try:
        if instante >= sessao["expires_at"] - 120:
            renovada = api(
                "POST", "/auth/v1/token?grant_type=refresh_token",
                data={"refresh_token": sessao["refresh_token"]}
            )
            sessao.update(
                access_token=renovada["access_token"],
                refresh_token=renovada["refresh_token"],
                expires_at=time.time() + int(renovada["expires_in"])
            )
            force = True
        if force or instante - sessao["verified_at"] > RECHECK_SECONDS:
            usuario = api("GET", "/auth/v1/user", token=sessao["access_token"])
            if usuario["id"] != sessao["user_id"]:
                raise AuthError("Identidade da sessão inválida.")
            sessao["profile"] = perfil(sessao["access_token"], sessao["user_id"])
            sessao["verified_at"] = instante
    except (AuthError, KeyError, TypeError):
        sair()
        return None
    return sessao


def exigir_login():
    if not config("SUPABASE_URL") or not config("SUPABASE_ANON_KEY"):
        st.warning("Acesso temporariamente indisponível. Entre em contato com o administrador.")
        st.stop()
    sessao = validar_sessao()
    if sessao:
        # Atualiza a atividade apenas no rerun completo provocado pelo usuário.
        # O fragmento de gráficos (1 s) NÃO atualiza esse cronômetro.
        sessao["last_action_at"] = time.time()
        return sessao
    from .interface import _logo_base64
    col_esquerda, col_centro, col_direita = st.columns([1, 1.15, 1])
    with col_centro:
        with st.container(key="login_panel"):
            nacional = _logo_base64("logo_nacional.png")
            logo = (
                f'<img src="data:image/png;base64,{nacional}" '
                'alt="Nacional Gás" style="max-height:32px;max-width:145px;object-fit:contain;margin-bottom:10px">'
                if nacional else ""
            )
            st.markdown(
                '<div class="login-brand">'
                + logo
                + '<div class="login-title">ACESSO AO SUPERVISÓRIO</div>'
                + '<div class="login-subtitle">Sistema de Monitoramento de Motores NG Betim/MG</div>'
                + '</div>',
                unsafe_allow_html=True,
            )
            with st.form("login", clear_on_submit=True):
                email = st.text_input("E-mail", placeholder="Digite seu e-mail")
                senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                enviado = st.form_submit_button("Entrar", type="primary", width="stretch")
            if enviado:
                if not email or not senha:
                    st.warning("Informe e-mail e senha.")
                else:
                    try:
                        entrar(email, senha)
                        st.rerun()
                    except (AuthError, KeyError):
                        st.error("Não foi possível entrar. Verifique suas credenciais.")
    st.stop()


def autorizado(sessao, permissao):
    return permissao in sessao["profile"]["permissions"]

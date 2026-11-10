"""Administração de usuários e regras, executada apenas no servidor Streamlit."""
import re

import streamlit as st

from .acesso import AuthError, api, autorizado, validar_sessao


def _admin_api(method, path, params=None, data=None):
    # Confira a identidade e permissões no Supabase ANTES de cada operação sensível.
    sessao = validar_sessao(force=True)
    if not sessao or not autorizado(sessao, "users.manage"):
        raise AuthError("Acesso administrativo negado.")
    return api(method, path, params=params, data=data, admin=True)


def exibir_administracao():
    sessao = validar_sessao(force=True)
    if not sessao or not autorizado(sessao, "users.manage"):
        st.error("Acesso restrito à administração.")
        return
    st.subheader("Administração de acessos")
    if not st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", ""):
        st.warning("Configure SUPABASE_SERVICE_ROLE_KEY exclusivamente nos Secrets do aplicativo.")
        return
    try:
        roles = _admin_api("GET", "/rest/v1/app_roles", params={"select": "role_key,label", "order": "label.asc"})
        users = _admin_api("GET", "/rest/v1/app_profiles", params={
            "select": "id,email,display_name,role_key,enabled", "order": "email.asc"
        })
    except AuthError as exc:
        st.error(str(exc))
        return

    aba_usuarios, aba_regras = st.tabs(["Usuários", "Permissões por perfil"])

    with aba_usuarios:
        st.caption("Usuários cadastrados no Supabase Auth. As senhas não são armazenadas no Streamlit.")
        if users:
            st.dataframe([{
                "E-mail": u["email"], "Nome": u["display_name"],
                "Perfil": u["role_key"], "Habilitado": u["enabled"]
            } for u in users], hide_index=True, width="stretch")
        with st.expander("Cadastrar novo usuário"):
            with st.form("novo_usuario", clear_on_submit=True):
                email = st.text_input("E-mail do usuário")
                nome = st.text_input("Nome")
                senha = st.text_input("Senha inicial (mínimo 12 caracteres)", type="password")
                role = st.selectbox("Perfil inicial", [r["role_key"] for r in roles])
                enviar = st.form_submit_button("Criar usuário")
            if enviar:
                if "@" not in email or len(senha) < 12:
                    st.error("Informe um e-mail válido e uma senha de pelo menos 12 caracteres.")
                else:
                    try:
                        criado = _admin_api("POST", "/auth/v1/admin/users", data={
                            "email": email.strip().lower(), "password": senha,
                            "email_confirm": True, "user_metadata": {"full_name": nome}
                        })
                        _admin_api("PATCH", "/rest/v1/app_profiles", params={
                            "id": "eq." + criado["id"]
                        }, data={"role_key": role, "enabled": True, "display_name": nome})
                        st.success("Usuário criado. Compartilhe a senha inicial por canal seguro.")
                        st.rerun()
                    except (AuthError, KeyError) as exc:
                        st.error(f"Cadastro incompleto: {exc}. Verifique o Supabase Auth.")

        outros = [u for u in users if u["id"] != sessao["user_id"]]
        if outros:
            with st.form("alterar_usuario"):
                alvo = st.selectbox("Alterar usuário", outros, format_func=lambda u: u["email"])
                novo_role = st.selectbox(
                    "Novo perfil", [r["role_key"] for r in roles],
                    index=next((i for i, r in enumerate(roles) if r["role_key"] == alvo["role_key"]), 0)
                )
                habilitado = st.checkbox("Acesso habilitado", value=alvo["enabled"])
                salvar = st.form_submit_button("Salvar acesso")
            if salvar:
                try:
                    _admin_api("PATCH", "/rest/v1/app_profiles", params={
                        "id": "eq." + alvo["id"]
                    }, data={"role_key": novo_role, "enabled": habilitado})
                    st.success("Acesso atualizado.")
                    st.rerun()
                except AuthError as exc:
                    st.error(str(exc))
        else:
            st.info("Cadastre outro usuário para gerenciar acessos. Seu próprio perfil não pode ser desativado aqui.")

    with aba_regras:
        if not autorizado(sessao, "roles.manage"):
            st.info("Seu perfil não permite gerenciar permissões.")
            return
        st.caption("O perfil administrador tem permissão integral e não pode ser reduzido por esta tela.")
        try:
            permissoes = _admin_api("GET", "/rest/v1/app_permissions", params={"select": "permission_key,label", "order": "permission_key.asc"})
            vinculos = _admin_api("GET", "/rest/v1/app_role_permissions", params={"select": "role_key,permission_key"})
        except AuthError as exc:
            st.error(str(exc))
            return
        editaveis = [r for r in roles if r["role_key"] != "admin"]
        if editaveis:
            selecionado = st.selectbox("Perfil para configurar", editaveis, format_func=lambda r: r["label"])
            atuais = {x["permission_key"] for x in vinculos if x["role_key"] == selecionado["role_key"]}
            with st.form("permissoes_role"):
                marcados = []
                for p in permissoes:
                    if p["permission_key"] in ("users.manage", "roles.manage"):
                        continue  # Administração sempre reservada ao administrador.
                    if st.checkbox(p["label"], value=p["permission_key"] in atuais, key="perm_" + p["permission_key"]):
                        marcados.append(p["permission_key"])
                confirmar = st.form_submit_button("Salvar permissões do perfil")
            if confirmar:
                try:
                    _admin_api("DELETE", "/rest/v1/app_role_permissions", params={"role_key": "eq." + selecionado["role_key"]})
                    if marcados:
                        _admin_api("POST", "/rest/v1/app_role_permissions", data=[
                            {"role_key": selecionado["role_key"], "permission_key": chave} for chave in marcados
                        ])
                    st.success("Permissões atualizadas. Sessões recebem novas regras em até 30 segundos.")
                    st.rerun()
                except AuthError as exc:
                    st.error("Falha ao gravar permissões: " + str(exc))
        with st.expander("Criar novo perfil"):
            with st.form("criar_role"):
                slug = st.text_input("Identificador (letras minúsculas e _)", placeholder="manutencao")
                rotulo = st.text_input("Nome do perfil", placeholder="Manutenção")
                criar = st.form_submit_button("Criar perfil")
            if criar:
                if not re.fullmatch(r"[a-z][a-z0-9_]{2,30}", slug) or not rotulo.strip():
                    st.error("Informe um identificador válido e nome.")
                else:
                    try:
                        _admin_api("POST", "/rest/v1/app_roles", data={
                            "role_key": slug, "label": rotulo.strip()
                        })
                        st.success("Perfil criado sem permissões. Configure-as acima.")
                        st.rerun()
                    except AuthError as exc:
                        st.error(str(exc))

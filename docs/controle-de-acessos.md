# Controle de acessos — implantação (Supabase Auth + Streamlit)

> Projeto: NG BETIM REMOTO. Execute no Supabase antes de atualizar o app em produção.

## Como instalar
1. No Supabase, **SQL Editor**, execute \`telemetria/acessos_supabase.sql\`. Ele cria roles, permissões, perfis e RLS para \`motor_snapshots\`. Não altera nem apaga as leituras já existentes.
2. Em **Authentication → Users**, crie sua própria conta (e-mail/senha) pelo Dashboard. A função SQL cria o perfil **desabilitado**.
3. Copie o **UUID do usuário** nessa página e execute no SQL Editor (substituindo o UUID pelo verdadeiro):

\`\`\`sql
UPDATE public.app_profiles
SET role_key = 'admin', enabled = true
WHERE id = 'COLE-AQUI-SEU-UUID';
\`\`\`

Confira que retornou \`UPDATE 1\`. Se retornar \`UPDATE 0\`, o UUID está errado ou o usuário não foi criado.
4. Em **Project Settings → API Keys**, obtenha **publishable key** (\`sb_publishable_...\`) e **secret key** (\`sb_secret_...\`). Use somente a secret key no backend Streamlit, em Secrets. Nunca comite essas chaves no GitHub.
5. No Streamlit Community Cloud, aplicativo vinculado à branch \`develop\`, configure **App settings → Secrets**:

\`\`\`toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_..."
SUPABASE_SERVICE_ROLE_KEY = "sb_secret_..."
TELEMETRIA_STATION_ID = "betim"
\`\`\`

6. Reinicie o app. A primeira tela passa a ser **login por e-mail e senha**. Faça login como administradora, abra **Administração** para criar usuários, ativar/desativar acessos, atribuir perfis e configurar permissões.

## Perfis e permissões
- \`admin\`: todas as áreas, gerencia usuários e perfis (permissões não editáveis pela interface).
- \`gerente\`, \`operador\`, \`visualizador\`: inicialmente enxergam os mesmos motores, indicadores, gráficos e última leitura.
- Novos perfis podem ser criados na interface, inicialmente sem permissões (deny by default).
- Permissões disponíveis: \`motors.view\`, \`motors.metrics\`, \`motors.charts\`, \`telemetry.latest\`, \`users.manage\`, \`roles.manage\`.
- Só a conta administradora pode administrar acessos. Alterações são verificadas novamente no servidor no máximo a cada 30 segundos; leituras remotas também são protegidas por RLS.
- Usuários precisam existir no Supabase Auth e ter perfil habilitado para entrar. Contas criadas fora do painel ficam desabilitadas até liberação administrativa.

## Sessões
- Login obrigatório a cada nova sessão do navegador (recarregar a página também exige novo login).
- JWT Supabase renovado automaticamente antes de expirar; sessão expira após 30 minutos sem interação ou 8 horas desde o login, o que ocorrer primeiro.
- O plano Supabase Free não fornece todos os controles de duração de sessão no painel; estes limites são implementados na aplicação. Ajuste a expiração do JWT no Supabase conforme necessário.
- Senhas ficam no Supabase Auth, nunca no banco de aplicação nem em arquivos Streamlit.
- Segredos administrativos \`SUPABASE_SERVICE_ROLE_KEY\` nunca são expostos no cliente.
- Se você pretende exigir autenticação forte, configure MFA e/ou regras adicionais no Supabase (a implementação inicial usa e-mail e senha).
- Administradores devem usar senha longa; o cadastro exige mínimo de 12 caracteres.

## Dados da fábrica e limite de 30 dias
O coletor Python que lê o CLP continuará escrevendo diretamente no PostgreSQL pela sua conexão privada \`DATABASE_URL\`; o Streamlit apenas lê com JWT limitado por RLS. A rotina \`limpeza_motores_diaria\` no Supabase não é afetada. O backup de 30 dias permanece no SQLite local.

## Importante antes de liberar usuários externos
- **Acesso precisa ser testado** com uma conta admin e uma conta operacional. Confirmar que conta desabilitada e usuário anônimo não acessam \`motor_snapshots\`.
- Testar criar usuário e trocar perfis na aba Administração. Se a API Auth Admin rejeitar uma chave nova, verifique a configuração das API keys e logs do Supabase; não desabilite RLS para contornar o problema.
- Retire credenciais \`DATABASE_URL\` antigas dos Secrets do Streamlit quando elas não forem mais usadas (o coletor ainda precisa de suas próprias credenciais).
- Não faça deploy em produção antes de criar a conta admin: a nova versão bloqueia o acesso por padrão.

# Agente local SQLite -> PostgreSQL

Este agente **não acessa o CLP**: acompanha o CSV já gravado pelo leitor Python existente, sem criar conexão Snap7 adicional.

## 1. Banco PostgreSQL
Execute `telemetria/schema.sql` uma única vez no PostgreSQL. Recomenda-se criar usuário exclusivo com INSERT na tabela para o PC e outro usuário somente SELECT para o Streamlit. Use TLS (`sslmode=require` ou `verify-full` com certificado).

## 2. PC Windows da fábrica
Instale Python 3.10+ e execute:

```powershell
py -m pip install "psycopg[binary]>=3.2,<4"
$env:MOTORES_CSV_PATH="C:\\caminho\\dados_motores.csv"
$env:TELEMETRIA_SQLITE_PATH="C:\\telemetria\\fila.sqlite3"
$env:TELEMETRIA_STATION_ID="betim"
$env:TELEMETRIA_TZ="America/Sao_Paulo"
$env:DATABASE_URL="postgresql://usuario:senha@servidor:5432/banco?sslmode=require"
py -m telemetria.agent
```

**Não salve DATABASE_URL no GitHub, scripts versionados ou capturas de tela.** Prefira segredo gerenciado no Windows. O SQLite é a fila local durável. O agente lê novas linhas do CSV e envia em lotes; quando a internet falha, guarda pendências e reenvia depois. Só marca como enviado após confirmação do commit remoto. Eventos enviados são retidos localmente por 7 dias (configurável).

## 3. Streamlit
Defina `DATABASE_URL` e `TELEMETRIA_STATION_ID="betim"` nos Secrets do aplicativo Streamlit, com credenciais **somente leitura**. O app consulta os últimos registros do PostgreSQL; não conecta ao CLP.

## Observações
- Uma linha de CSV equivale a um snapshot com os 87 motores em JSONB, reduzindo o número de linhas no PostgreSQL.
- O tamanho da fila cresce quando a internet cai: monitore espaço em disco.
- A transmissão usa HTTPS/TLS PostgreSQL, não Node-RED nesta etapa.
- Não publique credenciais, IPs industriais ou arquivos de dados reais.

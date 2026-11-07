# Arquitetura de telemetria — proposta (branch develop)

## Fluxo
CLP Siemens -> leitor Python no PC -> SQLite (fila durável) -> Node-RED (envio HTTPS) -> API autenticada -> PostgreSQL externo -> Streamlit.

O leitor Python existente não deve ser substituído antes de validar a integração. O Node-RED não precisa abrir uma segunda conexão com o CLP.

## Persistência e confirmação
- Registrar `event_id` UUID, `motor_id`, `captured_at_utc`, `corrente_a`, `velocidade_pct`, `sent_at_utc` opcional.
- Gravar localmente em transação antes de tentar envio.
- Enviar em lotes por HTTPS com autenticação; o backend faz UPSERT por `event_id` e confirma IDs persistidos.
- Marcar como enviado somente após confirmação; retentar com backoff exponencial.
- Limpar somente eventos confirmados e após período de retenção definido; manter backup local quando necessário.
- Limitar tamanho da fila e monitorar espaço livre no disco.
- Não armazenar segredos no repositório.

## Tela
- Consultar dados externos em intervalo configurável (alvo: 1 s, sujeito à latência/cotas).
- Mostrar timestamp real da última amostra recebida, com timezone explícito.
- Se idade da amostra ultrapassar 10 s, exibir estado desatualizado.
- Nunca substituir falhas de comunicação por dados simulados.
- Status ligado/desligado somente após mapeamento real no CLP.

## Pendências
- Escolher provedor PostgreSQL/API e política de autenticação.
- Confirmar fuso horário e frequência real do logger.
- Validar volume (87 motores x 1 Hz), custo, retenção e limites do serviço.
- Definir política de retenção/limpeza local e recuperação após falha.
- Implementar fila SQLite e fluxo Node-RED em etapa separada, com teste offline/online.

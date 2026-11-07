# Supervisório Siemens

Dashboard web Streamlit para monitoramento de 87 motores (M01–M85, M102, M103). Exibe tendência de corrente e velocidade, seleção lateral, atualização visual a cada 2 segundos.

## Publicação

No Streamlit Community Cloud, selecione este repositório, branch `main`, arquivo `streamlit_app.py`. A implantação na nuvem exibe **dados simulados** enquanto não houver uma integração segura com a coleta da fábrica.

## Execução local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Para dados reais, disponibilize o CSV gerado pelo leitor já existente como `dados_motores.csv` na pasta de execução ou defina a variável de ambiente `MOTORES_CSV_PATH`. O arquivo deve ter `timestamp`, colunas `M01_corrente`, `M01_velocidade` etc., separador `;` e decimal `,`.

**Segurança:** não publique endereços industriais, credenciais, CSVs reais ou portas do CLP. Não exponha o PLC diretamente à internet. Status de falha e ligado/desligado ainda não estão mapeados. Este aplicativo não envia comandos ao CLP.

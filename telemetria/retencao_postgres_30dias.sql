-- PostgreSQL/Supabase: manter somente os dados do dia atual.
-- Executar no SQL Editor do projeto, uma vez.
-- A limpeza ocorre a cada dia as 03:00 UTC = 00:00 America/Sao_Paulo.
-- PostgreSQL e cache de visualizacao nao sao backup. O historico de 30 dias fica no SQLite local.

CREATE EXTENSION IF NOT EXISTS pg_cron;

DO $$
DECLARE tarefa RECORD;
BEGIN
  FOR tarefa IN
    SELECT jobid FROM cron.job
    WHERE jobname IN ('limpeza_motores_30dias', 'limpeza_motor_snapshots_30d', 'limpeza_motores_diaria')
  LOOP
    PERFORM cron.unschedule(tarefa.jobid);
  END LOOP;
END $$;

SELECT cron.schedule(
  'limpeza_motores_diaria',
  '0 3 * * *',
  $$TRUNCATE TABLE public.motor_snapshots;$$
);

-- Confirmacao:
-- SELECT jobid, jobname, schedule, active FROM cron.job WHERE jobname = 'limpeza_motores_diaria';

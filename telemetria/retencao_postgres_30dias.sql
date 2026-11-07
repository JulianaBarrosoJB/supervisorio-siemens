-- Executar uma vez no SQL Editor do Supabase/PostgreSQL.
-- Requer a extensão pg_cron disponível e habilitada no projeto.
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Recria o job com nome estável (sem acumular agendamentos).
DO $$
DECLARE existing_job bigint;
BEGIN
  SELECT jobid INTO existing_job FROM cron.job WHERE jobname = 'limpeza_motor_snapshots_30d';
  IF existing_job IS NOT NULL THEN
    PERFORM cron.unschedule(existing_job);
  END IF;
END $$;

-- Executa diariamente às 03:00 UTC. Mantém apenas os últimos 30 dias.
SELECT cron.schedule(
  'limpeza_motor_snapshots_30d',
  '0 3 * * *',
  $$DELETE FROM public.motor_snapshots
    WHERE captured_at < NOW() - INTERVAL '30 days'$$
);

-- Consulta para verificar a rotina:
-- SELECT jobid, jobname, schedule, command FROM cron.job
-- WHERE jobname = 'limpeza_motor_snapshots_30d';

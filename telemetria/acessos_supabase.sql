-- Execute UMA VEZ no SQL Editor do projeto Supabase.
-- Autenticação via Supabase Auth; permissões são dados de aplicação, não logins PostgreSQL.
CREATE TABLE IF NOT EXISTS public.app_roles (
  role_key text PRIMARY KEY,
  label text NOT NULL,
  description text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS public.app_permissions (
  permission_key text PRIMARY KEY,
  label text NOT NULL
);
CREATE TABLE IF NOT EXISTS public.app_role_permissions (
  role_key text NOT NULL REFERENCES public.app_roles(role_key) ON DELETE CASCADE,
  permission_key text NOT NULL REFERENCES public.app_permissions(permission_key) ON DELETE CASCADE,
  PRIMARY KEY (role_key, permission_key)
);
CREATE TABLE IF NOT EXISTS public.app_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL,
  display_name text NOT NULL DEFAULT '',
  role_key text NOT NULL DEFAULT 'visualizador' REFERENCES public.app_roles(role_key),
  enabled boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_app_profiles_role ON public.app_profiles(role_key);

INSERT INTO public.app_roles(role_key,label,description) VALUES
  ('admin','Administrador','Controle integral do supervisório'),
  ('gerente','Gerente','Visão gerencial'),
  ('operador','Operador','Acompanhamento operacional'),
  ('visualizador','Visualizador','Somente consulta')
ON CONFLICT (role_key) DO UPDATE SET label=EXCLUDED.label,description=EXCLUDED.description;
INSERT INTO public.app_permissions(permission_key,label) VALUES
  ('motors.view','Visualizar motores'),
  ('motors.metrics','Ver indicadores de motores'),
  ('motors.charts','Ver gráficos de corrente'),
  ('telemetry.latest','Ver data e qualidade da última leitura'),
  ('users.manage','Gerenciar usuários'),
  ('roles.manage','Gerenciar permissões dos perfis')
ON CONFLICT (permission_key) DO UPDATE SET label=EXCLUDED.label;

INSERT INTO public.app_role_permissions(role_key,permission_key)
SELECT r.role_key,p.permission_key
FROM public.app_roles r CROSS JOIN public.app_permissions p
WHERE p.permission_key IN ('motors.view','motors.metrics','motors.charts','telemetry.latest')
  OR r.role_key='admin'
ON CONFLICT DO NOTHING;

-- Cria perfil DESABILITADO por padrão para qualquer conta Auth nova.
CREATE OR REPLACE FUNCTION public.initialize_app_profile()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=''
AS $$
BEGIN
  INSERT INTO public.app_profiles(id,email,display_name,role_key,enabled)
  VALUES (NEW.id,COALESCE(NEW.email,''),COALESCE(NEW.raw_user_meta_data->>'full_name',''),
          'visualizador',false)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS trg_initialize_app_profile ON auth.users;
CREATE TRIGGER trg_initialize_app_profile
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.initialize_app_profile();

-- Se contas Auth já existirem, cria perfis desabilitados.
INSERT INTO public.app_profiles(id,email,display_name,role_key,enabled)
SELECT id,COALESCE(email,''),COALESCE(raw_user_meta_data->>'full_name',''),'visualizador',false
FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- Nunca exponha a tabela de telemetria para visitantes anônimos.
ALTER TABLE public.motor_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "motors_authenticated_view" ON public.motor_snapshots;
CREATE POLICY "motors_authenticated_view" ON public.motor_snapshots FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.app_profiles u
    JOIN public.app_role_permissions rp ON rp.role_key=u.role_key
    WHERE u.id=(SELECT auth.uid()) AND u.enabled AND rp.permission_key='motors.view'
  )
);
DROP POLICY IF EXISTS "app_profiles_self_read" ON public.app_profiles;
CREATE POLICY "app_profiles_self_read" ON public.app_profiles FOR SELECT TO authenticated
USING (id=(SELECT auth.uid()));
DROP POLICY IF EXISTS "app_roles_read" ON public.app_roles;
CREATE POLICY "app_roles_read" ON public.app_roles FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS "app_permissions_read" ON public.app_permissions;
CREATE POLICY "app_permissions_read" ON public.app_permissions FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS "app_role_permissions_read" ON public.app_role_permissions;
CREATE POLICY "app_role_permissions_read" ON public.app_role_permissions FOR SELECT TO authenticated USING (true);

-- Restringir privilégios da Data API mesmo que políticas adicionais sejam criadas.
REVOKE ALL ON public.motor_snapshots FROM anon, authenticated;
GRANT SELECT ON public.motor_snapshots TO authenticated;
REVOKE ALL ON public.app_profiles FROM anon, authenticated;
GRANT SELECT ON public.app_profiles TO authenticated;
REVOKE ALL ON public.app_roles,public.app_permissions,public.app_role_permissions FROM anon,authenticated;
GRANT SELECT ON public.app_roles,public.app_permissions,public.app_role_permissions TO authenticated;

-- A coleta Siemens grava via conexão privada PostgreSQL (DATABASE_URL).
-- O Streamlit lê exclusivamente pela API com JWT do usuário, sujeito às políticas acima.
-- IMPORTANTE: crie o primeiro usuário em Authentication > Users no Supabase;
-- depois promova SOMENTE seu usuário pelo ID (UUID), sem publicar email no repositório:
-- UPDATE public.app_profiles SET role_key='admin',enabled=true
-- WHERE id='COLE_AQUI_O_UUID_DO_SEU_USUARIO';

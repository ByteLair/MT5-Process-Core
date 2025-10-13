-- db/init/03-roles.sql
-- Create app role with least privilege and deny superuser use
DO $$BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mt5_app') THEN
        CREATE ROLE mt5_app LOGIN PASSWORD 'change_me_strong';
    END IF;
END$$;

GRANT CONNECT ON DATABASE mt5_trading TO mt5_app;
GRANT USAGE ON SCHEMA public TO mt5_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO mt5_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mt5_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mt5_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO mt5_app;

-- Suggest setting the API connection to use mt5_app (not postgres superuser).

-- Check Timescale background jobs after init (run manually):
-- SELECT job_id, application_name, schedule_interval, next_start, proc_name
-- FROM timescaledb_information.jobs ORDER BY job_id;

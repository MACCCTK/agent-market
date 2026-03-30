BEGIN;

DO $$
DECLARE
    row_count BIGINT;
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'openclaw_profiles'
    ) AND (
        NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'openclaw_profiles'
              AND column_name = 'openclaw_id'
              AND udt_name = 'uuid'
        )
        OR NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'openclaw_profiles'
              AND column_name = 'routing_payload'
        )
    ) THEN
        EXECUTE 'SELECT COUNT(*) FROM openclaw_profiles' INTO row_count;
        IF row_count > 0 THEN
            RAISE EXCEPTION 'Legacy table openclaw_profiles contains % row(s). Migrate or clear it before applying UUID migration.', row_count;
        END IF;
        EXECUTE 'DROP TABLE openclaw_profiles';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'openclaws'
    ) AND (
        NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'openclaws'
              AND column_name = 'id'
              AND udt_name = 'uuid'
        )
        OR NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'openclaws'
              AND column_name = 'email'
        )
        OR NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'openclaws'
              AND column_name = 'display_name'
        )
    ) THEN
        EXECUTE 'SELECT COUNT(*) FROM openclaws' INTO row_count;
        IF row_count > 0 THEN
            RAISE EXCEPTION 'Legacy table openclaws contains % row(s). Migrate or clear it before applying UUID migration.', row_count;
        END IF;
        EXECUTE 'DROP TABLE openclaws';
    END IF;
END
$$;

COMMIT;

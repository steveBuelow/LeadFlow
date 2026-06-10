CREATE TABLE IF NOT EXISTS users (
    id           SERIAL PRIMARY KEY,
    username     VARCHAR(32)  NOT NULL,
    email        VARCHAR(254) NOT NULL,
    password     VARCHAR(255) NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login   TIMESTAMPTZ,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email    UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS leads (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name          VARCHAR(120) NOT NULL,
    company       VARCHAR(120),
    email         VARCHAR(254),
    phone         VARCHAR(30),
    source        VARCHAR(80)  NOT NULL DEFAULT 'Manual',
    status        VARCHAR(20)  NOT NULL DEFAULT 'New'
                      CHECK (status IN ('New','Contacted','Qualified','Proposal','Closed-Won','Closed-Lost')),
    priority      VARCHAR(10)  NOT NULL DEFAULT 'medium'
                      CHECK (priority IN ('low','medium','high')),
    value         NUMERIC(12,2),
    message       TEXT,
    notes         TEXT,
    next_followup DATE,
    ai_score      SMALLINT CHECK (ai_score BETWEEN 0 AND 100),
    ai_summary    TEXT,
    ai_category   VARCHAR(60),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_user_id    ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_status     ON leads(user_id, status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_followup   ON leads(user_id, next_followup)
    WHERE next_followup IS NOT NULL;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_leads_updated_at ON leads;
CREATE TRIGGER trg_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Password Reset Tokens ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS password_resets (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64)  NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ  NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pw_resets_token ON password_resets(token_hash);
CREATE INDEX IF NOT EXISTS idx_pw_resets_user  ON password_resets(user_id);

-- ── Safe column migrations ────────────────────────────────────────────────
-- These are no-ops if the column already exists. They fix production databases
-- that were created with an older schema missing these columns.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS company       VARCHAR(120);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email         VARCHAR(254);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS phone         VARCHAR(30);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS source        VARCHAR(80)  NOT NULL DEFAULT 'Manual';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS priority      VARCHAR(10)  NOT NULL DEFAULT 'medium';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS value         NUMERIC(12,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS message       TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS notes         TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS next_followup DATE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_score      SMALLINT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_summary    TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_category   VARCHAR(60);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW();

-- ── Sequence guard ────────────────────────────────────────────────────────
-- CREATE TABLE IF NOT EXISTS is a no-op when the table already exists, so
-- SERIAL sequences are never created on pre-existing tables. This block
-- detects and repairs any id column that has no DEFAULT (i.e. no sequence).
DO $$
DECLARE
  tbl TEXT;
  seq TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY['users', 'leads', 'password_resets'] LOOP
    IF (SELECT column_default FROM information_schema.columns
        WHERE table_schema = 'public'
        AND   table_name   = tbl
        AND   column_name  = 'id') IS NULL THEN

      seq := 'public.' || tbl || '_id_seq';
      EXECUTE format('CREATE SEQUENCE IF NOT EXISTS %s', seq);
      EXECUTE format(
        'ALTER TABLE public.%I ALTER COLUMN id SET DEFAULT nextval(%L::regclass)',
        tbl, seq
      );
      EXECUTE format('ALTER SEQUENCE %s OWNED BY public.%I.id', seq, tbl);
      EXECUTE format(
        'SELECT setval(%L, COALESCE((SELECT MAX(id) FROM public.%I), 0) + 1, false)',
        seq, tbl
      );
      RAISE NOTICE 'Attached missing sequence % to %.id', seq, tbl;
    END IF;
  END LOOP;
END $$;

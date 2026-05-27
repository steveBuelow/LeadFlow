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

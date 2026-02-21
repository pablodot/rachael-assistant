-- Rachael – memory-db schema
-- PostgreSQL 16
-- Sección 9 de SPEC.md

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- ─────────────────────────────────────────
-- sessions
-- Una sesión agrupa una conversación completa con el usuario.
-- ─────────────────────────────────────────
CREATE TABLE sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT,
    status      TEXT        NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'closed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────
-- messages
-- Mensajes individuales dentro de una sesión.
-- ─────────────────────────────────────────
CREATE TABLE messages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT        NOT NULL
                            CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content     TEXT        NOT NULL,
    tokens      INTEGER,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- ─────────────────────────────────────────
-- tasks
-- Plan de ejecución generado por el LLM.
-- ─────────────────────────────────────────
CREATE TABLE tasks (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID        REFERENCES sessions(id) ON DELETE SET NULL,
    goal        TEXT        NOT NULL,
    plan_json   JSONB,
    status      TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN (
                                'pending', 'running', 'waiting_approval',
                                'done', 'failed', 'cancelled'
                            )),
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_session_id ON tasks(session_id);
CREATE INDEX idx_tasks_status    ON tasks(status);

-- ─────────────────────────────────────────
-- approvals
-- Pasos del plan que requieren confirmación explícita del usuario.
-- ─────────────────────────────────────────
CREATE TABLE approvals (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID        NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_index  INTEGER     NOT NULL,
    ok_prompt   TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_approvals_task_id ON approvals(task_id);
CREATE INDEX idx_approvals_status  ON approvals(status);

-- ─────────────────────────────────────────
-- entities
-- Hechos y entidades extraídas de conversaciones.
-- ─────────────────────────────────────────
CREATE TABLE entities (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT        NOT NULL,
    entity_type  TEXT        NOT NULL
                             CHECK (entity_type IN (
                                 'person', 'place', 'organization',
                                 'event', 'product', 'concept', 'other'
                             )),
    attributes   JSONB       NOT NULL DEFAULT '{}',
    source_session_id UUID   REFERENCES sessions(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entities_name        ON entities(name);
CREATE INDEX idx_entities_entity_type ON entities(entity_type);

-- ─────────────────────────────────────────
-- browser_runs
-- Registro de cada acción ejecutada por el browser-agent.
-- ─────────────────────────────────────────
CREATE TABLE browser_runs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID        REFERENCES tasks(id) ON DELETE SET NULL,
    url         TEXT,
    action      TEXT        NOT NULL,
    args_json   JSONB       NOT NULL DEFAULT '{}',
    result_json JSONB,
    status      TEXT        NOT NULL DEFAULT 'success'
                            CHECK (status IN ('success', 'error', 'blocked')),
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_browser_runs_task_id ON browser_runs(task_id);
CREATE INDEX idx_browser_runs_status  ON browser_runs(status);

-- ─────────────────────────────────────────
-- Trigger: actualiza updated_at automáticamente
-- ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

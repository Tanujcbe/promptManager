-- Prompt Vault v0 Database Schema
-- Run this SQL in your Supabase SQL Editor

-- ============================================
-- USER TABLE
-- ============================================
-- Users are synced from Supabase Auth on first API request.
-- The id field corresponds to auth.users.id (UUID as string).

CREATE TABLE IF NOT EXISTS "user" (
    id TEXT PRIMARY KEY,  -- Supabase Auth user_id
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1
);

-- Index for soft delete queries
CREATE INDEX IF NOT EXISTS idx_user_deleted_at ON "user"(deleted_at);


-- ============================================
-- PERSONA TABLE
-- ============================================
-- User-defined prompt templates (e.g., Official, Side Project, Fun)

CREATE TABLE IF NOT EXISTS persona (
    id TEXT PRIMARY KEY,  -- ULID
    user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    persona_prompt TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, name)
);

-- Indexes for persona
CREATE INDEX IF NOT EXISTS idx_persona_user_id ON persona(user_id);
CREATE INDEX IF NOT EXISTS idx_persona_deleted_at ON persona(deleted_at);
CREATE INDEX IF NOT EXISTS idx_persona_user_deleted ON persona(user_id, deleted_at);


-- ============================================
-- MESSAGE TABLE
-- ============================================
-- Saved prompts and AI responses

-- Create enum type for message_type
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_type') THEN
        CREATE TYPE message_type AS ENUM ('prompt', 'response');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS message (
    id TEXT PRIMARY KEY,  -- ULID
    user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    persona_id TEXT REFERENCES persona(id) ON DELETE SET NULL,
    message_type message_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary VARCHAR(10000),
    starred BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1
);

-- Indexes for message
CREATE INDEX IF NOT EXISTS idx_message_user_id ON message(user_id);
CREATE INDEX IF NOT EXISTS idx_message_persona_id ON message(persona_id);
CREATE INDEX IF NOT EXISTS idx_message_deleted_at ON message(deleted_at);
CREATE INDEX IF NOT EXISTS idx_message_user_deleted ON message(user_id, deleted_at);
CREATE INDEX IF NOT EXISTS idx_message_starred ON message(user_id, starred) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_message_type ON message(user_id, message_type) WHERE deleted_at IS NULL;


-- ============================================
-- ROW LEVEL SECURITY (RLS) - Optional
-- ============================================
-- Uncomment these if you want Supabase RLS for additional security.
-- Note: The FastAPI backend already enforces user ownership in services.

-- ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE persona ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE message ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY "Users can only access their own data" ON "user"
--     FOR ALL USING (auth.uid()::text = id);

-- CREATE POLICY "Users can only access their own personas" ON persona
--     FOR ALL USING (auth.uid()::text = user_id);

-- CREATE POLICY "Users can only access their own messages" ON message
--     FOR ALL USING (auth.uid()::text = user_id);

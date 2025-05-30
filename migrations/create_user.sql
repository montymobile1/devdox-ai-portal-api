-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create user table
CREATE TABLE IF NOT EXISTS public.user (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,

    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(255) DEFAULT '',
    role VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,

    membership_level VARCHAR(100) DEFAULT 'free',
    token_limit INTEGER DEFAULT 0,
    token_used INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.user ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own user record"
ON public.user FOR SELECT
USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert their own user record"
ON public.user FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update their own user record"
ON public.user FOR UPDATE
USING (auth.uid()::text = user_id);

CREATE POLICY "Users can delete their own user record"
ON public.user FOR DELETE
USING (auth.uid()::text = user_id);

-- Index
CREATE INDEX IF NOT EXISTS user_user_id_created_at_idx
ON public.user (user_id, created_at);
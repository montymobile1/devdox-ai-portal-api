-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create repo table
CREATE TABLE IF NOT EXISTS public.repo (
    repo_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR NOT NULL,
    token_id UUID NOT NULL,
    repo_name TEXT NOT NULL,
    description TEXT,
    last_commit TEXT,
    star_count INTEGER DEFAULT 0,
    commit_count INTEGER DEFAULT 0,
    fork_count INTEGER DEFAULT 0,
    branch_default TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Foreign key constraint
    CONSTRAINT fk_token_id FOREIGN KEY (token_id)
        REFERENCES public.git_label(id)
        ON DELETE CASCADE
);

-- Reuse existing handle_updated_at trigger function (already created)

-- Add trigger to update updated_at on UPDATE
CREATE TRIGGER set_updated_at_repo
BEFORE UPDATE ON public.repo
FOR EACH ROW
EXECUTE FUNCTION public.handle_updated_at();

-- Enable RLS on repo table
ALTER TABLE public.repo ENABLE ROW LEVEL SECURITY;

-- Create RLS policies

-- SELECT policy
CREATE POLICY "Users can view their own repos"
ON public.repo FOR SELECT
USING (auth.uid()::text = user_id);

-- INSERT policy
CREATE POLICY "Users can insert their own repos"
ON public.repo FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

-- UPDATE policy
CREATE POLICY "Users can update their own repos"
ON public.repo FOR UPDATE
USING (auth.uid()::text = user_id);

-- DELETE policy
CREATE POLICY "Users can delete their own repos"
ON public.repo FOR DELETE
USING (auth.uid()::text = user_id);

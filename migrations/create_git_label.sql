-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create git_label table
CREATE TABLE IF NOT EXISTS public.git_label (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR NOT NULL,
    label TEXT NOT NULL,
    git_hosting TEXT NOT NULL, -- e.g., 'github' or 'gitlab'
    username TEXT NOT NULL,
    token_value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create or replace handle_updated_at trigger function
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to update updated_at on UPDATE
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON public.git_label
FOR EACH ROW
EXECUTE FUNCTION public.handle_updated_at();

-- Enable RLS on git_label table
ALTER TABLE public.git_label ENABLE ROW LEVEL SECURITY;

-- Create RLS policies

-- SELECT policy
CREATE POLICY "Users can view their own git labels"
ON public.git_label FOR SELECT
USING (auth.uid()::text = user_id);

-- INSERT policy
CREATE POLICY "Users can insert their own git labels"
ON public.git_label FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

-- UPDATE policy
CREATE POLICY "Users can update their own git labels"
ON public.git_label FOR UPDATE
USING (auth.uid()::text = user_id);

-- DELETE policy
CREATE POLICY "Users can delete their own git labels"
ON public.git_label FOR DELETE
USING (auth.uid()::text = user_id);

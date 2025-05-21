-- Add new field to git_label table
ALTER TABLE public.git_label
ADD COLUMN masked_token VARCHAR;
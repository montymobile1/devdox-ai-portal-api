from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "git_label" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(255) NOT NULL,
    "label" TEXT NOT NULL,
    "git_hosting" VARCHAR(50) NOT NULL,
    "username" TEXT NOT NULL,
    "token_value" TEXT NOT NULL,
    "masked_token" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "git_label"."user_id" IS 'User identifier';
COMMENT ON COLUMN "git_label"."label" IS 'Label/name for this git configuration';
COMMENT ON COLUMN "git_label"."git_hosting" IS 'Git hosting service (e.g., ''github'', ''gitlab'')';
COMMENT ON COLUMN "git_label"."username" IS 'Username for the git hosting service';
COMMENT ON COLUMN "git_label"."token_value" IS 'Access token for the git hosting service';
COMMENT ON COLUMN "git_label"."masked_token" IS 'Masked Access token for the git hosting service';
COMMENT ON COLUMN "git_label"."created_at" IS 'Record creation timestamp';
COMMENT ON COLUMN "git_label"."updated_at" IS 'Record last update timestamp';
COMMENT ON TABLE "git_label" IS 'Table for storing git hosting service configurations per user';
CREATE TABLE IF NOT EXISTS "repo" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(255) NOT NULL UNIQUE,
    "repo_id" VARCHAR(255) NOT NULL,
    "repo_name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "html_url" VARCHAR(500) NOT NULL,
    "default_branch" VARCHAR(100) NOT NULL DEFAULT 'main',
    "forks_count" INT NOT NULL DEFAULT 0,
    "stargazers_count" INT NOT NULL DEFAULT 0,
    "is_private" BOOL NOT NULL DEFAULT False,
    "visibility" VARCHAR(50),
    "token_id" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "repo_created_at" TIMESTAMPTZ,
    "repo_updated_at" TIMESTAMPTZ,
    "language" VARCHAR(100),
    "size" INT
);
CREATE INDEX IF NOT EXISTS "idx_repo_user_id_05a4f0" ON "repo" ("user_id", "created_at");
COMMENT ON COLUMN "repo"."user_id" IS 'User ID who owns this repository';
COMMENT ON COLUMN "repo"."repo_id" IS 'Repository ID from the Git provider';
COMMENT ON COLUMN "repo"."repo_name" IS 'Repository name';
COMMENT ON COLUMN "repo"."description" IS 'Repository description';
COMMENT ON COLUMN "repo"."html_url" IS 'Repository URL';
COMMENT ON COLUMN "repo"."default_branch" IS 'Default branch name';
COMMENT ON COLUMN "repo"."forks_count" IS 'Number of forks';
COMMENT ON COLUMN "repo"."stargazers_count" IS 'Number of stars';
COMMENT ON COLUMN "repo"."is_private" IS 'Whether repository is private';
COMMENT ON COLUMN "repo"."visibility" IS 'Repository visibility (GitLab)';
COMMENT ON COLUMN "repo"."token_id" IS 'Associated token ID';
COMMENT ON COLUMN "repo"."created_at" IS 'Record creation timestamp';
COMMENT ON COLUMN "repo"."updated_at" IS 'Record update timestamp';
COMMENT ON COLUMN "repo"."repo_created_at" IS 'Repository creation date from provider';
COMMENT ON COLUMN "repo"."repo_updated_at" IS 'Repository last update from provider';
COMMENT ON COLUMN "repo"."language" IS 'Primary programming language';
COMMENT ON COLUMN "repo"."size" IS 'Repository size in KB';
COMMENT ON TABLE "repo" IS 'Repository information from Git providers';
CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(255) NOT NULL,
    "first_name" VARCHAR(255) NOT NULL,
    "last_name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "username" VARCHAR(255) NOT NULL DEFAULT '',
    "role" VARCHAR(255) NOT NULL,
    "active" BOOL NOT NULL DEFAULT True,
    "membership_level" VARCHAR(100) NOT NULL DEFAULT 'free',
    "token_limit" INT NOT NULL DEFAULT 0,
    "token_used" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_user_user_id_d610a5" ON "user" ("user_id", "created_at");
COMMENT ON COLUMN "user"."user_id" IS 'User ID';
COMMENT ON COLUMN "user"."first_name" IS 'First name of user';
COMMENT ON COLUMN "user"."last_name" IS 'Last name of user';
COMMENT ON COLUMN "user"."email" IS 'Email of user';
COMMENT ON COLUMN "user"."username" IS 'Username of user';
COMMENT ON COLUMN "user"."role" IS 'Role name of user';
COMMENT ON COLUMN "user"."membership_level" IS 'Default membership_level';
COMMENT ON COLUMN "user"."token_limit" IS 'Number of token of each month';
COMMENT ON COLUMN "user"."token_used" IS 'Number of tokens used';
COMMENT ON COLUMN "user"."created_at" IS 'Record creation timestamp';
COMMENT ON TABLE "user" IS 'User information from Clerk';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """

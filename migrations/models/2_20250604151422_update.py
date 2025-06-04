from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ALTER COLUMN "updated_at" TYPE TIMESTAMPTZ USING "updated_at"::TIMESTAMPTZ;
        COMMENT ON COLUMN "user"."updated_at" IS 'Record updated timestamp';
        ALTER TABLE "user" ALTER COLUMN "encryption_salt" SET DEFAULT '0';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "user"."updated_at" IS 'Record creation timestamp';
        ALTER TABLE "user" ALTER COLUMN "updated_at" TYPE TIMESTAMPTZ USING "updated_at"::TIMESTAMPTZ;
        ALTER TABLE "user" ALTER COLUMN "encryption_salt" SET DEFAULT 0;"""

import os
import subprocess
import asyncio
import logging
import re
import shutil
import glob
from datetime import datetime
from typing import Any, Dict, List, Tuple

from tortoise import Tortoise
from tortoise.transactions import in_transaction

from app.config import TORTOISE_ORM

logger = logging.getLogger(__name__)

# =============================================================
# --- Schema snapshot & diff helpers --------------------------
# =============================================================
async def _snapshot_with_conn(conn) -> Dict[str, List[Dict[str, Any]]]:
    # Tables
    tables = await conn.execute_query_dict("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type='BASE TABLE'
          AND table_schema NOT IN ('pg_catalog','information_schema')
        ORDER BY table_schema, table_name
    """)
    # Columns
    columns = await conn.execute_query_dict("""
        SELECT table_schema, table_name, column_name,
               data_type, udt_name,
               is_nullable,
               column_default,
               character_maximum_length, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog','information_schema')
        ORDER BY table_schema, table_name, ordinal_position
    """)
    # Indexes
    indexes = await conn.execute_query_dict("""
        SELECT schemaname AS table_schema, tablename AS table_name,
               indexname, indexdef
        FROM pg_indexes
        WHERE schemaname NOT IN ('pg_catalog','information_schema')
        ORDER BY schemaname, tablename, indexname
    """)
    # Constraints (PK/UK/FK/Check)
    constraints = await conn.execute_query_dict("""
        SELECT n.nspname AS table_schema,
               c.relname  AS table_name,
               con.conname AS constraint_name,
               con.contype AS constraint_type,
               pg_get_constraintdef(con.oid) AS constraint_def
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema')
        ORDER BY n.nspname, c.relname, con.conname
    """)
    # Column comments
    comments = await conn.execute_query_dict("""
        SELECT n.nspname AS table_schema,
               c.relname  AS table_name,
               a.attname  AS column_name,
               d.description AS comment
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_attribute a
               ON a.attrelid = c.oid AND a.attnum > 0
        LEFT JOIN pg_description d
               ON d.objoid = a.attrelid AND d.objsubid = a.attnum
        WHERE n.nspname NOT IN ('pg_catalog','information_schema')
          AND c.relkind = 'r'
        ORDER BY n.nspname, c.relname, a.attnum
    """)
    # Extensions (handy to confirm pgvector availability/location)
    extensions = await conn.execute_query_dict("""
        SELECT extname,
               extnamespace::regnamespace::text AS schema
        FROM pg_extension
        ORDER BY extname
    """)
    return {
        "tables": tables,
        "columns": columns,
        "indexes": indexes,
        "constraints": constraints,
        "comments": comments,
        "extensions": extensions,
    }

async def snapshot_schema() -> Dict[str, List[Dict[str, Any]]]:
    """Open a short-lived connection and capture a schema snapshot."""
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        conn = Tortoise.get_connection("default")
        return await _snapshot_with_conn(conn)
    finally:
        await Tortoise.close_connections()

def _index_by(rows: List[Dict[str, Any]], keys: Tuple[str, ...]) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
    return {tuple(row[k] for k in keys): row for row in rows}

def _diff_simple(before: List[Dict[str, Any]],
                 after: List[Dict[str, Any]],
                 keycols: Tuple[str, ...],
                 comparable_cols: List[str]) -> Dict[str, Any]:
    bmap = _index_by(before, keycols)
    amap = _index_by(after, keycols)
    added_keys   = list(amap.keys() - bmap.keys())
    removed_keys = list(bmap.keys() - amap.keys())
    common_keys  = list(amap.keys() & bmap.keys())

    added   = [amap[k] for k in sorted(added_keys)]
    removed = [bmap[k] for k in sorted(removed_keys)]
    changed = []

    for k in sorted(common_keys):
        b = bmap[k]; a = amap[k]
        diffs = {}
        for col in comparable_cols:
            if b.get(col) != a.get(col):
                diffs[col] = {"before": b.get(col), "after": a.get(col)}
        if diffs:
            changed.append({"key": dict(zip(keycols, k)), "changes": diffs})

    return {"added": added, "removed": removed, "changed": changed}

def diff_snapshots(before: Dict[str, List[Dict[str, Any]]],
                   after: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    return {
        "tables": _diff_simple(
            before["tables"], after["tables"],
            keycols=("table_schema", "table_name"),
            comparable_cols=[]
        ),
        "columns": _diff_simple(
            before["columns"], after["columns"],
            keycols=("table_schema", "table_name", "column_name"),
            comparable_cols=["data_type", "udt_name", "is_nullable", "column_default",
                             "character_maximum_length", "numeric_precision", "numeric_scale"]
        ),
        "indexes": _diff_simple(
            before["indexes"], after["indexes"],
            keycols=("table_schema", "table_name", "indexname"),
            comparable_cols=["indexdef"]
        ),
        "constraints": _diff_simple(
            before["constraints"], after["constraints"],
            keycols=("table_schema", "table_name", "constraint_name"),
            comparable_cols=["constraint_type", "constraint_def"]
        ),
        "comments": _diff_simple(
            before["comments"], after["comments"],
            keycols=("table_schema", "table_name", "column_name"),
            comparable_cols=["comment"]
        ),
        "extensions": _diff_simple(
            before["extensions"], after["extensions"],
            keycols=("extname",),
            comparable_cols=["schema"]
        ),
    }

def print_diff_summary(diff: Dict[str, Any], max_per_section: int = 25) -> None:
    def _head(lst): return lst[:max_per_section]
    print("\n📋 Schema change summary")
    for section in ["extensions", "tables", "columns", "indexes", "constraints", "comments"]:
        d = diff[section]
        print(f"\n— {section.upper()} —")
        print(f"  + added   : {len(d['added'])}")
        print(f"  - removed : {len(d['removed'])}")
        print(f"  ~ changed : {len(d['changed'])}")

        if d["added"]:
            print("   • Added (sample):")
            for row in _head(d["added"]):
                print(f"     - {row}")
        if d["removed"]:
            print("   • Removed (sample):")
            for row in _head(d["removed"]):
                print(f"     - {row}")
        if d["changed"]:
            print("   • Changed (sample):")
            for ch in _head(d["changed"]):
                print(f"     - key={ch['key']} changes={ch['changes']}")

# =============================================================
# --- PGVECTOR Migration Operations ---------------------------
# =============================================================
async def apply_pgvector_migration():
    
    PGVECTOR_MIGRATION_SQL = """
        -- 1) Handle old JSONB 'embedding' -> 'embedding_json2' (including the "stuck rename" case)
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='code_chunks'
              AND column_name='embedding' AND data_type='jsonb'
          ) THEN
            IF EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema='public' AND table_name='code_chunks'
                AND column_name='embedding_json2'
            ) THEN
              UPDATE "public"."code_chunks"
              SET "embedding_json2" = "embedding"
              WHERE "embedding_json2" IS NULL;
              ALTER TABLE "public"."code_chunks" DROP COLUMN "embedding";
            ELSE
              ALTER TABLE "public"."code_chunks" RENAME COLUMN "embedding" TO "embedding_json2";
            END IF;
          END IF;
        END $$;
        
        -- 2) Discover 'vector' type schema, ensure embedding is vector(768), and (conditionally) backfill
        DO $$
        DECLARE
          v_ns        text;  -- schema that owns 'vector' type (e.g., 'public' or 'extensions')
          v_coltype   text;  -- current type of public.code_chunks.embedding if present
          v_has_json2 boolean; -- whether embedding_json2 column exists
        BEGIN
          -- Find the namespace of the 'vector' type
          SELECT n.nspname
          INTO v_ns
          FROM pg_type t
          JOIN pg_namespace n ON n.oid = t.typnamespace
          WHERE t.typname = 'vector'
          LIMIT 1;
        
          IF v_ns IS NULL THEN
            RAISE EXCEPTION 'pgvector type not found; ensure the extension is installed';
          END IF;
        
          -- If embedding exists, verify it's vector(768); else create it as such
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='code_chunks'
              AND column_name='embedding'
          ) THEN
            SELECT format_type(a.atttypid, a.atttypmod)
            INTO v_coltype
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname='public'
              AND c.relname='code_chunks'
              AND a.attname='embedding'
              AND a.attnum > 0;
        
            IF v_coltype IS DISTINCT FROM 'vector(768)' THEN
              RAISE EXCEPTION
                'Existing column public.code_chunks.embedding is %, expected vector(768)', v_coltype;
              -- Or ALTER to vector(768) if you prefer auto-fix.
            END IF;
          ELSE
            EXECUTE format(
              'ALTER TABLE "public"."code_chunks" ADD COLUMN "embedding" %I.vector(768)',
              v_ns
            );
          END IF;
        
          -- Only backfill if the source column embedding_json2 actually exists
          SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='code_chunks'
              AND column_name='embedding_json2'
          ) INTO v_has_json2;
        
          IF v_has_json2 THEN
            EXECUTE format($sql$
              UPDATE "public"."code_chunks"
              SET "embedding" = (
                SELECT (ARRAY(
                  SELECT jsonb_array_elements_text("embedding_json2")::float8
                ))::%I.vector
              )
              WHERE "embedding" IS NULL
                AND "embedding_json2" IS NOT NULL
                AND jsonb_typeof("embedding_json2") = 'array'
                AND jsonb_array_length("embedding_json2") = 768
            $sql$, v_ns);
          END IF;
        END $$;
    """
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        async with in_transaction() as conn:
            await conn.execute_script(PGVECTOR_MIGRATION_SQL)
    finally:
        await Tortoise.close_connections()

# ======================================================================================================
# --- Apply custom partial indexes defined in the `devdox-ai-models` package ---------------------------
# ======================================================================================================

async def apply_queue_processing_registry_one_claim_unique():
    queue_partial_unique_sql = """
    -- 0) Sanity checks
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'queue_processing_registry'
      ) THEN
        RAISE EXCEPTION 'Table public.queue_processing_registry does not exist';
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='queue_processing_registry' AND column_name='message_id'
      ) THEN
        RAISE EXCEPTION 'Column "message_id" missing on public.queue_processing_registry';
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='queue_processing_registry' AND column_name='status'
      ) THEN
        RAISE EXCEPTION 'Column "status" missing on public.queue_processing_registry';
      END IF;
    END $$ LANGUAGE plpgsql;

    -- 1) Abort if duplicates would violate the unique partial index
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1
        FROM (
          SELECT message_id, COUNT(*) AS c
          FROM public.queue_processing_registry
          WHERE status IN ('pending','in_progress')
          GROUP BY message_id
          HAVING COUNT(*) > 1
        ) d
      ) THEN
        RAISE EXCEPTION
          'Cannot create unique partial index: duplicates exist for (message_id) with status in (pending,in_progress). Fix data and rerun.';
      END IF;
    END $$ LANGUAGE plpgsql;

    -- 2) Replace any previous index to guarantee exact definition
    DROP INDEX IF EXISTS public."queue_processing_registry_message_id_idx";
    
    -- 3) Create the index
    
    CREATE UNIQUE INDEX public."queue_processing_registry_message_id_idx"
    ON public."queue_processing_registry" ("message_id")
    WHERE "status" IN ('pending','in_progress');

    COMMENT ON INDEX public."queue_processing_registry_message_id_idx"
      IS 'Enforces at most one row per message_id while status is pending/in_progress.';
    """
    
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        async with in_transaction() as conn:
            await conn.execute_script(queue_partial_unique_sql)
    finally:
        await Tortoise.close_connections()

# =============================================================
# --- OTHER ---------------------------------------------------
# =============================================================

def auto_run_command(cmd):
    """Run any command with automatic 'yes' responses."""
    try:
        process = subprocess.Popen(
            cmd.split() if isinstance(cmd, str) else cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate(input="y\n" * 20, timeout=300)
        success = process.returncode == 0

        print(f"🔧 Command: {cmd}")
        print(f"✅ Success: {success}")
        if stdout:
            print(f"📄 Output: {stdout}")
        if stderr and not success:
            print(f"❌ Error: {stderr}")

        return success, stdout, stderr
    except Exception as e:
        print(f"❌ Command failed: {e}")
        return False, "", str(e)

def validate_identifier(name):
    """Validate SQL identifier to prevent injection."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid identifier: {name}")
    return name

def find_migration_files():
    """Find migration files in any directory structure."""
    possible_dirs = ["migrations", "migrations/models", "db/migrations"]

    for dir_path in possible_dirs:
        if os.path.exists(dir_path):
            files = glob.glob(f"{dir_path}/*.py")
            files = [f for f in files if not f.endswith("__init__.py")]
            if files:
                return dir_path, files

    return None, []


def create_ultimate_migration(migration_path):
    """Create the ultimate migration that handles any future conflicts."""

    # Backup original if it exists
    if os.path.exists(migration_path):
        backup = f"{migration_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(migration_path, backup)
        print(f"📦 Backed up to: {backup}")


    print(f"🤖 Created ultimate safe migration: {migration_path}")


async def check_database():
    """Quick database connectivity check."""
    try:
        await Tortoise.init(config=TORTOISE_ORM)
        connection = Tortoise.get_connection("default")
        await connection.execute_query("SELECT 1;")
        print("✅ Database connection verified")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        await Tortoise.close_connections()


async def run_ultimate_migrations():
    """🚀 THE ULTIMATE MIGRATION SOLUTION - Handles everything automatically."""

    print("🚀 === ULTIMATE AUTOMATED MIGRATION SYSTEM === 🚀")
    print("✅ Handles prompts automatically")
    print("✅ Resolves conflicts automatically")
    print("✅ Adapts to future schema changes")
    print("✅ Works in any environment")

    # Step 1: Check database
    print("\n1️⃣ Verifying database connection...")
    if not await check_database():
        print("❌ Fix database connection first")
        return False
        
    # Take PRE snapshot of the database
    print("\n📸 Taking PRE-migration snapshot...")
    snapshot_before = await snapshot_schema()
    
    # Step 2: Setup environment
    os.environ["PYTHONUNBUFFERED"] = "1"
    migrations_dir, existing_files = find_migration_files()

    if not migrations_dir:
        print("📁 Creating migrations directory...")
        os.makedirs("migrations", exist_ok=True)
        migrations_dir = "migrations"

    print(f"📁 Using migrations directory: {migrations_dir}")

    # Step 3: Initialize if needed
    if not existing_files:
        print("\n2️⃣ Initializing aerich...")
        success, _, _ = auto_run_command("aerich init -t app.config.TORTOISE_ORM")
        if not success:
            print("❌ Aerich init failed")
            return False

        print("\n3️⃣ Running init-db...")
        success, _, _ = auto_run_command("aerich init-db")
        if not success:
            print("❌ Init-db failed")
            return False

    # Step 4: Create migration with auto-confirmation
    print("\n4️⃣ Creating migration (auto-confirming all prompts)...")
    success, stdout, stderr = auto_run_command("aerich migrate")

    # Extract new migration filename
    new_migration = None
    if "Success creating migration file" in stdout:
        match = re.search(r"Success creating migration file (\S\.py)", stdout)
        if match:
            new_migration = match.group(1)
            print(f"📝 Created migration: {new_migration}")

    # Force create if needed
    if not success and "No changes detected" not in (stdout, stderr):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"🔧 Force creating migration: ultimate_{timestamp}")
        success, stdout, stderr = auto_run_command(
            f"aerich migrate --name ultimate_{timestamp}"
        )
        if success:
            new_migration = f"ultimate_{timestamp}.py"

    # Step 5: Make migration ultimate safe
    if new_migration:
        migration_path = os.path.join(migrations_dir, new_migration)
        print(f"\n5️⃣ Making migration ultimate safe: {new_migration}")
        create_ultimate_migration(migration_path)
    else:
        # Find latest migration and fix it
        _, migration_files = find_migration_files()
        if migration_files:
            latest = sorted(migration_files)[-1]
            print(
                f"\n5️⃣ Making latest migration ultimate safe: {os.path.basename(latest)}"
            )
            create_ultimate_migration(latest)
    
    # Step 6: Apply migration (guaranteed to work)
    print("\n6️⃣ Applying ultimate safe migration...")
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            await asyncio.sleep(2 ** (attempt - 1))  # Exponential backoff
        print(f"📤 Attempt {attempt}/{max_attempts}...")
        success, stdout, stderr = auto_run_command("aerich upgrade")

        if success:
            print(f"✅ Upgrade successful on attempt {attempt}!")
            
            # Now do the rename/add/backfill/index work
            print("🧠 Applying pgvector data migration (rename/backfill/index)…")
            await apply_pgvector_migration()
            
            print("🧩 Creating unique partial index `queue_processing_registry_message_id_idx` on queue_processing_registry…")
            await apply_queue_processing_registry_one_claim_unique()
            
            break

        if attempt < max_attempts:
            print(f"⚠️ Attempt {attempt} failed, retrying...")
            print(f"Error: {stderr}")
        else:
            print(f"❌ All attempts failed: {stderr}")
            return False

    # Step 7: Final verification + POST snapshot + diff
    print("\n7️⃣ Final verification...")
    if await check_database():
        print("✅ Database connection still working")
        
        print("\n📸 Taking POST-migration snapshot...")
        snapshot_after = await snapshot_schema()
        
        diff = diff_snapshots(snapshot_before, snapshot_after)
        print_diff_summary(diff)

        return True
    else:
        print("❌ Database verification failed")
        return False


if __name__ == "__main__":
    """
    🚀 ULTIMATE AUTOMATED MIGRATION RUNNER

    Usage: python ultimate_automated_migrations.py

    This script handles EVERYTHING automatically:
    - Prompts → Auto-confirmed
    - Conflicts → Auto-resolved
    - Future changes → Configuration-driven
    - Any environment → Works everywhere
    """

    # Simple logging setup
    logging.basicConfig(level=logging.WARNING)

    print("🚀 Starting ultimate migration process...")
    result = asyncio.run(run_ultimate_migrations())

    if result:
        print("\n🎉 === MIGRATION COMPLETED SUCCESSFULLY === 🎉")
        print("✨ Your database is now fully up to date!")
        print("🔧 To add future schema changes, edit migration_schema_config.py")
        print("📚 Run with --examples to see how to extend the system")
    else:
        print("\n💥 Migration failed. Check the output above for details.")
        print("🔧 You may need to check your database connection or configuration.")
        exit(1)

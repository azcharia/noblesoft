"""
Database Migration Runner
Automatically applies pending SQL migrations from supabase/migrations/ directory
Supports incremental migrations with tracking to prevent re-execution (similar to Prisma/Supabase CLI)
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Ensure root paths are in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Load environment variables
load_dotenv()

def get_connection():
    """Establish connection to PostgreSQL using DATABASE_URL"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable is not set.")
        print("Please add DATABASE_URL to your backend/.env file.")
        print("Example: DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        sys.exit(1)

def ensure_migration_table(cursor):
    """Create migration tracking table if not exists"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS public._migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            executed_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

def get_applied_migrations(cursor):
    """Retrieve list of already applied migrations"""
    cursor.execute("SELECT name FROM public._migrations;")
    return {row[0] for row in cursor.fetchall()}

def run_migrations():
    """Main function to scan and execute migrations"""
    # Resolve migrations path
    project_root = Path(__file__).resolve().parents[2]
    migrations_dir = project_root / "supabase" / "migrations"
    
    if not migrations_dir.exists():
        print(f"Error: Migrations directory not found at {migrations_dir}")
        sys.exit(1)
        
    migration_files = sorted([f for f in migrations_dir.glob("*.sql") if f.is_file()])
    if not migration_files:
        print("No migration files found.")
        return

    print("Connecting to Supabase Database...")
    conn = get_connection()
    conn.autocommit = False # Disable autocommit for transactional safety
    cursor = conn.cursor()
    
    try:
        ensure_migration_table(cursor)
        applied = get_applied_migrations(cursor)
        
        pending_migrations = [f for f in migration_files if f.name not in applied]
        
        if not pending_migrations:
            print("Database is up to date. No pending migrations.")
            conn.commit()
            return
            
        print(f"Found {len(pending_migrations)} pending migrations.")
        
        for migration_path in pending_migrations:
            migration_name = migration_path.name
            print(f"Applying migration: {migration_name} ...", end="", flush=True)
            
            with open(migration_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
                
            try:
                # Execute migration content
                if sql_content.strip():
                    cursor.execute(sql_content)
                
                # Record migration tracking
                cursor.execute(
                    "INSERT INTO public._migrations (name) VALUES (%s);",
                    (migration_name,)
                )
                print(" SUCCESS")
            except Exception as e:
                print(" FAILED")
                print(f"\nError details during execution of {migration_name}:")
                print(str(e))
                print("\nRolling back transaction...")
                conn.rollback()
                sys.exit(1)
                
        # Commit all successful migrations
        conn.commit()
        print("All migrations applied successfully!")
        
    except Exception as exc:
        conn.rollback()
        print(f"Migration runner failed: {str(exc)}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migrations()

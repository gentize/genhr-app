import sqlite3
import os
from sqlalchemy import create_engine, MetaData
from employee_portal import create_app, db

# --- CONFIGURATION ---
# Your SQLite file path
SQLITE_DB = 'instance/app.db'
# Your NEW Postgres URL (e.g., 'postgresql://user:password@localhost:5432/genhr')
POSTGRES_URL = os.environ.get('DATABASE_URL')

def migrate():
    if not POSTGRES_URL:
        print("Error: DATABASE_URL environment variable not set.")
        return

    print(f"Starting migration from {SQLITE_DB} to PostgreSQL...")

    # Initialize Flask App to get models
    app = create_app()
    
    with app.app_context():
        # 1. Create tables in PostgreSQL
        print("Creating tables in PostgreSQL...")
        db.create_all()

        # 2. Get SQLAlchemy Engine for Postgres
        pg_engine = db.engine
        
        # 3. Connect to SQLite
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_cursor = sqlite_conn.cursor()

        # Get all table names from SQLite
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%';")
        tables = [t[0] for t in sqlite_cursor.fetchall()]

        # 4. Transfer Data
        for table in tables:
            print(f"Transferring table: {table}...")
            try:
                # Read from SQLite
                data = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
                if not data:
                    continue

                # Get column names
                columns = [description[0] for description in sqlite_conn.execute(f"SELECT * FROM {table}").description]
                
                # Insert into Postgres using raw SQL to preserve IDs
                placeholders = ', '.join(['%s'] * len(columns))
                column_names = ', '.join(columns)
                insert_query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                
                with pg_engine.connect() as pg_conn:
                    # Clear existing data if any (optional)
                    # pg_conn.execute(f"DELETE FROM {table}")
                    
                    for row in data:
                        pg_conn.execute(insert_query, row)
                
                print(f"Successfully migrated {len(data)} rows for {table}.")
            except Exception as e:
                print(f"Error migrating {table}: {e}")

        sqlite_conn.close()
        print("Migration Complete!")

if __name__ == "__main__":
    migrate()

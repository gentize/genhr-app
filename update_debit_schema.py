import sqlite3
import os

db_path = 'instance/app.db'

def update_debit_schema():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(debit)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'bill_file' not in columns:
            print("Adding 'bill_file' column to 'debit' table...")
            cursor.execute("ALTER TABLE debit ADD COLUMN bill_file VARCHAR(255)")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'bill_file' already exists.")

    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_debit_schema()

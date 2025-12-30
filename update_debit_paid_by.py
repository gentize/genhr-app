import sqlite3
import os

db_path = 'instance/app.db'

def update_debit_paid_by():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(debit)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'paid_by' not in columns:
            print("Adding 'paid_by' column to 'debit' table...")
            cursor.execute("ALTER TABLE debit ADD COLUMN paid_by VARCHAR(100)")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'paid_by' already exists.")

    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_debit_paid_by()

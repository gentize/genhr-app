import sqlite3
import os

db_path = 'instance/app.db'

def update_bill_estimate_schema():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(bill_estimate)")
        if not cursor.fetchall():
            print("Creating 'bill_estimate' table...")
            cursor.execute("""
                CREATE TABLE bill_estimate (
                    id INTEGER PRIMARY KEY,
                    estimate_number VARCHAR(50) UNIQUE,
                    date DATE NOT NULL,
                    total_amount FLOAT NOT NULL,
                    items_json TEXT,
                    pdf_file VARCHAR(255),
                    created_by VARCHAR(100),
                    created_at DATETIME
                )
            """)
            conn.commit()
            print("Table created successfully.")
        else:
            print("Table 'bill_estimate' already exists.")

    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_bill_estimate_schema()

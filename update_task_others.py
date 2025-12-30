import sqlite3
import os

db_path = 'instance/app.db'

def update_task_other_type():
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(task)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'other_type_name' not in columns:
            print("Adding 'other_type_name' column to 'task' table...")
            cursor.execute("ALTER TABLE task ADD COLUMN other_type_name VARCHAR(50)")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column already exists.")

    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_task_other_type()

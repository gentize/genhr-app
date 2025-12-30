import sqlite3
import os

db_path = 'instance/app.db'

def update_task_system():
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Add task_no to Task table
        cursor.execute("PRAGMA table_info(task)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'task_no' not in cols:
            print("Adding 'task_no' to 'task' table...")
            cursor.execute("ALTER TABLE task ADD COLUMN task_no VARCHAR(10)")
        
        if 'status' not in cols:
            print("Adding 'status' to 'task' table...")
            cursor.execute("ALTER TABLE task ADD COLUMN status VARCHAR(20) DEFAULT 'Assigned'")

        # 2. Ensure EmployeeTask has all fields
        cursor.execute("PRAGMA table_info(employee_task)")
        et_cols = [c[1] for c in cursor.fetchall()]
        
        updates = [
            ("status", "VARCHAR(20) DEFAULT 'YTS'"),
            ("reason", "TEXT"),
            ("followup_date", "DATE")
        ]

        for name, dtype in updates:
            if name not in et_cols:
                print(f"Adding '{name}' to 'employee_task' table...")
                cursor.execute(f"ALTER TABLE employee_task ADD COLUMN {name} {dtype}")

        conn.commit()
        print("Task system schema updated successfully.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_task_system()

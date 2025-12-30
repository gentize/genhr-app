import sqlite3
import os

db_path = 'instance/app.db'

def update_employee_task_schema():
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(employee_task)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_cols = [
            ("status", "VARCHAR(20) DEFAULT 'YTS'"),
            ("reason", "TEXT"),
            ("followup_date", "DATE")
        ]

        for col_name, col_type in new_cols:
            if col_name not in columns:
                print(f"Adding '{col_name}' column to 'employee_task' table...")
                cursor.execute(f"ALTER TABLE employee_task ADD COLUMN {col_name} {col_type}")
        
        conn.commit()
        print("EmployeeTask schema updated successfully.")

    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_employee_task_schema()

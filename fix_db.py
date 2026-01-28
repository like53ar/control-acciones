import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(portfolio)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns before: {columns}")

    if 'current_price' not in columns:
        print("Adding current_price column...")
        cursor.execute('ALTER TABLE portfolio ADD COLUMN current_price REAL DEFAULT 0')
        conn.commit()
        print("Column added.")
    else:
        print("Column already exists.")

    cursor.execute("PRAGMA table_info(portfolio)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns after: {columns}")
    conn.close()
    print("Success")
except Exception as e:
    print(f"Error: {e}")

import sqlite3
conn = sqlite3.connect("portfolio.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(portfolio)")
for col in cursor.fetchall():
    print(col)
conn.close()

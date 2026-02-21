import sqlite3
conn = sqlite3.connect('portfolio.db')
cr = conn.cursor()
cr.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cr.fetchall()
for t in tables:
    try:
        count = cr.execute(f"SELECT count(*) FROM {t[0]}").fetchone()[0]
        print(f"Table: {t[0]}, Rows: {count}")
    except:
        pass
conn.close()

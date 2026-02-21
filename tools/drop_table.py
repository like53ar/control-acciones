import sqlite3
import os

db_path = os.path.join('c:\\', 'Users', 'fabar', 'OneDrive', 'Escritorio', 'ACCIONES', 'control-acciones', 'portfolio.db')
conn = sqlite3.connect(db_path)
cr = conn.cursor()
cr.execute("DROP TABLE IF EXISTS transactions;")
conn.commit()
conn.close()
print("Table 'transactions' dropped successfully.")

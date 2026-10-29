import os
import sqlite3

DB_FILE = "data/necromap.db"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

os.makedirs("data", exist_ok=True)
conn = sqlite3.connect(DB_FILE)

for file_name in ["sql/schema.sql", "sql/demo_data.sql"]:
    with open(file_name, encoding="utf-8") as file:
        conn.executescript(file.read())
conn.commit()

print("База создана:", DB_FILE)
for table in ["Cemeteries", "Plots", "People", "Burials"]:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count}")

conn.close()

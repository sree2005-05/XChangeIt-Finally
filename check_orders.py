import sqlite3

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM order_requests WHERE status='accepted'")
rows = c.fetchall()
print(f"Found {len(rows)} accepted order(s):\n")
for o in rows:
    print(dict(o))
conn.close()

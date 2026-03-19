import sqlite3
from datetime import date

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Show all accepted orders first
c.execute("SELECT * FROM order_requests WHERE status='accepted'")
orders = c.fetchall()
print(f"Found {len(orders)} accepted order(s):\n")
for o in orders:
    print(f"  ID:{o['id']} | product_id:{o['product_id']} | buyer:{o['buyer']} | rent_from:{o['rent_from']} | rent_to:{o['rent_to']} | rent_days:{o['rent_days']}")

print()

for o in orders:
    product_id = o['product_id']
    c.execute("SELECT name, category FROM products WHERE id=?", (product_id,))
    prod = c.fetchone()
    if not prod:
        continue

    if prod['category'] == 'buy':
        c.execute("UPDATE products SET status='sold' WHERE id=?", (product_id,))
        print(f"  ✓ '{prod['name']}' → SOLD")

    elif prod['category'] == 'rent':
        rent_from = o['rent_from']
        rent_to   = o['rent_to']
        rent_days = o['rent_days']

        # Calculate rent_days from dates if missing
        if not rent_days and rent_from and rent_to:
            d1 = date.fromisoformat(rent_from)
            d2 = date.fromisoformat(rent_to)
            rent_days = (d2 - d1).days + 1
            c.execute("UPDATE order_requests SET rent_days=? WHERE id=?", (rent_days, o['id']))
            print(f"  ✓ Calculated rent_days={rent_days} for order {o['id']}")

        c.execute("UPDATE products SET status='rented', rented_until=? WHERE id=?",
                  (rent_to or '', product_id))
        print(f"  ✓ '{prod['name']}' → RENTED | days={rent_days} | until={rent_to}")

conn.commit()
conn.close()
print("\nDone! Restart Flask and refresh the page.")

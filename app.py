from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import requests as http_requests

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- PATH SETUP ----------------
BASE_DIR = os.getcwd()
DATABASE = os.path.join(BASE_DIR, "users.db")
print("Database will be created at:", DATABASE)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# ---------------- SUPABASE CONFIG ----------------
SUPABASE_URL = "https://mllhwywquaoyaoriktys.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1sbGh3eXdxdWFveWFvcmlrdHlzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA5ODgzMzYsImV4cCI6MjA4NjU2NDMzNn0.2IhysGT2hkq8n5OZnazP1kwEc_9JPI6G5xmyHc3wZSo"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def sb_get(table, params=""):
    r = http_requests.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=SUPABASE_HEADERS)
    return r.json() if r.ok else []

def sb_post(table, data):
    r = http_requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=SUPABASE_HEADERS, json=data)
    return r.json() if r.ok else None

def sb_patch(table, params, data):
    r = http_requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=SUPABASE_HEADERS, json=data)
    return r.ok

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, price INTEGER NOT NULL,
        short_desc TEXT, detailed_desc TEXT, category TEXT,
        image1 TEXT, image2 TEXT, image3 TEXT, image4 TEXT, image5 TEXT, seller TEXT
    )''')
    try:
        c.execute("ALTER TABLE products ADD COLUMN seller TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, message TEXT NOT NULL, year TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, product_id INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, product_id INTEGER
    )''')
    conn.commit()
    conn.close()


def insert_sample_products():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        samples = [
            ("Engineering Calculator", 1200, "Scientific calculator",
             "Best for engineering exams. Casio fx-991EX, barely used.", "buy", None,None,None,None,None,"admin"),
            ("Hostel Mattress", 800, "Comfortable mattress",
             "Single bed hostel mattress, used for one year. Clean condition.", "rent", None,None,None,None,None,"admin"),
            ("Mountain Cycle", 2500, "Geared mountain cycle",
             "Good condition 21-speed mountain cycle. Negotiable.", "buy", None,None,None,None,None,"admin"),
            ("Study Table", 500, "Sturdy wooden study table",
             "Perfect for hostel rooms. 3x2 ft. Minor scratches.", "rent", None,None,None,None,None,"admin"),
            ("Data Structures Textbook", 300, "CLRS Algorithm textbook",
             "CLRS 3rd edition. Good condition, no missing pages.", "buy", None,None,None,None,None,"admin"),
            ("Table Fan", 450, "Usha table fan",
             "12-inch Usha table fan. Works perfectly.", "buy", None,None,None,None,None,"admin"),
        ]
        c.executemany('''INSERT INTO products
            (name,price,short_desc,detailed_desc,category,image1,image2,image3,image4,image5,seller)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''', samples)
        conn.commit()
    conn.close()


# ── helper: pending request count for navbar badge ──
def get_pending_count(username):
    if not username:
        return 0
    data = sb_get("chat_requests",
                  f"seller=eq.{username}&status=eq.pending&select=id")
    return len(data) if isinstance(data, list) else 0


# ── helper: enrich request list with product info from SQLite ──
def enrich_with_products(req_list):
    if not req_list:
        return {}
    ids = set(r["product_id"] for r in req_list)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    c.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", list(ids))
    result = {p["id"]: dict(p) for p in c.fetchall()}
    conn.close()
    return result


# ---------------- HOME ----------------
@app.route("/")
def home():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT name, message, year FROM reviews ORDER BY id DESC")
    reviews = c.fetchall()
    conn.close()
    pending = get_pending_count(session.get("user"))
    return render_template("index.html", reviews=reviews, pending_count=pending)


# ---------------- EXPLORE ----------------
@app.route("/explore")
def explore():
    category = request.args.get("category", "all")
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    if category == "buy":
        c.execute("SELECT * FROM products WHERE category='buy' ORDER BY id DESC")
    elif category == "rent":
        c.execute("SELECT * FROM products WHERE category='rent' ORDER BY id DESC")
    else:
        c.execute("SELECT * FROM products ORDER BY id DESC")
    products = c.fetchall()
    conn.close()
    pending = get_pending_count(session.get("user"))
    return render_template("explore.html", products=products, category=category, pending_count=pending)


# ---------------- PRODUCT DETAIL ----------------
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()
    if not product:
        flash("Product not found.")
        return redirect(url_for("explore"))

    chat_status = None
    if session.get("user") and session["user"] != product[11]:
        reqs = sb_get("chat_requests",
                      f"product_id=eq.{product_id}&buyer=eq.{session['user']}&select=status")
        if reqs and len(reqs) > 0:
            chat_status = reqs[0]["status"]

    pending = get_pending_count(session.get("user"))
    return render_template("product_detail.html", product=product,
                           chat_status=chat_status, pending_count=pending)


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user"):
        return redirect(url_for("home"))
    if request.method == "POST":
        name     = request.form["name"].strip()
        email    = request.form["email"].strip().lower()
        password = request.form["password"]
        if not email.endswith("@gecskp.ac.in"):
            flash("Please use your official @gecskp.ac.in email address.")
            return render_template("signup.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return render_template("signup.html")
        hashed = generate_password_hash(password)
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                      (name, email, hashed))
            conn.commit()
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.")
        finally:
            conn.close()
    return render_template("signup.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("home"))
    if request.method == "POST":
        email    = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):
            session["user"] = user[1]
            flash(f"Welcome back, {user[1]}!")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.")
    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.")
    return redirect(url_for("home"))


# ---------------- ADD REVIEW ----------------
@app.route("/add_review", methods=["GET", "POST"])
def add_review():
    if not session.get("user"):
        flash("Please log in to add a review.")
        return redirect(url_for("login"))
    if request.method == "POST":
        message = request.form["message"].strip()
        year    = request.form["year"]
        if not message:
            flash("Review cannot be empty.")
            return render_template("review.html")
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO reviews (name, message, year) VALUES (?, ?, ?)",
                  (session["user"], message, year))
        conn.commit()
        conn.close()
        flash("Review added!")
        return redirect(url_for("home"))
    return render_template("review.html")


# ---------------- WISHLIST ----------------
@app.route("/add_to_wishlist/<int:product_id>")
def add_to_wishlist(product_id):
    if not session.get("user"):
        flash("Please log in to wishlist items.")
        return redirect(url_for("login"))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id FROM wishlist WHERE user=? AND product_id=?",
              (session["user"], product_id))
    if not c.fetchone():
        c.execute("INSERT INTO wishlist (user, product_id) VALUES (?, ?)",
                  (session["user"], product_id))
        conn.commit()
        flash("Added to wishlist!")
    else:
        flash("Already in your wishlist.")
    conn.close()
    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/wishlist")
def wishlist():
    if not session.get("user"):
        flash("Please log in to view your wishlist.")
        return redirect(url_for("login"))
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT products.id, products.name, products.price, products.short_desc,
               products.category, products.image1
               FROM wishlist JOIN products ON wishlist.product_id = products.id
               WHERE wishlist.user=? ORDER BY wishlist.id DESC""", (session["user"],))
    items = c.fetchall()
    conn.close()
    pending = get_pending_count(session.get("user"))
    return render_template("wishlist.html", items=items, pending_count=pending)


# ---------------- CART ----------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if not session.get("user"):
        flash("Please log in to add to cart.")
        return redirect(url_for("login"))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id FROM cart WHERE user=? AND product_id=?",
              (session["user"], product_id))
    if not c.fetchone():
        c.execute("INSERT INTO cart (user, product_id) VALUES (?, ?)",
                  (session["user"], product_id))
        conn.commit()
        flash("Added to cart!")
    else:
        flash("Already in your cart.")
    conn.close()
    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/cart")
def cart():
    if not session.get("user"):
        flash("Please log in to view your cart.")
        return redirect(url_for("login"))
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT products.id, products.name, products.price, products.image1
               FROM cart JOIN products ON cart.product_id = products.id
               WHERE cart.user=? ORDER BY cart.id DESC""", (session["user"],))
    items = c.fetchall()
    conn.close()
    total = sum(item["price"] for item in items)
    pending = get_pending_count(session.get("user"))
    return render_template("cart.html", items=items, total=total, pending_count=pending)


@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    if not session.get("user"):
        return redirect(url_for("login"))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM cart WHERE user=? AND product_id=?",
              (session["user"], product_id))
    conn.commit()
    conn.close()
    flash("Item removed from cart.")
    return redirect(url_for("cart"))


# ---------------- SELL ----------------
@app.route("/sell", methods=["GET", "POST"])
def sell():
    if not session.get("user"):
        flash("Please log in to list an item.")
        return redirect(url_for("login"))
    if request.method == "POST":
        name          = request.form["name"].strip()
        price         = request.form["price"]
        short_desc    = request.form["short_desc"].strip()
        detailed_desc = request.form["detailed_desc"].strip()
        category      = request.form["category"]
        seller        = session["user"]
        images = []
        for i in range(1, 6):
            file = request.files.get(f"image{i}")
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                images.append(filename)
            else:
                images.append(None)
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO products
            (name,price,short_desc,detailed_desc,category,image1,image2,image3,image4,image5,seller)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (name, price, short_desc, detailed_desc, category,
             images[0], images[1], images[2], images[3], images[4], seller))
        conn.commit()
        conn.close()
        flash("Item listed successfully!")
        return redirect(url_for("profile"))
    pending = get_pending_count(session.get("user"))
    return render_template("sell.html", pending_count=pending)


# ---------------- CHAT REQUEST: BUYER SENDS ----------------
@app.route("/request_chat/<int:product_id>")
def request_chat(product_id):
    if not session.get("user"):
        flash("Please log in first.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()

    if not product:
        flash("Product not found.")
        return redirect(url_for("explore"))

    buyer  = session["user"]
    seller = product["seller"]

    if buyer == seller:
        flash("This is your own listing.")
        return redirect(url_for("product_detail", product_id=product_id))

    existing = sb_get("chat_requests",
                      f"product_id=eq.{product_id}&buyer=eq.{buyer}&select=id,status")
    if existing and len(existing) > 0:
        flash("You've already sent a request for this item.")
        return redirect(url_for("product_detail", product_id=product_id))

    sb_post("chat_requests", {
        "product_id": product_id,
        "buyer":  buyer,
        "seller": seller,
        "status": "pending"
    })

    flash("Chat request sent! Waiting for the seller to accept.")
    return redirect(url_for("product_detail", product_id=product_id))


# ---------------- ACCEPT / DECLINE REQUEST ----------------
@app.route("/respond_request/<int:request_id>/<action>")
def respond_request(request_id, action):
    if not session.get("user"):
        return redirect(url_for("login"))
    if action not in ("accepted", "declined"):
        flash("Invalid action.")
        return redirect(url_for("chat_inbox"))
    sb_patch("chat_requests", f"id=eq.{request_id}", {"status": action})
    if action == "accepted":
        flash("Chat request accepted!")
    else:
        flash("Request declined.")
    return redirect(url_for("chat_inbox"))


# ---------------- CHAT INBOX ----------------
@app.route("/chat_inbox")
def chat_inbox():
    if not session.get("user"):
        flash("Please log in.")
        return redirect(url_for("login"))

    user = session["user"]

    pending_reqs = sb_get("chat_requests",
                          f"seller=eq.{user}&status=eq.pending&select=*&order=created_at.desc")
    if not isinstance(pending_reqs, list):
        pending_reqs = []

    buyer_accepted = sb_get("chat_requests",
                            f"buyer=eq.{user}&status=eq.accepted&select=*&order=created_at.desc")
    if not isinstance(buyer_accepted, list):
        buyer_accepted = []

    seller_accepted = sb_get("chat_requests",
                             f"seller=eq.{user}&status=eq.accepted&select=*&order=created_at.desc")
    if not isinstance(seller_accepted, list):
        seller_accepted = []

    products_map = enrich_with_products(pending_reqs + buyer_accepted + seller_accepted)
    pending = get_pending_count(user)

    return render_template("chat_inbox.html",
                           pending_reqs=pending_reqs,
                           buyer_accepted=buyer_accepted,
                           seller_accepted=seller_accepted,
                           products_map=products_map,
                           current_user=user,
                           pending_count=pending,
                           SUPABASE_URL=SUPABASE_URL,
                           SUPABASE_KEY=SUPABASE_KEY)


# ---------------- MY LISTINGS CHAT HUB ----------------
@app.route("/my_listings_chat")
def my_listings_chat():
    """Chat icon → seller sees all their listings with chat activity."""
    if not session.get("user"):
        flash("Please log in.")
        return redirect(url_for("login"))

    user = session["user"]

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE seller=? ORDER BY id DESC", (user,))
    my_products = [dict(p) for p in c.fetchall()]
    conn.close()

    for p in my_products:
        accepted = sb_get("chat_requests",
                          f"product_id=eq.{p['id']}&seller=eq.{user}&status=eq.accepted&select=id")
        p["chat_count"] = len(accepted) if isinstance(accepted, list) else 0

        pending_r = sb_get("chat_requests",
                           f"product_id=eq.{p['id']}&seller=eq.{user}&status=eq.pending&select=id")
        p["pending_count"] = len(pending_r) if isinstance(pending_r, list) else 0

    # Also get chats where user is buyer (items they are buying)
    buying_chats = sb_get("chat_requests",
                          f"buyer=eq.{user}&status=eq.accepted&select=*&order=created_at.desc")
    if not isinstance(buying_chats, list):
        buying_chats = []
    buying_products_map = enrich_with_products(buying_chats)

    pending = get_pending_count(user)
    return render_template("my_listings_chat.html",
                           my_products=my_products,
                           buying_chats=buying_chats,
                           buying_products_map=buying_products_map,
                           current_user=user,
                           pending_count=pending)


# ---------------- PRODUCT CHAT LIST ----------------
@app.route("/product_chats/<int:product_id>")
def product_chats(product_id):
    """Seller clicks a product → sees all buyers (pending + accepted)."""
    if not session.get("user"):
        flash("Please log in.")
        return redirect(url_for("login"))

    user = session["user"]

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=? AND seller=?", (product_id, user))
    product = c.fetchone()
    conn.close()

    if not product:
        flash("Product not found or you don't own it.")
        return redirect(url_for("my_listings_chat"))

    all_reqs = sb_get("chat_requests",
                      f"product_id=eq.{product_id}&seller=eq.{user}&select=*&order=created_at.desc")
    if not isinstance(all_reqs, list):
        all_reqs = []

    pending = get_pending_count(user)
    return render_template("product_chats.html",
                           product=dict(product),
                           all_reqs=all_reqs,
                           current_user=user,
                           pending_count=pending,
                           SUPABASE_URL=SUPABASE_URL,
                           SUPABASE_KEY=SUPABASE_KEY)


# ---------------- CHAT_SELLER shortcut (buyer opens chat) ----------------
@app.route("/chat_seller/<int:product_id>")
def chat_seller(product_id):
    if not session.get("user"):
        flash("Please log in.")
        return redirect(url_for("login"))
    return redirect(url_for("chat_page", product_id=product_id, buyer=session["user"]))


# ---------------- CHAT PAGE ----------------
@app.route("/chat/<int:product_id>/<buyer>")
def chat_page(product_id, buyer):
    if not session.get("user"):
        flash("Please log in.")
        return redirect(url_for("login"))

    current_user = session["user"]

    reqs = sb_get("chat_requests",
                  f"product_id=eq.{product_id}&buyer=eq.{buyer}&status=eq.accepted&select=*")
    if not reqs or len(reqs) == 0:
        flash("Chat not available. The request may be pending or declined.")
        return redirect(url_for("chat_inbox"))

    req    = reqs[0]
    seller = req["seller"]

    if current_user not in (buyer, seller):
        flash("You don't have access to this chat.")
        return redirect(url_for("chat_inbox"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()

    if not product:
        flash("Product not found.")
        return redirect(url_for("chat_inbox"))

    other_user = seller if current_user == buyer else buyer
    parts      = sorted([buyer, seller])
    room_id    = f"p{product_id}_{parts[0]}_{parts[1]}"
    pending    = get_pending_count(current_user)

    return render_template("chat.html",
                           product=product,
                           room_id=room_id,
                           current_user=current_user,
                           other_user=other_user,
                           pending_count=pending,
                           SUPABASE_URL=SUPABASE_URL,
                           SUPABASE_KEY=SUPABASE_KEY)


# ---------------- API: PENDING COUNT ----------------
@app.route("/api/pending_count")
def api_pending_count():
    if not session.get("user"):
        return jsonify({"count": 0, "accepted_count": 0})
    user = session["user"]
    # Seller: pending requests
    pending = get_pending_count(user)
    # Buyer: newly accepted requests (accepted but buyer hasn't opened chat yet)
    accepted_data = sb_get("chat_requests",
                           f"buyer=eq.{user}&status=eq.accepted&select=id")
    accepted_count = len(accepted_data) if isinstance(accepted_data, list) else 0
    return jsonify({"count": pending, "accepted_count": accepted_count})


# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if not session.get("user"):
        flash("Please log in to view your profile.")
        return redirect(url_for("login"))
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE name=?", (session["user"],))
    user = c.fetchone()
    c.execute("SELECT * FROM products WHERE seller=? ORDER BY id DESC", (session["user"],))
    listings = c.fetchall()
    c.execute("SELECT COUNT(*) as cnt FROM cart WHERE user=?", (session["user"],))
    cart_count = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM wishlist WHERE user=?", (session["user"],))
    wishlist_count = c.fetchone()["cnt"]
    conn.close()
    pending = get_pending_count(session.get("user"))
    return render_template("profile.html", user=user, listings=listings,
                           cart_count=cart_count, wishlist_count=wishlist_count,
                           pending_count=pending)


# ---------------- REMOVE LISTING ----------------
@app.route("/remove_listing/<int:product_id>")
def remove_listing(product_id):
    if not session.get("user"):
        return redirect(url_for("login"))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=? AND seller=?",
              (product_id, session["user"]))
    conn.commit()
    conn.close()
    flash("Listing removed.")
    return redirect(url_for("profile"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    insert_sample_products()
    app.run(debug=True)

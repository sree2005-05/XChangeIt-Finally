from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- PATH SETUP ----------------
BASE_DIR = os.getcwd()
DATABASE = os.path.join(BASE_DIR, "users.db")

print("Database will be created at:", DATABASE)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            email    TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            price        INTEGER NOT NULL,
            short_desc   TEXT,
            detailed_desc TEXT,
            category     TEXT,
            image1       TEXT,
            image2       TEXT,
            image3       TEXT,
            image4       TEXT,
            image5       TEXT,
            seller       TEXT
        )
    ''')

    # Add seller column to existing products table if it doesn't exist yet
    try:
        c.execute("ALTER TABLE products ADD COLUMN seller TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            message TEXT NOT NULL,
            year    TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user       TEXT,
            product_id INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user       TEXT,
            product_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()


# ---------------- INSERT SAMPLE PRODUCTS ----------------
def insert_sample_products():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM products")
    count = c.fetchone()[0]

    if count == 0:
        sample_products = [
            ("Engineering Calculator", 1200, "Scientific calculator",
             "Best for engineering exams. Casio fx-991EX, barely used, all functions working.",
             "buy", None, None, None, None, None, "admin"),

            ("Hostel Mattress", 800, "Comfortable mattress",
             "Single bed hostel mattress, used for one year. Clean condition, no stains.",
             "rent", None, None, None, None, None, "admin"),

            ("Mountain Cycle", 2500, "Geared mountain cycle",
             "Good condition 21-speed mountain cycle. Ideal for campus commutes. Negotiable.",
             "buy", None, None, None, None, None, "admin"),

            ("Study Table", 500, "Sturdy wooden study table",
             "Perfect study table for hostel rooms. 3x2 ft size. Minor scratches on surface.",
             "rent", None, None, None, None, None, "admin"),

            ("Data Structures Textbook", 300, "CLRS Algorithm textbook",
             "Introduction to Algorithms by CLRS, 3rd edition. Good condition, no missing pages.",
             "buy", None, None, None, None, None, "admin"),

            ("Table Fan", 450, "Usha table fan",
             "12-inch Usha table fan. Works perfectly, used for one semester.",
             "buy", None, None, None, None, None, "admin"),
        ]

        c.executemany('''
            INSERT INTO products
            (name, price, short_desc, detailed_desc, category,
             image1, image2, image3, image4, image5, seller)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_products)

        conn.commit()

    conn.close()


# ---------------- HOME ----------------
@app.route("/")
def home():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT name, message, year FROM reviews ORDER BY id DESC")
    reviews = c.fetchall()
    conn.close()

    return render_template("index.html",
                           user=session.get("user"),
                           reviews=reviews)


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

    return render_template("explore.html",
                           products=products,
                           category=category)


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

    return render_template("product_detail.html", product=product)


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user"):
        return redirect(url_for("home"))

    if request.method == "POST":
        name     = request.form["name"].strip()
        email    = request.form["email"].strip().lower()
        password = request.form["password"]

        # Basic server-side email validation
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
            c.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed)
            )
            conn.commit()
            flash("Account created successfully! Please log in.")
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
            flash("Invalid email or password. Please try again.")

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
        name    = session.get("user")
        message = request.form["message"].strip()
        year    = request.form["year"]

        if not message:
            flash("Review cannot be empty.")
            return render_template("review.html")

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO reviews (name, message, year) VALUES (?, ?, ?)",
            (name, message, year)
        )
        conn.commit()
        conn.close()

        flash("Review added successfully!")
        return redirect(url_for("home"))

    return render_template("review.html")


# ---------------- ADD TO WISHLIST ----------------
@app.route("/add_to_wishlist/<int:product_id>")
def add_to_wishlist(product_id):
    if not session.get("user"):
        flash("Please log in to add items to your wishlist.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Prevent duplicate wishlist entries
    c.execute(
        "SELECT id FROM wishlist WHERE user=? AND product_id=?",
        (session["user"], product_id)
    )
    existing = c.fetchone()

    if not existing:
        c.execute(
            "INSERT INTO wishlist (user, product_id) VALUES (?, ?)",
            (session["user"], product_id)
        )
        conn.commit()
        flash("Added to wishlist!")
    else:
        flash("Item is already in your wishlist.")

    conn.close()
    return redirect(url_for("product_detail", product_id=product_id))


# ---------------- ADD TO CART ----------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if not session.get("user"):
        flash("Please log in to add items to your cart.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Prevent duplicate cart entries
    c.execute(
        "SELECT id FROM cart WHERE user=? AND product_id=?",
        (session["user"], product_id)
    )
    existing = c.fetchone()

    if not existing:
        c.execute(
            "INSERT INTO cart (user, product_id) VALUES (?, ?)",
            (session["user"], product_id)
        )
        conn.commit()
        flash("Added to cart!")
    else:
        flash("Item is already in your cart.")

    conn.close()
    return redirect(url_for("product_detail", product_id=product_id))


# ---------------- CART PAGE ----------------
@app.route("/cart")
def cart():
    if not session.get("user"):
        flash("Please log in to view your cart.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT products.id, products.name, products.price, products.image1
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user = ?
        ORDER BY cart.id DESC
    """, (session["user"],))

    items = c.fetchall()
    conn.close()

    total = sum(item["price"] for item in items)

    return render_template("cart.html", items=items, total=total)


# ---------------- REMOVE FROM CART ----------------
@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    if not session.get("user"):
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "DELETE FROM cart WHERE user=? AND product_id=?",
        (session["user"], product_id)
    )
    conn.commit()
    conn.close()

    flash("Item removed from cart.")
    return redirect(url_for("cart"))


# ---------------- SELL PRODUCT ----------------
@app.route("/sell", methods=["GET", "POST"])
def sell():
    if not session.get("user"):
        flash("Please log in to list an item.")
        return redirect(url_for("login"))

    if request.method == "POST":
        name         = request.form["name"].strip()
        price        = request.form["price"]
        short_desc   = request.form["short_desc"].strip()
        detailed_desc = request.form["detailed_desc"].strip()
        category     = request.form["category"]
        seller       = session["user"]

        images = []
        for i in range(1, 6):
            file = request.files.get(f"image{i}")
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                images.append(filename)
            else:
                images.append(None)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO products
            (name, price, short_desc, detailed_desc, category,
             image1, image2, image3, image4, image5, seller)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, price, short_desc, detailed_desc, category,
              images[0], images[1], images[2], images[3], images[4], seller))
        conn.commit()
        conn.close()

        flash("Your item has been listed successfully!")
        return redirect(url_for("explore", category=category))

    return render_template("sell.html")


# ---------------- CHAT SELLER ----------------
@app.route("/chat_seller/<int:product_id>")
def chat_seller(product_id):
    if not session.get("user"):
        flash("Please log in to contact the seller.")
        return redirect(url_for("login"))

    # Future: redirect to WhatsApp or internal chat
    flash("Chat feature coming soon! Contact the seller on campus.")
    return redirect(url_for("product_detail", product_id=product_id))


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    insert_sample_products()
    app.run(debug=True)

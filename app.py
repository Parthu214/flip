from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-key"
DB = "shop.db"

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def setup():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user');
        CREATE TABLE IF NOT EXISTS products (
          id INTEGER PRIMARY KEY, name TEXT, description TEXT, price REAL);
        CREATE TABLE IF NOT EXISTS orders (
          id INTEGER PRIMARY KEY, username TEXT, items TEXT, total REAL, status TEXT DEFAULT 'Placed');
        """)
        con.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES('admin','admin123','admin')")
        if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            con.executemany("INSERT INTO products(name,description,price) VALUES(?,?,?)", [
                ("Headphones", "Wireless headphones for everyday use", 1299),
                ("Smart Watch", "Simple watch for daily activities", 1999),
                ("Backpack", "Bag for college and travel", 899),
                ("Sneakers", "Comfortable everyday shoes", 1599)])

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access only.")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    with db() as con:
        products = con.execute("SELECT * FROM products").fetchall()
    return render_template("index.html", products=products)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE username=? AND password=?",
                (request.form["username"], request.form["password"])).fetchone()
        if user:
            session["username"], session["role"] = user["username"], user["role"]
            return redirect(url_for("home"))
        flash("Incorrect username or password.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username, password = request.form["username"].strip(), request.form["password"]
        try:
            with db() as con:
                con.execute("INSERT INTO users(username,password) VALUES(?,?)", (username, password))
            flash("Account created. Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/order/<int:product_id>", methods=["POST"])
@login_required
def order(product_id):
    with db() as con:
        product = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product:
            con.execute("INSERT INTO orders(username,items,total) VALUES(?,?,?)",
                (session["username"], product["name"], product["price"]))
            flash("Order placed successfully!")
        else:
            flash("Product not found.")
    return redirect(url_for("home"))

@app.route("/orders")
@login_required
def orders():
    with db() as con:
        rows = con.execute("SELECT * FROM orders WHERE username=? ORDER BY id DESC",
                           (session["username"],)).fetchall()
    return render_template("orders.html", orders=rows)

@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    with db() as con:
        if request.method == "POST":
            name = request.form["name"].strip()
            description = request.form["description"].strip()
            try:
                price = float(request.form["price"])
            except ValueError:
                price = 0
            if name and description and price > 0:
                con.execute("INSERT INTO products(name,description,price) VALUES(?,?,?)",
                            (name, description, price))
                flash("Product added.")
                return redirect(url_for("admin"))
            flash("Enter valid product details.")
        products = con.execute("SELECT * FROM products").fetchall()
        all_orders = con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return render_template("admin.html", products=products, orders=all_orders)

if __name__ == "__main__":
    setup()
    app.run(debug=True)

import os
from decimal import Decimal, InvalidOperation

import requests
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for


app = Flask(__name__)
#app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")
app.secret_key = "poc-secret-key"  # fine for a local PoC

FAKE_STORE = "https://fakestoreapi.com/products"


def fetch_products():
    response = requests.get(FAKE_STORE, timeout=10)
    response.raise_for_status()
    return response.json()


def get_cart():
    # Session data is serialized, so store product IDs and quantities only.
    return session.setdefault("cart", {})


@app.get("/")
def products():
    try:
        items = fetch_products()
    except requests.RequestException:
        items = []
        flash("The product catalog is temporarily unavailable.", "error")

    return render_template("products.html", products=items)


@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    # Validate the ID against the source catalog before adding it.
    try:
        items = fetch_products()
    except requests.RequestException:
        flash("Could not reach the product catalog. Please try again.", "error")
        return redirect(url_for("products"))

    if not any(item["id"] == product_id for item in items):
        abort(404)

    cart = get_cart()
    key = str(product_id)
    cart[key] = int(cart.get(key, 0)) + 1
    session.modified = True
    flash("Added to cart.", "success")
    return redirect(url_for("products"))


@app.get("/cart")
def cart():
    try:
        catalog = {str(item["id"]): item for item in fetch_products()}
    except requests.RequestException:
        catalog = {}
        flash("Could not load product details for your cart.", "error")

    cart_items = []
    total = Decimal("0.00")

    for product_id, quantity in get_cart().items():
        product = catalog.get(product_id)
        if not product:
            continue

        price = Decimal(str(product["price"]))
        quantity = int(quantity)
        total += price * quantity
        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": price * quantity,
        })

    return render_template("cart.html", cart_items=cart_items, total=total)


@app.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    get_cart().pop(str(product_id), None)
    session.modified = True
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not get_cart():
        flash("Your cart is empty.", "error")
        return redirect(url_for("products"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Please enter your name.", "error")
            return redirect(url_for("checkout"))

        session.pop("cart", None)
        return render_template("checkout.html", order_name=name, completed=True)

    return render_template("checkout.html", completed=False)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
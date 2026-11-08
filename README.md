# Flask Shop Demo

A deliberately **thin** Flask + Jinja e-commerce frontend used as the **UI under
test** for the [`smart-qa-framework-python`](https://github.com/fransuarez/smart-qa-framework-python)
hybrid API + UI test suite.

- **Product catalog** comes from the real, external
  [Fake Store API](https://fakestoreapi.com) (read-only).
- **Cart and checkout** state live entirely in the **Flask session** — there is
  no database, no migrations, and no server-side persistence.

> **Why so minimal?** The test framework is the deliverable. This app exists to
> give Playwright a stable, controllable UI to drive, backed by a real catalog.
> Keeping it small (no DB, no admin, no auth) makes it trivial to run from any
> terminal with `flask run`.

> **Important** — Fake Store API's write endpoints (`/carts`, etc.) are
> **simulated and do not persist**. This app never calls them. The catalog is
> read-only; the cart belongs to the session, not to Fake Store.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Routes](#routes)
- [Session Model](#session-model)
- [Configuration](#configuration)
- [Testing Hooks](#testing-hooks)
- [Project Structure](#project-structure)
- [Known Limitations](#known-limitations)
- [Related Repository](#related-repository)

## Features

- Product grid rendered from Fake Store API (`GET https://fakestoreapi.com/products`)
- Add-to-cart with **server-side validation** of the product ID against the catalog
- Quantity-aware session cart (`{ "<product_id>": <quantity> }`)
- Remove-from-cart by product ID
- Simple checkout form (name only; no payment)
- Flash messages for success and error paths
- Money math via `Decimal` (no float rounding surprises)
- **No database, no migrations, no admin UI**

## Prerequisites

- Python 3.9+
- `pip`
- Network access to `https://fakestoreapi.com` (the catalog is fetched live per
  request; without network the UI renders an error flash and an empty grid)

No Docker, no SQLite, no environment file required for local use.

## Installation

```bash
git clone git@github.com:fransuarez/flask-shop-demo.git
cd flask-shop-demo

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install flask requests
```

## Running the App

```bash
flask run                          # http://127.0.0.1:5000
# or:
python app.py
```

`app.py` runs with `debug=True` and `port=5000` when executed directly. For a
test/CI run, prefer `flask run` with `FLASK_DEBUG=0` so template edits do not
trigger auto-reload mid-scenario.

## Routes

All routes are defined in `app.py`. This table is the contract the test suite
depends on — **if any row changes, update both this README and the test-repo
README in the same PR.**

| Method | Path | Behavior |
| :--- | :--- | :--- |
| `GET` | `/` | Fetches the Fake Store catalog and renders `products.html`. On `requests.RequestException`: renders an empty grid + flash `"The product catalog is temporarily unavailable."` |
| `POST` | `/cart/add/<int:product_id>` | Re-fetches the catalog to **validate the ID**. Unknown ID → `404`. Known ID → increments `session["cart"][str(id)]` by 1, flashes `"Added to cart."`, redirects to `/`. On catalog error → flash `"Could not reach the product catalog. Please try again."` and redirect to `/`. |
| `GET` | `/cart` | Fetches the catalog, builds `{product, quantity, subtotal}` rows, computes `total` as `Decimal`, renders `cart.html`. On catalog error → flash `"Could not load product details for your cart."` |
| `POST` | `/cart/remove/<int:product_id>` | Removes the ID from `session["cart"]`, redirects to `/cart`. |
| `GET` | `/checkout` | **If cart is empty → redirects to `/` with flash `"Your cart is empty."`**. Otherwise renders `checkout.html` with `completed=False`. |
| `POST` | `/checkout` | Same empty-cart guard. Requires a non-empty form field `name`. Missing → flash `"Please enter your name."` and redirect to `/checkout` (**cart is not cleared**). Success → clears `session["cart"]`, renders `checkout.html` with `completed=True` and `order_name=<name>`. |

## Session Model

Cart state is stored **only** in the signed Flask session cookie. It never
touches the server filesystem or a database.

- Shape: `session["cart"]` is a **dict** mapping product ID (string) → quantity (int).
  Example: `{"1": 2, "5": 1}`.
- Product details are **not** stored in the session — only IDs and quantities.
  The catalog is re-fetched on every page that needs product data.
- Adding the same product twice increments its quantity; it does not duplicate rows.
- `POST /checkout` (success) clears the cart via `session.pop("cart", None)`.

Consequences for testers:

- Each browser context starts with an **empty cart** — no reset fixture needed
  beyond a fresh cookie jar.
- Cart assertions must be **quantity-aware**, not "the row appears exactly once."
- Because the catalog is re-fetched on `/`, `/cart/add`, and `/cart`, a network
  blip can surface as an error flash mid-scenario — see *Known Limitations*.

## Configuration

There are no required environment variables for local use. `app.py` hardcodes:

| Setting | Value | Notes |
| :--- | :--- | :--- |
| `app.secret_key` | `"poc-secret-key"` | **PoC only.** Must be replaced before any deployment. The commented-out `os.environ.get("FLASK_SECRET_KEY", …)` line shows the intended production shape. |
| `FAKE_STORE` | `https://fakestoreapi.com/products` | Catalog endpoint. |
| Port | `5000` (when run via `python app.py`) | `flask run` default is also `5000`. |

Optional override for tests, if you prefer to keep the URL configurable:

```bash
export FAKESTORE_BASE_URL="https://fakestoreapi.com"
```

(This is a test-suite convention; `app.py` currently hardcodes the URL.)

## Testing Hooks

All UI elements addressed by the test suite carry a `data-testid` attribute.
Tests select by these only — never by CSS classes or XPath.

| Element | Selector | Location |
| :--- | :--- | :--- |
| Product card | `[data-testid="product-card"][data-product-id="<id>"]` | `products.html` |
| Add to cart | `[data-testid="add-to-cart-<id>"]` | `products.html` |
| Empty catalog | `[data-testid="products-empty"]` | `products.html` |
| Cart link (header) | `[data-testid="cart-link"]` | `base.html` |
| Cart row | `[data-testid="cart-row"][data-product-id="<id>"]` | `cart.html` |
| Cart quantity | `[data-testid="cart-qty-<id>"]` | `cart.html` |
| Remove from cart | `[data-testid="remove-from-cart-<id>"]` | `cart.html` |
| Empty cart | `[data-testid="cart-empty"]` | `cart.html` |
| Checkout button | `[data-testid="checkout-btn"]` | `cart.html` |
| Name input | `[data-testid="checkout-name"]` | `checkout.html` |
| Place order | `[data-testid="confirm-order"]` | `checkout.html` |
| Order confirmation (Applitools anchor) | `[data-testid="order-confirmed"]` | `checkout.html` |
| Flash message | `[data-testid="flash"][data-category="<success\|error>"]` | `base.html` |

If a hook is missing, add it here — never fall back to CSS or XPath in the tests.

## Project Structure

```
flask-shop-demo/
├── app.py                  # Flask app: routes, catalog fetch, session cart
├── requirements.txt        # flask, requests
├── README.md
└── templates/
    ├── products.html       # product grid (GET /)
    ├── cart.html           # cart table (GET /cart)
    └── checkout.html       # form (GET) + confirmation (POST)
```

There is no `models.py`, `migrations/`, `static/` bundle, or admin blueprint —
and that is intentional. If any of those appear later, this README must change
with them.

## Known Limitations

These are deliberate choices for a PoC. They are not bugs.

- **No persistence.** Restarting the Flask process, or clearing cookies, empties
  the cart. Nothing is written to disk.
- **Catalog re-fetched per request.** `/`, `/cart/add/<id>`, and `/cart` each
  call Fake Store live. This is what makes the "add validates the ID" behavior
  possible, but it also means a network failure can surface mid-flow. Tests
  should treat catalog failures as **skips**, not failures.
- **No auth, no admin, no pagination.** Fake Store returns 20 products; the UI
  renders all of them.
- **`debug=True` when run via `python app.py`.** Auto-reload is convenient
  locally but noisy for automation — prefer `flask run` with debug off for CI.
- **Hardcoded `secret_key`.** Fine for a local PoC; a real deployment must
  source it from the environment.
- **Checkout clears the cart before rendering the confirmation.** A refresh of
  the confirmation page will not preserve the order details; the flow is
  one-shot by design.
- **`POST /cart/add/<id>` aborts with `404` for IDs not in the catalog.** This
  is a testable behavior — include it in negative scenarios.

## Related Repository

The hybrid API + UI test framework that drives this app lives at
[`smart-qa-framework-python`](https://github.com/fransuarez/smart-qa-framework-python).
Its README documents:

- the three-layer split (Fake Store → this app → test harness),
- the `data-testid` contract (mirrored in *Testing Hooks* above),
- test isolation via session reset,
- the demo flow used by the framework.

If a route or hook changes here, update the test-repo README in the same change.

## License

Not yet chosen. A `LICENSE` file will be added before any public release.
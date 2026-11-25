import pytest
import app as shop


@pytest.fixture
def client(monkeypatch):
    known_product = {
        "id": 999,
        "title": "Test Product",
        "price": 12.50,
        "description": "A fixed test product.",
        "category": "test",
        "image": "https://example.test/product.png",
    }

    monkeypatch.setattr(shop, "fetch_products", lambda: [known_product])

    shop.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
    )

    with shop.app.test_client() as client:
        yield client


def test_add_known_product_to_cart(client):
    response = client.post("/cart/add/999", follow_redirects=True)

    assert response.status_code == 200
    assert b"Added to cart." in response.data

    response = client.get("/cart")
    assert b"Test Product" in response.data

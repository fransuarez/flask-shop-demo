def test_add_known_product_to_cart(client):
    response = client.post("/cart/add/999", follow_redirects=True)
    assert response.status_code == 200
    assert b"Added to cart." in response.data

    response = client.get("/cart")
    assert b"Test Product" in response.data

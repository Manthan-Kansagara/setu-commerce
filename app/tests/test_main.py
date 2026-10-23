
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Welcome to {settings.APP_NAME} API"
    }


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_products():
    response = client.get("/products/?skip=0&limit=2")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 2


def test_create_product():
    product_data = {
        "name": "Pytest Test Product",
        "description": "Product created during API testing",
        "price": "499.99",
    }

    response = client.post("/products/", json=product_data)

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["description"] == product_data["description"]
    assert float(data["price"]) == 499.99
    assert isinstance(data["id"], int)


def test_get_product_by_id():
    product_data = {
        "name": "Product Retrieval Test",
        "description": "Testing retrieval by ID",
        "price": "299.99",
    }

    create_response = client.post("/products/", json=product_data)
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["id"] == product_id
    assert response.json()["name"] == product_data["name"]

    # Clean up the test product
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204


def test_get_product_not_found():
    response = client.get("/products/999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_update_product():
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "Original Product",
            "description": "Original description",
            "price": "199.99",
        },
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Update the product
    update_response = client.put(
        f"/products/{product_id}",
        json={
            "name": "Updated Product",
            "description": "Updated description",
            "price": "399.99",
        },
    )

    assert update_response.status_code == 200

    updated_product = update_response.json()
    assert updated_product["id"] == product_id
    assert updated_product["name"] == "Updated Product"
    assert updated_product["description"] == "Updated description"
    assert float(updated_product["price"]) == 399.99

    # Clean up the test product
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204


def test_patch_product():
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "Original Product",
            "description": "Keep this description",
            "price": "199.99",
        },
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Update only the name
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"name": "Patched Product"},
    )

    assert patch_response.status_code == 200

    patched_product = patch_response.json()
    assert patched_product["name"] == "Patched Product"
    assert patched_product["description"] == "Keep this description"
    assert float(patched_product["price"]) == 199.99

    # Clean up the test product
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204


def test_delete_product():
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "Product To Delete",
            "description": "Temporary test product",
            "price": "149.99",
        },
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Delete the product
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    # Verify that the product no longer exists
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Product not found"}


def test_create_product_with_invalid_data():
    invalid_products = [
        {
            "name": "Invalid Price",
            "description": "Price must be positive",
            "price": "-10.00",
        },
        {
            "name": "",
            "description": "Name must not be empty",
            "price": "100.00",
        },
        {
            "name": "Invalid Precision",
            "description": "Price has too many decimal places",
            "price": "10.999",
        },
    ]

    for product_data in invalid_products:
        response = client.post("/products/", json=product_data)
        assert response.status_code == 422

def test_delete_product_not_found():
    response = client.delete("/products/999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

def test_update_product_not_found():
    response = client.put(
        "/products/999999999",
        json={
            "name": "Updated Product",
            "description": "This product does not exist",
            "price": "299.99",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

def test_patch_product_not_found():
    response = client.patch(
        "/products/999999999",
        json={"name": "Updated Product"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_patch_product_with_empty_data():
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "PATCH Validation Test",
            "description": "Testing empty PATCH data",
            "price": "199.99",
        },
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Try to update without providing any fields
    patch_response = client.patch(
        f"/products/{product_id}",
        json={},
    )

    assert patch_response.status_code == 422

    # Clean up the test product
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

def test_get_product_with_invalid_id():
    response = client.get("/products/abc")

    assert response.status_code == 422

def test_delete_product_with_invalid_id():
    response = client.delete("/products/abc")

    assert response.status_code == 422

def test_update_product_with_invalid_id():
    response = client.put(
        "/products/abc",
        json={
            "name": "Updated Product",
            "description": "Testing invalid ID",
            "price": "299.99",
        },
    )

    assert response.status_code == 422

def test_patch_product_with_invalid_id():
    response = client.patch(
        "/products/abc",
        json={"name": "Updated Product"},
    )

    assert response.status_code == 422

def test_create_product_missing_required_field():
    response = client.post(
        "/products/",
        json={
            "name": "Incomplete Product",
            "description": "Price is missing",
        },
    )

    assert response.status_code == 422

def test_create_product_missing_name():
    response = client.post(
        "/products/",
        json={
            "description": "Name is missing",
            "price": "199.99",
        },
    )

    assert response.status_code == 422

def test_create_product_with_empty_data():
    response = client.post("/products/", json={})

    assert response.status_code == 422

def test_create_product_with_long_name():
    product_data = {
        "name": "A" * 151,
        "description": "Testing maximum name length",
        "price": "199.99",
    }

    response = client.post("/products/", json=product_data)

    assert response.status_code == 422


def test_create_product_with_empty_name():
    response = client.post(
        "/products/",
        json={
            "name": "",
            "description": "Testing empty product name",
            "price": "199.99",
        },
    )

    assert response.status_code == 422

def test_create_product_with_long_description():
    product_data = {
        "name": "Description Length Test",
        "description": "A" * 1001,
        "price": "199.99",
    }

    response = client.post("/products/", json=product_data)

    assert response.status_code == 422

def test_create_product_without_description():
    response = client.post(
        "/products/",
        json={
            "name": "Product Without Description",
            "price": "99.99",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Product Without Description"
    assert data["description"] is None

    # Clean up the test product
    product_id = data["id"]
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

def test_create_product_with_zero_price():
    response = client.post(
        "/products/",
        json={
            "name": "Zero Price Product",
            "description": "Testing zero price validation",
            "price": "0.00",
        },
    )

    assert response.status_code == 422

def test_create_product_with_negative_price():
    response = client.post(
        "/products/",
        json={
            "name": "Negative Price Product",
            "description": "Testing negative price validation",
            "price": "-10.00",
        },
    )

    assert response.status_code == 422

def test_create_product_with_excessively_large_price():
    response = client.post(
        "/products/",
        json={
            "name": "Expensive Product",
            "description": "Testing maximum price digits",
            "price": "123456789.99",
        },
    )

    assert response.status_code == 422

def test_create_product_with_two_decimal_places():
    response = client.post(
        "/products/",
        json={
            "name": "Valid Decimal Price Product",
            "description": "Testing valid decimal precision",
            "price": "99.99",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Valid Decimal Price Product"
    assert float(data["price"]) == 99.99

    # Clean up the test product
    product_id = data["id"]
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

def test_create_product_with_maximum_name_length():
    product_name = "A" * 150

    response = client.post(
        "/products/",
        json={
            "name": product_name,
            "description": "Testing maximum valid name length",
            "price": "199.99",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == product_name

    # Clean up the test product
    product_id = response.json()["id"]
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

def test_patch_product_description_only():
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "PATCH Description Test",
            "description": "Original description",
            "price": "249.99",
        },
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Update only the description
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"description": "Updated description"},
    )

    assert patch_response.status_code == 200

    product = patch_response.json()
    assert product["name"] == "PATCH Description Test"
    assert product["description"] == "Updated description"
    assert float(product["price"]) == 249.99

    # Clean up
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

def test_patch_product_price_only():
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "PATCH Price Test",
            "description": "Keep this description",
            "price": "199.99",
        },
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Update only the price
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"price": "349.99"},
    )

    assert patch_response.status_code == 200

    product = patch_response.json()
    assert product["name"] == "PATCH Price Test"
    assert product["description"] == "Keep this description"
    assert float(product["price"]) == 349.99

    # Clean up
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

def test_patch_product_with_null_name():
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "Null Validation Test",
            "description": "Testing null name",
            "price": "199.99",
        },
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # A product name must not be null
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"name": None},
    )

    assert patch_response.status_code == 422

    # Clean up
    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

def test_get_products_with_invalid_limit():
    response = client.get("/products/?limit=101")

    assert response.status_code == 422

def test_get_products_with_negative_skip():
    response = client.get("/products/?skip=-1")

    assert response.status_code == 422

def test_get_products_with_zero_skip():
    response = client.get("/products/?skip=0&limit=2")

    assert response.status_code == 200
    assert len(response.json()) <= 2


def test_get_products_with_minimum_limit():
    response = client.get("/products/?limit=1")

    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_get_products_with_zero_limit():
    response = client.get("/products/?limit=0")

    assert response.status_code == 422


def test_get_products_with_negative_limit():
    response = client.get("/products/?limit=-5")

    assert response.status_code == 422

def test_get_products_with_large_skip():
    response = client.get("/products/?skip=10000&limit=20")

    assert response.status_code == 200
    assert response.json() == []


def test_get_products_with_maximum_limit():
    response = client.get("/products/?limit=100")

    assert response.status_code == 200
    assert len(response.json()) <= 100


def test_get_products_with_negative_skip_and_limit():
    response = client.get("/products/?skip=-1&limit=-5")

    assert response.status_code == 422

def test_get_products_returns_json():
    response = client.get("/products/")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_get_products_with_limit_one():
    response = client.get("/products/?limit=1")

    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_get_products_with_skip_and_limit():
    response = client.get("/products/?skip=1&limit=2")

    assert response.status_code == 200
    assert len(response.json()) <= 2

def test_get_products_with_non_integer_skip():
    response = client.get("/products/?skip=abc")

    assert response.status_code == 422


def test_get_products_with_non_integer_limit():
    response = client.get("/products/?limit=abc")

    assert response.status_code == 422


def test_get_products_with_limit_above_maximum():
    response = client.get("/products/?limit=101")

    assert response.status_code == 422
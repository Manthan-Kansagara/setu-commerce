import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from app.core.config import settings
from app.core.base import Base
from app.core.database import TestSessionLocal, test_engine
from app.core.dependencies import get_db
from app.main import app
from app.models import Product, User

from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.security import create_access_token

from app.core.security import hash_password, verify_password
from pydantic import ValidationError
from app.schemas.user import UserCreate, UserResponse


from datetime import timedelta
import jwt
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token

Base.metadata.drop_all(bind=test_engine)
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def override_database_dependency():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_products():
    def clear_database():
        with TestSessionLocal() as db:
            db.execute(delete(Product))
            db.execute(delete(User))
            db.commit()

    clear_database()
    yield
    clear_database()


client = TestClient(app)



def get_auth_headers(
    email: str = "seller@example.com",
    password: str = "SecurePass123!",
) -> dict[str, str]:
    registration = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )

    assert registration.status_code == 201

    # Promote this test user to seller in the test database.
    with TestSessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == email)
        )
        assert user is not None
        user.role = "seller"
        db.commit()

    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert login.status_code == 200

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}



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

    response = client.post("/products/", json=product_data, headers=get_auth_headers())

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["description"] == product_data["description"]
    assert float(data["price"]) == 499.99
    assert isinstance(data["id"], int)


def test_get_product_database_failure():
    class FakeDB:
        def scalar(self, statement):
            raise RuntimeError("Simulated database query failure")

    fake_db = FakeDB()

    def override_failed_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_failed_db

    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/products/999")

        assert response.status_code == 500
    finally:
        app.dependency_overrides[get_db] = override_get_db


def test_get_products_database_failure():
    class FakeDB:
        def scalars(self, statement):
            raise RuntimeError("Simulated database query failure")

    fake_db = FakeDB()

    def override_failed_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_failed_db

    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/products/")

        assert response.status_code == 500
    finally:
        app.dependency_overrides[get_db] = override_get_db


def test_create_product_database_failure():
    
    class FakeDB:
        def add(self, product):
            pass

        def commit(self):
            raise RuntimeError("Simulated database failure")

        def refresh(self, product):
            pass

        def rollback(self):
            self.rollback_called = True

    fake_db = FakeDB()
    fake_db.rollback_called = False

    def override_failed_db():
        yield fake_db

    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="seller@example.com",
        password_hash="test-hash",
        is_active=True,
        role="seller",
    )
    app.dependency_overrides[get_db] = override_failed_db

    try:
        response = client.post(
            "/products/",
            json={
                "name": "Failure Test Product",
                "description": "Testing database failure",
                "price": "10.00",
            },
        )

        assert response.status_code == 500
        assert response.json() == {
            "detail": "Failed to create product"
        }
        assert fake_db.rollback_called is True
    finally:
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.pop(get_current_user, None)

def test_get_product_by_id():
    headers = get_auth_headers()
    product_data = {
        "name": "Product Retrieval Test",
        "description": "Testing retrieval by ID",
        "price": "299.99",
    }

    create_response = client.post("/products/", json=product_data,headers=headers)
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["id"] == product_id
    assert response.json()["name"] == product_data["name"]

    # Clean up the test product
    delete_response = client.delete(
        f"/products/{product_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204


def test_get_product_not_found():
    response = client.get("/products/999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_update_product_database_failure():
    class FakeDB:
        rollback_called = False

        def scalar(self, statement):
            return Product(
                id=999,
                name="Original Product",
                description="Original description",
                price="10.00",
                seller_id=1,
            )

        def commit(self):
            raise RuntimeError("Simulated database failure")

        def refresh(self, product):
            pass

        def rollback(self):
            self.rollback_called = True

    fake_db = FakeDB()

    def override_failed_db():
        yield fake_db

    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="seller@example.com",
        password_hash="test-hash",
        is_active=True,
        role="seller",
    )
    app.dependency_overrides[get_db] = override_failed_db

    try:
        response = client.put(
            "/products/999",
            json={
                "name": "Updated Product",
                "description": "Updated description",
                "price": "20.00",
            },
        )

        assert response.status_code == 500
        assert response.json() == {
            "detail": "Failed to update product"
        }
        assert fake_db.rollback_called is True
    finally:
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.pop(get_current_user, None)


def test_update_product():
    # Create a product
    headers = get_auth_headers()
    create_response = client.post(
        "/products/",
        json={
            "name": "Original Product",
            "description": "Original description",
            "price": "199.99",
        },
        headers=headers
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
        headers=headers
    )

    assert update_response.status_code == 200

    updated_product = update_response.json()
    assert updated_product["id"] == product_id
    assert updated_product["name"] == "Updated Product"
    assert updated_product["description"] == "Updated description"
    assert float(updated_product["price"]) == 399.99

    # Clean up the test product
    delete_response = client.delete(
        f"/products/{product_id}",
        headers=headers,
    )   
    assert delete_response.status_code == 204


def test_patch_product():
    # Create a product
    headers = get_auth_headers()
    create_response = client.post(
        "/products/",
        json={
            "name": "Original Product",
            "description": "Keep this description",
            "price": "199.99",
        },
        headers=headers
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Update only the name
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"name": "Patched Product"},
        headers=headers
    )

    assert patch_response.status_code == 200

    patched_product = patch_response.json()
    assert patched_product["name"] == "Patched Product"
    assert patched_product["description"] == "Keep this description"
    assert float(patched_product["price"]) == 199.99

    # Clean up the test product
    delete_response = client.delete(f"/products/{product_id}",headers=headers)
    assert delete_response.status_code == 204


def test_delete_product_database_failure():
    class FakeDB:
        rollback_called = False

        def scalar(self, statement):
            return Product(
                id=999,
                name="Product to Delete",
                description="Testing deletion failure",
                price="10.00",
                seller_id=1,
            )

        def delete(self, product):
            pass

        def commit(self):
            raise RuntimeError("Simulated database failure")

        def rollback(self):
            self.rollback_called = True

    fake_db = FakeDB()

    def override_failed_db():
        yield fake_db

    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="seller@example.com",
        password_hash="test-hash",
        is_active=True,
        role="seller",
    )
    app.dependency_overrides[get_db] = override_failed_db

    try:
        response = client.delete("/products/999")

        assert response.status_code == 500
        assert response.json() == {
            "detail": "Failed to delete product"
        }
        assert fake_db.rollback_called is True
    finally:
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.pop(get_current_user, None)


def test_delete_product():
    headers = get_auth_headers()
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "Product To Delete",
            "description": "Temporary test product",
            "price": "149.99",
        },
        headers=headers
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Delete the product
    delete_response = client.delete(
        f"/products/{product_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    # Verify that the product no longer exists
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Product not found"}

def test_create_product_with_invalid_data():
    headers = get_auth_headers()

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
        response = client.post(
            "/products/",
            json=product_data,
            headers=headers,
        )
        assert response.status_code == 422



def test_delete_product_not_found():
    response = client.delete("/products/999999999", headers=get_auth_headers())

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
        headers=get_auth_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

def test_patch_product_not_found():
    response = client.patch(
        "/products/999999999",
        json={"name": "Updated Product"},
        headers=get_auth_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_patch_product_with_empty_data():
    headers = get_auth_headers()
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "PATCH Validation Test",
            "description": "Testing empty PATCH data",
            "price": "199.99",
        },
        headers=headers
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Try to update without providing any fields
    patch_response = client.patch(
        f"/products/{product_id}",
        json={},
        headers=headers,
    )

    assert patch_response.status_code == 422

    # Clean up the test product
    delete_response = client.delete(f"/products/{product_id}", headers=headers)
    assert delete_response.status_code == 204

def test_get_product_with_invalid_id():
    response = client.get("/products/abc")

    assert response.status_code == 422

def test_delete_product_with_invalid_id():
    response = client.delete("/products/abc", headers=get_auth_headers())

    assert response.status_code == 422

def test_update_product_with_invalid_id():
    response = client.put(
        "/products/abc",
        json={
            "name": "Updated Product",
            "description": "Testing invalid ID",
            "price": "299.99",
        },
        headers=get_auth_headers(),
    )

    assert response.status_code == 422

def test_patch_product_with_invalid_id():
    response = client.patch(
        "/products/abc",
        json={"name": "Updated Product"},
        headers=get_auth_headers(),
    )

    assert response.status_code == 422

def test_create_product_missing_required_field():
    headers = get_auth_headers()

    response = client.post(
        "/products/",
        json={
            "name": "Incomplete Product",
            "description": "Price is missing",
        },
        headers=headers,
    )

    assert response.status_code == 422

def test_create_product_missing_name():
    headers = get_auth_headers()

    response = client.post(
        "/products/",
        json={
            "description": "Name is missing",
            "price": "199.99",
        },
        headers=headers,
    )

    assert response.status_code == 422

def test_create_product_with_empty_data():
    headers = get_auth_headers()

    response = client.post(
        "/products/",
        json={},
        headers=headers,
    )

    assert response.status_code == 422

def test_create_product_with_long_name():
    headers = get_auth_headers()

    product_data = {
        "name": "A" * 151,
        "description": "Testing maximum name length",
        "price": "199.99",
    }

    response = client.post(
        "/products/",
        json=product_data,
        headers=headers,
    )

    assert response.status_code == 422


def test_create_product_with_empty_name():
    headers = get_auth_headers()
    response = client.post(
        "/products/",
        json={
            "name": "",
            "description": "Testing empty product name",
            "price": "199.99",
        },
        headers=headers
    )

    assert response.status_code == 422

def test_create_product_with_long_description():
    headers = get_auth_headers()
    product_data = {
        "name": "Description Length Test",
        "description": "A" * 1001,
        "price": "199.99",
    }

    response = client.post("/products/", json=product_data,headers=headers)

    assert response.status_code == 422

def test_create_product_without_description():
    headers = get_auth_headers()
    response = client.post(
        "/products/",
        json={
            "name": "Product Without Description",
            "price": "99.99",
        },
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Product Without Description"
    assert data["description"] is None

    # Clean up the test product
    product_id = data["id"]
    delete_response = client.delete(f"/products/{product_id}", headers=headers)
    assert delete_response.status_code == 204

def test_create_product_with_zero_price():
    headers = get_auth_headers()
    response = client.post(
        "/products/",
        json={
            "name": "Zero Price Product",
            "description": "Testing zero price validation",
            "price": "0.00",
        },
        headers=headers
    )

    assert response.status_code == 422

def test_create_product_with_negative_price():
    headers = get_auth_headers()

    response = client.post(
        "/products/",
        json={
            "name": "Negative Price Product",
            "description": "Testing negative price validation",
            "price": "-10.00",
        },
        headers=headers
    )

    assert response.status_code == 422

def test_create_product_with_excessively_large_price():
    headers = get_auth_headers()

    response = client.post(
        "/products/",
        json={
            "name": "Expensive Product",
            "description": "Testing maximum price digits",
            "price": "123456789.99",
        },
        headers=headers
    )

    assert response.status_code == 422

def test_create_product_with_two_decimal_places():
    headers = get_auth_headers()

    response = client.post(
        "/products/",
        json={
            "name": "Valid Decimal Price Product",
            "description": "Testing valid decimal precision",
            "price": "99.99",
        },
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Valid Decimal Price Product"
    assert float(data["price"]) == 99.99

    # Clean up the test product
    product_id = data["id"]
    delete_response = client.delete(f"/products/{product_id}", headers=headers)
    assert delete_response.status_code == 204

def test_create_product_with_maximum_name_length():
    headers = get_auth_headers()

    product_name = "A" * 150

    response = client.post(
        "/products/",
        json={
            "name": product_name,
            "description": "Testing maximum valid name length",
            "price": "199.99",
        },
        headers=headers
    )

    assert response.status_code == 201
    assert response.json()["name"] == product_name

    # Clean up the test product
    product_id = response.json()["id"]
    delete_response = client.delete(f"/products/{product_id}", headers=headers)
    assert delete_response.status_code == 204

def test_patch_product_description_only():
    headers = get_auth_headers()
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "PATCH Description Test",
            "description": "Original description",
            "price": "249.99",
        },
        headers=headers
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Update only the description
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"description": "Updated description"},
        headers=headers,
    )

    assert patch_response.status_code == 200

    product = patch_response.json()
    assert product["name"] == "PATCH Description Test"
    assert product["description"] == "Updated description"
    assert float(product["price"]) == 249.99

    # Clean up
    delete_response = client.delete(f"/products/{product_id}", headers=headers)
    assert delete_response.status_code == 204

def test_patch_product_price_only():
    headers = get_auth_headers()
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "PATCH Price Test",
            "description": "Keep this description",
            "price": "199.99",
        },
        headers=headers
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Update only the price
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"price": "349.99"},
        headers=headers,
    )

    assert patch_response.status_code == 200

    product = patch_response.json()
    assert product["name"] == "PATCH Price Test"
    assert product["description"] == "Keep this description"
    assert float(product["price"]) == 349.99

    # Clean up
    delete_response = client.delete(f"/products/{product_id}", headers=headers)
    assert delete_response.status_code == 204

def test_patch_product_with_null_name():
    headers = get_auth_headers()
    # Create a product
    create_response = client.post(
        "/products/",
        json={
            "name": "Null Validation Test",
            "description": "Testing null name",
            "price": "199.99",
        },
        headers=headers
    )
    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # A product name must not be null
    patch_response = client.patch(
        f"/products/{product_id}",
        json={"name": None},
        headers=headers,
    )

    assert patch_response.status_code == 422

    # Clean up
    delete_response = client.delete(f"/products/{product_id}", headers=headers)
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


def test_hash_password():
    password = "SetuSecure123!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert hashed_password.startswith("$argon2id$")


def test_verify_password():
    password = "SetuSecure123!"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True
    assert verify_password("WrongPassword123!", hashed_password) is False


def test_user_create_valid_data():
    user = UserCreate(
        email="buyer@example.com",
        password="SetuSecure123!",
    )

    assert user.email == "buyer@example.com"
    assert user.password == "SetuSecure123!"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",
            password="SetuSecure123!",
        )


def test_user_create_short_password():
    with pytest.raises(ValidationError):
        UserCreate(
            email="buyer@example.com",
            password="short",
        )


def test_user_response_excludes_password_hash():
    user = UserResponse(
        id=1,
        email="buyer@example.com",
        is_active=True,
        role="customer"
    )

    assert "password" not in user.model_dump()
    assert "password_hash" not in user.model_dump()


def test_register_user_success():
    response = client.post(
        "/auth/register",
        json={
            "email": "newbuyer@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newbuyer@example.com"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert "password" not in data
    assert response.json()["role"] == "customer"


def test_register_duplicate_email():
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePass123!",
    }

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_register_invalid_email():
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 422


def test_register_short_password():
    response = client.post(
        "/auth/register",
        json={
            "email": "buyer2@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_create_and_decode_access_token():
    token = create_access_token(subject="123")
    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert "exp" in payload


def test_decode_expired_access_token():
    token = create_access_token(
        subject="123",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_decode_access_token_with_invalid_signature():
    token = create_access_token(subject="123")
    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered_token)

def test_login_success():
    registration = client.post(
        "/auth/register",
        json={
            "email": "loginbuyer@example.com",
            "password": "SecurePass123!",
        },
    )
    assert registration.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": "loginbuyer@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["access_token"]


def test_login_wrong_password():
    client.post(
        "/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "SecurePass123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "IncorrectPass123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email():
    response = client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_inactive_user():
    registration = client.post(
        "/auth/register",
        json={
            "email": "inactive@example.com",
            "password": "SecurePass123!",
        },
    )
    assert registration.status_code == 201

    # Disable the account in the isolated test database.
    with TestSessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == "inactive@example.com")
        )
        assert user is not None
        user.is_active = False
        db.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is inactive"


def test_get_current_user_with_valid_token():
    registration = client.post(
        "/auth/register",
        json={
            "email": "currentuser@example.com",
            "password": "SecurePass123!",
        },
    )
    assert registration.status_code == 201

    with TestSessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == "currentuser@example.com")
        )
        assert user is not None
        user_id = user.id

    token = create_access_token(subject=str(user_id))

    with TestSessionLocal() as db:
        current_user = get_current_user(
            token=token,
            db=db,
        )
        assert current_user.id == user_id
        assert current_user.email == "currentuser@example.com"


def test_get_current_user_with_invalid_token():
    from fastapi import HTTPException

    with TestSessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                token="this-is-not-a-valid-token",
                db=db,
            )

    assert exc_info.value.status_code == 401


def test_get_current_user_with_nonexistent_user():
    from fastapi import HTTPException

    token = create_access_token(subject="999999999")

    with TestSessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                token=token,
                db=db,
            )

    assert exc_info.value.status_code == 401


from app.core.auth import require_role
from fastapi import HTTPException


def test_require_role_rejects_customer():
    checker = require_role("seller", "admin")

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=User(
            id=1,
            email="customer@example.com",
            password_hash="hashed-password",
            is_active=True,
            role="customer",
        ))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == (
        "You do not have permission to perform this action"
    )

def test_require_role_allows_seller():
    checker = require_role("seller", "admin")

    seller = User(
        id=2,
        email="seller@example.com",
        password_hash="hashed-password",
        is_active=True,
        role="seller",
    )

    result = checker(current_user=seller)

    assert result is seller

    

# Phase 6 hardening regression tests

def get_admin_headers(
    email: str = "admin@example.com",
    password: str = "SecurePass123!",
) -> dict[str, str]:
    registration = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert registration.status_code == 201

    with TestSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()

    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.parametrize("method,payload", [
    ("put", {"name": "Changed", "description": "Changed", "price": "25.00"}),
    ("patch", {"name": "Changed"}),
    ("delete", None),
])
def test_seller_cannot_modify_another_sellers_product(method, payload):
    owner_headers = get_auth_headers("owner@example.com")
    other_seller_headers = get_auth_headers("other-seller@example.com")

    created = client.post(
        "/products/",
        json={"name": "Owner product", "description": "Original", "price": "10.00"},
        headers=owner_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    response = getattr(client, method)(
        f"/products/{product_id}",
        headers=other_seller_headers,
        **({"json": payload} if payload is not None else {}),
    )
    assert response.status_code == 403

    # The owner can still delete the product during cleanup.
    cleanup = client.delete(f"/products/{product_id}", headers=owner_headers)
    assert cleanup.status_code == 204


def test_admin_can_manage_another_sellers_product():
    seller_headers = get_auth_headers("product-owner@example.com")
    admin_headers = get_admin_headers()

    created = client.post(
        "/products/",
        json={"name": "Seller product", "description": "Original", "price": "10.00"},
        headers=seller_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    updated = client.patch(
        f"/products/{product_id}",
        json={"name": "Admin updated product"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Admin updated product"

    deleted = client.delete(f"/products/{product_id}", headers=admin_headers)
    assert deleted.status_code == 204


def test_seller_cannot_modify_legacy_product_without_owner():
    seller_headers = get_auth_headers("legacy-test-seller@example.com")
    with TestSessionLocal() as db:
        legacy_product = Product(
            name="Legacy product",
            description="No owner assigned",
            price="12.00",
            seller_id=None,
        )
        db.add(legacy_product)
        db.commit()
        db.refresh(legacy_product)
        product_id = legacy_product.id

    response = client.patch(
        f"/products/{product_id}",
        json={"name": "Seller should not change this"},
        headers=seller_headers,
    )
    assert response.status_code == 403


def test_admin_can_manage_legacy_product_without_owner():
    admin_headers = get_admin_headers("legacy-admin@example.com")
    with TestSessionLocal() as db:
        legacy_product = Product(
            name="Legacy product for admin",
            description="No owner assigned",
            price="12.00",
            seller_id=None,
        )
        db.add(legacy_product)
        db.commit()
        db.refresh(legacy_product)
        product_id = legacy_product.id

    response = client.patch(
        f"/products/{product_id}",
        json={"name": "Admin updated legacy product"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Admin updated legacy product"


def test_public_registration_cannot_self_assign_admin_role():
    response = client.post(
        "/auth/register",
        json={
            "email": "self-promote@example.com",
            "password": "SecurePass123!",
            "role": "admin",
        },
    )
    assert response.status_code == 201

    with TestSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "self-promote@example.com"))
        assert user is not None
        assert user.role == "customer"

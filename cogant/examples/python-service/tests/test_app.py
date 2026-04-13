"""Tests for the example service application."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import app, get_db
from models import Base, UserDB, ItemDB

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up database between tests."""
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


class TestHealth:
    """Tests for health endpoints."""

    def test_root(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestUsers:
    """Tests for user endpoints."""

    def test_create_user(self):
        """Test creating a user."""
        response = client.post(
            "/api/v1/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True

    def test_create_duplicate_user(self):
        """Test that duplicate usernames are rejected."""
        # Create first user
        client.post(
            "/api/v1/users",
            json={
                "username": "duplicate",
                "email": "first@example.com",
            },
        )

        # Try to create duplicate
        response = client.post(
            "/api/v1/users",
            json={
                "username": "duplicate",
                "email": "second@example.com",
            },
        )
        assert response.status_code == 400

    def test_list_users(self):
        """Test listing users."""
        # Create users
        for i in range(3):
            client.post(
                "/api/v1/users",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                },
            )

        response = client.get("/api/v1/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 3

    def test_get_user(self):
        """Test getting a user by ID."""
        # Create user
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "getuser",
                "email": "get@example.com",
            },
        )
        user_id = create_response.json()["id"]

        # Get user
        response = client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "getuser"

    def test_get_nonexistent_user(self):
        """Test getting a nonexistent user."""
        response = client.get("/api/v1/users/9999")
        assert response.status_code == 404

    def test_update_user(self):
        """Test updating a user."""
        # Create user
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "updateuser",
                "email": "update@example.com",
                "full_name": "Original Name",
            },
        )
        user_id = create_response.json()["id"]

        # Update user
        response = client.put(
            f"/api/v1/users/{user_id}",
            json={
                "username": "updateuser",
                "email": "newemail@example.com",
                "full_name": "New Name",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name"

    def test_delete_user(self):
        """Test deleting a user."""
        # Create user
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "deleteuser",
                "email": "delete@example.com",
            },
        )
        user_id = create_response.json()["id"]

        # Delete user
        response = client.delete(f"/api/v1/users/{user_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == 404


class TestItems:
    """Tests for item endpoints."""

    @pytest.fixture
    def user_id(self):
        """Create a test user and return its ID."""
        response = client.post(
            "/api/v1/users",
            json={
                "username": "itemowner",
                "email": "owner@example.com",
            },
        )
        return response.json()["id"]

    def test_create_item(self, user_id):
        """Test creating an item."""
        response = client.post(
            "/api/v1/items",
            json={
                "name": "Test Item",
                "description": "A test item",
                "owner_id": user_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Item"

    def test_create_item_no_owner(self):
        """Test that creating item without valid owner fails."""
        response = client.post(
            "/api/v1/items",
            json={
                "name": "Orphan Item",
                "owner_id": 9999,
            },
        )
        assert response.status_code == 404

    def test_list_items(self, user_id):
        """Test listing items."""
        # Create items
        for i in range(2):
            client.post(
                "/api/v1/items",
                json={
                    "name": f"Item {i}",
                    "owner_id": user_id,
                },
            )

        response = client.get("/api/v1/items")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2

    def test_list_items_by_owner(self, user_id):
        """Test filtering items by owner."""
        # Create other user
        other_response = client.post(
            "/api/v1/users",
            json={
                "username": "otherowner",
                "email": "other@example.com",
            },
        )
        other_user_id = other_response.json()["id"]

        # Create items for both users
        client.post(
            "/api/v1/items",
            json={"name": "Item 1", "owner_id": user_id},
        )
        client.post(
            "/api/v1/items",
            json={"name": "Item 2", "owner_id": other_user_id},
        )

        # Filter by first user
        response = client.get(f"/api/v1/items?owner_id={user_id}")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["owner_id"] == user_id

    def test_update_item(self, user_id):
        """Test updating an item."""
        # Create item
        create_response = client.post(
            "/api/v1/items",
            json={
                "name": "Original Item",
                "owner_id": user_id,
            },
        )
        item_id = create_response.json()["id"]

        # Update item
        response = client.put(
            f"/api/v1/items/{item_id}",
            json={
                "name": "Updated Item",
                "description": "New description",
                "owner_id": user_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Item"

    def test_delete_item(self, user_id):
        """Test deleting an item."""
        # Create item
        create_response = client.post(
            "/api/v1/items",
            json={
                "name": "Item to delete",
                "owner_id": user_id,
            },
        )
        item_id = create_response.json()["id"]

        # Delete item
        response = client.delete(f"/api/v1/items/{item_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/v1/items/{item_id}")
        assert get_response.status_code == 404

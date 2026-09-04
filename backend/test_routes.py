import pytest
from app.models import Content, User, db


# -------------------------------------------------------------------
# FIXTURE: Setup Authenticated Test Context
# -------------------------------------------------------------------
@pytest.fixture
def auth_context(client, app):
    """Creates a primary user and authenticates to get a bearer token."""
    with app.app_context():
        user = User(
            email="writer@moringadaily.dev",
            username="writer",
            Role="user",
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.UserID

    login_res = client.post(
        "/api/auth/login",
        json={"email": "writer@moringadaily.dev", "password": "SecurePassword123!"},
    )
    token = login_res.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return headers, user_id


# ===================================================================
# HAPPY PATH TEST CASES
# ===================================================================

def test_create_content_happy_path(client, auth_context, app):
    """HAPPY CASE: Standard valid content creation request succeeds with 201 Created."""
    headers, user_id = auth_context

    payload = {
        "title": "Clean Backend Design Principles",
        "description": "Comprehensive guide to building REST APIs in Flask.",
        "content_type": "Article",
        "status": "Published"
    }

    response = client.post("/api/content", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "Content submitted successfully!"
    assert data["status"] == "Published"
    assert "content_id" in data

    # Verify database persistence
    with app.app_context():
        item = db.session.get(Content, data["content_id"])
        assert item is not None
        assert item.Title == "Clean Backend Design Principles"
        assert item.UserID == user_id


# ===================================================================
# EDGE CASE TEST CASES
# ===================================================================

def test_status_sanitization_edge_case(client, auth_context, app):
    """EDGE CASE: Malformed/lowercase status input ('draft') is sanitized to title-case ('Draft')

    preventing a raw Database CheckConstraint violation.
    """
    headers, _ = auth_context

    # Lowercase 'draft' would trigger DB CheckConstraint if not sanitized by route logic
    payload = {
        "title": "Edge Case Status Test",
        "description": "Testing status fallback and capitalization.",
        "content_type": "Article",
        "status": "draft"  
    }

    response = client.post("/api/content", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.get_json()
    assert data["status"] == "Draft"  # Must be converted to strict 'Draft'

    with app.app_context():
        item = db.session.get(Content, data["content_id"])
        assert item.Status == "Draft"


def test_cross_user_edit_unauthorized_edge_case(client, auth_context, app):
    """EDGE CASE: Non-owner/non-admin user attempts to modify another user's post.

    Should return 403 Forbidden without mutating the database state.
    """
    headers, _ = auth_context

    # Create a secondary victim user and their content item directly
    with app.app_context():
        victim = User(
            email="victim@moringadaily.dev",
            username="victim",
            Role="user"
        )
        db.session.add(victim)
        db.session.commit()

        victim_post = Content(
            Title="Victim Original Title",
            Description="Original text",
            ContentType="Article",
            Status="Published",
            UserID=victim.UserID
        )
        db.session.add(victim_post)
        db.session.commit()
        victim_post_id = victim_post.ContentID

    # Attempt to overwrite victim's content using primary user's auth headers
    response = client.put(
        f"/api/content/{victim_post_id}",
        json={"title": "Hacked Title Hijack"},
        headers=headers
    )

    assert response.status_code == 403
    assert "Forbidden" in response.get_json()["error"]

    # Example: simple route check in test_routes.py
def test_get_notifications(client):
    response = client.get('/api/users/me/notifications')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    # Verify victim content remains untouched in database
    with app.app_context():
        original_item = db.session.get(Content, victim_post_id)
        assert original_item.Title == "Victim Original Title"
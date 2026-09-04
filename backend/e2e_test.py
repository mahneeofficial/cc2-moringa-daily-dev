"""End-to-end smoke test for the fixed backend flows.

Run:  python e2e_test.py   (from the backend/ folder)
Creates a throwaway SQLite DB, starts the app in-process and exercises:
auth (user + admin signup/login), profile save/reload (skills+github),
Instagram-style post creation (JSON + multipart upload), reactions toggle,
notifications triggers, admin moderation and role security.
"""
import io
import json
import os
import sys

# Use a throwaway DB for the test
os.environ["DATABASE_URL"] = "sqlite:///e2e_test.db"
os.environ["GEMINI_API_KEY"] = ""

DB_PATH = "e2e_test.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

app = create_app("development")
app.config["TESTING"] = True

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


with app.app_context():
    db.create_all()
    from app.models import Category, Subscription

    # A category to post into
    cat = Category(Name="Frontend", Description="Frontend posts")
    db.session.add(cat)
    db.session.commit()
    CAT_ID = cat.CategoryID

client = app.test_client()


def as_user(token):
    return {"Authorization": f"Bearer {token}"}


print("\n== 1. AUTH: signup (learner / tech writer / admin) + login ==")
r = client.post("/api/auth/register", json={
    "username": "ann", "email": "ann@moringa.com", "password": "Passw0rd!", "role": "user"})
check("learner signup 201", r.status_code == 201, r.get_json())
ANN_TOKEN = r.get_json()["token"]

r = client.post("/api/auth/register", json={
    "username": "adminboss", "email": "admin@moringa.com", "password": "Passw0rd!", "role": "Admin"})
check("admin signup 201", r.status_code == 201, r.get_json())
ADMIN_TOKEN = r.get_json()["token"]
check("admin role stored as 'Admin'", r.get_json()["user"]["role"] == "Admin", r.get_json())

r = client.post("/api/auth/register", json={
    "username": "writer", "email": "writer@moringa.com", "password": "Passw0rd!", "role": "tech_writer"})
WRITER_TOKEN = r.get_json()["token"]
check("tech_writer signup 201", r.status_code == 201, r.get_json())

r = client.post("/api/auth/login", json={"username": "ann", "password": "Passw0rd!"})
check("login 200", r.status_code == 200, r.get_json())
check("login returns is_admin flag", "is_admin" in r.get_json()["user"], r.get_json())

print("\n== 1b. SEPARATE ADMIN LOGIN (public form rejects admins) ==")
r = client.post("/api/auth/login", json={"username": "adminboss", "password": "Passw0rd!"})
check("public login rejects admin (403)", r.status_code == 403, r.get_json())
check("rejection message points to admin login",
      "admin" in str(r.get_json().get("error", "")).lower(), r.get_json())
r = client.post("/api/auth/admin/login", json={"username": "adminboss", "password": "Passw0rd!"})
check("admin login endpoint works (200)", r.status_code == 200, r.get_json())
check("admin login returns admin role", r.get_json()["user"]["role"] == "Admin", r.get_json())
r = client.post("/api/auth/admin/login", json={"username": "ann", "password": "Passw0rd!"})
check("admin login rejects non-admin (403)", r.status_code == 403, r.get_json())
r = client.post("/api/auth/login", json={"username": "writer", "password": "Passw0rd!"})
check("tech_writer can still use public login", r.status_code == 200, r.get_json())

print("\n== 1c. AUTH PATH ALIASES (logout / forgot-password / reset-password / avatar) ==")
# Regression: the frontend calls /api/auth/forgot-password etc., but only the
# short /api/forgot-password forms existed -> 404 -> the browser showed a
# misleading CORS error on the preflight.
r = client.options("/api/auth/forgot-password", headers={
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "POST",
})
check("OPTIONS /api/auth/forgot-password preflight 200", r.status_code == 200, r.status_code)
check("preflight has ACAO header",
      r.headers.get("Access-Control-Allow-Origin") is not None, dict(r.headers))

r = client.post("/api/auth/forgot-password", json={})
check("forgot-password without email 400", r.status_code == 400, r.get_json())
r = client.post("/api/auth/forgot-password", json={"email": "ghost@nowhere.dev"})
check("forgot-password unknown email -> generic 200",
      r.status_code == 200 and "instructions" in r.get_json().get("message", ""), r.get_json())
r = client.post("/api/auth/forgot-password", json={"email": "ann@moringa.com"})
check("forgot-password existing email 200 (dev link when SMTP unconfigured)",
      r.status_code == 200, r.get_json())

r = client.post("/api/auth/logout")
check("logout via /auth alias 200", r.status_code == 200, r.get_json())
r = client.post("/api/auth/reset-password", json={"token": "bogus", "password": "NewPass123!"})
check("reset-password via /auth alias rejects bad token",
      r.status_code == 400, r.get_json())

r = client.options("/api/auth/avatar", headers={
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "PATCH",
})
check("OPTIONS /api/auth/avatar preflight 200", r.status_code == 200, r.status_code)

print("\n== 2. PROFILE: save skills + github, then reload ==")
r = client.put("/api/profiles/me", headers=as_user(ANN_TOKEN), json={
    "bio": "Moringa student", "skills": "React, Python, Tailwind",
    "github_url": "https://github.com/ann", "interests": "Frontend, DevOps"})
check("profile update 200", r.status_code == 200, r.get_json())

r = client.get("/api/profiles/me", headers=as_user(ANN_TOKEN))
data = r.get_json()
check("GET /profiles/me keeps skills", data.get("skills") == "React, Python, Tailwind", data)
check("GET /profiles/me keeps github_url", data.get("github_url") == "https://github.com/ann", data)

r = client.get("/api/me", headers=as_user(ANN_TOKEN))
data = r.get_json()
check("GET /api/me includes skills", data.get("skills") == "React, Python, Tailwind", data)
check("GET /api/me includes github_url", data.get("github_url") == "https://github.com/ann", data)

print("\n== 3. INSTAGRAM-STYLE POST: multipart upload with image ==")
fake_png = io.BytesIO(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c626001000000ffff03000006000557"
    "bfabd40000000049454e44ae426082"))

r = client.post("/api/content", headers=as_user(ANN_TOKEN), data={
    "title": "My first photo post",
    "description": "Sunset at Moringa 🌅 #blessed",
    "content_type": "Image",
    "category_id": str(CAT_ID),
    "media_file": (io.BytesIO(fake_png.read()), "sunset.png", "image/png"),
}, content_type="multipart/form-data")
check("image post created 201", r.status_code == 201, r.get_json())
data = r.get_json()
check("response has 'id' (frontend navigates with it)", "id" in data, data)
check("learner post is Pending (moderation)", data.get("status") == "Pending", data)
ANN_POST_ID = data.get("content_id")

r = client.get(f"/api/content/{ANN_POST_ID}")
check("single content GET 200", r.status_code == 200, r.get_json())
check("single content has likes_count", "likes_count" in r.get_json(), r.get_json())
check("single content has author", r.get_json().get("author", {}).get("username") == "ann", r.get_json())
data = r.get_json()
check("createdAt camelCase alias present (ContentCard)", "createdAt" in data, list(data.keys()))
check("created_at is UTC-aware (ends Z) — fixes +3h '3 hours ago' in Nairobi",
      isinstance(data.get("created_at"), str) and data["created_at"].endswith("Z"), data.get("created_at"))
check("media url is ABSOLUTE (frontend origin differs from backend)",
      isinstance(data.get("url"), str) and data["url"].startswith("http"), data.get("url"))
check("mediaUrl camelCase alias present", "mediaUrl" in data, list(data.keys()))

print("\n== 4. REACTIONS: like / summary / toggle-off ==")
r = client.post(f"/api/content/{ANN_POST_ID}/reactions",
                headers=as_user(ADMIN_TOKEN), json={"type": "like"})
check("react 200", r.status_code == 200, r.get_json())
check("react returns summary", r.get_json().get("likes") == 1 and r.get_json().get("userReaction") == "like", r.get_json())

r = client.get(f"/api/content/{ANN_POST_ID}/reactions")
check("GET reaction summary 200", r.status_code == 200, r.get_json())
check("summary counts likes", r.get_json().get("likes") == 1, r.get_json())

r = client.post(f"/api/content/{ANN_POST_ID}/reactions",
                headers=as_user(ADMIN_TOKEN), json={"type": "like"})
check("re-click toggles off", r.get_json().get("likes") == 0, r.get_json())

r = client.post(f"/api/content/{ANN_POST_ID}/reactions",
                headers=as_user(ADMIN_TOKEN), json={"type": "like"})
r = client.post(f"/api/content/{ANN_POST_ID}/reactions",
                headers=as_user(WRITER_TOKEN), json={"type": "dislike"})
data = r.get_json()
check("dislike recorded", data.get("dislikes") == 1, data)

print("\n== 4b. COMMENTS + DELETE OWN POST ==")
# Regression: the frontend used to call addComment(id, user.id, text),
# sending user.id as the body and the TEXT as parent_comment_id — every
# top-level comment 404'd with "Parent comment not found".
r = client.post(f"/api/content/{ANN_POST_ID}/comments",
                headers=as_user(ANN_TOKEN), json={"text": "First! Great post 🎉"})
check("top-level comment 201", r.status_code == 201, r.get_json())
comment_id = r.get_json().get("id") or r.get_json().get("comment_id")
check("comment response has id", bool(comment_id), r.get_json())
check("comment createdAt is UTC Z-suffixed",
      str(r.get_json().get("createdAt", "")).endswith("Z"), r.get_json())

r = client.post(f"/api/content/{ANN_POST_ID}/comments",
                headers=as_user(ADMIN_TOKEN),
                json={"text": "Thanks — approved!", "parent_comment_id": comment_id})
check("reply 201", r.status_code == 201, r.get_json())
check("reply linked to parent", r.get_json().get("parent_comment_id") == comment_id, r.get_json())

r = client.get(f"/api/content/{ANN_POST_ID}/comments")
tree = r.get_json()
check("comment tree lists top-level", any(c["id"] == comment_id for c in tree), tree)
check("reply nested under parent",
      any(r_["text"] == "Thanks — approved!" for c in tree for r_ in c.get("replies", [])), tree)

r = client.post(f"/api/content/{ANN_POST_ID}/comments",
                headers=as_user(ANN_TOKEN),
                json={"text": "orphan", "parent_comment_id": 999999})
check("bogus parent 404 'Parent comment not found'",
      r.status_code == 404 and "Parent comment" in r.get_json().get("error", ""), r.get_json())

r = client.post(f"/api/content/{ANN_POST_ID}/comments", json={"text": "anon"})
check("comment without token 401", r.status_code == 401, r.status_code)

# --- delete own post: author can, other users can't, admin can ---
r = client.post("/api/content", headers=as_user(ANN_TOKEN), json={
    "title": "Delete me please", "description": "temporary post",
    "type": "article", "category_id": CAT_ID})
check("create temp post for delete test", r.status_code == 201, r.get_json())
del_id = r.get_json().get("content_id") or r.get_json().get("id")

r = client.delete(f"/api/content/{del_id}", headers=as_user(WRITER_TOKEN))
check("another user CANNOT delete someone else's post (403)",
      r.status_code == 403, r.get_json())
r = client.delete(f"/api/content/{del_id}", headers=as_user(ANN_TOKEN))
check("author CAN delete own post (200)",
      r.status_code == 200, r.get_json())
r = client.get(f"/api/content/{del_id}")
check("deleted post is gone (404)", r.status_code == 404, r.status_code)

print("\n== 5. NOTIFICATIONS: like + publish triggers ==")
r = client.get("/api/users/me/notifications", headers=as_user(ANN_TOKEN))
notifs = r.get_json()
check("notifications list is real (not hardcoded [])", isinstance(notifs, list) and len(notifs) > 0, notifs)
check("notification has camelCase isRead", notifs and "isRead" in notifs[0], notifs)
check("like notification exists", any("liked your post" in n["message"] for n in notifs), notifs)

nid = notifs[0]["id"]
r = client.patch(f"/api/users/me/notifications/{nid}/read", headers=as_user(ANN_TOKEN))
check("mark one read 200", r.status_code == 200, r.get_json())
r = client.patch("/api/users/me/notifications/read-all", headers=as_user(ANN_TOKEN))
check("mark all read 200", r.status_code == 200, r.get_json())
r = client.get("/api/users/me/notifications", headers=as_user(ANN_TOKEN))
check("all read after read-all", all(n["isRead"] for n in r.get_json()), r.get_json())

print("\n== 6. ADMIN: pending queue, approve (notifies + publishes), role security ==")
r = client.get("/api/admin/pending-content", headers=as_user(ADMIN_TOKEN))
check("pending queue lists learner post", r.status_code == 200 and any(
    p["id"] == ANN_POST_ID for p in r.get_json()), r.get_json())

r = client.patch(f"/api/admin/content/{ANN_POST_ID}/status",
                 headers=as_user(ADMIN_TOKEN), json={"status": "Published"})
check("approve 200", r.status_code == 200, r.get_json())

r = client.get("/api/content", query_string={"status": "Published"})
items = r.get_json()["items"]
check("approved post is Published in feed", any(i["id"] == ANN_POST_ID for i in items), None)

r = client.patch(f"/api/admin/content/{ANN_POST_ID}/status",
                 headers=as_user(ADMIN_TOKEN), json={"status": "Rejected", "reason": "Spam"})
check("reject maps to Archived (no constraint crash)", r.status_code == 200 and
      r.get_json().get("status") == "Archived", r.get_json())

# Non-admin must NOT be able to use admin endpoints
r = client.get("/api/admin/pending-content", headers=as_user(ANN_TOKEN))
check("non-admin blocked from admin API (403)", r.status_code == 403, r.get_json())

# Non-admin cannot flag content
r = client.patch(f"/api/content/{ANN_POST_ID}/flag", headers=as_user(ANN_TOKEN))
check("non-admin blocked from flag (403)", r.status_code == 403, r.get_json())

print("\n== 7. SUBSCRIBER NOTIFICATIONS on publish (tech_writer posts instantly) ==")
with app.app_context():
    from app.models import Subscription, User
    ann_id = User.query.filter_by(Username="ann").first().UserID
    if not Subscription.query.filter_by(UserID=ann_id, CategoryID=CAT_ID).first():
        db.session.add(Subscription(UserID=ann_id, CategoryID=CAT_ID))
        db.session.commit()

r = client.post("/api/content", headers=as_user(WRITER_TOKEN), json={
    "title": "Instant writer post", "description": "Published immediately",
    "type": "article", "category_id": CAT_ID})
check("tech_writer post 201", r.status_code == 201, r.get_json())
check("tech_writer post Published instantly", r.get_json().get("status") == "Published", r.get_json())
check("writer response explains WHY it published (publish_reason)",
      bool(r.get_json().get("publish_reason")), r.get_json())
check("writer response has published_immediately flag",
      r.get_json().get("published_immediately") is True, r.get_json())

r = client.get("/api/users/me/notifications", headers=as_user(ANN_TOKEN))
check("subscriber notified of new content", any(
    "New content in your feed" in n["message"] for n in r.get_json()), r.get_json())
check("notification created_at is UTC-aware (ends Z)",
      all(str(n.get("created_at", "")).endswith("Z") for n in r.get_json()), r.get_json()[:2])

print("\n== 8. REPORTS + WISHLIST + SEARCH ==")
r = client.post(f"/api/content/{ANN_POST_ID}/report",
                headers=as_user(ANN_TOKEN), json={"reason": "Broken image"})
check("report via /report alias 201", r.status_code == 201, r.get_json())

r = client.get("/api/reports", headers=as_user(ADMIN_TOKEN))
check("admin sees enriched reports", r.status_code == 200 and r.get_json() and
      "content" in r.get_json()[0] and "reporter" in r.get_json()[0], r.get_json())

r = client.post("/api/wishlist", headers=as_user(ANN_TOKEN), json={"content_id": ANN_POST_ID})
check("add to wishlist 201", r.status_code == 201, r.get_json())
r = client.get("/api/users/me/wishlist", headers=as_user(ANN_TOKEN))
items = r.get_json()
check("wishlist lists item with row id", items and "id" in items[0] and "content_id" in items[0], items)
r = client.delete(f"/api/wishlist/{items[0]['id']}", headers=as_user(ANN_TOKEN))
check("remove from wishlist 200", r.status_code == 200, r.get_json())

r = client.get("/api/content", query_string={"search": "instant"})
found = any("instant" in (i.get("description") or "").lower() or "instant" in i["title"].lower()
            for i in r.get_json()["items"])
check("search finds posts", found, r.get_json()["items"][:1])

r = client.get("/api/content", query_string={"status": "pending"})
check("status filter case-insensitive", r.status_code == 200, None)

print("\n== 9. SUBSCRIPTIONS (was 404 -> CORS preflight failure) ==")
# Clean slate first: section 7 may have already subscribed ANN to CAT_ID
client.delete(f"/api/subscriptions/{CAT_ID}", headers=as_user(ANN_TOKEN))
r = client.post("/api/subscriptions", headers=as_user(ANN_TOKEN),
                json={"category_id": CAT_ID})
check("subscribe 201", r.status_code == 201, r.get_json())
r = client.get("/api/subscriptions", headers=as_user(ANN_TOKEN))
subs = r.get_json()
check("list subscriptions 200", r.status_code == 200 and isinstance(subs, list), subs)
check("subscription includes category_id", subs and subs[0].get("category_id") == CAT_ID, subs)
r = client.delete(f"/api/subscriptions/{CAT_ID}", headers=as_user(ANN_TOKEN))
check("unsubscribe 200", r.status_code == 200, r.get_json())

# CORS preflight: the browser sends OPTIONS before cross-origin requests
r = client.options("/api/subscriptions", headers={
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "authorization,content-type",
})
check("OPTIONS /api/subscriptions preflight 200", r.status_code == 200, r.status_code)
check("preflight has ACAO header",
      r.headers.get("Access-Control-Allow-Origin") in ("*", "http://localhost:5173"),
      dict(r.headers))
r = client.options("/api/content", headers={
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "authorization,content-type",
})
check("OPTIONS /api/content preflight 200", r.status_code == 200, r.status_code)

# Unhandled errors must stay JSON (so CORS headers survive) — simulate drift
from app import create_app as _caf
with app.test_request_context():
    pass
r = client.get("/api/content/999999999")
check("GET missing content is JSON 404 (not werkzeug page)",
      r.status_code == 404 and r.is_json, r.status_code)

print("\n" + "=" * 60)
print(f"RESULT: {len(PASSED)} passed, {len(FAILED)} failed")

# Clean up test artifacts (throwaway DB + uploaded file)
for path in (DB_PATH, os.path.join("instance", DB_PATH),
             os.path.join("app", "static", "uploads", "sunset.png")):
    try:
        os.remove(path)
    except OSError:
        pass

if FAILED:
    print("Failed checks:", FAILED)
    sys.exit(1)
print("ALL CHECKS PASSED ✔")

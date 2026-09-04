# Bug-Fix Report — `fix/all-bugfixes` branch

All fixes below are in **one branch** (`fix/all-bugfixes`) and verified with an
automated end-to-end test (`backend/e2e_test.py`, **45/45 checks passing**) plus a
live run of both servers.

Run the whole stack with one command: **`bash dev.sh`**

---

## 1. Backend wouldn't even start (crashers)

| # | Bug | Fix |
|---|-----|-----|
| 1.1 | `app/__init__.py` imported `app.routes.auth` and `app.routes.users` — **those files don't exist** → `ModuleNotFoundError` on every startup | Removed the phantom imports; all real blueprints now registered |
| 1.2 | `ai_routes.py` lived in `app/Routes/` (capital R) but was imported as `app.routes.ai_routes` — works on macOS (case-insensitive), **crashes on Linux/CI** | Moved to `app/routes/ai_routes.py` |
| 1.3 | `auth_profile_bp` (login, register, forgot/reset password, `/me`) was **never registered** → all auth endpoints 404 | Registered under `/api` |
| 1.4 | `admin_bp` was **never registered** → all `/api/admin/*` endpoints 404 | Registered under `/api/admin` |
| 1.5 | `comments.py` & `comment_reactions.py` used `from app import db` → `ImportError` | Changed to `from app.extensions import db` |
| 1.6 | `run.py` called `create_app(config_name=...)` but the factory expected `config_class` → `TypeError` on `python run.py` | Factory accepts both kwargs |
| 1.7 | `ai_routes.py` imported `google.genai` at module level → crash when `google-genai` isn't installed | Lazy import; AI route degrades gracefully (503) instead of killing the app |

## 2. Profile: Skills & GitHub disappear on reload ❌ → ✅

Root causes (there were two):

1. `GET /api/me` (`auth_profile.get_my_profile`) **did not include `skills` or `github_url`** in its response — every page that reads `/me` after a reload showed them empty.
2. `PUT /api/auth/me` saved GitHub to `profile.GithubProfile` — **a column that doesn't exist** (the real column is `GithubURL`), so the value silently vanished.

**Fixed:** `/me` now returns `skills` + `github_url` (+ nested copies), the update
writes to the correct `GithubURL` column, `/api/profiles/me` only overwrites fields
actually sent (a partial update can no longer blank other fields), and the profile
page re-reads from the server after saving so what you see is what's stored.

## 3. Post submission failing ❌ → ✅

- The `Content` model's status check-constraint only allowed
  `Draft / Published / Archived` — new learner posts are saved as **`Pending`**,
  which **violated the constraint → 500 "Failed to submit content"** on any fresh
  database. The constraint now includes `Pending` (matching migration `6aa238642ae6`).
- The create response returned `content_id` but the frontend navigated to
  `/content/${created.id}` → `/content/undefined`. Response now includes `id` and the
  frontend falls back across both shapes.
- Uploads were saved to `static/uploads` (relative to the working directory) while
  Flask serves `/static/` from `app/static` → **uploaded media 404'd**. `UPLOAD_FOLDER`
  is now pinned to `backend/app/static/uploads` (+ 64 MB upload ceiling).
- `GET /api/content/<id>` returned `None` (500) whenever content had no author — the
  `return` was nested inside the author `if` block.
- The composer's file fields (`media_file`, `thumbnail`) were ignored by the backend;
  it now accepts `file` / `media_file` / `media` / `content_url` + `thumbnail` and
  stores `ThumbnailURL`, `Summary`, `Duration`.

## 4. Reactions button not working ❌ → ✅

- `ContentDetail` called `react(id, user.id, type)` — **three arguments into a
  two-parameter function**, so the API received the numeric user id as the reaction
  type and rejected every click with 400.
- `GET /api/content/<id>/reactions` (the summary the page loads on mount) **didn't
  exist** on the backend.
- The POST returned only `{message}` while the UI expected `{likes, dislikes, userReaction}`.

**Fixed:** correct frontend call, new GET summary endpoint, POST returns the full
summary, and clicking the same reaction again **toggles it off (Instagram-style)**.
Feed cards now have an Instagram-style heart button with optimistic UI.

## 5. Notifications ❌ → ✅

- `notifications.py` was a stub that **always returned `[]`** — the notifications page
  could never show anything. Now: real list + `unread-count` + `PATCH .../read` +
  `PATCH .../read-all`, with both camelCase and snake_case keys (the page read
  `n.isRead` / `n.contentId` / `n.createdAt` which never existed before).
- **`_notify_subscribers()` in `content.py` was defined but never called.** It now
  fires when content is published (immediately for admin/tech_writer, and when an
  admin approves a pending post), and it can never fail the request that triggered it.
- Likes create author notifications (`"X liked your post: …"`).

## 6. Admin signup + login + dashboard ❌ → ✅

- **Sign-up now has an account-type picker** (Learner / Tech Writer / Admin) — the
  backend already accepted a role, the form just never sent one. Roles are
  normalised (`admin` → `Admin`), and admins land on `/admin` after registering.
- `RoleRoute` compared roles **case-sensitively** (`allow={['admin']}` vs stored
  `"Admin"`) → real admins were redirected away from `/admin`. Now case-insensitive.
- `role_required` read the role from the JWT, but the JWT only stores the user id —
  so the check **passed everyone through** (any user could hit admin APIs). It now
  verifies the role from the database, case-insensitively.
- `adminApi.js` called `api.get(...)` on a fetch wrapper that has no `.get` →
  `TypeError` on the dashboard; URLs didn't match the backend
  (`/users` vs `/api/admin/users`, `/content?status=pending` vs `Pending`);
  `approveContent` pointed at a non-existent `/approve` route. All rewritten against
  the real endpoints.
- Admin "Rejected" status **violated the DB check constraint → 500 on reject**.
  It now maps to `Archived` (allowed by the constraint) with the reason stored in
  the new `RejectionReason` column (+ migration).
- `GET /api/reports` was never actually routable (the blueprint registered `""`
  under `/api`, i.e. `/api` itself) → 404. Reports now return enriched data
  (content title, reporter username, camelCase dates).

## 7. Instagram-style post creation ✨ new

`/create` is now an Instagram-style composer: drag & drop (or click) to pick an
image/video/audio, live preview, caption, auto-derived title, category chips,
share button, and a "Post shared / Sent for review" confirmation screen. The old
long-form editor (with the AI helpers) moved to `/create-article`.

## 8. Other fixes

- `wishlistApi.removeFromWishlist(contentId)` sent the **content id** where the API
  expects the **wishlist row id** → 404. It now resolves the row first.
- Search (`?q=` / `?search=`) was ignored by the content API — it now filters by
  title/description; `status` filter is case-insensitive.
- Duplicate/unreachable `return` lines and a duplicate `request` import cleaned up.
- `requirements.txt` now includes `google-genai` (used by the AI routes).
- Model re-aligned with the migration history (`Summary`, `Duration`, `LikesCount`,
  `is_admin`, `RejectionReason`).

## New files

- `dev.sh` — **one command** that installs everything, prepares/migrates the DB,
  seeds categories + a default admin (`admin` / `Admin123!`) on first run, and
  starts backend + frontend together (Ctrl+C stops both).
- `backend/setup_db.py` — safe DB bootstrap for fresh *and* existing databases
  (create-all + stamp, or upgrade).
- `backend/e2e_test.py` — 45-check end-to-end test (`python e2e_test.py`).
- `BUGFIX_REPORT.md` — this file.

## How to verify after pulling

```bash
bash dev.sh                                # run the stack
cd backend && .venv/bin/python e2e_test.py # 45 automated checks
```

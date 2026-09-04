# PR: `fix/all-bugfixes` → `main`

Everything below is ready to copy-paste into GitHub.

---

## 1. PR TITLE

```
fix: backend startup crash, profile persistence, post submission, reactions, notifications, admin flow + Instagram-style posting, Render deployment, separate admin login & timestamp/media/session fixes
```

---

## 2. PR DESCRIPTION (paste into the PR body)

```markdown
## Summary

This PR repairs the backend (which could not start on `main`), fixes every
reported user-facing bug (profile fields disappearing on reload, post
submission 500s, dead reactions button, empty notifications, broken admin
dashboard, subscriptions CORS errors), adds Instagram-style post creation and
admin sign-up, **separates the admin login from the public login form**, adds
**one-click deployment to Render** (`render.yaml` + production config), and
fixes a second wave of reported bugs (**wrong "3 hours ago" timestamps, post
media not rendering, null-user crashes, random 401s, and DB schema drift
healing itself at request time**).

Verified with **66 automated backend e2e checks** (`backend/e2e_test.py`)
and **37 frontend tests** — all passing — plus a live gunicorn/production-mode
smoke test of the exact Render start command.

## What was broken

### Backend could not even start
- `app/__init__.py` imported `app.routes.auth` / `app.routes.users` which **do not exist** → `ModuleNotFoundError` on startup
- `ai_routes.py` lived in `app/Routes/` (capital R) but is imported lowercase → crashes on Linux/CI
- `auth_profile_bp` (login / register / forgot-password / `/me`) and `admin_bp` were **never registered** → all auth & admin endpoints 404
- `comments.py` / `comment_reactions.py` used `from app import db` → `ImportError`
- `run.py` called `create_app(config_name=…)` vs the factory's `config_class` → `TypeError`

### User-facing bugs
- **Skills & GitHub disappear on reload**: `GET /api/me` never returned them, and updates wrote GitHub to a non-existent column (`GithubProfile` instead of `GithubURL`) so it was silently never saved
- **Post submission failing (500)**: the `Content` status check-constraint didn't allow `Pending` (what new learner posts get); the create response had no `id` (frontend navigated to `/content/undefined`); uploads were saved to a folder Flask doesn't serve → media 404; `GET /api/content/<id>` returned `None` when content had no author
- **Reactions not working**: `ContentDetail` called `react(id, user.id, type)` — the user id was sent *as the reaction type* (400 every click); no GET summary endpoint existed; the POST returned no counts
- **Notifications dead**: `notifications.py` was a hardcoded `return []`; `_notify_subscribers()` in `content.py` was defined but **never called**; response keys didn't match what the page reads (`isRead` / `contentId` / `createdAt`)
- **Admin broken**: `role_required` read a role that isn't in the JWT → passed everyone through; dashboard's `adminApi` called `api.get()` on a fetch wrapper (TypeError) with wrong URLs; "Rejected" status violated the DB constraint (500); `RoleRoute` compared roles case-sensitively so real admins were locked out of `/admin` (same bug in `NavDrawer`); `GET /api/reports` was unroutable
- **Subscriptions CORS error**: blueprint registered under `/api` with empty routes → `GET/POST /api/subscriptions` 404 → the OPTIONS preflight failed, which the browser reports as a CORS error
- **Misleading CORS errors on 500s**: unhandled exceptions in debug mode escalated to the Werkzeug debugger page, which carries **no CORS headers**
- Wishlist remove sent the content id where the API expects the wishlist row id; search (`?q=`) was ignored by the content API

### Second wave of user-reported bugs
- **"3 hours ago" on brand-new posts**: every serializer emitted naive UTC ISO strings (`2026-09-04T10:00:00` with no `Z`), which JavaScript parses as **local** time — in Nairobi (UTC+3) a post made one minute ago rendered as "3 hours ago". All serializers now go through one shared `iso_utc()` helper that appends `Z`, and the content serializer also returns `createdAt` (ContentCard read `item.createdAt` and previously got `undefined`)
- **Post media not rendering on the detail page**: the API returned *relative* `/static/uploads/...` URLs, which 404 against the frontend's origin (5173 ≠ 5001); image posts additionally had **no `<img>` element at all** (only video/audio had a player). Media URLs are now absolute and images render
- **"Cannot read properties of null (reading 'id')"**: submitting a post / subscribing to a category / marking notifications read crashed when no user was logged in — all guarded now (submitting redirects to login)
- **Random 401s on reactions/subscriptions**: a stale or missing token produced scattered 401s. `api.js` now handles 401 globally — clears the dead session, shows "your session expired" on the login page, and returns you where you were after logging back in
- **DB schema drift 500s (`no such column: content.Summary`)**: the global error handler now detects drift, **runs the repair automatically once**, and answers `503 {schema_repaired: true, retry: true}` — the frontend transparently retries and the user never sees the error

### Security
- **Admin accounts could sign in through the public login form** — dangerous. Now:
  - the public `POST /api/auth/login` **rejects Admin accounts (403)** and tells them where to go
  - a dedicated **`POST /api/auth/admin/login`** accepts *only* Admin accounts (non-admins get 403)
  - new **`/admin/login`** page (separate dark "admin portal" UI, public route) → admins land on `/admin`
  - the public login form shows a "Continue on the secure admin login" link when an admin tries it, and a discreet footer link
  - admin **sign-up** (account-type picker) is unchanged — admins are still created via `/signup`
  - `role_required` now enforces roles from the DB case-insensitively: admin endpoints return 403 for non-admins

## What's new

- 📸 **Instagram-style composer** at `/create`: drag & drop image/video/audio with live preview, caption, auto-derived title, category chips, share confirmation ("live" vs "sent for review"); long-form editor (with AI helpers) moved to `/create-article`; optimistic ❤️ button on feed cards
- 👑 **Admin sign-up + separate admin sign-in**: account-type picker (Learner / Tech Writer / Admin) on `/signup`; dedicated admin portal login at `/admin/login`; admins land on `/admin`
- 🚀 **Render deployment** (`render.yaml` blueprint): free PostgreSQL + Flask/gunicorn web service in one click — `DATABASE_URL` wired automatically, `SECRET_KEY`/`JWT_SECRET_KEY` auto-generated, health check on `/`, idempotent DB bootstrap/seed on every deploy; optional persistent-disk and static-site frontend blocks documented inline; `DEPLOYMENT.md` has the full guide
  - production hardening: `ProductionConfig` (`DEBUG=False`), `FLASK_ENV` config selection, `postgres://` → `postgresql://` URL normalisation, empty-DB bootstrap at startup, gunicorn added to requirements
  - client no longer hardcodes `http://localhost:5001` — everything reads `VITE_API_BASE_URL` (default localhost for dev), so a deployed frontend just needs that one build-time env var
- 🥬 **`bash dev.sh`** — one command: installs deps, prepares/migrates/seeds the DB (default admin `admin` / `Admin123!` — **signs in via `/admin/login`**), starts backend (5001) + frontend (5173)
- 🩺 **`app/schema_doctor.py`** — idempotent schema repair for databases created from old models (adds missing columns, allows `Pending` status, preserves data); runs automatically on dev-server boot, via `backend/setup_db.py`, **and now at request time** (drift-triggered auto-repair + transparent client retry)
- 🏷️ **Moderation clarity**: the create-post response explains *why* a post was published instantly vs sent to review (admins/tech writers publish by design — learners' posts go to Pending); the success screen shows that reason. Optional `MODERATE_ALL_POSTS=1` env var forces *everyone* (including admins) through review while testing
- 🔔 Subscriber notifications fire when content is published (immediately for admin/tech_writer, or when an admin approves a pending post)
- Global JSON error handler keeps CORS headers on every error and returns an actionable "schema is out of date — run bash dev.sh" hint when drift is detected

## Database

- New migration `a1f2c3d4e5f6` (adds `content.RejectionReason`); model re-aligned with the migration history (`Summary`, `Duration`, `LikesCount`, `is_admin`)
- **No data loss**: old local databases are auto-repaired in place on first `bash dev.sh` / `python run.py`; existing users and posts are preserved

## How to test

```bash
bash dev.sh                                  # runs the whole stack
# learner login: sign up normally
# admin login:  http://localhost:5173/admin/login  with admin / Admin123!

cd backend && .venv/bin/python e2e_test.py   # 66 automated checks
cd ../client && npx jest                     # 37 frontend tests
```

Manual smoke test:
1. Sign up (pick **Admin**) → auto-logged-in and lands on `/admin`
2. Log out → try the admin credentials on the **public** `/login` → rejected with a link to the admin login; sign in at `/admin/login` → lands on `/admin`
3. Profile → add skills + GitHub URL → save → **reload** → both still there
4. `/create` → drag in a photo + caption → Share → post appears in the feed with the image served from `/static/uploads/...`
5. Heart a post from the feed and from the detail page → count updates, click again to unlike
6. As a learner, post something → it's "Pending"; as admin, approve it from `/admin` → the author gets a notification
7. Notifications page → list loads, "mark all as read" works
8. **Post as admin → success screen says "published immediately" *and why*; post as learner → "sent for review"**
9. **Open a post with an image → the image renders on the detail page; timestamps say "just now" for fresh posts (not "3 hours ago" in UTC+3)**
10. Deploy: Render dashboard → New → Blueprint → Apply (see `DEPLOYMENT.md`)

## Notes for reviewers

- All API changes are additive (extra fields / aliases like `id` + `content_id`, camelCase + snake_case) — existing consumers keep working
- The only intentional breaking behaviour: **`/api/auth/login` now returns 403 for Admin accounts** (use `/api/auth/admin/login`) — enforced server-side, not just in the UI
- `role_required` now actually enforces roles from the DB (case-insensitive): admin endpoints return 403 for non-admins (covered by e2e)
- Free Render plan caveats documented in `DEPLOYMENT.md` (service sleep, ephemeral uploads → optional `disk:` block, 30-day Postgres expiry)
```

---

## 3. COMMIT MESSAGE

The branch has **8 commits** (see `git log main..fix/all-bugfixes`). If you merge
with **"Squash and merge"** (recommended), GitHub will ask for one commit
message — use this:

```
fix: repair backend startup, profile persistence, post submission, reactions, notifications, admin flow + Instagram-style posting, Render deployment, separate admin login & timestamp/media/session fixes

Backend could not start on main: phantom auth/users imports, unregistered
auth/admin blueprints, wrong-case Routes/ folder, and `from app import db`
ImportErrors. Beyond startup:

- Profile: /api/me returns skills + github_url; GitHub saved to the real
  GithubURL column (was silently lost) — fields no longer vanish on reload
- Posts: 'Pending' allowed by the status constraint (fresh-DB 500), uploads
  land in the servable static folder, response includes id, single-content
  GET fixed, search + case-insensitive status filter added
- Reactions: correct frontend call, GET summary endpoint, POST returns
  counts and toggles off on repeat; Instagram-style heart on feed cards
- Notifications: real endpoints (was hardcoded []), _notify_subscribers
  fires on publish/approval, camelCase keys
- Admin security: public /api/auth/login rejects Admin accounts (403);
  new dedicated /api/auth/admin/login (admins only) + /admin/login portal
  page; admin sign-up picker unchanged; role checks enforced
  case-insensitively from the DB (RoleRoute + NavDrawer case bugs fixed)
- Admin dashboard: blueprint registered, Rejected mapped to Archived
  (constraint-safe), RejectionReason column + migration, dashboard API
  rewritten against real routes
- Subscriptions: registered at /api/subscriptions (was 404 -> CORS error)
- Errors: global JSON handler keeps CORS headers on 500s; schema drift
  triggers an automatic in-place repair at REQUEST time (once) + a 503
  the frontend transparently retries — 'no such column' 500s heal
  themselves instead of persisting
- DB: app/schema_doctor.py repairs old local databases idempotently,
  bootstraps empty ones at startup, auto-runs on dev-server boot;
  dev.sh one-command stack; setup_db.py
- Deployment: render.yaml blueprint (free Postgres + gunicorn web service,
  auto-generated secrets, health check, idempotent deploy bootstrap);
  ProductionConfig with postgres:// URL normalisation; gunicorn added;
  client fetches moved to VITE_API_BASE_URL (no hardcoded localhost);
  DEPLOYMENT.md guide
- Frontend: account-type picker on signup (Learner / Tech Writer / Admin),
  case-insensitive RoleRoute, wishlist remove uses the row id
- Timestamps: shared iso_utc() helper — every API timestamp is UTC-aware
  (Z suffix) so relative times are right in every timezone (fixes '3 hours
  ago' for fresh posts in UTC+3); createdAt/mediaUrl camelCase aliases
- Media: absolute URLs in the content serializer (relative /static/uploads/
  paths 404'd on the frontend origin) + <img> rendering for image posts on
  the detail page
- Sessions: global 401 handling in api.js clears stale tokens and redirects
  to /login (with a 'session expired' notice and a return trip); null-user
  guards on post submit, category subscribe, and mark-all-notifications
- Moderation: create response explains published-immediately vs review
  (admins/tech_writers publish by design); MODERATE_ALL_POSTS=1 forces
  everyone through review while testing

Verified: 66 backend e2e checks + 37 frontend tests, all passing, plus a
gunicorn production-mode smoke test of the exact Render start command.
```

---

## 4. HOW TO GET THIS INTO GITHUB

### Step 1 — apply the patch on your machine

Download **`fix-all.patch`** from the workspace, then:

```bash
cd cc2-moringa-daily-dev
git checkout main && git pull origin main
git checkout -b fix/all-bugfixes
git am --3way ~/Downloads/fix-all.patch
```

(If you already created `fix/all-bugfixes` from an older patch, reset it first:
`git checkout main && git branch -D fix/all-bugfixes`.)

### Step 2 — push the branch

```bash
git push -u origin fix/all-bugfixes
```

### Step 3 — open the PR

Open:

```
https://github.com/mahneeofficial/cc2-moringa-daily-dev/compare/main...fix/all-bugfixes
```

(or GitHub shows a "Compare & pull request" button right after the push)
Paste section **2** as the description and create the PR.

### Step 4 — merge

Click **"Squash and merge"** and paste section **3** as the commit message.

### Step 5 — deploy the merged main to Render

1. Render dashboard → **New → Blueprint** → pick the repo → **Apply**
   (the blueprint lives in `render.yaml` at the repo root).
2. First boot creates the DB, seeds categories and the default admin
   (`admin` / `Admin123!`) — **sign in at `https://<your-backend>.onrender.com`'s
   frontend via `/admin/login`** and change that password immediately.
3. Optional: uncomment the `moringa-client` static-site block in `render.yaml`
   (or use Vercel/Netlify) with `VITE_API_BASE_URL` set to the backend URL.

### Step 6 — everyone else pulls the fix

```bash
git checkout main && git pull origin main && bash dev.sh
```

`bash dev.sh` repairs old local databases automatically on first run —
nobody needs to delete their `app.db` (delete it only for a completely fresh
seeded database).

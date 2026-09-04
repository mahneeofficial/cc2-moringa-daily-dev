# Deploying Moringa Daily Dev to Render

The repo ships a Render Blueprint (`render.yaml`) that deploys the **backend
(Flask + gunicorn) and a PostgreSQL database** in one click.

## One-time setup

1. **Merge/push `render.yaml` to your default branch** (it is included in the
   `fix/all-bugfixes` branch).
2. Go to **[dashboard.render.com](https://dashboard.render.com)** →
   **New → Blueprint**, pick the `cc2-moringa-daily-dev` repo, click **Apply**.
3. Render creates:
   - `moringa-db` — PostgreSQL (free plan)
   - `moringa-backend` — the API at `https://moringa-backend.onrender.com`
   - `SECRET_KEY` / `JWT_SECRET_KEY` are generated for you,
     `DATABASE_URL` is wired to the database automatically.
4. First boot runs `python setup_db.py` → tables are created, categories
   seeded, and a default admin is created:
   **`admin` / `Admin123!`** → change this immediately (log in and use a new
     admin account, or delete the seeded admin after creating your own).

## After deploying

- **AI features**: add `GEMINI_API_KEY` in the Render dashboard
  (moringa-backend → Environment) if you want the Gemini assistant.
- **Free plan limits**: the service sleeps after inactivity (first request
  after sleep takes ~30–60 s to wake), and **uploaded media is ephemeral**
  (lost on each deploy). To persist uploads, upgrade the plan and uncomment
  the `disk:` block in `render.yaml`.
- **Free Postgres expires after 30 days of inactivity** — keep using it or
  attach a credit card to keep it alive.

## Deploying the frontend

Option A — **Render static site** (free): uncomment the `moringa-client`
block at the bottom of `render.yaml`, set `VITE_API_BASE_URL` to your
backend URL (e.g. `https://moringa-backend.onrender.com`), push, and Render
builds and hosts it.

Option B — **Vercel/Netlify**: import the `client/` folder and set the same
environment variable `VITE_API_BASE_URL` before building.

The client reads `VITE_API_BASE_URL` everywhere (default
`http://localhost:5001` for local dev).

## What the blueprint runs

```yaml
buildCommand: pip install -r requirements.txt
startCommand: python setup_db.py && gunicorn -w 2 --threads 4 -b 0.0.0.0:$PORT run:app
healthCheckPath: /
```

`setup_db.py` is idempotent — on every deploy it either bootstraps a fresh
database (create + seed) or applies pending migrations / repairs schema drift
without touching your data.

## Redeploys

Every push to the default branch redeploys automatically (`autoDeploy: true`).

# Deploying Athena on Render

Step-by-step guide for standing up the full Athena stack (database, backend API, frontend, Discord OAuth) on [Render](https://render.com).

---

## Prerequisites

- A GitHub repo containing the Athena codebase.
- A [Discord Developer Application](https://discord.com/developers/applications) for OAuth2.
- A Render account connected to your GitHub.

---

## Architecture on Render

```
Browser
  |
  |  HTTPS
  v
athena-web (Static Site)
  |-- /* --> /index.html           (SPA fallback rewrite)
  |-- /api/* --> athena-api/api/*  (reverse proxy rewrite)
  |
  v
athena-api (Web Service, Python 3)
  |-- FastAPI + Uvicorn
  |-- Reads ATHENA_* env vars
  |
  v
athena-db (PostgreSQL)
  |-- Managed by Render
  |-- Connected via internal URL
```

The frontend is a static Vue build. All `/api/*` requests are rewritten to the backend service. The backend connects to the managed PostgreSQL instance over Render's private network.

---

## 1. Create the Database

1. Render Dashboard > **New** > **PostgreSQL**.
2. **Name**: `athena-db` (or `athena-db-dev` for a dev environment).
3. **Region**: Oregon (or match your backend region).
4. **Plan**: Free tier works for dev; Starter or higher for production.
5. After creation, copy the **Internal Database URL** from the Info tab.

> The Internal URL looks like `postgresql://user:pass@host/dbname`. You will use this as `ATHENA_DATABASE_URL`.

---

## 2. Create the Discord Application

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications).
2. **New Application** > name it (e.g., `Athena` or `Athena Dev`).
3. Navigate to **OAuth2** in the sidebar.
4. Under **Redirects**, add:
   ```
   https://<your-backend-url>/api/auth/callback
   ```
   Example: `https://athena-api.onrender.com/api/auth/callback`
5. Copy the **Client ID** and **Client Secret** (under "Reset Secret" if needed).

> For separate prod/dev environments, create a separate Discord app for each so callback URLs don't conflict.

---

## 3. Create the Backend (Web Service)

1. Render Dashboard > **New** > **Web Service**.
2. **Source**: Connect your GitHub repo.
3. **Branch**: `main` for production, `develop` for dev.
4. **Name**: `athena-api` (or `athena-api-dev`).
5. **Region**: Oregon (match the database).
6. **Runtime**: Python 3.
7. **Build Command**:
   ```bash
   pip install -e .
   ```
8. **Start Command**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### Environment Variables

Set all variables with the `ATHENA_` prefix:

| Variable | Description | Example |
|---|---|---|
| `ATHENA_DATABASE_URL` | Internal DB URL from Step 1 | `postgresql://user:pass@host/dbname` |
| `ATHENA_JWT_SECRET` | Random secret for signing auth tokens | `openssl rand -hex 32` |
| `ATHENA_DISCORD_CLIENT_ID` | From Step 2 | `1234567890` |
| `ATHENA_DISCORD_CLIENT_SECRET` | From Step 2 | `abc123...` |
| `ATHENA_DISCORD_REDIRECT_URI` | OAuth callback URL | `https://athena-api.onrender.com/api/auth/callback` |
| `ATHENA_FRONTEND_URL` | Frontend origin (for post-login redirect) | `https://athena-web.onrender.com` |
| `ATHENA_CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `https://athena-web.onrender.com` |

#### Optional (Gmail integration)

| Variable | Description |
|---|---|
| `ATHENA_GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `ATHENA_GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret |
| `ATHENA_GOOGLE_REFRESH_TOKEN` | Gmail API refresh token (offline access) |
| `ATHENA_GOOGLE_PROJECT_ID` | GCP project ID for Pub/Sub |
| `ATHENA_GOOGLE_PUSH_AUDIENCE` | OIDC audience for Pub/Sub push verification |

> Gmail variables are only needed if you want automatic balance/transaction parsing from bank emails.

---

## 4. Run Database Migrations

After the backend deploys successfully:

1. Open the **Shell** tab on the backend service in Render.
2. Run:
   ```bash
   alembic upgrade head
   ```

This creates all tables from scratch. Alembic reads `ATHENA_DATABASE_URL` from the environment automatically.

> Run this again after any deployment that includes new migrations.

---

## 5. Create the Frontend (Static Site)

1. Render Dashboard > **New** > **Static Site**.
2. **Source**: Same GitHub repo.
3. **Branch**: `main` for production, `develop` for dev.
4. **Name**: `athena-web` (or `athena-web-dev`).
5. **Root Directory**: `frontend`
6. **Build Command**:
   ```bash
   npm install && npm run build
   ```
7. **Publish Directory**: `dist`

### Rewrite Rules

Add these two rules in the Static Site's **Redirects/Rewrites** settings (order matters):

| Type | Source | Destination | Action |
|---|---|---|---|
| Rewrite | `/api/*` | `https://athena-api.onrender.com/api/*` | Rewrite |
| Rewrite | `/*` | `/index.html` | Rewrite |

The first rule proxies API calls to the backend. The second is the SPA fallback so Vue Router handles all other paths.

> Replace `athena-api.onrender.com` with your actual backend URL (e.g., `athena-api-dev.onrender.com` for dev).

---

## 6. Verify the Deployment

1. Open `https://athena-web.onrender.com` (or your frontend URL).
2. Health check: visit `https://athena-api.onrender.com/health` -- should return `{"status": "ok"}`.
3. Click **Login with Discord** -- you should be redirected through Discord and back.
4. Check the API docs at `https://athena-api.onrender.com/docs`.

---

## Multiple Environments (Dev / Staging)

Render supports **Environments** within a Project to group related services.

### Setup

1. In your Render Project, click **Add a new environment**.
2. Name it `Development` (or `Staging`).
3. Create `athena-db-dev`, `athena-api-dev`, and `athena-web-dev` inside the new environment.
4. Point all dev services at the `develop` branch.
5. Use a separate Discord application with the dev callback URL.

### Branch Strategy

```
develop  -->  auto-deploys to Development environment
main     -->  auto-deploys to Production environment
```

Merge `develop` into `main` when changes are validated.

### Environment Variables per Environment

Each environment has its own set of env vars. The only values that change between prod and dev:

| Variable | Production | Development |
|---|---|---|
| `ATHENA_DATABASE_URL` | Prod DB internal URL | Dev DB internal URL |
| `ATHENA_DISCORD_CLIENT_ID` | Prod Discord app | Dev Discord app |
| `ATHENA_DISCORD_CLIENT_SECRET` | Prod Discord app | Dev Discord app |
| `ATHENA_DISCORD_REDIRECT_URI` | `https://athena-api.../api/auth/callback` | `https://athena-api-dev.../api/auth/callback` |
| `ATHENA_FRONTEND_URL` | `https://athena-web...` | `https://athena-web-dev...` |
| `ATHENA_CORS_ORIGINS` | `https://athena-web...` | `https://athena-web-dev...` |

`ATHENA_JWT_SECRET` and Google credentials can be shared or separate.

---

## Troubleshooting

### "Database is not configured" on startup
`ATHENA_DATABASE_URL` is missing or empty. Check the env var is set on the Web Service.

### Discord OAuth redirects to wrong URL
`ATHENA_DISCORD_REDIRECT_URI` must exactly match one of the Redirect URIs configured in the Discord Developer Portal. Check for trailing slashes.

### CORS errors in browser console
`ATHENA_CORS_ORIGINS` must include the exact frontend origin including scheme (`https://`). No trailing slash.

### Migrations fail with "role does not exist"
Render free-tier DBs have a specific user. Make sure `ATHENA_DATABASE_URL` is the Internal URL from the Render Postgres dashboard, not a manually constructed one.

### Frontend shows blank page after deploy
Check that the **Publish Directory** is set to `dist` (not `frontend/dist`), since the **Root Directory** is already `frontend`.

### Backend crashes with RuntimeError on startup
The app validates required config at startup. Check the error message -- it will tell you which `ATHENA_*` variable is missing or invalid.

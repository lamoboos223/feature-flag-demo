# Flagsmith Docker + Python Toggle Demo

This project runs a self-hosted Flagsmith instance with Docker and provides a Python script to turn a feature flag on or off.

## 1) Start Flagsmith in Docker

```powershell
docker compose up -d
```

Open:

- Dashboard: `http://localhost:8000`
- Sign up page: `http://localhost:8000/signup`

## 2) Create your first feature

In the Flagsmith dashboard:

1. Create an Organization / Project (if prompted).
2. Open an Environment.
3. Create a feature (example: `my_feature`).
4. Keep the Environment API key handy.
5. Create/copy an Organization Admin API token (for Admin API calls).

## 3) Install Python dependencies in `.venv`

```powershell
make install
```

## 4) Turn feature ON

```powershell
.venv\Scripts\python toggle_feature.py `
  --base-url http://localhost:8000 `
  --environment-name "Development" `
  --admin-token "<YOUR_ADMIN_TOKEN>" `
  --auth-mode auto `
  --feature my_feature `
  --state on
```

## 5) Turn feature OFF

```powershell
.venv\Scripts\python toggle_feature.py `
  --base-url http://localhost:8000 `
  --environment-name "Development" `
  --admin-token "<YOUR_ADMIN_TOKEN>" `
  --auth-mode auto `
  --feature my_feature `
  --state off
```

## 6) Stop containers

```powershell
docker compose down
```

---

## 7) Run HTML demo (two API responses by flag state)

Set environment variables in PowerShell:

```powershell
$env:FLAGSMITH_BASE_URL = "http://localhost:8000"
$env:FLAGSMITH_ADMIN_TOKEN = "<YOUR_ADMIN_TOKEN>"
$env:FLAGSMITH_ENVIRONMENT_NAME = "Development"
$env:FLAGSMITH_FEATURE_NAME = "my_feature"
$env:FLAGSMITH_AUTH_MODE = "auto"
```

Start the demo app:

```powershell
make run-demo
```

Open `http://127.0.0.1:5000`, click **Fetch API Response**.

- If flag is ON, endpoint returns **response A**
- If flag is OFF, endpoint returns **response B**

API endpoint used by the page: `GET /api/demo-response`

---

## 8) Run HTML demo in Docker (with Flagsmith stack)

Set env vars in PowerShell for compose interpolation:

```powershell
$env:FLAGSMITH_ADMIN_TOKEN = "<YOUR_ADMIN_TOKEN>"
$env:FLAGSMITH_ENVIRONMENT_NAME = "Development"
$env:FLAGSMITH_FEATURE_NAME = "my_feature"
$env:FLAGSMITH_AUTH_MODE = "auto"
```

Bring up the full stack (Flagsmith + demo app):

```powershell
docker compose up -d --build
```

Open:

- Flagsmith dashboard: `http://localhost:8000`
- Demo app: `http://localhost:5000`

Stop all services:

```powershell
docker compose down
```

---

## 9) Run with Makefile

Start everything:

```powershell
make
```

Stop everything:

```powershell
make down
```

Optional:

```powershell
make ps
make logs
make rebuild
make install
make run-demo
```

---

## Notes

- This uses Flagsmith Admin API endpoints, primarily `/api/v1/features/featurestates/`.
- Use an **Organization Admin API token** for `--admin-token` (not an SDK key).
- Auth header mode is auto-detected; for org keys this is usually `Authorization: Api-Key <key>`.
- If your environment key starts with `ser.`, that is typically a server-side SDK key and may not work for this Admin API endpoint.
- You can avoid env-key confusion by using `--environment-name` or `--environment-id` instead.
- If your token lacks permissions, the script will return an HTTP 401 / 403 response.
- For production, set a strong `DJANGO_SECRET_KEY` and tighten host/domain settings in `docker-compose.yml`.
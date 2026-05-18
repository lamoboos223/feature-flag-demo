# Flipt + Flask Feature Flag Demo

This demo runs:
- Flipt server
- Flask API that returns `v1` or `v2` based on a Flipt boolean feature flag

## Start with Docker Compose

```powershell
docker compose up --build -d
```

Open Flipt UI:
- `http://localhost:8080`

## Toggle the flag using Python (`.venv`)

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Turn feature ON:

```powershell
.\.venv\Scripts\python toggle_feature.py --state on
```

Turn feature OFF:

```powershell
.\.venv\Scripts\python toggle_feature.py --state off
```

By default, the script manages:
- namespace: `default`
- flag: `api-version-v2`
- Flipt base URL: `http://localhost:8080`

You can override them:

```powershell
.\.venv\Scripts\python toggle_feature.py `
  --base-url http://localhost:8080 `
  --namespace default `
  --flag api-version-v2 `
  --state on
```

## Test the API

```powershell
curl "http://localhost:5000/?userId=alice"
```

Expected behavior:
- Flag ON -> `"version": "v2"`
- Flag OFF -> `"version": "v1"`

If `userId` is missing:

```json
{"error":"Missing required query parameter: userId"}
```

## Run tests

```powershell
.\.venv\Scripts\pytest -q
```

## Stop

```powershell
docker compose down
```

# Flipt + Flask Feature Flag Demo

This demo runs:
- Flipt server
- Flask API that returns `v1` or `v2` based on Flipt rules

## Start with Docker Compose

```powershell
docker compose up --build -d
```

Open Flipt UI:
- `http://localhost:8080`

## Change flag behavior (Git source of truth)

Edit `flipt-state-repo/features.yml` and commit the change:

```powershell
cd flipt-state-repo
git add features.yml
git commit -m "Update Flipt rules"
```

Flipt polls the repository and applies changes automatically.

## Test the API

```powershell
curl.exe --location "http://localhost:5000" `
  --header "Content-Type: application/json" `
  --data-raw "{\"email\":\"alice@gmail.com\"}"
```

If `email` is missing:

```json
{"error":"Missing required JSON field: email"}
```

## Stop

```powershell
docker compose down
```

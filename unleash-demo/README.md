# Unleash + Flask Feature Flag Demo

This demo runs:
- Unleash server
- Postgres database for Unleash
- Flask API that returns `v1` or `v2` based on a feature flag

## Start

Add your Unleash backend token to `.env` first:

```env
UNLEASH_API_TOKEN=default:development.your-token-here
```

Then start:

```bash
docker compose up --build -d
```

## Open Unleash

- URL: `http://localhost:4242`
- First time login uses setup flow in the UI.
- Create a project/environment token if you do not use the pre-seeded demo token.

## Create the Feature Flag

1. In Unleash, create a feature flag named `api-version-v2`.
2. Enable it in the `development` environment.
3. Add a strategy:
   - **Flexible rollout** to test percentages, or
   - **User ID** constraints for targeted users.

## Test the API

```bash
curl "http://localhost:5000/?userId=alice"
curl "http://localhost:5000/?userId=bob"
```

`userId` is required. If omitted, API returns:

```json
{"error":"Missing required query parameter: userId"}
```

Response example:

```json
{
  "feature_flag": "api-version-v2",
  "response": "Hello from v2",
  "userId": "alice",
  "version": "v2"
}
```

If flag is disabled (or user not targeted), response version is `v1`.

## Local Python run (optional)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Run tests

```bash
pytest -q
```

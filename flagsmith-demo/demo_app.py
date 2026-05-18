import os
from functools import lru_cache
from typing import Dict, Iterable, Tuple

import requests
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

FLAGSMITH_BASE_URL = os.getenv("FLAGSMITH_BASE_URL", "http://localhost:8000").rstrip("/")
FLAGSMITH_ADMIN_TOKEN = os.getenv("FLAGSMITH_ADMIN_TOKEN", "")
FLAGSMITH_ENVIRONMENT_NAME = os.getenv("FLAGSMITH_ENVIRONMENT_NAME", "Development")
FLAGSMITH_FEATURE_NAME = os.getenv("FLAGSMITH_FEATURE_NAME", "my_feature")
FLAGSMITH_AUTH_MODE = os.getenv("FLAGSMITH_AUTH_MODE", "auto").lower()

HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Flagsmith Demo</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; background: #f8fafc; }
      .card { max-width: 820px; background: white; border-radius: 12px; padding: 1.2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
      .ok { color: #166534; }
      .off { color: #991b1b; }
      pre { background: #0f172a; color: #e2e8f0; padding: 1rem; border-radius: 8px; overflow: auto; }
      button { background: #4f46e5; color: white; border: none; padding: 0.6rem 1rem; border-radius: 8px; cursor: pointer; }
      button:hover { background: #4338ca; }
      .meta { color: #334155; margin: 0.6rem 0; }
    </style>
  </head>
  <body>
    <div class="card">
      <h2>Flagsmith API Response Demo</h2>
      <p class="meta">
        Feature: <b>{{ feature_name }}</b> | Environment: <b>{{ environment_name }}</b>
      </p>
      <p>Toggle your feature with <code>toggle_feature.py</code>, then click refresh below.</p>
      <button onclick="loadResponse()">Fetch API Response</button>
      <p id="status" class="meta">Waiting for first request...</p>
      <pre id="payload">{}</pre>
    </div>

    <script>
      async function loadResponse() {
        const status = document.getElementById("status");
        const payload = document.getElementById("payload");
        status.textContent = "Loading...";
        status.className = "meta";

        try {
          const res = await fetch("/api/demo-response");
          const data = await res.json();
          payload.textContent = JSON.stringify(data, null, 2);

          if (data.feature_enabled) {
            status.textContent = "Feature is ON -> returned response A";
            status.className = "meta ok";
          } else {
            status.textContent = "Feature is OFF -> returned response B";
            status.className = "meta off";
          }
        } catch (err) {
          status.textContent = "Request failed: " + err;
          status.className = "meta off";
        }
      }
    </script>
  </body>
</html>
"""


def parse_json_or_raise(resp: requests.Response, context: str):
    try:
        return resp.json()
    except ValueError as exc:
        snippet = (resp.text or "").strip().replace("\n", " ")
        snippet = snippet[:220] + ("..." if len(snippet) > 220 else "")
        raise RuntimeError(
            f"{context} did not return JSON. status={resp.status_code} body={snippet!r}"
        ) from exc


def build_auth_header(token: str, mode: str) -> Dict[str, str]:
    if mode == "api-key":
        return {"Authorization": f"Api-Key {token}"}
    if mode == "token":
        return {"Authorization": f"Token {token}"}
    raise RuntimeError(f"Unsupported auth mode: {mode}")


def detect_auth_headers(base_url: str, token: str, preferred_mode: str = "auto") -> Dict[str, str]:
    if not token:
        raise RuntimeError(
            "FLAGSMITH_ADMIN_TOKEN is missing. Set it before starting demo_app.py."
        )
    modes = [preferred_mode] if preferred_mode in {"api-key", "token"} else ["api-key", "token"]
    for mode in modes:
        headers = build_auth_header(token, mode)
        resp = requests.get(f"{base_url}/api/v1/projects/", headers=headers, timeout=20)
        if resp.status_code == 401:
            continue
        resp.raise_for_status()
        return headers
    raise RuntimeError("Admin token is invalid for both Api-Key and Token auth modes.")


def list_projects(base_url: str, headers: Dict[str, str]) -> Iterable[dict]:
    resp = requests.get(f"{base_url}/api/v1/projects/", headers=headers, timeout=20)
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Projects API")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    raise RuntimeError(f"Unexpected projects payload: {type(data)}")


def list_environments(base_url: str, headers: Dict[str, str], project_id: int) -> Iterable[dict]:
    resp = requests.get(
        f"{base_url}/api/v1/environments/",
        headers=headers,
        params={"project": project_id},
        timeout=20,
    )
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Environments API")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    raise RuntimeError(f"Unexpected environments payload: {type(data)}")


@lru_cache(maxsize=1)
def resolve_context() -> Tuple[Dict[str, str], int, int]:
    headers = detect_auth_headers(FLAGSMITH_BASE_URL, FLAGSMITH_ADMIN_TOKEN, FLAGSMITH_AUTH_MODE)
    for project in list_projects(FLAGSMITH_BASE_URL, headers):
        project_id = project.get("id")
        if not isinstance(project_id, int):
            continue
        for env in list_environments(FLAGSMITH_BASE_URL, headers, project_id):
            if (env.get("name") or "").lower() == FLAGSMITH_ENVIRONMENT_NAME.lower():
                env_id = env.get("id")
                if isinstance(env_id, int):
                    return headers, project_id, env_id
    raise RuntimeError(f"Environment '{FLAGSMITH_ENVIRONMENT_NAME}' not found.")


def resolve_feature_id(headers: Dict[str, str], project_id: int, environment_id: int) -> int:
    resp = requests.get(
        f"{FLAGSMITH_BASE_URL}/api/v1/projects/{project_id}/features/",
        headers=headers,
        params={"environment": environment_id, "search": FLAGSMITH_FEATURE_NAME},
        timeout=20,
    )
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Features API")
    items = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise RuntimeError(f"Unexpected features payload: {type(items)}")
    for feature in items:
        if (feature.get("name") or "").lower() == FLAGSMITH_FEATURE_NAME.lower():
            feature_id = feature.get("id")
            if isinstance(feature_id, int):
                return feature_id
    raise RuntimeError(
        f"Feature '{FLAGSMITH_FEATURE_NAME}' not found in environment '{FLAGSMITH_ENVIRONMENT_NAME}'."
    )


def is_feature_enabled() -> bool:
    headers, project_id, environment_id = resolve_context()
    feature_id = resolve_feature_id(headers, project_id, environment_id)
    resp = requests.get(
        f"{FLAGSMITH_BASE_URL}/api/v1/features/featurestates/",
        headers=headers,
        params={"environment": environment_id},
        timeout=20,
    )
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Featurestates API")
    states = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(states, list):
        raise RuntimeError(f"Unexpected featurestates payload: {type(states)}")

    for state in states:
        raw_feature = state.get("feature")
        if raw_feature == feature_id:
            return bool(state.get("enabled"))
        if isinstance(raw_feature, dict) and raw_feature.get("id") == feature_id:
            return bool(state.get("enabled"))
    raise RuntimeError(
        f"Feature state for '{FLAGSMITH_FEATURE_NAME}' not found in environment '{FLAGSMITH_ENVIRONMENT_NAME}'."
    )


@app.get("/")
def index():
    return render_template_string(
        HTML,
        feature_name=FLAGSMITH_FEATURE_NAME,
        environment_name=FLAGSMITH_ENVIRONMENT_NAME,
    )


@app.get("/api/demo-response")
def demo_response():
    enabled = is_feature_enabled()
    if enabled:
        payload = {
            "feature_enabled": True,
            "response_type": "A",
            "message": "Feature is ON - returning premium response payload.",
            "data": {
                "recommendation": "Use new ranking model",
                "items": ["alpha", "beta", "gamma"],
            },
        }
    else:
        payload = {
            "feature_enabled": False,
            "response_type": "B",
            "message": "Feature is OFF - returning fallback response payload.",
            "data": {
                "recommendation": "Use stable ranking model",
                "items": ["legacy-1", "legacy-2"],
            },
        }
    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

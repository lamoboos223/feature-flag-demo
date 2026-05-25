import os
import subprocess

import requests
import yaml
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
flipt_url = os.getenv("FLIPT_URL", "http://localhost:8080")
namespace = os.getenv("FLIPT_NAMESPACE_KEY", "default")
state_repo = os.getenv("FLIPT_STATE_REPO", "./flipt-state-repo")

TWK_FLAGS = [
    "twk_show-wakeb",
    "twk_show-messages",
    "twk_show-quick-access",
    "twk_show-city-banner",
    "twk_show-search-bar",
]


# ---------------------------------------------------------------------------
# Flipt helpers  (variant flags with "on" / "off" keys)
# ---------------------------------------------------------------------------

def _api(path=""):
    return f"{flipt_url.rstrip('/')}{path}"


def evaluate_variant_flag(flag_key: str, entity_id: str = "demo-user",
                          context: dict | None = None) -> bool:
    """Evaluate a variant flag and return True when the variant is 'on'."""
    payload = {
        "namespaceKey": namespace,
        "flagKey": flag_key,
        "entityId": entity_id,
        "context": context or {},
    }
    try:
        r = requests.post(_api("/evaluate/v1/variant"), json=payload, timeout=5)
        r.raise_for_status()
        data = r.json()
        if not data.get("match", False):
            return True  # no rule matched → default visible
        return data.get("variantKey", "on") == "on"
    except Exception:
        return True


def get_global_flag_state(flag_key: str) -> bool:
    try:
        r = requests.get(
            _api(f"/api/v1/namespaces/{namespace}/flags/{flag_key}"), timeout=5
        )
        if r.ok:
            return r.json().get("enabled", True)
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# Git-based flag toggle
# ---------------------------------------------------------------------------

def toggle_flag_in_repo(flag_key: str) -> bool | None:
    """Toggle a flag's enabled state in features.yml and git-commit the change."""
    features_path = os.path.join(state_repo, "features.yml")

    with open(features_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    new_enabled = None
    for flag in data.get("flags", []):
        if flag["key"] == flag_key:
            flag["enabled"] = not flag.get("enabled", True)
            new_enabled = flag["enabled"]
            break

    if new_enabled is None:
        return None

    with open(features_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False,
                  sort_keys=False)

    subprocess.run(["git", "add", "features.yml"],
                   cwd=state_repo, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Toggle {flag_key} {'on' if new_enabled else 'off'}"],
        cwd=state_repo, capture_output=True,
    )
    return new_enabled


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def twk_page():
    return render_template("twk.html")


@app.get("/api/twk/flags")
def get_flags():
    email = request.args.get("email", "demo@gmail.com")
    context = {"email": email}
    result = {}
    for key in TWK_FLAGS:
        evaluated = evaluate_variant_flag(key, email, context)
        global_state = get_global_flag_state(key)
        result[key] = {
            "evaluated": evaluated,
            "global": global_state,
            "overridden": evaluated != global_state,
        }
    return jsonify(result)


@app.post("/api/twk/flags/<flag_key>/toggle")
def toggle_flag(flag_key):
    if flag_key not in TWK_FLAGS:
        return jsonify({"error": "Unknown flag"}), 404
    new_state = toggle_flag_in_repo(flag_key)
    if new_state is None:
        return jsonify({"error": "Flag not found in features.yml"}), 404
    return jsonify({"key": flag_key, "enabled": new_state})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")))

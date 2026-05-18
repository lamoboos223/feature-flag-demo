import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
flipt_url = os.getenv("FLIPT_URL", "http://localhost:8080")
namespace = os.getenv("FLIPT_NAMESPACE_KEY", "default")
flag = os.getenv("FLIPT_FLAG_NAME", "api-version-v2")
skip_flipt_eval = os.getenv("SKIP_FLIPT_EVAL", "0") == "1"

def evaluate_version(base_url: str, namespace: str, flag: str, email: str) -> str:
    payload = {
        "namespaceKey": namespace,
        "flagKey": flag,
        "entityId": email,
        "context": {"email": email},
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/evaluate/v1/variant",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return str(response.json().get("variantKey", "v1"))


@app.post("/")
def greeting():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    if not email:
        return jsonify({"error": "Missing required JSON field: email"}), 400

    version = "v1" if skip_flipt_eval else evaluate_version(flipt_url, namespace, flag, str(email))
    return jsonify(
        {
            "feature_flag": flag,
            "email": email,
            "response": f"Hello from {version}",
            "version": version,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))

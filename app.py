import os

import requests
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
flipt_url = os.getenv("FLIPT_URL", "http://localhost:8080")
namespace = os.getenv("FLIPT_NAMESPACE_KEY", "default")
feature_flag_key = os.getenv("FLIPT_FLAG_NAME", "api-version-v2")

def get_feature_flag_value(feature_flag_key: str, context_values: dict) -> str:
    payload = {
        "namespaceKey": namespace,
        "flagKey": feature_flag_key,
        "context": context_values,
    }
    response = requests.post(
        f"{flipt_url.rstrip('/')}/evaluate/v1/variant",
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

    version = get_feature_flag_value(feature_flag_key, {"email": email})
    return jsonify(
        {
            "feature_flag": feature_flag_key,
            "email": email,
            "response": f"Hello from {version}",
            "version": version,
        }
    )


@app.get("/page")
def versioned_page() -> Response:
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Missing required query parameter: email"}), 400

    version = get_feature_flag_value(feature_flag_key, {"email": email})
    if version == "v2":
        html = f"""
        <html><body style="font-family:Arial;background:#ecfeff;padding:24px;">
          <h1 style="color:#0f766e;">V2 Experience</h1>
          <p>Welcome <b>{email}</b>.</p>
          <p>You are seeing the new version based on Flipt rules.</p>
        </body></html>
        """
    else:
        html = f"""
        <html><body style="font-family:Arial;background:#f8fafc;padding:24px;">
          <h1 style="color:#334155;">V1 Experience</h1>
          <p>Welcome <b>{email}</b>.</p>
          <p>You are seeing the stable fallback version.</p>
        </body></html>
        """
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))

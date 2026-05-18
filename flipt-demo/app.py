import os
from typing import Callable

import requests
from flask import Flask, jsonify, request


def evaluate_boolean_flag(
    base_url: str,
    namespace_key: str,
    flag_key: str,
    entity_id: str,
    extra_context: dict[str, str] | None = None,
    auth_token: str | None = None,
) -> bool:
    url = f"{base_url.rstrip('/')}/evaluate/v1/boolean"
    context = {"entityId": entity_id, "userId": entity_id}
    if extra_context:
        context.update(extra_context)
    payload = {
        "namespaceKey": namespace_key,
        "flagKey": flag_key,
        "entityId": entity_id,
        "context": context,
    }
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    return bool(data.get("enabled", False))


def resolve_version(
    evaluator: Callable[[str, str, dict[str, str] | None], bool],
    flag_name: str,
    entity_id: str,
    extra_context: dict[str, str] | None = None,
) -> str:
    return "v2" if evaluator(flag_name, entity_id, extra_context) else "v1"


def create_app() -> Flask:
    app = Flask(__name__)

    flipt_url = os.getenv("FLIPT_URL", "http://localhost:8080")
    namespace_key = os.getenv("FLIPT_NAMESPACE_KEY", "default")
    flag_name = os.getenv("FLIPT_FLAG_NAME", "api-version-v2")
    auth_token = os.getenv("FLIPT_AUTH_TOKEN", "")
    skip_flipt_eval = os.getenv("SKIP_FLIPT_EVAL", "0") == "1"

    def evaluator(
        target_flag_name: str,
        entity_id: str,
        extra_context: dict[str, str] | None = None,
    ) -> bool:
        if skip_flipt_eval:
            return False
        return evaluate_boolean_flag(
            base_url=flipt_url,
            namespace_key=namespace_key,
            flag_key=target_flag_name,
            entity_id=entity_id,
            extra_context=extra_context,
            auth_token=auth_token or None,
        )

    @app.get("/")
    def get_versioned_response():
        user_id = request.args.get("userId")
        if not user_id:
            return jsonify({"error": "Missing required query parameter: userId"}), 400

        version = resolve_version(evaluator, flag_name, user_id)
        return jsonify(
            {
                "feature_flag": flag_name,
                "userId": user_id,
                "response": f"Hello from {version}",
                "version": version,
            }
        )

    def evaluate_with_payload():
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict) or not payload:
            return jsonify({"error": "Request JSON body must contain at least one field"}), 400

        context = {
            str(key): str(value)
            for key, value in payload.items()
            if value is not None
        }
        if not context:
            return jsonify({"error": "Request JSON body must contain at least one non-null field"}), 400

        entity_id = str(
            payload.get("entityId")
            or payload.get("userId")
            or payload.get("email")
            or next(iter(context.values()))
        )

        version = resolve_version(evaluator, flag_name, entity_id, context)
        return jsonify(
            {
                "feature_flag": flag_name,
                "entityId": entity_id,
                "input": payload,
                "response": f"Hello from {version}",
                "version": version,
            }
        )

    @app.post("/")
    def post_root_versioned_response():
        return evaluate_with_payload()

    @app.post("/evaluate")
    def post_versioned_response():
        return evaluate_with_payload()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))

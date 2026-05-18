import atexit
import os
from typing import Callable, TYPE_CHECKING

from flask import Flask, jsonify, request

if TYPE_CHECKING:
    from UnleashClient import UnleashClient


def create_unleash_client() -> "UnleashClient":
    from UnleashClient import UnleashClient

    url = os.getenv("UNLEASH_URL", "http://localhost:4242/api")
    app_name = os.getenv("UNLEASH_APP_NAME", "flask-demo")
    instance_id = os.getenv("UNLEASH_INSTANCE_ID", "flask-demo-instance")
    token = os.getenv(
        "UNLEASH_API_TOKEN",
        "default:development.unleash-insecure-api-token",
    )
    refresh_interval = int(os.getenv("UNLEASH_REFRESH_INTERVAL", "5"))
    metrics_interval = int(os.getenv("UNLEASH_METRICS_INTERVAL", "30"))

    client = UnleashClient(
        url=url,
        app_name=app_name,
        instance_id=instance_id,
        custom_headers={"Authorization": token},
        refresh_interval=refresh_interval,
        metrics_interval=metrics_interval,
    )
    client.initialize_client()
    return client


def resolve_version(
    is_enabled: Callable[[str, dict], bool], flag_name: str, user_id: str
) -> str:
    context = {"userId": user_id}
    return "v2" if is_enabled(flag_name, context) else "v1"


def create_app() -> Flask:
    app = Flask(__name__)
    flag_name = os.getenv("UNLEASH_FLAG_NAME", "api-version-v2")
    skip_unleash = os.getenv("SKIP_UNLEASH_CLIENT", "0") == "1"
    unleash_client = None if skip_unleash else create_unleash_client()

    @atexit.register
    def shutdown_unleash_client() -> None:
        if unleash_client is not None:
            unleash_client.destroy()

    @app.get("/")
    def get_versioned_response():
        user_id = request.args.get("userId")
        if not user_id:
            return jsonify({"error": "Missing required query parameter: userId"}), 400
        checker = (
            unleash_client.is_enabled
            if unleash_client is not None
            else lambda _flag, _context: False
        )
        version = resolve_version(checker, flag_name, user_id)
        return jsonify(
            {
                "feature_flag": flag_name,
                "userId": user_id,
                "response": f"Hello from {version}",
                "version": version,
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))

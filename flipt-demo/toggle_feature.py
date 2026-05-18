import argparse
import sys
from typing import Any

import requests


def request_headers(auth_token: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def ensure_namespace(base_url: str, namespace_key: str, auth_token: str | None) -> None:
    headers = request_headers(auth_token)
    get_url = f"{base_url.rstrip('/')}/api/v1/namespaces/{namespace_key}"
    get_response = requests.get(get_url, headers=headers, timeout=15)
    if get_response.status_code == 200:
        return
    if get_response.status_code != 404:
        get_response.raise_for_status()

    create_url = f"{base_url.rstrip('/')}/api/v1/namespaces"
    payload = {"key": namespace_key, "name": namespace_key}
    create_response = requests.post(create_url, json=payload, headers=headers, timeout=15)
    create_response.raise_for_status()


def ensure_boolean_flag(
    base_url: str,
    namespace_key: str,
    flag_key: str,
    enabled: bool,
    auth_token: str | None,
) -> dict[str, Any]:
    headers = request_headers(auth_token)
    get_url = f"{base_url.rstrip('/')}/api/v1/namespaces/{namespace_key}/flags/{flag_key}"
    get_response = requests.get(get_url, headers=headers, timeout=15)
    if get_response.status_code == 200:
        existing = get_response.json()
        update_payload = {
            "key": existing.get("key", flag_key),
            "name": existing.get("name", flag_key),
            "description": existing.get("description", "Demo API version flag"),
            "enabled": enabled,
            "type": existing.get("type", "BOOLEAN_FLAG_TYPE"),
        }
        update_url = f"{base_url.rstrip('/')}/api/v1/namespaces/{namespace_key}/flags/{flag_key}"
        update_response = requests.put(
            update_url, json=update_payload, headers=headers, timeout=15
        )
        update_response.raise_for_status()
        return update_response.json()

    if get_response.status_code != 404:
        get_response.raise_for_status()

    create_url = f"{base_url.rstrip('/')}/api/v1/namespaces/{namespace_key}/flags"
    create_payload = {
        "key": flag_key,
        "name": flag_key,
        "description": "Demo API version flag",
        "enabled": enabled,
        "type": "BOOLEAN_FLAG_TYPE",
    }
    create_response = requests.post(
        create_url, json=create_payload, headers=headers, timeout=15
    )
    create_response.raise_for_status()
    return create_response.json()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create/update a Flipt boolean feature flag to ON or OFF."
    )
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--flag", default="api-version-v2")
    parser.add_argument("--state", required=True, choices=["on", "off"])
    parser.add_argument("--auth-token", default="", help="Optional Flipt bearer token.")
    args = parser.parse_args()

    desired = args.state == "on"

    try:
        ensure_namespace(args.base_url, args.namespace, args.auth_token or None)
        flag = ensure_boolean_flag(
            args.base_url,
            args.namespace,
            args.flag,
            desired,
            args.auth_token or None,
        )
        print(
            f"Flag '{flag.get('key', args.flag)}' is now "
            f"{'ON' if flag.get('enabled') else 'OFF'}."
        )
        return 0
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else "<no response body>"
        print(f"HTTP error: {exc}\nResponse body: {body}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

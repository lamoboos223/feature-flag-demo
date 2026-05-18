import argparse
import sys
from typing import Any, Dict, Iterable, Optional, Tuple

import requests


def parse_json_or_raise(resp: requests.Response, context: str) -> Any:
    try:
        return resp.json()
    except ValueError as exc:
        snippet = (resp.text or "").strip().replace("\n", " ")
        snippet = snippet[:240] + ("..." if len(snippet) > 240 else "")
        raise RuntimeError(
            f"{context} did not return JSON. "
            f"status={resp.status_code} content-type={resp.headers.get('content-type')!r} "
            f"body={snippet!r}. "
            "This usually means your key/token is incorrect for this endpoint."
        ) from exc


def auth_header(token: str, auth_mode: str) -> Dict[str, str]:
    if auth_mode == "api-key":
        return {"Authorization": f"Api-Key {token}"}
    if auth_mode == "token":
        return {"Authorization": f"Token {token}"}
    raise RuntimeError(f"Unsupported auth mode: {auth_mode}")


def detect_auth_mode(base_url: str, token: str, preferred_mode: str = "auto") -> Tuple[str, Dict[str, str]]:
    # Some Flagsmith versions require query params on /environments/,
    # so we validate auth against /projects/ instead.
    url = f"{base_url.rstrip('/')}/api/v1/projects/"
    modes = [preferred_mode] if preferred_mode in {"api-key", "token"} else ["api-key", "token"]
    for mode in modes:
        headers = auth_header(token, mode)
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 401:
            continue
        resp.raise_for_status()
        return mode, headers
    raise RuntimeError(
        "Admin token is invalid (401) for both auth modes (Api-Key and Token). "
        "Generate a fresh Organization Admin API token and use it immediately."
    )


def list_projects(base_url: str, headers: Dict[str, str]) -> Iterable[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/projects/"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Projects API")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    raise RuntimeError(
        f"Unexpected projects payload shape: {type(data)}. "
        "Expected list or paginated dict with 'results'."
    )


def list_environments(base_url: str, headers: Dict[str, str], project_id: int) -> Iterable[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/environments/"
    resp = requests.get(
        url,
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
    raise RuntimeError(
        f"Unexpected environments payload shape: {type(data)}. "
        "Expected list or paginated dict with 'results'."
    )


def resolve_environment_id(base_url: str, headers: Dict[str, str], environment_name: str) -> int:
    projects = list_projects(base_url, headers)
    all_envs = []
    for project in projects:
        project_id = project.get("id")
        if not isinstance(project_id, int):
            continue
        envs = list_environments(base_url, headers, project_id=project_id)
        all_envs.extend(envs)

    for env in all_envs:
        if (env.get("name") or "").lower() == environment_name.lower():
            env_id = env.get("id")
            if isinstance(env_id, int):
                return env_id
            raise RuntimeError(
                f"Environment '{environment_name}' found but id is invalid: {env_id!r}"
            )
    available = ", ".join(sorted((env.get("name") or "<unnamed>") for env in all_envs))
    raise RuntimeError(
        f"Environment '{environment_name}' not found. Available: {available or '<none>'}"
    )


def get_environment(base_url: str, headers: Dict[str, str], environment_id: int) -> Dict[str, Any]:
    projects = list_projects(base_url, headers)
    for project in projects:
        project_id = project.get("id")
        if not isinstance(project_id, int):
            continue
        envs = list_environments(base_url, headers, project_id=project_id)
        for env in envs:
            if env.get("id") == environment_id:
                return env
    raise RuntimeError(f"Environment id '{environment_id}' not found.")


def resolve_feature_id(
    base_url: str,
    headers: Dict[str, str],
    project_id: int,
    environment_id: int,
    feature_name: str,
) -> int:
    url = f"{base_url.rstrip('/')}/api/v1/projects/{project_id}/features/"
    resp = requests.get(
        url,
        headers=headers,
        params={"environment": environment_id, "search": feature_name},
        timeout=20,
    )
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Features API")
    features = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(features, list):
        raise RuntimeError(f"Unexpected features payload shape: {type(features)}")

    for feature in features:
        if (feature.get("name") or "").lower() == feature_name.lower():
            feature_id = feature.get("id")
            if isinstance(feature_id, int):
                return feature_id
            raise RuntimeError(
                f"Feature '{feature_name}' found but id is invalid: {feature_id!r}"
            )
    raise RuntimeError(
        f"Feature '{feature_name}' not found in project {project_id} / environment {environment_id}."
    )


def fetch_featurestates_by_env_key(base_url: str, env_key: str, headers: Dict[str, str]) -> Iterable[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/environments/{env_key}/featurestates/"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Featurestates API")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    raise RuntimeError(
        f"Unexpected featurestates payload shape: {type(data)}. "
        "Expected list or paginated dict with 'results'."
    )


def fetch_featurestates_by_env_id(base_url: str, env_id: int, headers: Dict[str, str]) -> Iterable[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/features/featurestates/"
    resp = requests.get(url, headers=headers, params={"environment": env_id}, timeout=20)
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Featurestates API")
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    raise RuntimeError(
        f"Unexpected featurestates payload shape: {type(data)}. "
        "Expected paginated dict with 'results' or a list."
    )


def find_featurestate(
    states: Iterable[Dict[str, Any]],
    feature_name: str,
    feature_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    for state in states:
        raw_feature = state.get("feature")
        if isinstance(raw_feature, dict):
            if raw_feature.get("name") == feature_name:
                return state
            if feature_id is not None and raw_feature.get("id") == feature_id:
                return state
        elif isinstance(raw_feature, int):
            if feature_id is not None and raw_feature == feature_id:
                return state
    return None


def update_featurestate(base_url: str, headers: Dict[str, str], state: Dict[str, Any], enabled: bool) -> Dict[str, Any]:
    state_id = state["id"]
    url = f"{base_url.rstrip('/')}/api/v1/features/featurestates/{state_id}/"
    raw_feature = state.get("feature")
    if isinstance(raw_feature, dict):
        feature_id = raw_feature.get("id")
    else:
        feature_id = raw_feature
    if not isinstance(feature_id, int):
        raise RuntimeError(f"Unexpected feature field in featurestate: {raw_feature!r}")
    payload = {
        "feature": feature_id,
        "enabled": enabled,
        "environment": state["environment"],
        "feature_segment": state.get("feature_segment"),
        "identity": state.get("identity"),
        "feature_state_value": state.get("feature_state_value"),
    }
    resp = requests.put(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    data = parse_json_or_raise(resp, "Featurestate update API")
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected update payload shape: {type(data)}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Toggle a Flagsmith feature flag on/off using the Admin API."
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="Flagsmith base URL.")
    env_selector = parser.add_mutually_exclusive_group(required=True)
    env_selector.add_argument(
        "--env-key",
        help="Environment API key (legacy path).",
    )
    env_selector.add_argument(
        "--environment-id",
        type=int,
        help="Environment numeric id (recommended).",
    )
    env_selector.add_argument(
        "--environment-name",
        help="Environment name to resolve via Admin API (example: Development).",
    )
    parser.add_argument("--admin-token", required=True, help="Organization Admin API token.")
    parser.add_argument(
        "--auth-mode",
        default="auto",
        choices=["auto", "api-key", "token"],
        help="Authorization header mode. 'auto' tries Api-Key first, then Token.",
    )
    parser.add_argument("--feature", required=True, help="Feature name to toggle.")
    parser.add_argument(
        "--state",
        required=True,
        choices=["on", "off"],
        help="Desired state for the feature.",
    )
    args = parser.parse_args()

    try:
        if args.env_key and args.env_key.startswith("ser."):
            print(
                "Warning: key starts with 'ser.' (SDK/server-side key). "
                "Admin API routes may require the Environment API key used by Admin endpoints."
            )

        auth_mode, headers = detect_auth_mode(
            args.base_url,
            args.admin_token,
            preferred_mode=args.auth_mode,
        )
        print(f"Authenticated using Authorization mode: {auth_mode}.")
        feature_id = None
        if args.environment_id is not None:
            env = get_environment(args.base_url, headers, args.environment_id)
            states = fetch_featurestates_by_env_id(
                args.base_url, args.environment_id, headers
            )
            feature_id = resolve_feature_id(
                args.base_url,
                headers,
                project_id=env["project"],
                environment_id=args.environment_id,
                feature_name=args.feature,
            )
        elif args.environment_name:
            env_id = resolve_environment_id(
                args.base_url, headers, args.environment_name
            )
            print(f"Resolved environment '{args.environment_name}' to id {env_id}.")
            env = get_environment(args.base_url, headers, env_id)
            states = fetch_featurestates_by_env_id(args.base_url, env_id, headers)
            feature_id = resolve_feature_id(
                args.base_url,
                headers,
                project_id=env["project"],
                environment_id=env_id,
                feature_name=args.feature,
            )
        else:
            states = fetch_featurestates_by_env_key(
                args.base_url, args.env_key, headers
            )
        target = find_featurestate(states, args.feature, feature_id=feature_id)
        if not target:
            print(f"Feature '{args.feature}' was not found in this environment.")
            return 2

        desired = args.state == "on"
        current = bool(target.get("enabled"))
        if current == desired:
            print(f"Feature '{args.feature}' is already {'ON' if desired else 'OFF'}.")
            return 0

        updated = update_featurestate(
            args.base_url,
            headers,
            target,
            enabled=desired,
        )
        print(
            f"Feature '{args.feature}' updated: "
            f"{'ON' if updated.get('enabled') else 'OFF'}"
        )
        return 0
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else "<no body>"
        print(f"HTTP error: {exc}\nResponse: {body}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

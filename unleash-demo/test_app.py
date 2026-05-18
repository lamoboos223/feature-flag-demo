import os

os.environ["SKIP_UNLEASH_CLIENT"] = "1"

from app import create_app, resolve_version


def test_returns_v1_when_flag_is_disabled():
    def fake_is_enabled(flag_name, context):
        return False

    result = resolve_version(fake_is_enabled, "api-version-v2", "user-a")
    assert result == "v1"


def test_returns_v2_when_flag_is_enabled():
    def fake_is_enabled(flag_name, context):
        return True

    result = resolve_version(fake_is_enabled, "api-version-v2", "user-b")
    assert result == "v2"


def test_requires_user_id_query_param():
    client = create_app().test_client()

    response = client.get("/")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Missing required query parameter: userId",
    }


def test_uses_query_param_user_id():
    client = create_app().test_client()

    response = client.get("/?userId=alice")

    assert response.status_code == 200
    data = response.get_json()
    assert data["userId"] == "alice"

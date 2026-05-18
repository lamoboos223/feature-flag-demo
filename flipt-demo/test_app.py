import os

os.environ["SKIP_FLIPT_EVAL"] = "1"

from app import create_app, resolve_version


def test_returns_v1_when_flag_is_disabled():
    def fake_evaluator(flag_name, entity_id, extra_context):
        return "v1"

    result = resolve_version(fake_evaluator, "api-version-v2", "user-a")
    assert result == "v1"


def test_returns_v2_when_flag_is_enabled():
    def fake_evaluator(flag_name, entity_id, extra_context):
        return "v2"

    result = resolve_version(fake_evaluator, "api-version-v2", "user-b")
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


def test_post_requires_non_empty_payload():
    client = create_app().test_client()

    response = client.post("/", json={})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Request JSON body must contain at least one field",
    }


def test_post_payload_returns_response_shape():
    client = create_app().test_client()

    response = client.post(
        "/",
        json={"email": "alice2@gmail.com"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["entityId"] == "alice2@gmail.com"
    assert data["input"] == {"email": "alice2@gmail.com"}

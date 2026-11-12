import pytest

from silip.shared.auth.domain import AuthenticationError, user_from_claims
from silip.shared.config import ApiSettings, ConfigError
from tests.api.helpers import auth

CLAIMS = {
    "token_use": "access",
    "client_id": "c",
    "sub": "s",
    "username": "u",
    "cognito:groups": ["engineers"],
}


def test_health_is_public(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_me_needs_a_token(client):
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_returns_the_signed_in_user(client):
    assert client.get("/api/v1/me", headers=auth("engineer-token")).json()["groups"] == [
        "engineers"
    ]


def test_invalid_token_is_401(client):
    assert client.get("/api/v1/me", headers=auth("forged")).status_code == 401


@pytest.mark.parametrize(
    "bad", [{"token_use": "id"}, {"client_id": "other"}, {"cognito:groups": "engineers"}]
)
def test_claim_rules_reject_bad_tokens(bad):
    with pytest.raises(AuthenticationError):
        user_from_claims({**CLAIMS, **bad}, client_id="c")


def test_auth_disabled_is_refused_in_lambda(monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "silip-api")
    with pytest.raises(ConfigError):
        ApiSettings(auth_disabled=True)

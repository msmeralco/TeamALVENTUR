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


def test_token_in_the_silip_header_is_accepted(client):
    # Behind CloudFront the Authorization header carries CloudFront's SigV4 signature (OAC),
    # so the web sends the Cognito token in X-Silip-Authorization instead.
    sigv4 = "AWS4-HMAC-SHA256 Credential=x/20261112/ap-southeast-1/lambda/aws4_request"
    headers = {"X-Silip-Authorization": "Bearer engineer-token", "Authorization": sigv4}
    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["groups"] == ["engineers"]


def test_a_sigv4_authorization_header_alone_is_401(client):
    sigv4 = "AWS4-HMAC-SHA256 Credential=x/20261112/ap-southeast-1/lambda/aws4_request"
    assert client.get("/api/v1/me", headers={"Authorization": sigv4}).status_code == 401


def test_a_bad_token_in_the_silip_header_is_401(client):
    assert (
        client.get("/api/v1/me", headers={"X-Silip-Authorization": "Bearer forged"}).status_code
        == 401
    )

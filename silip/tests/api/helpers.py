"""Test helpers: a fake Cognito decoder and auth headers (no network)."""

from collections.abc import Mapping
from typing import Any

from silip.shared.auth.domain import AuthenticationError

CLIENT_ID = "test-client"
GROUPS = {"engineer-token": ["engineers"], "household-token": ["households"], "nogroup-token": []}


class FakeDecoder:
    """Maps a few fixed tokens to claims; anything else is invalid."""

    def decode(self, token: str) -> Mapping[str, Any]:
        if token not in GROUPS:
            raise AuthenticationError("unknown test token")
        return {
            "token_use": "access",
            "client_id": CLIENT_ID,
            "sub": f"sub-{token}",
            "username": token.removesuffix("-token"),
            "cognito:groups": GROUPS[token],
        }


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

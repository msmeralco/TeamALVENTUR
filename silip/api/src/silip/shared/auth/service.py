"""Authenticate a bearer token."""

from __future__ import annotations

from silip.shared.auth.domain import AuthUser, TokenDecoder, user_from_claims


def authenticate(decoder: TokenDecoder, token: str, client_id: str) -> AuthUser:
    """Verify `token` and apply the claim rules. Raises `AuthenticationError`."""
    return user_from_claims(decoder.decode(token), client_id)

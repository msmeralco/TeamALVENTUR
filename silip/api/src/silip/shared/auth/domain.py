"""The signed-in user and the claim rules a verified Cognito access token must meet.

Signature, issuer and expiry are checked by the `TokenDecoder` adapter; SILIP's own rules
(token use, app client, groups) live here only. Modelled on Lawata's auth.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

ENGINEERS_GROUP = "engineers"
HOUSEHOLDS_GROUP = "households"
ACCESS_TOKEN_USE = "access"  # noqa: S105  (a claim value, not a password)
CLOCK_LEEWAY_S = 60
SIGNING_ALGORITHMS = ("RS256",)


class AuthenticationError(Exception):
    """Missing, malformed or unverifiable token. The message is for logs; clients get a 401."""


@dataclass(frozen=True)
class CognitoPool:
    """A user pool and the app client whose access tokens the API accepts."""

    region: str
    user_pool_id: str
    client_id: str

    @property
    def issuer(self) -> str:
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"


@dataclass(frozen=True)
class AuthUser:
    """A signed-in person. `subject` is Cognito's stable `sub`; it links a household account."""

    subject: str
    username: str
    email: str | None
    groups: tuple[str, ...]

    @property
    def is_engineer(self) -> bool:
        return ENGINEERS_GROUP in self.groups

    @property
    def is_household(self) -> bool:
        return HOUSEHOLDS_GROUP in self.groups


# Every request's user when AUTH_DISABLED=true (local dev and tests only).
DEV_USER = AuthUser(
    subject="dev", username="dev", email=None, groups=(ENGINEERS_GROUP, HOUSEHOLDS_GROUP)
)


class TokenDecoder(Protocol):
    """Port: verify a JWT's signature, issuer and expiry and return its claims."""

    def decode(self, token: str) -> Mapping[str, Any]: ...


def _text_claim(claims: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = claims.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise AuthenticationError(f"token has no {names[0]}")


def user_from_claims(claims: Mapping[str, Any], client_id: str) -> AuthUser:
    """Apply SILIP's claim rules to verified claims and build the user.

    Raises:
        AuthenticationError: if `token_use` is not "access", the client differs, or a claim is malformed.
    """
    if claims.get("token_use") != ACCESS_TOKEN_USE:
        raise AuthenticationError("token_use is not 'access'")
    if claims.get("client_id") != client_id:
        raise AuthenticationError("client_id does not match")
    groups = claims.get("cognito:groups", [])
    if not isinstance(groups, list) or not all(isinstance(group, str) for group in groups):
        raise AuthenticationError("cognito:groups is not a list of strings")
    email = claims.get("email")
    return AuthUser(
        subject=_text_claim(claims, "sub"),
        username=_text_claim(claims, "cognito:username", "username"),
        email=email if isinstance(email, str) and email else None,
        groups=tuple(groups),
    )

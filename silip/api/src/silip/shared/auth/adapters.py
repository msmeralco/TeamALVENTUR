"""PyJWT token decoder with the pool's JWKS fetched once and cached."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import jwt

from silip.shared.auth.domain import (
    CLOCK_LEEWAY_S,
    SIGNING_ALGORITHMS,
    AuthenticationError,
    CognitoPool,
)

JWKS_CACHE_LIFESPAN_S = 3600
JWKS_TIMEOUT_S = 5


class CognitoTokenDecoder:
    """Verifies RS256 signature, `iss`, and `exp`/`nbf` (60 s leeway). One per process on Lambda."""

    def __init__(self, pool: CognitoPool) -> None:
        self._issuer = pool.issuer
        self._keys = jwt.PyJWKClient(
            pool.jwks_url,
            cache_jwk_set=True,
            lifespan=JWKS_CACHE_LIFESPAN_S,
            timeout=JWKS_TIMEOUT_S,
        )

    def decode(self, token: str) -> Mapping[str, Any]:
        try:
            key = self._keys.get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                key,
                algorithms=list(SIGNING_ALGORITHMS),
                issuer=self._issuer,
                leeway=CLOCK_LEEWAY_S,
                # Cognito access tokens have no `aud`; the app client is checked in the domain.
                options={"require": ["exp", "iss"], "verify_aud": False},
            )
        except jwt.PyJWTError as error:
            raise AuthenticationError(f"invalid token: {type(error).__name__}") from error

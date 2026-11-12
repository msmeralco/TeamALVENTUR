"""FastAPI auth dependencies and `GET /api/v1/me`.

- `require_engineer` / `require_household`: 401 `Sign in required` (+ `WWW-Authenticate: Bearer`)
  for a missing or invalid token; 403 for a valid token outside the group.
- With `AUTH_DISABLED=true` (refused in Lambda) every request is the dev user in both groups.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from silip.shared.auth import service
from silip.shared.auth.adapters import CognitoTokenDecoder
from silip.shared.auth.domain import (
    DEV_USER,
    AuthenticationError,
    AuthUser,
    CognitoPool,
    TokenDecoder,
)
from silip.shared.config import ApiSettings, ConfigError, Settings

logger = logging.getLogger(__name__)

SIGN_IN_REQUIRED = "Sign in required"
ENGINEER_REQUIRED = "Engineer access required"
HOUSEHOLD_REQUIRED = "Household access required"

CLIENT_AUTH_HEADER = "X-Silip-Authorization"

_bearer = HTTPBearer(auto_error=False, scheme_name="CognitoAccessToken")
# CloudFront signs /api/* requests to the Lambda function URL with SigV4 (origin access control), and that
# signature replaces the viewer's Authorization header. The web app therefore sends its Cognito token in
# X-Silip-Authorization, which CloudFront forwards untouched. Authorization: Bearer still works directly.
_token_header = APIKeyHeader(
    name=CLIENT_AUTH_HEADER, auto_error=False, scheme_name="CognitoAccessTokenHeader"
)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
TokenHeader = Annotated[str | None, Depends(_token_header)]


def bearer_token(header: TokenHeader, credentials: Credentials) -> str | None:
    """The Cognito access token from X-Silip-Authorization, else from Authorization: Bearer."""
    if header is not None:
        scheme, _, token = header.partition(" ")
        return token.strip() or None if scheme.lower() == "bearer" else None
    return None if credentials is None else credentials.credentials


BearerToken = Annotated[str | None, Depends(bearer_token)]


def cognito_pool(settings: ApiSettings) -> CognitoPool:
    if settings.cognito_user_pool_id is None or settings.cognito_client_id is None:
        raise ConfigError(
            "Set COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID (or AUTH_DISABLED=true locally)"
        )
    return CognitoPool(
        settings.cognito_region, settings.cognito_user_pool_id, settings.cognito_client_id
    )


@lru_cache(maxsize=4)
def _decoder_for(pool: CognitoPool) -> TokenDecoder:
    return CognitoTokenDecoder(pool)  # cached so the JWKS cache survives across requests


def token_decoder(settings: Settings) -> TokenDecoder | None:
    """Provide the decoder (overridden in tests). None when auth is disabled."""
    return None if settings.auth_disabled else _decoder_for(cognito_pool(settings))


Decoder = Annotated[TokenDecoder | None, Depends(token_decoder)]


def _sign_in_required() -> HTTPException:
    return HTTPException(
        status_code=401, detail=SIGN_IN_REQUIRED, headers={"WWW-Authenticate": "Bearer"}
    )


def require_user(token: BearerToken, settings: Settings, decoder: Decoder) -> AuthUser:
    """Any signed-in user, or 401."""
    if decoder is None:  # AUTH_DISABLED=true, local dev only
        return DEV_USER
    if token is None:
        raise _sign_in_required()
    try:
        return service.authenticate(decoder, token, cognito_pool(settings).client_id)
    except AuthenticationError as error:
        logger.info("rejected bearer token: %s", error)  # the reason, never the token
        raise _sign_in_required() from error


User = Annotated[AuthUser, Depends(require_user)]


def require_engineer(user: User) -> AuthUser:
    if not user.is_engineer:
        raise HTTPException(status_code=403, detail=ENGINEER_REQUIRED)
    return user


def require_household(user: User) -> AuthUser:
    if not user.is_household:
        raise HTTPException(status_code=403, detail=HOUSEHOLD_REQUIRED)
    return user


Engineer = Annotated[AuthUser, Depends(require_engineer)]
Household = Annotated[AuthUser, Depends(require_household)]

AUTH_RESPONSES: dict[int | str, dict[str, str]] = {
    401: {"description": SIGN_IN_REQUIRED},
    403: {"description": "Signed in, but not in the required group"},
}

router = APIRouter(prefix="/api/v1", tags=["auth"])


class MeOut(BaseModel):
    """The signed-in user."""

    username: str
    email: str | None
    groups: list[str]


@router.get("/me", response_model=MeOut, responses=AUTH_RESPONSES)
def me(user: User) -> MeOut:
    """Who is signed in."""
    return MeOut(username=user.username, email=user.email, groups=list(user.groups))

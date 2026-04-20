from functools import lru_cache

from fastapi import APIRouter, Header, status

from models.auth_schemas import (
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthSessionResponse,
    AuthSignInRequest,
    AuthSignOutRequest,
    AuthStatusResponse,
    AuthUserResponse,
)
from services.auth_store import AuthStoreService
from utils.config import get_settings
from utils.exceptions import SmartFitError

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()


@lru_cache
def _get_auth_store() -> AuthStoreService:
    return AuthStoreService(
        database_url=settings.database_url,
        access_token_secret=settings.auth_token_secret,
        access_token_minutes=settings.auth_access_token_minutes,
        refresh_token_days=settings.auth_refresh_token_days,
        max_failed_attempts=settings.auth_max_failed_attempts,
        lockout_minutes=settings.auth_lockout_minutes,
        attempt_window_minutes=settings.auth_attempt_window_minutes,
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise SmartFitError(
            message="Authentication required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_REQUIRED",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise SmartFitError(
            message="Invalid authorization header.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_AUTH_HEADER",
        )

    return token.strip()


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: AuthRegisterRequest) -> AuthSessionResponse:
    auth_store = _get_auth_store()
    user = auth_store.register_user(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
    )
    session = auth_store.create_session(user_id=user["id"])
    return AuthSessionResponse(**session)


@router.post("/signin", response_model=AuthSessionResponse)
def sign_in(payload: AuthSignInRequest) -> AuthSessionResponse:
    auth_store = _get_auth_store()
    user = auth_store.authenticate(email=payload.email, password=payload.password)
    session = auth_store.create_session(user_id=user["id"])
    return AuthSessionResponse(**session)


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh_session(payload: AuthRefreshRequest) -> AuthSessionResponse:
    auth_store = _get_auth_store()
    session = auth_store.refresh_session(refresh_token=payload.refresh_token)
    return AuthSessionResponse(**session)


@router.post("/signout", response_model=AuthStatusResponse)
def sign_out(payload: AuthSignOutRequest) -> AuthStatusResponse:
    auth_store = _get_auth_store()
    auth_store.revoke_session(refresh_token=payload.refresh_token)
    return AuthStatusResponse(status="signed_out", message="Session signed out.")


@router.get("/me", response_model=AuthUserResponse)
def get_me(authorization: str | None = Header(default=None)) -> AuthUserResponse:
    auth_store = _get_auth_store()
    access_token = _extract_bearer_token(authorization)
    user = auth_store.get_user_from_access_token(access_token)
    return AuthUserResponse(**user)

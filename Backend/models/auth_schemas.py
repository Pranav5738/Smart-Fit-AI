from __future__ import annotations

from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    height_cm: float | None = Field(default=None, gt=0, lt=280)
    weight_kg: float | None = Field(default=None, gt=0, lt=500)


class AuthSignInRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=512)


class AuthSignOutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=512)


class AuthUserResponse(BaseModel):
    id: str
    name: str
    email: str
    height_cm: float | None = None
    weight_kg: float | None = None
    created_at: str
    last_login_at: str | None = None


class AuthTokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: str
    refresh_expires_at: str


class AuthSessionResponse(BaseModel):
    user: AuthUserResponse
    tokens: AuthTokensResponse


class AuthStatusResponse(BaseModel):
    status: str
    message: str

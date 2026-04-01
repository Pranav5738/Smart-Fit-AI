from fastapi import APIRouter, status

from models.auth_schemas import AuthRegisterRequest, AuthSignInRequest, AuthUserResponse
from services.auth_store import AuthStoreService
from utils.config import get_settings

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()
auth_store = AuthStoreService(db_path=settings.data_store_path)


@router.post("/register", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: AuthRegisterRequest) -> AuthUserResponse:
    user = auth_store.register_user(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
    )
    return AuthUserResponse(**user)


@router.post("/signin", response_model=AuthUserResponse)
def sign_in(payload: AuthSignInRequest) -> AuthUserResponse:
    user = auth_store.authenticate(email=payload.email, password=payload.password)
    return AuthUserResponse(**user)

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import CurrentUserDependency
from app.core.config import settings
from app.dependencies.rate_limit import per_ip_rate_limit
from app.dependencies.services import UserServiceDependency
from app.schemas.jwt import LoginResponse, TokenRefreshResponse, TokenRefreshRequest
from app.schemas.user import (
    UserLoginRequest,
    UserRead,
    UserRegister,
    UserUpdate,
    VerificationResendRequest,
)

router = APIRouter()

MINUTE = 60
HOUR = 60 * MINUTE

# Email-sending endpoints fail closed when Redis is down; login fails open, so an
# outage does not lock every user out (Argon2 still makes each guess expensive).
register_rate_limit = per_ip_rate_limit("register", settings.RATE_LIMIT_REGISTER_PER_HOUR, HOUR)
login_rate_limit = per_ip_rate_limit(
    "login", settings.RATE_LIMIT_LOGIN_PER_MINUTE, MINUTE, fail_open=True
)
resend_rate_limit = per_ip_rate_limit("resend", settings.RATE_LIMIT_RESEND_PER_HOUR, HOUR)

VERIFICATION_RESEND_MESSAGE = (
    "If this address belongs to an unverified account, a new verification email is on its way."
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(register_rate_limit)],
)
async def create_user_endpoint(
    user: UserRegister,
    service: UserServiceDependency,
):
    return await service.create(user)


@router.post("/token", response_model=LoginResponse, dependencies=[Depends(login_rate_limit)])
async def login(
    user: UserLoginRequest,
    service: UserServiceDependency,
):
    return await service.login(user)


@router.post("/token/refresh", response_model=TokenRefreshResponse)
async def refresh_access_token(token_request: TokenRefreshRequest, service: UserServiceDependency):
    return await service.refresh_access_token(token_request.refresh_token)


@router.put("/me", response_model=UserRead)
async def update_user(
    user_update: UserUpdate, current_user: CurrentUserDependency, service: UserServiceDependency
):
    return await service.update_by_id(current_user.id, user_update)


@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: CurrentUserDependency, service: UserServiceDependency):
    return await service.get_by_id(current_user.id)


@router.get("/verification/{token}")
async def verify_user(token: str, service: UserServiceDependency):
    return await service.verify_user(token)


@router.post("/verification/resend", status_code=202, dependencies=[Depends(resend_rate_limit)])
async def resend_verification_email(
    request: VerificationResendRequest, service: UserServiceDependency
) -> dict[str, str]:
    await service.resend_verification(request.email)
    return {"detail": VERIFICATION_RESEND_MESSAGE}

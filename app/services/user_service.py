from fastapi import HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy.exc import IntegrityError

from app.core.auth.utils import create_access_token
from app.core.auth.utils import create_refresh_token
from app.core.auth.utils import verify_token
from app.core.cache import acquire_cooldown
from app.core.security import (
    dummy_verify_password,
    get_password_hash,
    password_needs_rehash,
    verify_password,
)
from app.db.unit_of_work import UnitOfWork
from app.pubsub.outbox import publish_now
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.user_repository import UserRepository
from app.schemas.jwt import LoginResponse, TokenRefreshResponse
from app.schemas.user import UserRegister, UserLoginRequest
from app.schemas.user import UserInDB
from app.schemas.user import UserUpdate
from app.core.security import verify_verification_token

VERIFICATION_RESEND_COOLDOWN_SECONDS = 60


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        outbox_repository: OutboxRepository,
        uow: UnitOfWork,
    ) -> None:
        self.repository = user_repository
        self.outbox = outbox_repository
        self.uow = uow

    async def create(self, user: UserRegister) -> UserInDB:
        try:
            created_user: UserInDB = await self.repository.create(
                username=user.username,
                hashed_password=get_password_hash(user.password),
                email=user.email,
                commit=False,
            )
        except IntegrityError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username or email already exists.",
            ) from e

        event = self.outbox.add("new-user-registration", {"id": created_user.id})
        self.uow.after_commit(publish_now, self.uow, self.outbox, [event])
        return created_user

    async def get_by_id(self, user_id: int) -> UserInDB:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )
        return user

    async def authenticate(self, user: UserLoginRequest) -> UserInDB:
        user_db = await self.repository.get_by_username(user.username)
        if user_db:
            password_ok = verify_password(user.password, user_db.hashed_password)
        else:
            dummy_verify_password()
            password_ok = False

        if not password_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
            )

        if password_needs_rehash(user_db.hashed_password):
            await self.repository.update_by_id(
                record_id=user_db.id, hashed_password=get_password_hash(user.password)
            )

        if not user_db.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user, verify you account",
            )

        return user_db

    async def login(self, user: UserLoginRequest) -> LoginResponse:
        user = await self.authenticate(user)

        access_token = create_access_token(
            data={"user_id": user.id},
        )
        refresh_token = create_refresh_token(
            data={"user_id": user.id},
        )

        return LoginResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> TokenRefreshResponse:
        try:
            payload = verify_token(refresh_token)
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        if payload["token_type"] != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await self.get_by_id(payload["user_id"])

        new_access_token = create_access_token(
            data={"user_id": user.id},
        )
        return TokenRefreshResponse(
            access_token=new_access_token,
        )

    async def update_by_id(self, user_id: int, user: UserUpdate) -> UserInDB:
        updated = await self.repository.update_by_id(
            record_id=user_id, **user.model_dump(exclude_unset=True)
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return await self.repository.get_by_id(user_id)

    async def verify_user(
        self,
        token: str,
    ):
        email = verify_verification_token(token=token)

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user = await self.repository.get_by_email(email)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User is already active"
            )

        await self.repository.update_by_id(record_id=user.id, is_active=True, commit=False)
        event = self.outbox.add("new-active-user", {"email": email})
        self.uow.after_commit(publish_now, self.uow, self.outbox, [event])

    async def resend_verification(self, email: str) -> None:
        """Queue a new verification email for an unverified user.

        Does nothing for unknown or already active addresses, so callers cannot
        tell them apart. The outbox relay publishes the event; publishing it
        inline would make the response slower only for existing accounts.
        """
        cooldown_key = f"verification-resend:{email.lower()}"
        if not await acquire_cooldown(cooldown_key, VERIFICATION_RESEND_COOLDOWN_SECONDS):
            return

        user = await self.repository.get_by_email(email)
        if not user or user.is_active:
            return

        self.outbox.add("new-user-registration", {"id": user.id})

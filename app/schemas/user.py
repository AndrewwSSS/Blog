from typing import ClassVar

from pydantic import BaseModel, EmailStr, Field, model_validator
from pydantic import ConfigDict


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class UserLoginRequest(BaseModel):
    username: str
    password: str


class VerificationResendRequest(BaseModel):
    email: EmailStr


class UserRead(BaseModel):
    id: int
    post_auto_reply: bool
    reply_after: float
    username: str
    email: EmailStr

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class UserUpdate(BaseModel):
    post_auto_reply: bool | None = None
    reply_after: float | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if self.post_auto_reply is None and self.reply_after is None:
            raise ValueError("At least one of 'post_auto_reply' or 'reply_after' must be set.")
        return self


class UserInDB(BaseModel):
    id: int
    username: str
    email: EmailStr
    post_auto_reply: bool
    reply_after: float
    hashed_password: str
    welcome_email_sent: bool
    is_active: bool
    is_admin: bool

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )

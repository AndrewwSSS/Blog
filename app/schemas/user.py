from typing import ClassVar

from pydantic import BaseModel, EmailStr, model_validator
from pydantic import ConfigDict
from pydantic import field_validator


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
    reply_after: float | None = None

    @field_validator("reply_after")
    def check_reply_after(cls, value) -> float:
        if value and value < 1:
            raise ValueError("reply_after must be greater than 1")
        return value

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if not any([self.post_auto_reply, self.reply_after]):
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

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserRead(UserCreate):
    id: int
    post_auto_reply: bool
    reply_after: float

    class Config:
        orm_mode = True


class UserUpdate(UserCreate):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    post_auto_reply: bool | None = None
    reply_after: float | None = None

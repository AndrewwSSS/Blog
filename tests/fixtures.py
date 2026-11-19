import uuid

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import make_sessionmaker
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentCreate, CommentInDB
from app.schemas.post import Post, PostInDB
from app.schemas.user import UserInDB

engine_test = create_async_engine(
    settings.test_database_url,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine_test.sync_engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session_maker = make_sessionmaker(engine_test)


async def create_comment(
    owner_id: int,
    post_id: int,
    content: str = "",
) -> CommentInDB:
    async with async_session_maker() as session:
        repository = CommentRepository(session)
        comment = CommentCreate(content=f"{content}-{uuid.uuid4()}", post_id=post_id)
        created_comment = await repository.create(**comment.model_dump(), owner_id=owner_id)
    return created_comment


async def create_post(owner_id: int, content: str = "", title: str = "") -> PostInDB:
    async with async_session_maker() as session:
        repository = PostRepository(session)
        post = Post(content=f"{content}-{uuid.uuid4()}", title=f"{title}-{uuid.uuid4()}")
        created_post = await repository.create(**post.model_dump(), owner_id=owner_id)
    return created_post


async def create_user(username: str = "", email: str = "", password: str = "") -> UserInDB:
    async with async_session_maker() as session:
        repository = UserRepository(session)

        created_user = await repository.create(
            username=f"{username}{uuid.uuid4()}",
            hashed_password=f"{password}{uuid.uuid4()}",
            email=f"{email}{uuid.uuid4()}@gmail.com",
        )
    return created_user

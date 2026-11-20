import uuid

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import make_engine, make_sessionmaker
from app.db.unit_of_work import UnitOfWork
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentCreate, CommentInDB
from app.schemas.post import Post, PostInDB
from app.schemas.user import UserInDB

TEST_DATABASE_URL = make_url(settings.TEST_DATABASE_URL)
IS_SQLITE = TEST_DATABASE_URL.get_backend_name() == "sqlite"

if not IS_SQLITE and not (TEST_DATABASE_URL.database or "").endswith("_test"):
    raise RuntimeError(
        f"Refusing to run tests on database {TEST_DATABASE_URL.database!r}: "
        "tests drop all tables, so its name must end with '_test'."
    )

engine_test = make_engine(
    settings.TEST_DATABASE_URL,
    poolclass=NullPool,
    **({"connect_args": {"check_same_thread": False}} if IS_SQLITE else {}),
)

if IS_SQLITE:

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
    async with UnitOfWork(async_session_maker) as uow:
        repository = CommentRepository(uow.session)
        comment = CommentCreate(content=f"{content}-{uuid.uuid4()}", post_id=post_id)
        created_comment = await repository.create(**comment.model_dump(), owner_id=owner_id)
    return created_comment


async def create_post(owner_id: int, content: str = "", title: str = "") -> PostInDB:
    async with UnitOfWork(async_session_maker) as uow:
        repository = PostRepository(uow.session)
        post = Post(content=f"{content}-{uuid.uuid4()}", title=f"{title}-{uuid.uuid4()}")
        created_post = await repository.create(**post.model_dump(), owner_id=owner_id)
    return created_post


async def create_user(username: str = "", email: str = "", password: str = "") -> UserInDB:
    async with UnitOfWork(async_session_maker) as uow:
        repository = UserRepository(uow.session)

        created_user = await repository.create(
            username=f"{username}{uuid.uuid4()}",
            hashed_password=f"{password}{uuid.uuid4()}",
            email=f"{email}{uuid.uuid4()}@gmail.com",
        )
    return created_user

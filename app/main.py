from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from app.api.v1.endpoints import user, posts, comments
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
from app.core.async_elasticsearch_client import AsyncElasticsearchClient


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("aiosqlite").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(fast_api: FastAPI):
    await AsyncKafkaProducer.init()
    await AsyncElasticsearchClient.init()
    await AsyncElasticsearchClient.warm_index("posts")
    yield
    await AsyncElasticsearchClient.close()
    await AsyncKafkaProducer.stop()

app = FastAPI(lifespan=lifespan)

app.include_router(user.router, prefix="/api/v1/users", tags=["user"])
app.include_router(posts.router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(comments.router, prefix="/api/v1/comments", tags=["comments"])

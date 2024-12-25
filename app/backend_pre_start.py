import asyncio
import json
import logging

from sqlalchemy import select
from tenacity import (
    after_log,
    before_log,
    retry,
    stop_after_attempt,
    wait_fixed
)
from elasticsearch.exceptions import ConnectionError

from app.db.session import async_session
from app.core.async_elasticsearch_client import AsyncElasticsearchClient
from app.pubsub.async_kafka_producer import AsyncKafkaProducer


logger = logging.getLogger(__name__)

max_tries = 60 * 5
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
async def wait_for_db() -> None:
    logger.info("Waiting for database")
    try:
        async with async_session() as session:
            await session.execute(select(1))
        logger.info("Database is ready")
    except Exception as e:
        logger.error(e)
        raise e


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(4),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
async def wait_for_elasticsearch() -> AsyncElasticsearchClient:
    logger.info("Waiting for elasticsearch")
    try:
        repository = AsyncElasticsearchClient()
        if await repository.is_ready():
            logger.info("Elasticsearch is ready")
            return repository
        else:
            raise ConnectionError("Elasticsearch is not responding")
    except ConnectionError as e:
        logger.info(e)
        raise e


async def create_indexes(repository: AsyncElasticsearchClient) -> None:
    logger.info("Read mappings for posts index")

    with open("elasticsearch/posts-mappings.json", "r") as f:
        index_body = json.load(f)
        logger.info(f"Mappings loaded: {index_body}")

    if await repository.create_index(
        index_name="posts",
        body=index_body
    ):
        logger.info(f"Index 'posts' created.")
    else:
        logger.info(f"Index 'posts' already exists.")


async def create_search_templates(repository: AsyncElasticsearchClient) -> None:
    logger.info("Creating search templates")

    with open("elasticsearch/full-text-search.mustache", "r") as f:
        search_template_body = f.read()

    template_id = "full-text-search"

    if await repository.get_script(template_id):
        response = await repository.create_or_update_script(
            script_id=template_id,
            body=search_template_body
        )
        logger.info(f"Search template updated successfully. "
                    f"Response: {response}")
        return

    response = await repository.create_or_update_script(
        script_id=template_id,
        body=search_template_body
    )
    logger.info(f"Search template '{template_id}' created. "
                f"Response: {response}")


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(4),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
async def wait_for_kafka() -> None:
    try:
        await AsyncKafkaProducer.init()
        logger.info("Kafka is ready")
        await AsyncKafkaProducer.stop()
    except Exception as e:
        logger.info("Kafka is not ready")
        raise e


async def main() -> None:
    await asyncio.gather(wait_for_db(), wait_for_kafka())
    repo = await wait_for_elasticsearch()
    await create_indexes(repo)
    await create_search_templates(repo)
    await AsyncElasticsearchClient.close()

if __name__ == "__main__":
    asyncio.run(main())

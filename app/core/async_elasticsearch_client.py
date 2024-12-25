import logging

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import (
    NotFoundError,
    ConnectionError,
    RequestError,
)

from app.core.config import settings


logger = logging.getLogger(__name__)


class AsyncElasticsearchClient:
    _client = None
    _warm_query = {
        "query": {
            "match_all": {}
        }
    }

    def __init__(self):
        if not AsyncElasticsearchClient._client:
            AsyncElasticsearchClient._client = AsyncElasticsearch(
                settings.ELASTICSEARCH_URL
            )
        self._client = AsyncElasticsearchClient._client

    async def create_index(self, index_name: str, body: dict) -> bool:
        if not await self._client.indices.exists(index=index_name):
            await self._client.indices.create(index=index_name, body=body)
            return True
        return False

    async def delete_index(self, index_name: str) -> bool:
        raise NotImplemented

    async def search(self, index_name: str, query: dict) -> dict:
        return await self._client.search(index=index_name, query=query)

    async def search_by_template(
        self,
        index_name: str,
        search_template_id: str,
        params: dict,
    ) -> dict:
        try:
            return await self._client.search_template(
                index=index_name,
                body={
                    "id": search_template_id,
                    "params": params
                }
            )
        except (NotFoundError, ConnectionError, RequestError) as e:
            logger.error(
                f"Error while searching by search template: {search_template_id}, "
                f"params: {params}. "
                f"index_name: {index_name}"
                f"{e}"
            )

    async def create_document(
        self,
        index_name: str,
        document_id: str | int,
        document: dict
    ) -> None:
        await self._client.index(
            index=index_name,
            id=document_id,
            document=document
        )

    async def update_document(
        self,
        index_name: str,
        document_id: int,
        updated_document: dict
    ):
        await self._client.update(
            index=index_name,
            id=document_id,
            body=updated_document
        )
        await self._client.indices.refresh(index=index_name)

    async def delete_document(self, index_name: str, document_id: int):
        await self._client.delete(index=index_name, id=document_id)

    async def is_ready(self) -> bool:
        return await self._client.ping()

    async def get_script(self, script_id: str | int) -> None | object:
        try:
            return await self._client.get_script(
                id=script_id
            )
        except NotFoundError:
            ...

    async def create_or_update_script(self, script_id: str | int, body: str) -> object:
        return await self._client.put_script(
            id=script_id,
            body={
                "script": {
                    "lang": "mustache",
                    "source": body
                }
            }
        )

    @classmethod
    async def warm_index(cls, index_name: str) -> dict:
        """
        Perform a warm-up query on the specified index.
        """
        try:
            response = await cls._client.search(
                index=index_name,
                body=cls._warm_query
            )
            logger.info(f"Warm query performed on index '{index_name}': {response}")
            return response
        except Exception as e:
            logger.error(f"Error during warm-up query on index '{index_name}': {e}")
            raise

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            await cls._client.close()
            cls._client = None

    @classmethod
    async def init(cls) -> None:
        if cls._client:
            logger.warning("Elasticsearch client already initialized")
            return
        cls._client = AsyncElasticsearch(
            settings.ELASTICSEARCH_URL
        )

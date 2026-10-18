from datetime import datetime, timezone
import logging
import asyncio

from app.modules.data_collection.schemas import CollectionResult
from app.integrations.data_sources import BaseDataSource, registered_data_sources

class UnknownDataSourceError(Exception):
    pass


class CollectionService:
    adapter = {}  # name: DataSource Mapping of source name to DataSource instance

    def __init__(self, sources: list[str]):
        self.sources = sources
        for source in sources:
            if source not in registered_data_sources:
                logging.warning("Unknown data source configured: %s", source)
            else:
                logging.info("Data source configured: %s", source)

                self.adapter[source] = registered_data_sources[source]()
                
    async def collect(self) -> CollectionResult:
        for _, data_source in self.adapter.items():
            if not isinstance(data_source, BaseDataSource):
                raise UnknownDataSourceError(data_source)
            else:                
                data = await data_source.fetch()
                print(data)

        # adapter = self.sources.get(source)
        # if adapter is None:
            
        # records = await adapter.fetch()
        # return CollectionResult(
        #     source=source,
        #     fetched_at=datetime.now(timezone.utc),
        #     record_count=len(records),
        #     records=records,
        # )


def create_collection_service() -> CollectionService:
    """Build the shared collection service from environment settings."""
    from app.core.config import settings

    logging.info("Creating collection service with sources: %s", settings.data_collection_sources_list)
    return CollectionService(settings.data_collection_sources_list)

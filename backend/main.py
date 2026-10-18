import asyncio
import sys
import logging
from app.core.config import settings
from app.modules.data_collection.service import UnknownDataSourceError, create_collection_service

logger = logging.getLogger(__name__)
if settings.debug_mode:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(filename='myapp.log', level=logging.INFO)


def main() -> int:
    from app.integrations.data_sources import DataSourceError

    try:
        result = asyncio.run(create_collection_service().collect())
    except UnknownDataSourceError:
        return 1
    except DataSourceError as exc:
        print(f"抓取失败：{exc}", file=sys.stderr)
        return 1

    # print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

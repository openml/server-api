from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from schemas.datasets.openml import Quality


async def get_for_dataset(dataset_id: int, connection: AsyncConnection) -> list[Quality]:
    rows = await connection.execute(
        text(
            """
        SELECT `quality`,`value`
        FROM data_quality
        WHERE `data`=:dataset_id
        """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return [Quality(name=row.quality, value=row.value) for row in rows]


async def get_for_datasets(
    dataset_ids: Iterable[int],
    quality_names: Iterable[str],
    connection: AsyncConnection,
) -> dict[int, list[Quality]]:
    """Don't call with user-provided input, as query is not parameterized."""
    qualities_filter = ",".join(f"'{q}'" for q in quality_names)
    dids = ",".join(str(did) for did in dataset_ids)
    qualities_query = text(
        f"""
        SELECT `data`, `quality`, `value`
        FROM data_quality
        WHERE `data` in ({dids}) AND `quality` IN ({qualities_filter})
        """,  # noqa: S608 - dids and qualities are not user-provided
    )
    rows = await connection.execute(qualities_query)
    qualities_by_id = defaultdict(list)
    for did, quality, value in rows:
        if value is not None:
            qualities_by_id[did].append(Quality(name=quality, value=value))
    return dict(qualities_by_id)


async def list_all_qualities(connection: AsyncConnection) -> list[str]:
    # The current implementation only fetches *used* qualities, otherwise you should
    # query: SELECT `name` FROM `quality` WHERE `type`='DataQuality'
    qualities_ = await connection.execute(
        text(
            """
        SELECT DISTINCT(`quality`)
        FROM data_quality
        """,
        ),
    )
    return [quality.quality for quality in qualities_]

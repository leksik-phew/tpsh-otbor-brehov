import asyncpg


class DB:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def start(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def fetch_value(self, sql: str) -> int:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql)
            if row is None or "value" not in row:
                raise ValueError("SQL не вернул колонку value")
            val = row["value"]
            if val is None:
                return 0
            # asyncpg может вернуть Decimal/str в редких случаях — приводим аккуратно
            try:
                return int(val)
            except Exception:
                # если вдруг float
                return int(float(val))
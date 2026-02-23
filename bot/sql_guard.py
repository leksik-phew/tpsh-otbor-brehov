import re

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate)\b", re.I)
ONLY_SELECT = re.compile(r"^\s*select\b", re.I)
HAS_SEMICOLON = re.compile(r";")
BAD_TABLES = re.compile(r"\b(from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", re.I)

ALLOWED_TABLES = {"videos", "video_snapshots"}


def validate_sql(sql: str) -> None:
    s = sql.strip()

    if HAS_SEMICOLON.search(s):
        raise ValueError("Запрещены ';' и множественные запросы")
    if not ONLY_SELECT.search(s):
        raise ValueError("Разрешён только SELECT")
    if FORBIDDEN.search(s):
        raise ValueError("Запрещены изменяющие операции")

    for m in BAD_TABLES.finditer(s):
        table = m.group(2).lower()
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Запрещённая таблица: {table}")

    if re.search(r"\bas\s+value\b", s, re.I) is None:
        raise ValueError("Нужно вернуть одно число с алиасом AS value")
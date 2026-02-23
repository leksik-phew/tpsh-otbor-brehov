import asyncio
import json
import os
from datetime import datetime
from typing import Any

import asyncpg


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


VIDEO_UPSERT = """
INSERT INTO videos(
    id, creator_id, video_created_at,
    views_count, likes_count, comments_count, reports_count,
    created_at, updated_at
)
VALUES (
    $1::uuid, $2::text, $3::timestamptz,
    $4::bigint, $5::bigint, $6::bigint, $7::bigint,
    $8::timestamptz, $9::timestamptz
)
ON CONFLICT (id) DO UPDATE SET
    creator_id = EXCLUDED.creator_id,
    video_created_at = EXCLUDED.video_created_at,
    views_count = EXCLUDED.views_count,
    likes_count = EXCLUDED.likes_count,
    comments_count = EXCLUDED.comments_count,
    reports_count = EXCLUDED.reports_count,
    created_at = EXCLUDED.created_at,
    updated_at = EXCLUDED.updated_at;
"""

SNAPSHOT_UPSERT = """
INSERT INTO video_snapshots(
    id, video_id,
    views_count, likes_count, comments_count, reports_count,
    delta_views_count, delta_likes_count, delta_comments_count, delta_reports_count,
    created_at, updated_at
)
VALUES (
    $1::uuid, $2::uuid,
    $3::bigint, $4::bigint, $5::bigint, $6::bigint,
    $7::bigint, $8::bigint, $9::bigint, $10::bigint,
    $11::timestamptz, $12::timestamptz
)
ON CONFLICT (id) DO UPDATE SET
    video_id = EXCLUDED.video_id,
    views_count = EXCLUDED.views_count,
    likes_count = EXCLUDED.likes_count,
    comments_count = EXCLUDED.comments_count,
    reports_count = EXCLUDED.reports_count,
    delta_views_count = EXCLUDED.delta_views_count,
    delta_likes_count = EXCLUDED.delta_likes_count,
    delta_comments_count = EXCLUDED.delta_comments_count,
    delta_reports_count = EXCLUDED.delta_reports_count,
    created_at = EXCLUDED.created_at,
    updated_at = EXCLUDED.updated_at;
"""


async def main():
    dsn = os.environ["DATABASE_URL"] 
    path = os.environ.get("JSON_PATH", "data/videos.json")

    with open(path, "r", encoding="utf-8") as f:
        payload: dict[str, Any] = json.load(f)

    videos = payload.get("videos", [])
    if not isinstance(videos, list):
        raise ValueError("JSON: поле videos должно быть массивом")

    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            for v in videos:
                await conn.execute(
                    VIDEO_UPSERT,
                    v["id"],
                    v["creator_id"],
                    _parse_dt(v["video_created_at"]),
                    int(v["views_count"]),
                    int(v["likes_count"]),
                    int(v["comments_count"]),
                    int(v["reports_count"]),
                    _parse_dt(v["created_at"]),
                    _parse_dt(v["updated_at"]),
                )

                for s in v.get("snapshots", []):
                    await conn.execute(
                        SNAPSHOT_UPSERT,
                        s["id"],
                        s["video_id"],
                        int(s["views_count"]),
                        int(s["likes_count"]),
                        int(s["comments_count"]),
                        int(s["reports_count"]),
                        int(s["delta_views_count"]),
                        int(s["delta_likes_count"]),
                        int(s["delta_comments_count"]),
                        int(s["delta_reports_count"]),
                        _parse_dt(s["created_at"]),
                        _parse_dt(s["updated_at"]),
                    )
    finally:
        await conn.close()

    print(f"Loaded videos={len(videos)}")


if __name__ == "__main__":
    asyncio.run(main())
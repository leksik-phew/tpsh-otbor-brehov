CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS videos (
    id              uuid PRIMARY KEY,
    creator_id      text NOT NULL,
    video_created_at timestamptz NOT NULL,

    views_count     bigint NOT NULL,
    likes_count     bigint NOT NULL,
    comments_count  bigint NOT NULL,
    reports_count   bigint NOT NULL,

    created_at      timestamptz NOT NULL,
    updated_at      timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS video_snapshots (
    id                  uuid PRIMARY KEY,
    video_id            uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,

    views_count          bigint NOT NULL,
    likes_count          bigint NOT NULL,
    comments_count       bigint NOT NULL,
    reports_count        bigint NOT NULL,

    delta_views_count    bigint NOT NULL,
    delta_likes_count    bigint NOT NULL,
    delta_comments_count bigint NOT NULL,
    delta_reports_count  bigint NOT NULL,

    created_at          timestamptz NOT NULL,
    updated_at          timestamptz NOT NULL
);

-- Индексы под типичные запросы:
CREATE INDEX IF NOT EXISTS idx_videos_creator_id ON videos(creator_id);
CREATE INDEX IF NOT EXISTS idx_videos_video_created_at ON videos(video_created_at);

CREATE INDEX IF NOT EXISTS idx_snapshots_video_id_created_at ON video_snapshots(video_id, created_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON video_snapshots(created_at);

-- Часто спрашивают "за день прирост суммарно":
CREATE INDEX IF NOT EXISTS idx_snapshots_day ON video_snapshots ((date_trunc('day', created_at)));
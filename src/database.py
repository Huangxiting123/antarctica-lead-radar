from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


def app_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or Path.home())
        path = root / "OmniMediaIntelligenceRadar"
        legacy = root / "AntarcticaLeadRadar" / "lead_radar.db"
    else:
        path = Path.home() / ".omnimedia_intelligence_radar"
        legacy = Path.home() / ".antarctica_lead_radar" / "lead_radar.db"
    path.mkdir(parents=True, exist_ok=True)
    current = path / "lead_radar.db"
    if not current.exists() and legacy.exists():
        shutil.copy2(legacy, current)
    return path


def default_database_path() -> Path:
    return app_data_dir() / "lead_radar.db"


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    user_name TEXT NOT NULL DEFAULT '',
                    user_id TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    comment_time TEXT NOT NULL DEFAULT '',
                    video_id TEXT NOT NULL DEFAULT '',
                    video_title TEXT NOT NULL DEFAULT '',
                    video_url TEXT NOT NULL DEFAULT '',
                    platform_comment_id TEXT NOT NULL,
                    intent_label TEXT NOT NULL DEFAULT '未分析',
                    intent_level TEXT NOT NULL DEFAULT '未分析',
                    intent_score INTEGER NOT NULL DEFAULT 0,
                    reason TEXT NOT NULL DEFAULT '',
                    suggested_reply TEXT NOT NULL DEFAULT '',
                    final_reply TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '待审核',
                    collected_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(platform, platform_comment_id)
                );

                CREATE INDEX IF NOT EXISTS idx_comments_intent
                ON comments(intent_level, intent_score DESC);

                CREATE INDEX IF NOT EXISTS idx_comments_time
                ON comments(comment_time DESC);

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    @staticmethod
    def _comment_id(item: dict[str, Any]) -> str:
        supplied = str(item.get("platform_comment_id") or item.get("comment_id") or "").strip()
        if supplied:
            return supplied
        raw = "|".join(
            [
                str(item.get("platform", "")),
                str(item.get("user_id", "")),
                str(item.get("content", "")),
                str(item.get("comment_time", "")),
                str(item.get("video_url", "")),
            ]
        )
        return "local-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def upsert_comment(self, item: dict[str, Any]) -> tuple[int, bool]:
        now = self._now()
        comment_id = self._comment_id(item)
        values = {
            "platform": str(item.get("platform") or "手工导入"),
            "user_name": str(item.get("user_name") or ""),
            "user_id": str(item.get("user_id") or ""),
            "content": str(item.get("content") or "").strip(),
            "comment_time": str(item.get("comment_time") or ""),
            "video_id": str(item.get("video_id") or ""),
            "video_title": str(item.get("video_title") or ""),
            "video_url": str(item.get("video_url") or ""),
            "platform_comment_id": comment_id,
            "intent_label": str(item.get("intent_label") or "未分析"),
            "intent_level": str(item.get("intent_level") or "未分析"),
            "intent_score": int(item.get("intent_score") or 0),
            "reason": str(item.get("reason") or ""),
            "suggested_reply": str(item.get("suggested_reply") or ""),
            "collected_at": str(item.get("collected_at") or now),
            "updated_at": now,
        }
        if not values["content"]:
            raise ValueError("评论内容不能为空")
        with self.connect() as db:
            existing = db.execute(
                "SELECT id FROM comments WHERE platform=? AND platform_comment_id=?",
                (values["platform"], comment_id),
            ).fetchone()
            if existing:
                db.execute(
                    """
                    UPDATE comments SET user_name=:user_name, user_id=:user_id, content=:content,
                    comment_time=:comment_time, video_id=:video_id, video_title=:video_title,
                    video_url=:video_url, updated_at=:updated_at
                    WHERE id=:id
                    """,
                    {**values, "id": existing["id"]},
                )
                return int(existing["id"]), False
            cursor = db.execute(
                """
                INSERT INTO comments (
                    platform,user_name,user_id,content,comment_time,video_id,video_title,
                    video_url,platform_comment_id,intent_label,intent_level,intent_score,
                    reason,suggested_reply,collected_at,updated_at
                ) VALUES (
                    :platform,:user_name,:user_id,:content,:comment_time,:video_id,:video_title,
                    :video_url,:platform_comment_id,:intent_label,:intent_level,:intent_score,
                    :reason,:suggested_reply,:collected_at,:updated_at
                )
                """,
                values,
            )
            return int(cursor.lastrowid), True

    def bulk_upsert(self, items: Iterable[dict[str, Any]]) -> tuple[int, int, list[int]]:
        inserted = 0
        updated = 0
        ids: list[int] = []
        for item in items:
            row_id, created = self.upsert_comment(item)
            ids.append(row_id)
            inserted += int(created)
            updated += int(not created)
        self.log("批量导入", f"新增{inserted}条，更新{updated}条")
        return inserted, updated, ids

    def apply_classification(self, row_id: int, result: Any) -> None:
        with self.connect() as db:
            db.execute(
                """
                UPDATE comments SET intent_label=?, intent_level=?, intent_score=?, reason=?,
                suggested_reply=?, updated_at=? WHERE id=?
                """,
                (
                    result.label,
                    result.level,
                    int(result.score),
                    result.reason,
                    result.suggested_reply,
                    self._now(),
                    row_id,
                ),
            )

    def get(self, row_id: int) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM comments WHERE id=?", (row_id,)).fetchone()
        return dict(row) if row else None

    def list_comments(
        self,
        level: str = "全部",
        platform: str = "全部",
        status: str = "全部",
        query: str = "",
        limit: int = 3000,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if level != "全部":
            clauses.append("intent_level=?")
            params.append(level)
        if platform != "全部":
            clauses.append("platform=?")
            params.append(platform)
        if status != "全部":
            clauses.append("status=?")
            params.append(status)
        if query.strip():
            clauses.append("(user_name LIKE ? OR user_id LIKE ? OR content LIKE ? OR video_title LIKE ?)")
            token = f"%{query.strip()}%"
            params.extend([token, token, token, token])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT * FROM comments{where} ORDER BY intent_score DESC, comment_time DESC, id DESC LIMIT ?"
        params.append(limit)
        with self.connect() as db:
            rows = db.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def platforms(self) -> list[str]:
        with self.connect() as db:
            rows = db.execute("SELECT DISTINCT platform FROM comments ORDER BY platform").fetchall()
        return [str(row[0]) for row in rows]

    def dashboard_counts(self) -> dict[str, int]:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT COUNT(*) total,
                SUM(CASE WHEN intent_level='A级' THEN 1 ELSE 0 END) a_count,
                SUM(CASE WHEN intent_level='B级' THEN 1 ELSE 0 END) b_count,
                SUM(CASE WHEN status='待审核' THEN 1 ELSE 0 END) pending,
                SUM(CASE WHEN status='已回复' THEN 1 ELSE 0 END) replied
                FROM comments
                """
            ).fetchone()
        return {key: int(row[key] or 0) for key in row.keys()}

    def set_status(self, row_id: int, status: str, final_reply: str | None = None) -> None:
        with self.connect() as db:
            if final_reply is None:
                db.execute("UPDATE comments SET status=?,updated_at=? WHERE id=?", (status, self._now(), row_id))
            else:
                db.execute(
                    "UPDATE comments SET status=?,final_reply=?,updated_at=? WHERE id=?",
                    (status, final_reply, self._now(), row_id),
                )
        self.log("更新状态", f"评论#{row_id} → {status}")

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return str(row[0]) if row else default

    def log(self, action: str, detail: str = "") -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO activity_log(action,detail,created_at) VALUES(?,?,?)",
                (action, detail, self._now()),
            )

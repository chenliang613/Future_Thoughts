"""推送状态：记录已推过的文章 uid 和时间，避免重复。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)


class SentState:
    """文件存储的去重表。{uid: ISO 时间戳}。"""

    def __init__(self, path: Path, retention_days: int = 30) -> None:
        self.path = path
        self.retention_days = retention_days
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            log.info("state file %s not found, starting fresh", self.path)
            return
        try:
            self._data = json.loads(self.path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("failed to load state, starting fresh: %s", e)
            self._data = {}

    def contains(self, uid: str) -> bool:
        return uid in self._data

    def mark(self, uid: str) -> None:
        self._data[uid] = datetime.now(timezone.utc).isoformat()

    def prune(self) -> int:
        """删除超过 retention_days 的记录,返回删除条数。"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        before = len(self._data)
        self._data = {
            uid: ts for uid, ts in self._data.items()
            if datetime.fromisoformat(ts) > cutoff
        }
        return before - len(self._data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), "utf-8")
        log.info("saved state: %d entries", len(self._data))

"""PushPlus 微信推送客户端。"""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

PUSHPLUS_URL = "https://www.pushplus.plus/send"

# PushPlus 单条 content 限制约 64KB,远超我们的用量,无需分片
MAX_CONTENT_CHARS = 60_000


def push(token: str, title: str, content: str, template: str = "markdown") -> bool:
    """发到 PushPlus。返回 True 表示成功。"""
    if not token:
        log.error("missing PUSHPLUS_TOKEN")
        return False

    if len(content) > MAX_CONTENT_CHARS:
        log.warning("content too long (%d chars), truncating", len(content))
        content = content[:MAX_CONTENT_CHARS] + "\n\n...(内容过长已截断)"

    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": template,
    }

    try:
        resp = httpx.post(PUSHPLUS_URL, json=payload, timeout=30.0)
        resp.raise_for_status()
        result = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        log.error("pushplus request failed: %s", e)
        return False

    if result.get("code") != 200:
        log.error("pushplus returned error: %s", result)
        return False

    log.info("pushplus sent: %s", result.get("msg"))
    return True

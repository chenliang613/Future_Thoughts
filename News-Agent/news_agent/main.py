"""News Agent 编排入口：拉源 -> 去重 -> Claude 打分 -> top N 摘要 -> PushPlus -> 保存状态。

用法:
    python -m news_agent.main           # 正常运行
    python -m news_agent.main --dry-run # 不实际推送,只打印输出
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
import yaml

from . import filter as filter_mod
from . import push as push_mod
from . import sources
from .state import SentState

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS_PATH = ROOT / "keywords.md"
CONFIG_PATH = ROOT / "config.yaml"
STATE_PATH = ROOT / "state" / "sent.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("news_agent")


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text("utf-8"))


def render_push_content(items: list[filter_mod.ScoredArticle]) -> str:
    """生成 markdown 推送正文。"""
    lines: list[str] = []
    lines.append(f"# 共 {len(items)} 条")
    lines.append("")
    for i, item in enumerate(items, 1):
        a = item.article
        lines.append(f"## {i}. {a.title}")
        lines.append("")
        lines.append(f"**来源**: {a.source}  |  **相关度**: {item.score:.1f}/10")
        if item.summary:
            lines.append("")
            lines.append(item.summary)
        elif a.summary:
            lines.append("")
            lines.append(a.summary[:200] + ("…" if len(a.summary) > 200 else ""))
        lines.append("")
        lines.append(f"[阅读原文]({a.url})")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def run(dry_run: bool = False) -> int:
    config = load_config()
    keywords_md = KEYWORDS_PATH.read_text("utf-8")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        log.error("ANTHROPIC_API_KEY not set")
        return 1
    pushplus_token = os.environ.get("PUSHPLUS_TOKEN")
    if not pushplus_token and not dry_run:
        log.error("PUSHPLUS_TOKEN not set (use --dry-run to skip push)")
        return 1

    client = anthropic.Anthropic(api_key=anthropic_key)
    state = SentState(STATE_PATH, retention_days=config["state"]["retention_days"])
    pruned = state.prune()
    if pruned:
        log.info("pruned %d expired state entries", pruned)

    # 1. 采集
    log.info("=== 1. fetching sources ===")
    raw: list[sources.Article] = []
    raw.extend(sources.fetch_rss_sources(config["rss_feeds"]))
    raw.extend(sources.fetch_google_news(config["google_news_queries"]))
    raw.extend(sources.fetch_rsshub(
        config["rsshub"]["instance"],
        config["rsshub"].get("routes", []),
    ))
    log.info("fetched %d raw articles", len(raw))

    # 2. 去重(源内 + 跨源 + 历史)
    deduped = sources.dedupe(raw)
    fresh = [a for a in deduped if not state.contains(a.uid)]
    log.info("after dedup: %d unique, %d new (vs sent history)", len(deduped), len(fresh))

    if not fresh:
        log.info("no new articles; exiting")
        return 0

    # 3. Claude 打分
    log.info("=== 2. scoring with %s ===", config["claude"]["scorer_model"])
    scored = filter_mod.score_articles(
        client=client,
        articles=fresh,
        keywords_md=keywords_md,
        model=config["claude"]["scorer_model"],
        batch_size=config["claude"]["scorer_batch_size"],
    )

    # 4. 按阈值过滤 + top N
    min_score = float(config["push"]["min_score"])
    max_n = int(config["push"]["max_articles"])
    qualified = [s for s in scored if s.score >= min_score]
    qualified.sort(key=lambda s: s.score, reverse=True)
    top = qualified[:max_n]
    log.info("scored: %d total, %d >= %.1f, top %d selected", len(scored), len(qualified), min_score, len(top))

    if not top:
        log.info("nothing meets threshold; exiting without push")
        # 仍然把"已看过"的 uid 标记上,避免下次重打分浪费 token
        for s in scored:
            state.mark(s.article.uid)
        if not dry_run:
            state.save()
        return 0

    # 5. Sonnet 写摘要
    log.info("=== 3. summarizing top %d with %s ===", len(top), config["claude"]["summarizer_model"])
    top = filter_mod.summarize_top(
        client=client,
        scored=top,
        keywords_md=keywords_md,
        model=config["claude"]["summarizer_model"],
    )

    # 6. 推送
    title = config["push"]["title_template"].format(date=datetime.now().strftime("%Y-%m-%d"))
    content = render_push_content(top)

    if dry_run:
        log.info("=== DRY RUN: would push ===")
        print(f"\nTITLE: {title}\n")
        print(content)
    else:
        log.info("=== 4. pushing to PushPlus ===")
        ok = push_mod.push(pushplus_token, title, content)
        if not ok:
            log.error("push failed; not marking state so we can retry next run")
            return 2

    # 7. 标记所有"打过分的"为已处理(不止 top,避免下次反复打同样低分)
    for s in scored:
        state.mark(s.article.uid)
    if not dry_run:
        state.save()
    log.info("done")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="News Agent runner")
    parser.add_argument("--dry-run", action="store_true", help="不实际推送,只打印结果")
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

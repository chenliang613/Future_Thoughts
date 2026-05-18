"""Claude API 过滤层：用 keywords.md 做相关性打分,top N 写中文摘要。

设计要点：
- keywords.md 走 prompt caching(ephemeral),整个 run 内反复读但只付一次缓存写费用
- Haiku 批量打分(每批 N 条),Sonnet 单条精修摘要,平衡成本和质量
- prompt 把候选文章作为 JSON 数组放在最后(变化部分),keywords.md 在前(稳定部分)
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import anthropic

from .sources import Article

log = logging.getLogger(__name__)


@dataclass
class ScoredArticle:
    article: Article
    score: float           # 0-10 相关性
    reason: str            # 简要打分理由
    summary: str = ""      # Sonnet 生成的中文摘要(只有 top N 有)


# ---------- Prompt 模板 ----------

SCORER_SYSTEM = """你是一个新闻相关性评分助手。你将收到一份用户的关注主题说明(keywords.md),然后是一批待评分的新闻。

请按主题说明中描述的关注角度和过滤规则,给每条新闻打 0-10 分相关性:
- 0-3: 完全无关或属于过滤规则要排除的内容
- 4-5: 沾边但价值不高(如标题党、轻量八卦、纯产品发布)
- 6-7: 相关且有信息量(如行业落地案例、有数据支撑的产业分析)
- 8-10: 高度相关、信息密度高、对用户的核心研究目标(行业智能化方法论)有直接价值

严格按用户的过滤规则执行——属于排除项的一律给 0-3 分。

返回 JSON 数组,每条对应一篇新闻,顺序与输入一致。每条格式:
{"id": <输入序号>, "score": <0-10 数字,可带一位小数>, "reason": "<不超过30字的中文打分理由>"}

只返回 JSON,不要 markdown 包装,不要任何其他文字。"""

SCORER_USER_TEMPLATE = """以下是用户的关注主题说明:

<keywords>
{keywords}
</keywords>

以下是待评分的 {n} 条新闻(JSON 数组):

{articles_json}

请输出 JSON 数组评分结果。"""


SUMMARIZER_SYSTEM = """你是一个中文新闻摘要助手。你将收到一份用户关注主题说明,然后是若干已经被判定为高相关的新闻。

请为每条新闻写一段 80-150 字的中文摘要,要求:
- 突出与用户关注主题最相关的信息点(具体公司、数据、案例、决策)
- 不要堆砌形容词,不要复述标题
- 如果原文是英文,直接译写要点;不要保留英文术语除非是专有名词

返回 JSON 数组,每条格式:
{"id": <输入序号>, "summary": "<中文摘要>"}

只返回 JSON,不要 markdown 包装。"""

SUMMARIZER_USER_TEMPLATE = """用户关注主题:

<keywords>
{keywords}
</keywords>

待摘要的 {n} 条新闻:

{articles_json}

请输出 JSON 摘要结果。"""


# ---------- 辅助 ----------

def _article_to_dict(idx: int, a: Article) -> dict:
    return {
        "id": idx,
        "title": a.title,
        "source": a.source,
        "url": a.url,
        "preview": a.summary[:400] if a.summary else "",
    }


def _extract_json_array(text: str) -> list:
    """Claude 偶尔会包 markdown 代码块,这里兜底剥一层。"""
    text = text.strip()
    if text.startswith("```"):
        # 去掉 ```json ... ``` 或 ``` ... ```
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ---------- 公共接口 ----------

def score_articles(
    client: anthropic.Anthropic,
    articles: list[Article],
    keywords_md: str,
    model: str,
    batch_size: int = 20,
) -> list[ScoredArticle]:
    """批量打分。keywords.md 用 prompt caching,跨批次复用。"""
    if not articles:
        return []

    scored: list[ScoredArticle] = []

    for batch_start in range(0, len(articles), batch_size):
        batch = articles[batch_start : batch_start + batch_size]
        articles_json = json.dumps(
            [_article_to_dict(i, a) for i, a in enumerate(batch)],
            ensure_ascii=False,
            indent=2,
        )

        # 关键:keywords 放在 system 里并打 cache_control,
        # 这样跨批次的多次调用能复用缓存(prefix 不变)
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                system=[
                    {
                        "type": "text",
                        "text": SCORER_SYSTEM,
                    },
                    {
                        "type": "text",
                        "text": f"以下是用户的关注主题说明,后续每批新闻都按它打分:\n\n<keywords>\n{keywords_md}\n</keywords>",
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
                messages=[
                    {
                        "role": "user",
                        "content": f"以下是本批 {len(batch)} 条新闻(JSON 数组):\n\n{articles_json}\n\n请输出 JSON 数组评分结果。",
                    }
                ],
            )
        except anthropic.APIError as e:
            log.error("scorer API error on batch starting %d: %s", batch_start, e)
            # 失败的批次直接给中性分,保证流程继续
            for a in batch:
                scored.append(ScoredArticle(article=a, score=5.0, reason="评分失败"))
            continue

        # 记录缓存命中(诊断用)
        usage = response.usage
        log.info(
            "scorer batch %d: cache_read=%d cache_create=%d input=%d output=%d",
            batch_start // batch_size,
            getattr(usage, "cache_read_input_tokens", 0),
            getattr(usage, "cache_creation_input_tokens", 0),
            usage.input_tokens,
            usage.output_tokens,
        )

        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            result = _extract_json_array(text)
        except (json.JSONDecodeError, ValueError) as e:
            log.error("scorer returned non-JSON, raw=%r, err=%s", text[:200], e)
            for a in batch:
                scored.append(ScoredArticle(article=a, score=5.0, reason="解析失败"))
            continue

        # 按 id 对回原文
        by_id = {item.get("id"): item for item in result if isinstance(item, dict)}
        for idx, a in enumerate(batch):
            item = by_id.get(idx, {})
            try:
                score = float(item.get("score", 5.0))
            except (TypeError, ValueError):
                score = 5.0
            scored.append(ScoredArticle(
                article=a,
                score=max(0.0, min(10.0, score)),
                reason=str(item.get("reason", ""))[:50],
            ))

    return scored


def summarize_top(
    client: anthropic.Anthropic,
    scored: list[ScoredArticle],
    keywords_md: str,
    model: str,
) -> list[ScoredArticle]:
    """给已经按分数选出的 top N 写中文摘要。in-place 填 .summary 并返回。"""
    if not scored:
        return scored

    articles_json = json.dumps(
        [_article_to_dict(i, s.article) for i, s in enumerate(scored)],
        ensure_ascii=False,
        indent=2,
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            system=[
                {"type": "text", "text": SUMMARIZER_SYSTEM},
                {
                    "type": "text",
                    "text": f"用户关注主题:\n\n<keywords>\n{keywords_md}\n</keywords>",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"待摘要的 {len(scored)} 条新闻:\n\n{articles_json}\n\n请输出 JSON 摘要结果。",
                }
            ],
        )
    except anthropic.APIError as e:
        log.error("summarizer API error: %s", e)
        return scored

    usage = response.usage
    log.info(
        "summarizer: cache_read=%d cache_create=%d input=%d output=%d",
        getattr(usage, "cache_read_input_tokens", 0),
        getattr(usage, "cache_creation_input_tokens", 0),
        usage.input_tokens,
        usage.output_tokens,
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        result = _extract_json_array(text)
    except (json.JSONDecodeError, ValueError) as e:
        log.error("summarizer returned non-JSON, raw=%r, err=%s", text[:200], e)
        return scored

    by_id = {item.get("id"): item.get("summary", "") for item in result if isinstance(item, dict)}
    for idx, s in enumerate(scored):
        s.summary = str(by_id.get(idx, ""))[:400]
    return scored

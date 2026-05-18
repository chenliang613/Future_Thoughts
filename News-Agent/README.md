# News Agent

个人新闻 Agent：按 `keywords.md` 里描述的主题，每天从 RSS / Google News / RSSHub 拉新闻，
用 Claude 做相关性打分和中文摘要，通过 PushPlus 推送到微信。

## 架构

```
sources.py  → 拉 RSS / Google News / RSSHub,统一成 Article
state.py    → 用 state/sent.json 去重已推过的 URL hash
filter.py   → Haiku 批量打分(keywords.md 走 prompt caching) → Sonnet 写 top N 摘要
push.py     → PushPlus markdown 推送
main.py     → 编排 + 命令行入口
```

## 本地试跑（建议先在本地通一遍再部署）

```bash
# 1. 装依赖
pip install -r requirements.txt

# 2. 配两个环境变量(密钥)
export ANTHROPIC_API_KEY=sk-ant-...
export PUSHPLUS_TOKEN=...  # https://www.pushplus.plus 扫码登录后拿

# 3. 干跑(不实际推送,只打印 markdown 到控制台)
python -m news_agent.main --dry-run

# 4. 正式跑一次(会真的推到你的微信)
python -m news_agent.main
```

## 部署到 GitHub Actions（每天自动跑）

1. 把仓库推到 GitHub（public 或 private 都行，Actions 都免费够用）
2. 在 GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret，加两个：
   - `ANTHROPIC_API_KEY`
   - `PUSHPLUS_TOKEN`
3. 默认每天 UTC 00:00（北京时间 08:00）跑一次，触发延迟 5-15 分钟正常
4. 想改时间编辑 `.github/workflows/daily.yml` 里的 `cron`
5. 手动触发：仓库 → Actions → Daily News Push → Run workflow

跑完 workflow 会自动 commit `state/sent.json` 回仓库，保证下次跑能去重。

## 配置文件

### `keywords.md`
关注主题描述。Claude 读这份做打分。**这是你最常编辑的文件**。
建议写得详细一点，多举例子，越具体打分越准。

### `config.yaml`
- `push.max_articles` / `push.min_score`：每天最多推几条 / 相关度阈值
- `claude.scorer_model` / `summarizer_model`：换模型在这里改
- `google_news_queries`：Google News 搜索关键词
- `rss_feeds`：直接订阅的 RSS 源（新增源加这里）
- `rsshub.routes`：X 推主、微信公众号通过 RSSHub 包装的路由

### `state/sent.json`
自动维护的去重表，不用手动编辑。30 天前的记录会自动清理。

## 调优建议

- **第一周觉得推得太少 / 太多** → 调 `min_score`（5.5 宽松，7.0 严格）
- **推的内容偏题** → 编辑 `keywords.md` 把"过滤规则"写得更清楚
- **token 成本想压低** → 把 `summarizer_model` 也改成 `claude-haiku-4-5`
- **要加 X / 微信公众号** → 在 `rsshub.routes` 加路由，查 [RSSHub 文档](https://docs.rsshub.app)

## 加新 RSS 源

直接在 `config.yaml` 的 `rss_feeds` 加一项：

```yaml
rss_feeds:
  - name: "你的源名称"
    url: "https://example.com/feed"
```

## 注意

- Google News RSS 没有官方 API，遇到风控可能短暂返回空。脚本会自动跳过失败源。
- RSSHub 公共实例 `rsshub.app` 不稳定。如果重度用 X / 公众号，建议自部署。
- PushPlus 免费版每天 200 条配额，正常使用够。

# 一文读懂 Harness：AI Agent 时代的"操作系统"

> 撰写时间：2026-05-19
> 资料来源：Anthropic 工程博客两篇官方文章 + 业界（Mitchell Hashimoto、Martin Fowler、Milvus、Augment Code 等）对 Harness 的系统化理解

---

## 一、为什么必须先理解 Harness

2026 年是 AI Agent 大规模进入生产的一年。但一个令业界普遍困惑的现象出现了：**相同的底层模型（Claude、GPT、Gemini），不同团队做出来的 Agent 产品，效果可能差 10 倍。**

差异不在模型，差在 **Harness（脚手架 / 承载层）**。

Mitchell Hashimoto（HashiCorp 联合创始人、Terraform 作者）2026 年 2 月正式将这一领域命名为 **"Harness Engineering（脚手架工程）"**，并提出一句已经被广泛引用的名言：

> **"If you're not the model, you're the harness."**
> （如果你不是做模型的，那你就是在做 Harness。）

这意味着：**对绝大多数 AI 应用公司、AI 行业落地团队而言，竞争力 = Harness 工程能力。**

这对"行业智能化的倒金字塔产业结构"（硬件 1× → 模型 10× → 行业应用 100×）有直接含义——**让行业应用拿到那 100× 价值的工程学，就是 Harness 工程学。**

---

## 二、Harness 到底是什么：一个直观的类比

业界目前最被广泛接受的类比框架：

| 计算机体系 | AI Agent 体系 |
|---|---|
| **CPU（处理器）** | **LLM（大模型）** |
| **RAM（内存）** | **Context Window（上下文窗口）** |
| **磁盘 / 文件系统** | **Memory / Files / Git** |
| **操作系统（OS）** | **Harness（脚手架层）** |
| **应用程序** | **Agent 产品** |

也就是说：

- 模型只是"CPU"——它本身不知道现在几点、不知道上次做过什么、不知道下一步该用什么工具；
- Harness 才是"操作系统"——它负责调度、内存管理（上下文）、I/O（工具调用）、进程恢复（会话续接）、权限控制（安全）、错误处理（重试/回滚）。

**没有 OS 的 CPU 只是一块硅片，没有 Harness 的 LLM 也只是一次性的对话机器。**

---

## 三、Harness 解决的三个根本难题

Anthropic 两篇工程文章把"为什么 Agent 跑长任务会失败"归纳得非常清晰，可总结为三大难题：

### 难题 1：上下文会膨胀，模型会"焦虑"

Anthropic 在 Sonnet 4.5 上首次观察到 **"上下文焦虑（context anxiety）"** 现象：
- 当上下文窗口被填到接近模型认知中的上限时，**模型会主动提前结束任务**——不是因为做完了，而是因为它"感觉快没空间了"，于是抄近路。
- 这种行为在 Opus 4.6 后被消除，但**结构性问题没消失**：任何长任务都会遇到上下文饱和。

**Harness 的破解方法不是"压缩"，而是"重置"**：
- **错误做法**：把历史对话总结成短摘要塞回上下文（信息密度高但失去结构）。
- **正确做法**：清空上下文，让 Agent 通过**结构化交接物（git commit、progress.txt、feature list）**重新进入工作状态。

### 难题 2：Agent 不会客观评价自己

Anthropic 的明确发现：
> "当被要求评估自己的工作时，Agent 倾向于自信地赞美——即使人类观察者认为质量平庸。"

**Harness 的破解方法：分离 Generator 和 Evaluator**
- 不要让"做事的 Agent"自己打分，要派**独立的评估 Agent** 来打分。
- 这是受 GAN（生成对抗网络）启发的 Harness 模式，已被 Anthropic 用于前端设计循环（Generator-Evaluator Loop）。

### 难题 3：会话是离散的，Agent 没有跨会话记忆

> "agents must work in discrete sessions, and each new session begins with no memory of what came before."

每开一个新会话，Agent 都是"失忆"的。**Harness 必须为 Agent 提供"外置记忆"**：
- `init.sh`：怎么启动这个项目；
- `claude-progress.txt`：上次做到哪了；
- `feature-list.json`：200+ 条 JSON 格式的待办（**用 JSON 而非 Markdown，因为模型不太敢改 JSON**）；
- Git 提交历史：可回滚、可追溯的工作轨迹。

---

## 四、Harness 的核心组件清单

综合 Anthropic 两篇文章 + 业界共识，一个生产级 Harness 至少包含 7 个模块：

### 1. **上下文管理器（Context Manager）**
- 决定什么进入上下文、什么被裁剪、何时重置；
- 关键模式：**重置 > 压缩**。

### 2. **任务分解器（Planner / Task Decomposer）**
- 把模糊的人类指令（"做一个 DAW 应用"）转化为详细规范（**spec，不指定实现细节**）；
- Anthropic V1 架构里的"规划器"专门做这件事。

### 3. **执行器（Generator / Coder）**
- 真正干活的 Agent，按 "Sprint" 或 "Feature" 增量推进；
- 一次只做一件事（incremental progress）。

### 4. **评估器（Evaluator / QA Agent）**
- **独立**于执行器；
- 用浏览器自动化（Playwright/Puppeteer）做端到端测试；
- 截图验证、像人类用户一样点击。

### 5. **工具层（Tools / MCP）**
- 2026 年的标准是 **MCP（Model Context Protocol）**；
- 每个工具都需要详细 Metadata：是什么、何时用、参数是什么；
- 工具的边界 = Agent 能力的边界。

### 6. **持久化层（Memory / Filesystem / Git）**
- 文件系统是 Agent 最可靠的"长期记忆"；
- Git 是 Agent 最可靠的"撤销键"——允许 Agent 自己 `git revert` 回滚。

### 7. **可观测性与护栏（Observability + Guardrails）**
- 每一次工具调用、每一次上下文压缩、每一次安全否决都必须**可观测、可覆盖**；
- 业界共识："**transparency over magic**"。

---

## 五、Anthropic 的两个标杆案例

### 案例 A：前端设计循环（Generator-Evaluator）

| 角色 | 职责 |
|---|---|
| Generator | 生成前端代码 |
| Evaluator | 通过 Playwright 实时打开页面，按 4 个维度打分：设计质量、原创性、工艺、功能性 |

**单次运行 5–15 次迭代**，在荷兰美术馆项目第 10 次迭代时，Agent 出现了"创意飞跃"——从传统排版突然跳跃到 CSS 3D 空间体验。

**这是 Harness 工程最迷人的部分：好的 Harness 能让模型"涌现"出超出单次调用的创造力。**

### 案例 B：全栈编码三代理系统

**V1（Opus 4.5 时代）**：Planner + Generator + Evaluator，外加 "Sprint Contract" 机制——执行器和评估器在写代码之前必须先协商"什么算完成"。

**V2（Opus 4.6 时代）**：删除 Sprint 结构（因为模型变强了），只保留 Planner + Evaluator。

**关键教训**：
> "**每一个 Harness 组件都编码了一个关于模型能力的假设，这些假设值得被压力测试。**"

也就是说：**模型升级后，部分 Harness 是要被删掉的**。Harness 不是越复杂越好，是"刚好够用"最好。

### 性能对比

| 任务 | Solo Agent | V1 Harness | V2 Harness |
|---|---|---|---|
| 视频游戏制作器 | 20分钟 / $9 / 不可玩 | 6小时 / $200 / 可玩有缺陷 | — |
| DAW 应用 | — | — | 3.9小时 / $125 / 功能完整 |

**结论**：Harness 把"不可用"变成"可用"，但成本提升 10–20 倍。**这是 AI 工程师必须做的取舍判断**。

---

## 六、九条经过验证的 Harness 设计原则

综合两篇文章 + Hashimoto、Fowler、Augment Code 等业界实践：

1. **"每次 Agent 犯错，把修复编码进环境，让这个错误结构上不可能再发生。"**（Hashimoto 原则）
2. **关注点分离**：上下文管理、工具调度、安全护栏、模型选择，必须可独立替换。
3. **重置优于压缩**：清空上下文 + 结构化交接，比塞摘要更可靠。
4. **生成器与评估器必须分离**：自我评价不可信。
5. **一次只做一件事**：Incremental progress 是长任务的唯一可靠路径。
6. **JSON 优于 Markdown 作为状态文件**：模型不太敢误改 JSON。
7. **测试要像人类用户**：截图 + 端到端，而非单元测试。
8. **优雅降级**：上下文耗尽、工具失败、网络中断时，系统不能崩溃，要能续接。
9. **模型升级后必须重审 Harness**：删掉不再需要的部分。Harness 不是越厚越好。

---

## 七、Harness 的失败模式与对策表

| 常见失败 | Initializer Agent 对策 | Coding Agent 对策 |
|---|---|---|
| 过早宣布完成 | 建立功能清单（feature list） | 每次只选单一功能 |
| 留下未文档化的 bug | 写 `init.sh` + `progress.txt` | 读进度 → 测试 → 编码 → 提交 |
| 标记完成但没真正完成 | 功能清单强制要求测试通过 | 仅在测试通过后才能标记 |
| 不知道怎么运行应用 | 写好 `init.sh` 启动脚本 | 会话开始时第一件事就是跑 `init.sh` |
| 上下文焦虑 | 准备结构化交接物 | 会话短、目标单一、即时落盘 |

---

## 八、Harness 工程对"行业智能化"项目的直接启示

回到本项目的核心命题——**让行业应用拿到 AI 产业 100× 价值**——Harness 工程提供了非常具体的方法论：

### 启示 1：行业智能化项目的胜负手不在模型，在 Harness
- 同一个 Claude / GPT，在金融、医疗、制造业落地效果差 10 倍，差距几乎全部来自 Harness 工程；
- 行业 Know-how 必须**编码进 Harness**（工具、评估器、feature list、init 脚本），而不是塞进 prompt。

### 启示 2：行业落地的优先场景判定
**优先在 Harness 容易标准化的场景落地：**
- 有明确"完成"定义（如代码、文档、设计稿、报表）；
- 有自动化验证手段（如测试、规则、可观测指标）；
- 任务可分解为增量小步；
- 失败成本低（可回滚、可重做）。

按这个标准，**软件开发、金融研报、医疗影像审阅、合规审查、客服等场景天然适配 Harness 工程**——这也解释了为什么这些领域率先出现成功案例。

### 启示 3：行业智能化项目的核心方法论可凝练为
> **"用 Harness 把行业 Know-how 编码成 Agent 工作环境的物理约束，让模型在这个约束里跑出 100× 价值。"**

具体路径：
1. **第一阶段**：识别行业核心工作流的"完成定义"和"验证手段"（这是评估器设计的基础）；
2. **第二阶段**：把领域工具 MCP 化（CRM、ERP、PACS、Bloomberg 终端等都将被 MCP 包装）；
3. **第三阶段**：构建领域专用 Harness（含 Planner / Generator / Evaluator / Memory 全套组件）；
4. **第四阶段**：建立"模型升级 → Harness 简化"的持续迭代机制。

---

## 九、未来 12–24 个月需要持续关注的方向

1. **多 Agent vs 单 Agent 之争还没结论**：Anthropic 明确表示"it's still unclear whether a single, general-purpose coding agent performs best"；
2. **MCP 生态的成熟度**：MCP 已成事实标准，行业垂直 MCP（金融、医疗、制造）将成为下一波壁垒；
3. **Harness 即产品**：Cursor / Windsurf / Claude Code / Devin 等本质上都在卖 Harness，行业版 Harness 必然出现；
4. **可观测性标准化**：Agent OS 的 "Linux moment" 还没到，谁先做出标准谁吃肉。

---

## 十、一句话总结

> **"模型决定 Agent 的上限，Harness 决定 Agent 的下限——而 99% 的生产落地，吃的是下限。"**

对行业智能化项目而言，这句话可以更直接：

> **行业智能化的 100× 价值释放，不是等下一代模型，而是把今天的模型用 Harness 工程"包"成可靠的行业 Agent。**

---

## 附：核心参考资料

1. Anthropic Engineering：[Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)
2. Anthropic Engineering：[Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
3. Mitchell Hashimoto, 2026.02：Harness Engineering 概念正式提出
4. Martin Fowler：[Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)
5. Milvus Blog：[What Is Harness Engineering for AI Agents?](https://milvus.io/blog/harness-engineering-ai-agents.md)
6. Augment Code：[Harness Engineering for AI Coding Agents](https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents)

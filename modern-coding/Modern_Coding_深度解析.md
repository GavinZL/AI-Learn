# Modern Coding 深度解析

> **核心结论**：AI 时代的软件开发范式已经完成三轮演进——从 Prompt Engineering (2023) 到 Context Engineering (2025)，再到 Harness Engineering (2026)。Spec-Driven Development 与 Harness Engineering 的结合，构成了让 AI Agent 可靠工作的完整方法论体系。

## 概念起源与演进

### 三代演进

```
2023: Prompt Engineering（说什么）
  ↓  局限：单条指令无法驾驭复杂 Agent 任务
2025: Context Engineering（知道什么）
  ↓  缺陷：光有好的上下文，Agent 依然会失控
2026: Harness Engineering（在什么环境里做事）
       突破：通过系统设计预防重复错误
```

### 关键时间线

| 时间 | 事件 | 意义 |
|------|------|------|
| 2023年 | Prompt Engineering 兴起 | 关注"说什么"——如何向 AI 提问 |
| 2025年初 | Context Engineering 出现 | 关注"知道什么"——如何提供上下文 |
| 2025年2月 | Mitchell Hashimoto 首次命名 Harness Engineering | 概念诞生 |
| 2025年2月 | OpenAI 发布 Harness Engineering 实验报告 | 首个大规模验证案例 |
| 2025年9月 | GitHub 开源 Spec Kit | 规约驱动开发工具链成熟 |
| 2026年 | Harness Engineering 成为 AI 工程核心范式 | 从概念走向广泛实践 |

### 认知跃迁

| 阶段 | 关注点 | 局限性 | 代表实践 |
|------|--------|--------|---------|
| Prompt Engineering | 指令优化 | 单轮交互，无状态记忆 | Few-shot, CoT |
| Context Engineering | 上下文构建 | 性能在 25.6 万 Token 处衰减 | RAG, 长上下文窗口 |
| Harness Engineering | 系统约束 | 需要前期投入，学习曲线陡峭 | OpenAI Codex, Stripe Minions |

---

## 一、Why：为什么需要 Modern Coding 方法论

### 1.1 传统工程体系的失效

当 AI 进入软件开发流程时，原有的工程假设开始崩塌：

| 传统假设 | AI 时代现实 | 后果 |
|----------|-------------|------|
| 开发者理解上下文 | AI 无隐性知识 | 生成代码偏离设计意图 |
| 代码速度可控 | AI 可在分钟内生成千行代码 | 团队控制复杂度的能力被压倒 |
| 人类可通过评审发现问题 | AI 生成速度远超评审速度 | 架构决策被绕过，系统腐化 |
| 工具是为人类设计 | AI 需要机器接口 | 隐含约定导致 AI 失控 |

**真实案例**：Shopify CEO 报告的无人监控 Agent 造成 5 万美元 API 账单事故——上下文足够，但无边界约束。

### 1.2 实证数据

**OpenAI Codex 实验** (2025):

| 指标 | 数据 |
|------|------|
| 团队规模 | 3人起步，后扩至7人 |
| 时间周期 | 5个月 |
| 代码产出 | ~100万行 |
| 合并PR | ~1,500个 |
| 人均日均PR | 3.5个 |
| 手写代码 | **0行** |
| 效率提升 | **约10倍** |

**Stripe Minions 体系**:

| 指标 | 数据 |
|------|------|
| 周均合并 PR | 1,300+ |
| 人工代码 | 0行 |
| 审核模式 | 人类最终审核 |

**LangChain Harness 优化**:

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Terminal Bench 排名 | 第30名 | 第5名 |
| 得分 | 52.8% | 66.5% |
| 提升 | - | **+13.7%** |

### 1.3 核心价值主张

1. **范式转变**：工程师从"写代码"转变为"设计环境让 Agent 写代码"
2. **效率爆发**：OpenAI 证明 10 倍效率提升是可复现的
3. **质量保障**：通过 Harness 约束而非人工审查来保证代码质量
4. **可复用性**：Harness 一旦建成，可支持无数次 Agent 执行

---

## 二、What：Modern Coding 方法论体系

### 2.1 双轮驱动架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Modern Coding 方法论                              │
├────────────────────────────┬────────────────────────────────────────┤
│    Spec-Driven Development │        Harness Engineering             │
│    （规约驱动开发）          │        （马具工程）                      │
├────────────────────────────┼────────────────────────────────────────┤
│  定义"做什么"和"为什么"      │  保障"可靠地做"                         │
│  ─────────────────────     │  ───────────────────────               │
│  • 需求定义 (Define)        │  • 上下文工程                           │
│  • 规范设计 (Design)        │  • 架构约束                             │
│  • 任务分解 (Decompose)     │  • 反馈回路                             │
│  • 编码实现 (Develop)       │  • 垃圾回收                             │
│  • 验证部署 (Deliver)       │  • 可观测性                             │
└────────────────────────────┴────────────────────────────────────────┘
```

### 2.2 Spec-Driven Development 核心

#### Four Pillars（四大支柱）

| 支柱 | 含义 | 关键实践 |
|------|------|---------|
| **Traceability** | 每个代码变更可追溯到需求 | @require 标签、需求 ID 系统 |
| **DRY** | 每个事实只有一个权威来源 | OpenAPI → 自动生成类型/SDK |
| **Deterministic** | 能自动化的必须自动化 | CI/CD、Linter、自动化测试 |
| **Parsimony** | 最小表示保留完整语义 | 简洁规范、必要注释 |

#### 五阶段工作流

```
Phase 1        Phase 2        Phase 3        Phase 4        Phase 5
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ Define │───►│ Design │───►│Decompos│───►│Develop │───►│Deliver │
│ 需求定义│    │ 规范设计│    │ 任务分解│    │ 编码实现│    │ 验证部署│
└────────┘    └────────┘    └────────┘    └────────┘    └────────┘
    │             │             │             │             │
    ▼             ▼             ▼             ▼             ▼
  GWT 模板      ADR 决策      任务图        Harness        CI/CD
  需求 ID       OpenAPI       依赖排序       代码追溯       监控告警
  约束清单      领域模型       责任分配       自动验证       回滚机制
```

### 2.3 Harness Engineering 三维框架

```
     反馈回路（Feedback Loops）
          ↑
          │
系统可读性 ←→ 防御机制 ←→ 自动化反馈
```

#### 维度一：上下文工程（Context Engineering）

**核心思想**：渐进式文档披露，模仿人类工程师学习路径

```
AGENTS.md（入口，约100行）
├── ARCHITECTURE.md
├── DESIGN.md  
├── docs/
│   ├── design-docs/
│   ├── exec-plans/
│   ├── product-specs/
│   ├── FRONTEND.md
│   └── SECURITY.md
```

**反面教训**：巨大的单一文档会导致：
- 挤占任务和代码的上下文空间
- Agent 局部模式匹配，而非有意识导航
- 文档快速腐烂

#### 维度二：架构约束（Architectural Constraints）

**分层架构规则**：
```
Types → Config → Repo → Service → Runtime → UI
        只能向上依赖，严禁跨层
```

**关键实践**：
- 自定义 Linter + 结构化测试
- 违规代码拦截率 **100%**
- 预推送钩子 5 秒内反馈

#### 维度三：垃圾回收与熵管理（Garbage Collection）

**核心理念**：对抗系统衰退，保持 Harness 可读性

| 传统 GC | Harness GC |
|---------|-----------|
| 清理不再使用的内存 | 清理不再使用的文档、过时规则 |
| 防止内存泄漏 | 防止文档腐化 |
| 自动化 | Agent 驱动的自动化重构 |

---

## 三、How：如何实施

### 3.1 实施路线图

| 阶段 | 时间 | 目标 | 关键产出 |
|------|------|------|---------|
| **双轨执行** | 0-2周 | 建立对 Agent 能力认知 | 问题模式库 |
| **习惯养成** | 2-4周 | 逐步建立信心 | Agent 擅长任务清单 |
| **关键跃迁** | 4-8周 | 建立项目级规范 | AGENTS.md、Git Hooks |
| **反馈完善** | 2-3月 | 形成自愈循环 | 可观测性接入 |
| **架构强化** | 3-5月 | 机械化品味编码 | 100% 违规拦截 |
| **垃圾回收** | 5-6月+ | 长期可维护 | GC Agent、质量评分 |

### 3.2 四大原则

| 原则 | 错误做法 | 正确做法 |
|------|---------|---------|
| **从微观到宏观** | 逐行审查代码 | 设计架构、规则、边界，让 Agent 在框架内自由发挥 |
| **从一次性到闭环** | prompt 一次期望完美 | 建立反馈循环，持续校准 |
| **从依赖模型到依赖系统** | 期待 AI 完美解决 | 用系统约束 Agent |
| **用代码沟通** | 依赖自然语言 prompt | 代码、规则、测试——最精确无歧义 |

### 3.3 关键指标

| 指标类别 | 具体指标 | 目标值 | OpenAI 实际 |
|----------|----------|--------|-------------|
| 吞吐量 | 人均日 PR 数 | 2+ | 3.5 |
| 质量 | 架构违规拦截率 | 100% | 100% |
| 效率 | 代码评审自动化率 | >90% | >95% |
| 维护 | 可观测性覆盖率 | >80% | 完全覆盖 |

---

## 行业实践案例

### OpenAI Codex：Agent-First 的标杆

**核心洞察**："Agents aren't hard; the Harness is hard."

**关键实践**：
1. 仓库是 Agent 唯一的真相来源
2. 代码必须 Agent 可读（非仅人类可读）
3. 架构约束由 Linter 而非 Prompt 强制
4. 自主权渐进授予，分阶段有门槛
5. PR 需要人工干预 = Harness 有问题

### Stripe Minions：规模化典范

**周均 1,300 PR，零人工代码**

**核心机制**：
- Blueprint 编排：确定性节点 + Agentic 节点分离
- 二次重试规则：CI 失败后仅允许一次自动修复，否则人工介入
- Devbox 隔离：10 秒启动完整环境

### LangChain：评估体系构建

**从 Top 30 跃升至 Top 5**

**关键改进**：
- Harness 约束而非模型调优
- 结构化反馈循环
- 多维度评估框架

### Anthropic：GAN 启发的双 Agent 架构

**核心发现**：模型无法可靠评估自己的工作

**解决方案**：
- Generator Agent：生成代码
- Evaluator Agent：使用 Playwright 等工具进行端到端测试
- 专门训练 Evaluator 比 Generator 自省更有效

---

## 参考资源

| 来源 | 内容 |
|------|------|
| [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) | 官方技术报告，最权威来源 |
| [Stripe Minions Blog](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents) | 大规模实践案例 |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | 开源规约驱动工具链 |
| [Mitchell Hashimoto Blog](https://harness-engineering.ai/) | 概念首次命名和定义 |
| [LangChain State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering) | 行业调研报告 |
| [Anthropic MCP](https://modelcontextprotocol.io/) | Agent 工具协议标准 |

---

## 文档导航

- [01 - Spec Driven Development](01_Spec_Driven_Development/) - 规约驱动开发详解
- [02 - Harness Engineering](02_Harness_Engineering/) - 马具工程详解
- [03 - Industry Practices](03_Industry_Practices/) - 企业实践案例
- [04 - Expert Perspectives](04_Expert_Perspectives/) - 专家思想
- [05 - Open Source Tooling](05_Open_Source_Tooling/) - 开源工具链
- [06 - Evolution Tracker](06_Evolution_Tracker/) - 演进追踪

---

*文档生成日期：2026年3月27日*
*最后更新：2026年3月27日*
*信息来源：OpenAI、Stripe、GitHub、LangChain、Anthropic、Mitchell Hashimoto、Epsilla*
*收集版本：v1*

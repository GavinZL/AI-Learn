---
title: Spec Coding & Harness Engineering 每日资讯
date: 2026-04-02
collection_count: 8
sources: 12
---

# Spec Coding & Harness Engineering 资讯 - 2026年4月2日

## 📊 今日概览

| 类型 | 数量 | 重点推荐 |
|------|------|----------|
| 📝 博客文章 | 6 | ThoughtWorks SDD深度解析、Cursor Agent最佳实践 |
| 🔧 开源项目 | 2 | GitHub Spec-Kit、Amazon Kiro |

---

## 📝 博客文章

### 1. Spec-driven development: Unpacking one of 2025's key new AI-assisted engineering practices

**来源**: [ThoughtWorks](https://www.thoughtworks.com/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)  
**类型**: 📝 博客文章  
**关键词**: Spec-Driven Development, Context Engineering, AI-assisted

#### 核心思想

SDD（Spec-Driven Development）是2025年涌现的最重要AI辅助工程实践之一，其核心是用精心设计的软件规约（Specification）作为提示词，驱动AI编码助手生成可执行代码。

#### 主要论点

1. **Spec定义之争**: 行业对spec的角色存在分歧——激进派认为spec是唯一真相源（代码只是中间产物），保守派认为代码仍是真相源（spec只是驱动代码生成的元素）
2. **Context Engineering崛起**: 优化Agent-LLM交互比优化人-LLM交互更重要
3. **Spec质量决定代码质量**: 清晰、确定性的spec能减少模型幻觉，生成更健壮的代码
4. **规划与实现分离**: 最新AI编码助手普遍将开发过程的规划阶段和实现阶段分离，规划阶段专注于理解需求、设计约束和优化提示词

#### 逻辑结构

- 问题引入：SDD是什么？→ 定义辨析：不同观点对比 → 技术背景：LLM时代spec的复兴 → 实践指导：如何写好spec → 与Context Engineering的关系

#### 关键概念

| 概念 | 定义 |
|------|------|
| Spec-Driven Development | 以规约为提示词驱动AI生成代码的开发范式 |
| Context Engineering | 优化Agent与LLM交互的信息组织方式 |
| Vibe Coding | 无规约的随意编码方式，与SDD相对 |
| Specification | 明确定义目标软件的外部行为，包括输入/输出映射、前置/后置条件、不变式、约束、接口类型等 |

#### 实践建议

1. 使用领域通用语言（Ubiquitous Language）描述业务意图，避免技术绑定
2. 采用Given/When/Then结构定义场景
3. 保持spec完整但简洁，覆盖关键路径即可（有助于节省token）
4. 追求清晰性和确定性，减少模型幻觉
5. 使用半结构化格式，可显著提升模型推理性能
6. 将需求分析spec和技术spec分离（虽然实践中边界常不清晰）

#### 原文金句

> "Prompt engineering optimizes human-LLM interaction, while context engineering optimizes agent-LLM interaction."

---

### 2. The importance of Agent Harness in 2026

**来源**: [Philschmid.de](https://www.philschmid.de/agent-harness-2026)  
**类型**: 📝 博客文章  
**关键词**: Agent Harness, Context Engineering, Reliability, Long-running Tasks

#### 核心思想

2026年AI领域正处于转折点：我们不再只关注模型本身，而是转向构建能够管理长时间运行任务的"Agent Harness"（智能体马具）基础设施。

#### 主要论点

1. **模型差距正在缩小**: 顶级模型在静态排行榜上的差距正在缩小，但在长任务中的可靠性差异显著
2. **Harness是操作系统**: 将Harness比作操作系统——模型是CPU，上下文窗口是RAM，Harness管理资源、提供驱动
3. **Benchmark的局限性**: 现有基准测试很少测试模型在第50或100次工具调用后的行为，而这正是真实难度所在
4. **Bitter Lesson**: 通用计算方法胜过人工编码的知识，Harness必须轻量且易于替换

#### 逻辑结构

- 问题引入：模型差距缩小但长任务可靠性差异大 → Harness定义与类比 → Benchmark问题分析 → Bitter Lesson教训 → 未来展望

#### 关键概念

| 概念 | 定义 |
|------|------|
| Agent Harness | 包裹AI模型管理长任务的基础设施，提供提示预设、工具调用处理、生命周期钩子等 |
| Context Engineering | 通过压缩上下文、卸载状态到存储、隔离任务到子代理等策略管理上下文 |
| Durability | 模型在长时间执行中保持遵循指令的能力 |
| Hill Climbing | 基于真实用户反馈迭代改进系统的反馈循环 |

#### 实践建议

1. **从简单开始**: 不要构建复杂的控制流，提供健壮的原子工具，让模型制定计划
2. **为删除而构建**: 架构必须模块化，新模型会替换你的逻辑，必须准备好移除旧代码
3. **Harness即数据集**: 竞争优势不再是提示词，而是Harness捕获的轨迹数据
4. **实施防护栏**: 实现重试机制和验证，而非复杂的控制逻辑

#### 原文金句

> "The ability to improve a system is proportional to how easily you can verify its output."

> "Developers must build harnesses that allow them to rip out the 'smart' logic they wrote yesterday."

---

### 3. Best practices for coding with agents

**来源**: [Cursor Blog](https://cursor.com/blog/agent-best-practices)  
**类型**: 📝 博客文章  
**关键词**: Agent Best Practices, Plan Mode, Context Management, Rules, Skills

#### 核心思想

模型现在可以运行数小时、完成复杂的多文件重构、迭代直到测试通过。但充分利用Agent需要理解其工作原理并开发新的协作模式。

#### 主要论点

1. **Harness三要素**: 指令（系统提示词和规则）、工具（文件编辑、代码库搜索、终端执行等）、模型
2. **规划先于编码**: 芝加哥大学研究发现，经验丰富的开发者更可能在生成代码前进行规划
3. **上下文管理是关键**: 随着对Agent编写代码的适应，你的工作是提供Agent完成任务所需的上下文
4. **Rules vs Skills**: Rules提供持久静态上下文，Skills提供动态能力

#### 逻辑结构

- Harness组成介绍 → 规划优先原则 → 上下文管理策略 → Rules和Skills扩展机制 → 图像处理能力

#### 关键概念

| 概念 | 定义 |
|------|------|
| Agent Harness | 编排指令、工具和模型的系统，针对不同模型进行调优 |
| Plan Mode | 先研究代码库、澄清需求、创建详细实施计划，等待批准后再构建 |
| Rules | 持久静态上下文，定义项目命令、代码风格、工作流 |
| Skills | 动态能力，包含领域知识、工作流和脚本，按需加载 |
| MCP | Model Context Protocol，连接外部工具和数据源 |

#### 实践建议

1. **使用Plan Mode**: 按Shift+Tab切换，让Agent先创建可审查的计划
2. **保存计划到工作区**: 存储在`.cursor/plans/`便于团队文档化和恢复工作
3. **让Agent自己找上下文**: 不需要手动标记每个文件，Agent有强大的搜索工具
4. **适时开启新对话**: 切换到不同任务、Agent困惑、完成一个逻辑单元时开启新对话
5. **使用@Past Chats引用**: 比复制粘贴整个对话更高效
6. **Rules从简开始**: 只在Agent重复犯错时添加规则，避免过早优化
7. **使用Hooks创建长运行循环**: 可以构建迭代直到目标达成的Agent

#### 原文金句

> "As you get more comfortable with agents writing code, your job becomes giving each agent the context it needs to complete its task."

> "Start simple. Add rules only when you notice the agent making the same mistake repeatedly."

---

### 4. 2025 Was Agents. 2026 Is Agent Harnesses

**来源**: [Medium - Aakash Gupta](https://aakashgupta.medium.com/2025-was-agents-2026-is-agent-harnesses-heres-why-that-changes-everything-073e9877655e)  
**类型**: 📝 博客文章  
**关键词**: Agent Harness, 2026 Trends, Reliability, Infrastructure

#### 核心思想

每个人都在构建AI Agent，但大多数人在构建错误的东西。他们在优化模型，而应该优化的是Harness。

#### 主要论点

1. **从模型到Harness的转变**: 2025年是Agent之年，2026年是Harness之年
2. **Harness决定可靠性**: 模型能力只是基础，Harness决定了Agent能否可靠交付
3. **协调与可靠性挑战**: 当前挑战在于Agent协调和可靠性，Harness解决这些问题

#### 关键概念

| 概念 | 定义 |
|------|------|
| Agent Harness | 将原始认知能力转化为可靠输出的完整系统 |
| Agent Coordination | 多Agent之间的协调与协作 |

---

### 5. My LLM coding workflow going into 2026

**来源**: [Medium - Addy Osmani](https://medium.com/@addyosmani/my-llm-coding-workflow-going-into-2026-52fe1681325e)  
**类型**: 📝 博客文章  
**关键词**: LLM Workflow, AI Coding, Best Practices, 2026

#### 核心思想

有效的AI辅助编码依赖于预先规划和有纪律的执行：从清晰的spec开始，然后制定逐任务计划，最后让AI实现。

#### 主要论点

1. **保持控制**: 在使用AI编码时保持控制感
2. **10项必备技能**: 系统化调试、TDD工作流、规划模式、代码审查模式等
3. **工作流演进**: 2026年的工作流需要适应AI Agent的能力

---

### 6. Spec-Driven Development Is Eating Software Engineering

**来源**: [Medium - Visrow](https://medium.com/@visrow/spec-driven-development-is-eating-software-engineering-a-map-of-30-agentic-coding-frameworks-6ac0b5e2b484)  
**类型**: 📝 博客文章  
**关键词**: SDD, Agentic Coding Frameworks, 30+ Frameworks

#### 核心思想

AI编码工具正迅速从聊天助手演变为自主软件工程师。本文绘制了30多个支持Agent编码的框架图谱。

#### 主要论点

1. **框架爆炸式增长**: 超过30个框架支持Agentic Coding
2. **SDD成为主流**: Spec-Driven Development正在吞噬软件工程
3. **工具生态成熟**: 从原型到生产的完整工具链正在形成

---

## 🔧 开源项目

### 7. GitHub Spec-Kit

**来源**: [github.com/github/spec-kit](https://github.com/github/spec-kit)  
**类型**: 🔧 开源项目  
**关键词**: spec-driven, open-source, GitHub, toolkit, CLI

#### What - 项目功能

GitHub官方开源的Spec-Driven Development工具包，帮助开发者以结构化方式编写spec并与AI编码工具协作。它将规约变为可执行，直接生成工作实现而非仅指导实现。

#### How - 实现方式

**技术架构**:
- 语言: Python (使用uv工具链)
- 核心组件: Specify CLI、Spec模板引擎、Markdown解析器
- 安装方式: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`

**核心流程**:
```
specify init → 初始化项目
/speckit.constitution → 创建项目原则
/speckit.specify → 描述要构建的内容
/speckit.plan → 提供技术栈和架构选择
/speckit.tasks → 创建可执行任务列表
/speckit.implement → 执行所有任务
```

**关键机制**:
- **Constitution**: 项目级约束文件，定义架构风格、编码规范
- **Spec Templates**: 标准化的spec文档模板
- **Task Decomposition**: 自动将spec分解为可执行任务
- **Community Extensions**: 社区扩展生态，包括Jira集成、Azure DevOps集成、MAQA多Agent工作流等

#### 项目特点

| 特点 | 说明 |
|------|------|
| ✅ 官方支持 | GitHub官方维护，与Copilot深度集成 |
| ✅ 开源免费 | 开源协议，社区可贡献 |
| ✅ 工具无关 | 支持多种AI编码工具（Claude、Codex等） |
| ✅ 丰富扩展 | 20+社区扩展，覆盖文档、代码、流程、集成等 |
| ✅ 企业就绪 | 支持离线/隔离环境安装 |

#### 适用场景

- ✅ 新项目初始化，需要规范化流程
- ✅ 团队协作，需要统一的spec标准
- ✅ 复杂系统开发，需要分阶段规划
- ✅ 需要与Jira/Azure DevOps等项目管理工具集成

#### 限制与注意

- ⚠️ 需要Python/uv环境
- ⚠️ 对现有项目的适配可能需要重构spec
- ⚠️ 社区扩展质量参差不齐，需自行评估

#### 快速上手

```bash
# 安装
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# 初始化新项目
specify init my-project

# 或在现有项目中初始化
specify init . --ai claude

# 检查工具
specify check
```

---

### 8. Amazon Kiro

**来源**: [github.com/kirodotdev/Kiro](https://github.com/kirodotdev/Kiro)  
**类型**: 🔧 开源项目  
**关键词**: agentic IDE, spec-driven, AWS, CLI, desktop

#### What - 项目功能

Amazon开发的Agentic IDE和命令行界面，帮助开发者从原型到生产使用spec-driven development、agent hooks、powers和自然语言编码辅助。

#### How - 实现方式

**技术架构**:
- 平台: 桌面应用（macOS/Windows/Linux）+ CLI
- 核心组件: Spec引擎、Hooks系统、Agentic Chat、Steering系统
- 协议支持: MCP (Model Context Protocol)

**核心能力**:
- **Specs**: 使用结构化规约规划和构建功能，将需求分解为详细实施计划
- **Hooks**: 使用智能触发器自动化重复任务，响应文件变化和开发事件
- **Agentic Chat**: 通过自然对话构建功能，理解项目上下文
- **Steering**: 通过markdown文件中的自定义规则和项目特定上下文引导行为
- **Powers**: 按需为Kiro Agent提供专业上下文和工具，扩展能力
- **MCP Servers**: 通过Model Context Protocol连接外部工具和数据源

**核心流程**:
```
设置Steering文件 → 创建和管理Specs → 配置Hooks → 连接MCP Servers → 自然语言开发
```

#### 项目特点

| 特点 | 说明 |
|------|------|
| ✅ 企业级安全 | 企业级安全和隐私保护 |
| ✅ 双界面 | 桌面IDE + CLI两种使用方式 |
| ✅ 一键迁移 | 可导入VS Code设置和扩展 |
| ✅ AWS支持 | Amazon官方支持 |
| ✅ 隐私优先 | 代码安全，隐私保护 |

#### 适用场景

- ✅ 需要完整IDE体验的开发者
- ✅ 重视隐私和安全的团队
- ✅ 需要与AWS生态集成的项目
- ✅ 希望从VS Code无缝迁移的用户

#### 限制与注意

- ⚠️ 相对较新的项目，生态不如Spec-Kit丰富
- ⚠️ 部分功能可能需要AWS账户
- ⚠️ 社区扩展生态仍在建设中

#### 快速上手

```bash
# IDE: 从 kiro.dev 下载桌面应用

# CLI: 参考官方文档安装

# 开始第一个项目
# 1. 设置Steering文件
# 2. 创建Specs
# 3. 配置Hooks
# 4. 连接MCP Servers
```

---

## 📈 趋势总结

| 趋势 | 说明 | 关联资讯 |
|------|------|----------|
| **Context Engineering崛起** | 从人-LLM交互优化转向Agent-LLM交互优化 | #1, #2 |
| **Harness成为核心** | 2026年从关注模型转向关注Harness基础设施 | #2, #4 |
| **Spec作为核心契约** | 从vibe coding随意性转向结构化规约 | #1, #7, #8 |
| **规划先于编码** | 行业共识：先规划再实现，提高质量和可控性 | #1, #3 |
| **开源工具成熟** | GitHub Spec-Kit、Amazon Kiro等推动SDD普及 | #7, #8 |
| **长任务可靠性** | 关注模型在长工作流中的耐久性和可靠性 | #2 |
| **模块化架构** | Harness设计强调可替换、可删除的模块化 | #2 |

---

## 🔗 来源列表

1. ThoughtWorks - Spec-driven development: Unpacking one of 2025's key new AI-assisted engineering practices
2. Philschmid.de - The importance of Agent Harness in 2026
3. Cursor Blog - Best practices for coding with agents
4. Medium - 2025 Was Agents. 2026 Is Agent Harnesses
5. Medium - My LLM coding workflow going into 2026 (Addy Osmani)
6. Medium - Spec-Driven Development Is Eating Software Engineering
7. GitHub - github/spec-kit
8. GitHub - kirodotdev/Kiro

---

*生成时间: 2026-04-02T10:30:00*  
*收集工具: spec-harness-new*

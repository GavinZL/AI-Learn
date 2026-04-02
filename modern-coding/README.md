# Modern Coding 方法论

> **Spec-Driven Development + Harness Engineering 前沿实践知识库**
> 持续追踪 AI 辅助软件开发领域的最新方法论、行业实践和技术演进

---

## 文档导航

### 核心方法论

| 章节 | 内容 | 文档数 |
|------|------|-------|
| **[01 - Spec Driven Development](01_Spec_Driven_Development/)** | SDD 核心方法论、Four Pillars、五阶段工作流 | 1 |
| **[02 - Harness Engineering](02_Harness_Engineering/)** | 核心框架、上下文工程、架构约束、反馈回路设计 | 1 |

### 行业实践

| 章节 | 内容 | 文档数 |
|------|------|-------|
| **[03 - Industry Practices](03_Industry_Practices/)** | OpenAI、Stripe、LangChain 等企业的落地实践 | 3 |
| **[04 - Expert Perspectives](04_Expert_Perspectives/)** | Mitchell Hashimoto 等专家思想 | 1 |

### 工具与演进

| 章节 | 内容 | 文档数 |
|------|------|-------|
| **[05 - Open Source Tooling](05_Open_Source_Tooling/)** | GitHub Spec Kit、Harness 框架、Agent 编码平台 | 1 |
| **[06 - Evolution Tracker](06_Evolution_Tracker/)** | 年度重大进展、趋势预测 | 1 |

---

### 实践指南

| 章节 | 内容 | 说明 |
|------|------|------|
| **[实施落地指南](实施落地指南_详细解析.md)** | 6 阶段实施路线图、操作手册、配置模板、陷阱应对 | 操作手册 |
| **[AGENTS.md 模板](AGENTS_MD_模板_详细解析.md)** | TypeScript/Python/C++ 三种项目类型的 AGENTS.md 模板 | 直接复制使用 |

---

## 总览文档

**[Modern Coding 深度解析](Modern_Coding_深度解析.md)** - 全景总览，建议首先阅读

---

## 学习路径

### 路径一：快速概览（30 分钟）
1. [Modern Coding 深度解析](Modern_Coding_深度解析.md) - 了解全景
2. 选择一个感兴趣的企业实践阅读

### 路径二：深度理解（2 小时）
1. Modern Coding 深度解析
2. 01 - Spec Driven Development 全部文档
3. 02 - Harness Engineering 全部文档

### 路径三：实践落地（推荐）
1. [实施落地指南](实施落地指南_详细解析.md) - 从第一天开始做什么
2. [AGENTS.md 模板](AGENTS_MD_模板_详细解析.md) - 复制模板到项目
3. 03 - Industry Practices 中最接近你场景的案例
4. 05 - Open Source Tooling 选择合适的工具

### 路径四：持续追踪
1. 06 - Evolution Tracker 了解最新动态
2. 04 - Expert Perspectives 跟踪思想领袖

---

## 核心发现摘要

### 方法论演进

```
2023: Prompt Engineering（说什么）
2025: Context Engineering（知道什么）
2026: Harness Engineering（在什么环境里做事）
```

### 关键洞察

1. **"Agents aren't hard; the Harness is hard."** —— OpenAI Codex 团队
2. **效率提升 10 倍**：OpenAI 证明零人工代码是可行的
3. **约束创造自由**：好的 Harness 让 Agent 更高效
4. **评估体系是分水岭**：89% 有可观测性，仅 52% 有评估体系

### 企业实践数据

| 公司 | 关键指标 | 核心贡献 |
|------|---------|---------|
| OpenAI | 100万行代码/5月，0人工代码 | Agent-First 模式标杆 |
| Stripe | 1300 PR/周 | Blueprint 编排、二次重试规则 |
| LangChain | Terminal Bench #30→#5 | Agent 评估框架 |

---

## 内容统计

| 指标 | 数据 |
|------|------|
| 文档总数 | 10 |
| 覆盖企业 | 3+ |
| 追踪专家 | 1+ |
| 开源项目 | 1+ |
| 最后更新 | 2026年3月27日 |

---

## 目录结构

```
modern-coding/
├── README.md                          # 本文件
├── Modern_Coding_深度解析.md           # 总览文档
├── 实施落地指南_详细解析.md              # 操作手册（6 阶段路线图）
├── AGENTS_MD_模板_详细解析.md           # AGENTS.md 实战模板
├── 01_Spec_Driven_Development/        # SDD 方法论
│   └── SDD_核心方法论_详细解析.md
├── 02_Harness_Engineering/            # 马具工程
│   └── Harness_Engineering_核心框架_详细解析.md
├── 03_Industry_Practices/             # 企业实践
│   ├── OpenAI_Codex实践_详细解析.md
│   ├── Stripe_Minions实践_详细解析.md
│   └── LangChain_Agent评估实践_详细解析.md
├── 04_Expert_Perspectives/            # 专家思想
│   └── Mitchell_Hashimoto_Harness思想_详细解析.md
├── 05_Open_Source_Tooling/            # 开源工具
│   └── GitHub_Spec_Kit_详细解析.md
├── 06_Evolution_Tracker/              # 演进追踪
│   └── 2025-2026_演进报告.md
└── _meta/                             # 元数据（不同步到全局）
    ├── last-update.json
    ├── source-registry.json
    └── diff-reports/
```

---

## 关于本知识库

本知识库由 `modern-coding-intel` Skill 自动维护。

- **首次创建**：通过触发 "modern coding" 或 "前沿情报" 启动冷启动流程
- **增量更新**：再次触发时自动检测更新模式，搜索最新信息并对比整合
- **全局同步**：通过 "同步方法论到全局" 单向推送到 `/Volumes/LiSSD/AI_Knowledge/methodology/`

---

*知识库创建日期：2026年3月27日*
*最后更新：2026年3月27日*

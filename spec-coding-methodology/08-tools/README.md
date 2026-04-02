# 工具链与检查清单

## 工具分类

### 1. Spec 定义工具

| 工具 | 用途 | 示例 | 推荐场景 |
|------|------|------|---------|
| **Markdown** | 需求文档 | `.md` 文件 | 所有文本文档 |
| **YAML** | 结构化数据 | 任务定义、配置 | 机器可读的配置 |
| **OpenAPI** | API 规范 | `openapi.yaml` | HTTP API 设计 |
| **TypeSpec** | API 定义 | `.tsp` 文件 | 现代化 API 设计 |
| **JSON Schema** | 数据验证 | `.json` | 数据模型验证 |
| **PlantUML** | 架构图 | `.puml` | UML 图表 |
| **Mermaid** | 流程图 | Markdown 内嵌 | 文档内图表 |

### 2. AI 代码生成工具

| 工具 | 特点 | 适用场景 |
|------|------|---------|
| **Claude Code** | 上下文感知强 | 复杂逻辑、架构设计 |
| **Cursor** | IDE 集成好 | 日常开发、快速迭代 |
| **GitHub Copilot** | 代码补全 | 快速编写、 boilerplate |
| **GitHub Spec Kit** | Spec 原生 | 全流程 Spec-Driven |
| **Warp** | Terminal AI | 命令行辅助 |

### 3. Harness 工具

| 工具 | 用途 |
|------|------|
| **LangSmith** | Agent 执行追踪 |
| **Promptflow** | 工作流编排 |
| **Haystack** | Agent 框架 |
| **AgentOps** | Agent 监控 |
| **Weights & Biases** | ML 实验追踪 |

### 4. 验证工具

| 工具 | 用途 | 语言 |
|------|------|------|
| **gtest/catch2** | 单元测试 | C++ |
| **pytest** | 单元测试 | Python |
| **jest** | 单元测试 | JavaScript |
| **Zod** | 运行时类型检查 | TypeScript |
| **Pact** | 契约测试 | 多语言 |
| **Playwright** | E2E 测试 | 多语言 |
| **k6** | 性能测试 | 多语言 |
| **Valgrind** | 内存检测 | C/C++ |
| **clang-tidy** | 静态分析 | C++ |

---

## 检查清单模板

### 项目启动检查清单

```markdown
# Project Init Checklist

## Requirements
- [ ] FR (功能需求) 文档创建
- [ ] NFR (非功能需求) 文档创建
- [ ] 需求 ID 系统建立
- [ ] GWT 场景完整
- [ ] 约束清单填写

## Design
- [ ] ADR (架构决策) 创建
- [ ] 接口规范 (OpenAPI/TypeSpec)
- [ ] 领域模型图
- [ ] 数据 Schema

## Planning
- [ ] 任务分解 (YAML)
- [ ] 依赖关系图
- [ ] 工期估算
- [ ] 资源分配

## Harness Setup
- [ ] harness.yaml 配置
- [ ] CI/CD 流程配置
- [ ] 验证步骤定义
- [ ] 成本控制设置

## Tooling
- [ ] 代码仓库初始化
- [ ] Lint 配置
- [ ] 测试框架配置
- [ ] 文档工具配置
```

### 代码提交前检查清单

```markdown
# Pre-Commit Checklist

## Code Quality
- [ ] 代码编译无警告 (`-Wall -Werror`)
- [ ] 通过 Lint 检查
- [ ] 代码格式化 (clang-format/black/prettier)

## Testing
- [ ] 单元测试通过
- [ ] 新增功能有测试覆盖
- [ ] 覆盖率 > 80%

## Documentation
- [ ] 代码注释包含 `@require` 标签
- [ ] 公共 API 有文档注释
- [ ] ADR 已更新（如架构变更）

## Traceability
- [ ] 提交信息包含需求引用 (`Refs: FR-XXX`)
- [ ] 代码可追溯至 Spec
- [ ] 测试可追溯至需求

## Review
- [ ] 自我审查完成
- [ ] 复杂逻辑有注释说明
- [ ] 无调试代码/死代码
```

### 生产发布检查清单

```markdown
# Production Release Checklist

## Pre-Release
- [ ] 所有 P0/P1 Bug 修复
- [ ] 性能测试通过
- [ ] 安全扫描通过
- [ ] 文档已更新

## Deployment
- [ ] 蓝绿部署配置
- [ ] 回滚计划准备
- [ ] 监控告警配置
- [ ] 日志收集配置

## Validation
- [ ] Smoke Test 通过
- [ ] Canary 指标正常
- [ ] 业务指标监控
- [ ] 错误率监控

## Post-Release
- [ ] 24小时值班安排
- [ ] 客户通知发送
- [ ] 发布说明发布
- [ ] 回滚窗口确认
```

---

## 常见陷阱与对策

### 陷阱 1: "Spec 是文档，可以事后写"

**症状**:
- 先写代码，再补文档
- Spec 和代码不一致
- 代码成为"事实规范"

**对策**:
- Spec 必须在代码前
- Spec 变更触发代码变更
- CI 检查 Spec 和代码同步
- 代码审查时检查 Spec 追溯

### 陷阱 2: "AI 可以自动生成 Spec"

**症状**:
- 用 AI 从代码反推 Spec
- 需求未经人工审核
- 架构决策缺失

**对策**:
- AI 可以辅助起草，但需求和决策必须由人做
- Spec 是"思考的强迫函数"
- ADR 必须人工撰写

### 陷阱 3: "Spec 太详细，降低开发速度"

**症状**:
- 写 Spec 花费太多时间
- 团队觉得 Spec 是负担
- 绕过 Spec 直接写代码

**对策**:
- Spec 的详细程度与**风险成正比**
- 核心功能详细，实验性功能可简化
- 使用模板加速 Spec 编写
- 展示 Spec 减少返工的价值

### 陷阱 4: "追溯性维护成本太高"

**症状**:
- 忘记添加 @require 标签
- 需求变更后代码未更新
- 无法确定代码为何存在

**对策**:
- 使用自动化工具检查追溯性
- CI 失败时阻止提交
- 提交模板提示添加标签

### 陷阱 5: "Harness 过度工程化"

**症状**:
- 配置太复杂，难以维护
- 验证步骤太多，反馈慢
- 团队抵触流程

**对策**:
- 从最简单的验证循环开始
- 根据失败模式逐步添加组件
- 保持 Harness 简洁
- 让团队参与设计 Harness

### 陷阱 6: "AI 生成代码不需要测试"

**症状**:
- 相信 AI 不会出错
- 跳过单元测试
- 生产环境暴露 Bug

**对策**:
- 强制要求 AI 生成代码的测试
- 验证循环必须包含测试
- 覆盖率检查不可跳过

---

## 快速参考卡片

### Spec 文档结构
```
specs/
├── requirements/
│   ├── FR-XXX-*.md
│   └── NFR-XXX-*.md
├── architecture/
│   └── ADR-XXX-*.md
├── api/
│   └── *.openapi.yaml
└── data/
    └── schema.sql
```

### 需求 ID 格式
```
{TYPE}-{DOMAIN}-{NUMBER}

Examples:
  FR-ORDER-001   (功能需求-订单域-001)
  NFR-PERF-001   (非功能需求-性能域-001)
  BR-PAY-001     (业务规则-支付域-001)
```

### 代码注释标签
```cpp
// @require FR-001
// @adr ADR-001
// @complexity O(n)
// @threadsafe Yes
// @deprecated Use newMethod() instead
```

### 提交信息格式
```
type(scope): subject

body

Refs: FR-001, ADR-001
```

---

## 术语表

| 术语 | 定义 |
|------|------|
| **Spec** | 规范，定义系统行为的结构化文档 |
| **Harness** | 马具，使 Agent 可靠的编排基础设施 |
| **GWT** | Given-When-Then，BDD 格式 |
| **ADR** | Architecture Decision Record，架构决策记录 |
| **FR** | Functional Requirement，功能需求 |
| **NFR** | Non-Functional Requirement，非功能需求 |
| **Traceability** | 可追溯性，需求到代码的链接 |
| **MECE** | Mutually Exclusive, Collectively Exhaustive，互斥且完备 |
| **DRY** | Don't Repeat Yourself，单一真相源原则 |

---

## 参考资源

### 官方文档
- [GitHub Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai/)
- [OpenAPI Specification](https://spec.openapis.org/)
- [TypeSpec Documentation](https://typespec.io/)

### 博客与文章
- [Harness Engineering](https://harness-engineering.ai/)
- [Four Pillars of SDD](https://blog.rezvov.com/specification-driven-development-four-pillars)
- [MOP SDD Guide](https://ministryofprogramming.ghost.io/spec-driven-development-as-a-standard/)

### 工具链接
- [PlantUML](https://plantuml.com/)
- [Mermaid](https://mermaid.js.org/)
- [OpenAPI Generator](https://openapi-generator.tech/)

---

## 下一步

现在您已经了解了完整的 Spec Coding 方法论，接下来可以通过完整的示例项目来实践：

→ [查看示例: C++ TaskQueue + ThreadPool](../09-examples/taskqueue-threadpool/)

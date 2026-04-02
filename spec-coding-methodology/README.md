# Spec Coding 方法论

> **Spec-Driven Development + Harness Engineering**  
> 一套可落地的 AI 辅助软件开发方法论

---

## 📚 文档导航

### 核心方法论 (必须阅读)

| 章节 | 内容 | 预计阅读时间 |
|------|------|-------------|
| **[01-overview](01-overview/README.md)** | Spec Coding 与 Harness Engineering 概述，工程案例 | 15 min |
| **[02-framework](02-framework/README.md)** | 方法论框架，Four Pillars，MECE 五阶段 | 20 min |
| **[03-phase-define](03-phase-define/README.md)** | Phase 1: 需求定义 - GWT、需求 ID、约束清单 | 15 min |
| **[04-phase-design](04-phase-design/README.md)** | Phase 2: 规范设计 - ADR、OpenAPI、领域模型 | 15 min |
| **[05-phase-decompose](05-phase-decompose/README.md)** | Phase 3: 任务分解 - 任务编排、依赖图 | 15 min |
| **[06-phase-develop](06-phase-develop/README.md)** | Phase 4: 编码实现 - Harness、代码追溯 | 20 min |
| **[07-phase-deliver](07-phase-deliver/README.md)** | Phase 5: 验证部署 - CI/CD、监控 | 15 min |
| **[08-tools](08-tools/README.md)** | 工具链推荐、检查清单、常见陷阱 | 10 min |

### 完整示例 (实践参考)

| 示例 | 描述 | 技术栈 |
|------|------|--------|
| **[09-examples/taskqueue-threadpool](09-examples/taskqueue-threadpool/)** | C++ 任务队列 + 线程池系统 | C++17, CMake, gtest |

---

## 🎯 快速开始

### 5 分钟了解

**什么是 Spec Coding？**

```
传统:  Prompt → Code → Patch bugs → Explain later
        快速但不稳定，缺乏结构

Spec Coding:  Idea → Spec → Design → Tasks → Code → Tests
              规范先行，可追溯，可验证
```

**什么是 Harness Engineering？**

构建使 AI Agent 可靠的"马具"（Harness）：
1. **上下文工程** - 给 AI 精确的上下文
2. **工具编排** - 管理外部系统交互
3. **验证循环** - 每步检查输出
4. **成本封套** - 防止费用失控
5. **可观测性** - 执行轨迹和评估

### 15 分钟上手

**Step 1: 创建需求**
```markdown
# specs/requirements/FR-001-feature.md
id: FR-001
title: 实现 XX 功能

gwt: |
  Scenario: 正向场景
    Given [条件]
    When [动作]
    Then [结果]
```

**Step 2: 编写架构决策**
```markdown
# specs/architecture/ADR-001-strategy.md
## Decision
采用 XXX 方案

## Consequences
- Positive: [好处]
- Negative: [代价]
```

**Step 3: 配置 Harness**
```yaml
# harness.yaml
verification:
  steps:
    - name: compile
      command: "g++ -std=c++17 src/*.cpp"
      must_pass: true
    - name: test
      command: "./run_tests"
      must_pass: true
```

**Step 4: AI 生成代码**
```
Prompt: "基于 specs/FR-001.md 和 specs/ADR-001.md，
         实现 src/feature.cpp"
```

**Step 5: 验证并提交**
```bash
# Harness 自动验证
harness run

# 提交
git commit -m "feat: implement XX feature

Refs: FR-001, ADR-001"
```

---

## 🏗️ 方法论架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Spec Coding 方法论                        │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Define   │ Design   │ Decompose│ Develop  │ Deliver         │
│ 需求定义  │ 规范设计  │ 任务分解  │ 编码实现  │ 验证部署         │
├──────────┼──────────┼──────────┼──────────┼─────────────────┤
│ GWT      │ ADR      │ Tasks    │ Code     │ CI/CD           │
│ FR/NFR   │ OpenAPI  │ 依赖图    │ @require │ Monitoring      │
│ 约束清单  │ 领域模型  │ 并行识别  │ Harness  │ Alerting        │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Four Pillars (四大支柱)                     │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Traceability │ DRY          │ Deterministic│ Parsimony      │
│ 可追溯性      │ 单一真相源    │ 确定性执行   │ 简洁性         │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

---

## 💡 核心原则

### 1. Traceability (可追溯性)

每个代码变更都能追溯到需求：
```cpp
// @require FR-ORDER-001
// @adr ADR-001
void create_order() { ... }
```

### 2. DRY (单一真相源)

API 定义一处，处处生成：
```yaml
# specs/openapi.yaml (唯一来源)
# → 生成 TypeScript 类型
# → 生成 客户端 SDK
# → 生成 文档
```

### 3. Deterministic (确定性)

能自动化的必须自动化：
```yaml
verification:
  steps:
    - compile      # 编译检查
    - test         # 单元测试
    - lint         # 代码风格
    - traceability # 追溯性检查
```

### 4. Parsimony (简洁性)

最小表示，最大信息：
```cpp
// Good: 简洁且完整
// @require FR-001
// @complexity O(n)
int calculate(const vector<int>& data);

// Bad: 冗余
/**
 * This function calculates something.
 * It takes a vector as input.
 * Please make sure the vector is valid.
 * TODO: optimize this later.
 */
int calculate(const vector<int>& data);
```

---

## 📊 效果数据

| 团队/项目 | 改进 | 来源 |
|----------|------|------|
| OpenAI Codex | 3 人/5 月/100 万+ 行代码 | OpenAI |
| Stripe Minions | 每周 1000+ PR，零人工代码 | Stripe |
| Vercel | 准确率 80%→100%，Token -37% | Vercel |
| LangChain | 任务完成率 52.8%→66.5% | LangChain |
| MOP | 后期缺陷减少 30-50% | Ministry of Programming |

---

## 📁 目录结构

```
spec-coding-methodology/
├── README.md                          # 本文件
├── 01-overview/                       # 概述与案例
│   └── README.md
├── 02-framework/                      # 方法论框架
│   └── README.md
├── 03-phase-define/                   # Phase 1: 需求定义
│   └── README.md
├── 04-phase-design/                   # Phase 2: 规范设计
│   └── README.md
├── 05-phase-decompose/                # Phase 3: 任务分解
│   └── README.md
├── 06-phase-develop/                  # Phase 4: 编码实现
│   └── README.md
├── 07-phase-deliver/                  # Phase 5: 验证部署
│   └── README.md
├── 08-tools/                          # 工具链与检查清单
│   └── README.md
├── 09-examples/                       # 完整示例
│   └── taskqueue-threadpool/          # C++ 任务队列示例
│       ├── specs/                     # Spec 文档
│       ├── src/                       # 源代码
│       ├── tests/                     # 测试
│       └── README.md
└── scripts/                           # 工具脚本
    ├── check_requirement_tags.py
    ├── validate_spec.py
    └── generate_task_graph.py
```

---

## 🚀 推荐学习路径

### 路径 1: 快速概览 (30 分钟)
1. [01-overview](01-overview/README.md) - 了解核心概念
2. [02-framework](02-framework/README.md) - 理解框架
3. [09-examples](09-examples/taskqueue-threadpool/) - 看完整示例

### 路径 2: 深度掌握 (2 小时)
按顺序阅读 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08

### 路径 3: 实践应用
1. 选择一个现有项目
2. 从 [03-phase-define](03-phase-define/README.md) 开始应用
3. 使用 [08-tools](08-tools/README.md) 的检查清单
4. 参考 [09-examples](09-examples/taskqueue-threadpool/) 的结构

---

## 🤝 贡献

本方法论是开源的，欢迎：
- 分享您的实践经验
- 提交改进建议
- 贡献示例项目
- 完善工具脚本

---

## 📄 许可证

MIT License - 自由使用、修改、分发

---

## 🔗 相关资源

- [GitHub Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai/)
- [Harness Engineering Blog](https://harness-engineering.ai/)
- [Four Pillars of SDD](https://blog.rezvov.com/specification-driven-development-four-pillars)

---

**开始您的 Spec Coding 之旅 → [01-overview](01-overview/README.md)**

# Spec-Driven Development 核心方法论 详细解析

> **核心结论**：Spec-Driven Development (SDD) 是 AI 辅助软件开发的基石，通过"规范先行"确保 AI 生成的代码可追溯、可验证、可维护。Four Pillars 提供原则，五阶段工作流提供实施路径。

## 概述

Spec-Driven Development 将传统软件开发流程反转：**先定义规范，再生成代码**。这一方法论与 Harness Engineering 相辅相成：
- SDD 定义"做什么"和"为什么"
- Harness Engineering 保障"可靠地做"

> **2026年3月里程碑**：AWS 开发者正式宣布 "Vibe Coding is Dead"，SDD 成为 AI 编码新标准。

---

## 〇、SDD Triangle 模型（2026年3月新增）

> 来源：Drew Breunig @ MLOps Community "Coding Agents" Conference, 2026年3月3日

### 核心洞察

**实现代码有助于改进规范** —— 这是一个反馈循环，而非直线流程。

```
         Spec（规范）
           △
          ╱ ╲
         ╱   ╲
        ╱     ╲
       ╱       ╲
      ╱─────────╲
   Tests ←──────→ Code
```

### Triangle 同步机制

| 元素 | 角色 | 输入 | 输出 |
|------|------|------|------|
| **Spec** | 定义做什么和为什么 | Tests 反馈 | 改进的规范 |
| **Tests** | 测量和验证行为 | Spec 定义 | 验证结果 |
| **Code** | 实现行为 | Spec + Tests | 可运行代码 |

### 关键学习

1. **测试和规范并非免费**
   - 所有大项目都使用现有测试库（Bash tests、Python tests、C tests）
   - "SQLite 模式"：代码免费，测试付费
   - 测试是宝贵资产

2. **实现快速，但非即时**
   - 初期速度快，但复杂度增长后变难
   - Anthropic 的 C 编译器项目：卡在 1% 失败测试
   - 系统性变化需要系统性思考

3. **架构选择决定并行效率**
   - 支持多 Agent 并行开发的架构极其重要
   - 允许开源贡献（类似 SETI@home 分布式计算）
   - 结构化分工让每个人知道该做什么

### 历史类比

> "When you can't see over your code, you can't oversee your code."
> —— Drew Breunig，借用 Margaret Hamilton 1963年 NASA Apollo 项目经验

| 时代 | 挑战 | 解决方案 |
|------|------|---------|
| 1963 | 代码量大到无法理解 | 软件工程概念诞生 |
| 1972 | 巨型计算机 → 巨型编程问题 | Dijkstra 图灵奖演讲 |
| 2001 | 快速迭代需求 | Agile Manifesto |
| 2026 | AI 生成代码量爆炸 | **Spec-Driven Development** |

## 一、核心理念

### 1.1 范式对比

```
传统开发:    Prompt → Code → Patch bugs → Explain later
             快速但不稳定，缺乏结构

Spec Coding: Idea → Spec → Design → Tasks → Code → Tests
             规范先行，可追溯，可验证
```

### 1.2 为什么 AI 时代更需要 SDD

| 挑战 | 传统做法 | SDD 解决方案 |
|------|---------|-------------|
| AI 无隐性知识 | 期望 AI 理解隐含上下文 | 显式规范定义所有约束 |
| 需求漂移 | 口头传递，无记录 | 需求 ID 系统，全程追溯 |
| 代码审查困难 | 逐行检查 | 规范驱动测试，自动验证 |
| 一致性难以保证 | 依赖人工规范遵循 | 从规范自动生成代码骨架 |

---

## 二、Four Pillars（四大支柱）

### Pillar 1: Traceability（可追溯性）

**原则**：每个代码变更必须追溯到一个需求

#### 双向追溯链

```
Top-down:    需求 → 规范 → 代码 → 测试
Bottom-up:   测试 → 代码 → 规范 → 需求
```

#### 需求 ID 系统

```
格式: {TYPE}-{DOMAIN}-{NUMBER}

TYPE:   FR (功能需求) | NFR (非功能需求) | BR (业务规则)
DOMAIN: AUTH | ORDER | PAYMENT | USER | etc.
NUMBER: 001, 002, ...

示例: FR-ORDER-001, NFR-PERF-003
```

#### 代码注释标签

```cpp
// @require FR-ORDER-001
// @adr ADR-001
// @test test_order_creation
class OrderService {
    // ...
};
```

#### 提交信息规范

```
feat(order): implement creation API

- Add OrderService::create method
- Implement inventory locking
- Add comprehensive tests

Refs: FR-ORDER-001, ADR-001
```

---

### Pillar 2: DRY（单一真相源）

**原则**：每个事实只有一个权威来源

#### 错误示例

```
❌ 重复定义:
   - API 定义在 OpenAPI YAML 中
   - 相同定义又复制到 README
   - TypeScript 类型又手动定义一次
   
   结果: 更新 YAML 后，README 和 TS 类型不同步
```

#### 正确做法

```
✓ 单一来源:
   - API 定义: specs/openapi.yaml (唯一来源)
   - README: 引用 OpenAPI 文件，不复制内容
   - TypeScript 类型: 从 OpenAPI 自动生成
   
   结果: 修改一处，处处同步
```

#### 信息类型映射

| 信息类型 | 单一来源 | 派生产物 |
|---------|---------|---------|
| API 合约 | `specs/openapi.yaml` | 客户端 SDK、类型定义、文档 |
| 数据模型 | `specs/schema/*.yaml` | 数据库 Schema、ORM 模型 |
| 配置语义 | `specs/config.yaml` | 文档、验证代码 |
| 业务规则 | `specs/rules/*.md` | 测试用例、验证逻辑 |

---

### Pillar 3: Deterministic Enforcement（确定性执行）

**原则**：能写成脚本的就写成脚本，AI 填补需要判断力的空白

#### 验证金字塔

```
        ┌─────────────────┐
        │   纯 AI 验证    │ ◄── 需要人类判断力
        │  (语义审查)     │     架构决策、逻辑错误
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  脚本 + AI     │ ◄── 混合方式
        │  (筛选+判断)   │     脚本找可疑点，AI 判断
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  确定性工具     │ ◄── 完全自动化
        │  (编译、测试)   │     编译检查、单元测试
        └─────────────────┘
```

#### CI 配置示例

```yaml
verification:
  steps:
    - name: compile
      command: "g++ -std=c++17 -Wall -Werror src/*.cpp"
      must_pass: true
      
    - name: unit_tests
      command: "./run_tests --gtest_filter='*'"
      must_pass: true
      
    - name: lint
      command: "clang-tidy src/*.cpp"
      must_pass: true
      
    - name: traceability
      command: "python scripts/check_traceability.py src/"
      must_pass: true
```

---

### Pillar 4: Parsimony（简洁性）

**原则**：最小表示保留完整语义和可执行性

#### 对比示例

❌ **冗余写法** (150 tokens):
```markdown
When you are writing configuration files for the system, 
it is very important to remember that you should always 
validate the required fields at startup, because this 
helps catch errors early in the development process and 
prevents issues in production.
```

✓ **简洁写法** (15 tokens):
```markdown
Configuration MUST validate required fields at startup (fail-fast).
```

#### 指令词汇规范 (RFC 2119)

```yaml
MUST      # 绝对要求
MUST NOT  # 绝对禁止
SHOULD    # 推荐做法
MAY       # 可选做法
```

---

## 三、五阶段工作流

### 阶段总览

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

### MECE 边界检查

| 阶段 | 输入 | 输出 | 边界规则 |
|------|------|------|---------|
| **Define** | 业务需求、用户故事 | 结构化需求文档 | 不涉实现细节 |
| **Design** | 需求文档 | ADR、接口规范 | 不涉代码实现 |
| **Decompose** | 接口规范、架构决策 | 任务列表、依赖图 | 不涉具体代码 |
| **Develop** | 任务列表、Harness 配置 | 可运行代码、测试 | 不涉部署配置 |
| **Deliver** | 代码、测试 | 部署服务、监控 | 不涉新功能开发 |

---

## 四、最佳实践

### 推荐做法

1. **需求先行**：任何代码变更前，先写需求文档并分配 ID
2. **自动化优先**：能用脚本检查的，绝不依赖人工
3. **追溯标签**：代码中必须标注 @require 和 @adr
4. **单一来源**：API 定义、配置 Schema 等有且仅有一个权威文件

### 常见陷阱

1. **需求漂移**：口口相传，无文档记录
   - 解决：强制需求 ID，CI 检查追溯性
   
2. **规范腐烂**：文档与代码不同步
   - 解决：从规范生成代码骨架，或测试反向验证规范
   
3. **过度设计**：Spec 过于详细，限制 AI 创造力
   - 解决：Spec 描述"做什么"，不限制"怎么做"

---

## 相关文档

- [四阶段工作流详解](四阶段工作流_详细解析.md)
- [Spec 产物规范](Spec产物规范_详细解析.md)
- [需求定义最佳实践](需求定义最佳实践_详细解析.md)

---

*文档生成日期：2026年3月27日*
*最后更新：2026年3月27日*
*信息来源：GitHub Spec Kit、Alex Rezvov Four Pillars、OpenAI Codex 实践*
*收集版本：v1*

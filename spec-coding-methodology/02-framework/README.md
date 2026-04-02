# Spec Coding 方法论框架

## 金字塔三层结构

Spec Coding + Harness Engineering 方法论采用金字塔三层结构：

```
                    ┌─────────────────────────────────────┐
                    │         Spec Coding 方法论         │
                    │      （规约驱动 + 马具工程）        │
                    └──────────────┬──────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
   ┌────▼─────┐              ┌──────▼──────┐            ┌──────▼──────┐
   │  Spec层  │              │  Harness层  │            │  工具链层   │
   │ 定义规约 │◄────────────►│  保障执行   │◄──────────►│  加速开发   │
   └────┬─────┘              └──────┬──────┘            └──────┬──────┘
        │                          │                          │
   ┌────▼─────┐              ┌──────▼──────┐            ┌──────▼──────┐
   │ 需求分析 │              │ 验证循环    │            │ 代码生成    │
   │ 架构设计 │              │ 成本控制    │            │ 测试框架    │
   │ 任务分解 │              │ 可观测性    │            │ CI/CD集成   │
   └──────────┘              └─────────────┘            └─────────────┘
```

### 各层职责

| 层级 | 职责 | 关键产出 |
|------|------|---------|
| **Spec 层** | 定义"做什么"和"为什么" | 需求文档、架构决策、接口规范 |
| **Harness 层** | 保障"可靠地做" | 验证循环、成本控制、可观测性 |
| **工具链层** | 加速"如何做" | 代码生成、自动化测试、CI/CD |

---

## Four Pillars（四大支柱）

基于 Alex Rezvov 的 "Specification-Driven Development: The Four Pillars"

### Pillar 1: 可追溯性 (Traceability)

**原则**: 每个行为变化必须追溯到一个需求

**双向追溯**:
```
Top-down:    需求 → 规范 → 代码 → 测试
Bottom-up:   测试 → 代码 → 规范 → 需求
```

**实现方式**:

1. **需求 ID 系统**
   ```
   格式: {TYPE}-{DOMAIN}-{NUMBER}
   
   TYPE:   FR (功能需求) | NFR (非功能需求) | BR (业务规则)
   DOMAIN: AUTH | ORDER | PAYMENT | USER | etc.
   NUMBER: 001, 002, ...
   
   示例: FR-ORDER-001, NFR-PERF-003
   ```

2. **代码注释标签**
   ```cpp
   // @require FR-ORDER-001
   // @adr ADR-001
   // @test test_order_creation
   class OrderService {
       // ...
   };
   ```

3. **提交信息规范**
   ```
   feat(order): implement creation API
   
   - Add OrderService::create method
   - Implement inventory locking
   - Add comprehensive tests
   
   Refs: FR-ORDER-001, ADR-001
   ```

**验证检查**:
```bash
# 检查代码追溯性
python scripts/check_traceability.py src/

# 输出:
# ✓ FR-ORDER-001: 3 files reference this requirement
# ✓ FR-ORDER-002: 5 files reference this requirement
# ✗ FR-ORDER-003: No implementation found!
```

---

### Pillar 2: 单一真相源 (DRY - Don't Repeat Yourself)

**原则**: 每个事实只有一个权威来源

**常见重复问题**:
```
❌ 错误做法:
   - API 定义在 OpenAPI YAML 中
   - 相同定义又复制到 README
   - TypeScript 类型又手动定义一次
   
   结果: 更新 YAML 后，README 和 TS 类型不同步
```

**正确做法**:
```
✓ 正确做法:
   - API 定义: specs/openapi.yaml (唯一来源)
   - README: 引用 OpenAPI 文件，不复制内容
   - TypeScript 类型: 从 OpenAPI 自动生成
   
   结果: 修改一处，处处同步
```

**实施策略**:

| 信息类型 | 单一来源 | 派生产物 |
|---------|---------|---------|
| API 合约 | `specs/openapi.yaml` | 客户端 SDK、类型定义、文档 |
| 数据模型 | `specs/schema/*.yaml` | 数据库 Schema、ORM 模型 |
| 配置语义 | `specs/config.yaml` | 文档、验证代码 |
| 业务规则 | `specs/rules/*.md` | 测试用例、验证逻辑 |

**自动化生成示例**:
```yaml
# Makefile
generate-api-types:
    openapi-typescript specs/openapi.yaml -o src/types/api.ts
    
generate-client-sdk:
    openapi-generator generate -i specs/openapi.yaml -g typescript-axios
    
generate-docs:
    redocly build-docs specs/openapi.yaml -o docs/api.html
```

---

### Pillar 3: 确定性执行 (Deterministic Enforcement)

**原则**: 能写成脚本的就写成脚本，AI 填补需要判断力的空白

**验证金字塔**:

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

**每层示例**:

**Level 1: 确定性工具** (必须实现)
```yaml
# CI 配置
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
```

**Level 2: 脚本 + AI**
```python
# check_complexity.py
import re

# 脚本找出所有函数
functions = extract_functions('src/')

# AI 评估哪些函数过于复杂需要重构
for func in functions:
    if func.lines > 50:
        # 交给 AI 判断
        ai_review = ai_assess_complexity(func)
        if ai_review.needs_refactor:
            report(func, ai_review.reason)
```

**Level 3: 纯 AI**
```
当需要以下判断时使用纯 AI:
- 架构设计是否合理？
- 这段代码是否有逻辑错误？
- 命名是否符合领域惯例？
```

**关键规则**:
> 如果一个检查可以自动化，就必须自动化。不要依赖人工检查。

---

### Pillar 4: 简洁性 (Parsimony)

**原则**: 最小表示保留完整语义和可执行性

**三大要求**:

1. **最小性 (Minimality)**: 排除不影响行为的一切
2. **充分性 (Sufficiency)**: 压缩不引入歧义
3. **预算优先 (Budget Prioritization)**: Token 省下来用于核心内容

**对比示例**:

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

**Spec 写作规范**:

```yaml
# 指令词汇 (RFC 2119 风格)
MUST      # 绝对要求
MUST NOT  # 绝对禁止
SHOULD    # 推荐做法
MAY       # 可选做法

# 示例
requirements:
  - id: FR-001
    description: |
      The system MUST validate user input.
      The system SHOULD log validation errors.
      The system MAY cache validation results.
```

**代码注释规范**:
```cpp
// Good: 简洁且信息完整
// @require FR-ORDER-001
// @complexity O(n)
int calculate_total(const std::vector<Item>& items);

// Bad: 冗余和模糊
/**
 * This function calculates the total price of all items.
 * It iterates through each item and adds up the price.
 * Please make sure to pass valid items.
 * TODO: optimize this function later
 */
int calculate_total(const std::vector<Item>& items);
```

---

## MECE 五阶段方法论

**MECE = Mutually Exclusive, Collectively Exhaustive**  
（互斥且完备）

### 阶段总览

```
Phase 1        Phase 2        Phase 3        Phase 4        Phase 5
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ Define │───►│ Design │───►│Decompos│───►│Develop │───►│Deliver │
│ 需求定义│    │ 规范设计│    │ 任务分解│    │ 编码实现│    │ 验证部署│
└────────┘    └────────┘    └────────┘    └────────┘    └────────┘
    │             │             │             │             │
    ▼             ▼             ▼             ▼             ▼
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│输入分析│    │架构决策│    │任务编排│    │代码生成│    │验证循环│
│约束识别│    │接口定义│    │依赖排序│    │测试优先│    │监控部署│
│范围界定│    │模式选择│    │责任分配│    │版本控制│    │回滚机制│
└────────┘    └────────┘    └────────┘    └────────┘    └────────┘
```

### 各阶段边界（MECE 验证）

| 阶段 | 输入 | 输出 | 边界检查 |
|------|------|------|---------|
| **Define** | 业务需求、用户故事 | 结构化需求文档 (FR/NFR) | 不涉实现细节 |
| **Design** | 需求文档 | 架构决策 (ADR)、接口规范 | 不涉代码实现 |
| **Decompose** | 接口规范、架构决策 | 任务列表、依赖图 | 不涉具体代码 |
| **Develop** | 任务列表、Harness 配置 | 可运行代码、测试 | 不涉部署配置 |
| **Deliver** | 代码、测试 | 部署服务、监控 | 不涉新功能开发 |

### 阶段间追溯关系

```
FR-001 ────────► ADR-001 ────────► T-001 ────────► Code ────────► Deploy
   │                │                │               │              │
   │                │                │               │              │
   ▼                ▼                ▼               ▼              ▼
需求定义          架构设计          任务分解         编码实现        验证部署
```

**双向验证**:
- 代码中是否有未追溯的需求？
- 需求是否都有实现？
- 架构决策是否被遵守？

---

## 五阶段 + Four Pillars 矩阵

| 阶段 | Traceability | DRY | Deterministic | Parsimony |
|------|-------------|-----|---------------|-----------|
| **Define** | 需求 ID 系统 | 需求唯一存储 | GWT 模板化 | 简洁描述 |
| **Design** | ADR 编号 | Spec 生成代码 | Schema 验证 | 最小架构 |
| **Decompose** | Task ID 映射 | 任务单一定义 | 依赖图生成 | 原子任务 |
| **Develop** | @require 标签 | 代码即规范 | CI 自动检查 | 必要注释 |
| **Deliver** | 版本可追溯 | 配置即代码 | 自动化部署 | 最小配置 |

---

## 下一章

接下来，我们将深入讲解 **Phase 1: 需求定义 (Define)**，包括：
- GWT 用户故事模板
- 需求 ID 系统
- 约束清单
- 完整示例

→ [继续阅读: 03-phase-define](../03-phase-define/README.md)

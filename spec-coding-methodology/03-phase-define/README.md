# Phase 1: 需求定义 (Define)

## 目标

将模糊的业务需求转化为**结构化、可追溯、可验证**的规格说明。

**关键产出**:
- 功能需求文档 (FR-XXX)
- 非功能需求文档 (NFR-XXX)
- 约束清单
- 验收标准

---

## 可执行方法

### 方法 1: GWT 用户故事模板

**GWT = Given-When-Then** (BDD 风格)

**模板结构**:
```gherkin
Feature: [功能名称]
  As a [角色]
  I want [目标]
  So that [价值]

  Background:
    Given [共享的前置条件]

  Scenario: [正向场景]
    Given [前置条件 1]
    And [前置条件 2]
    When [动作]
    Then [预期结果 1]
    And [预期结果 2]

  Scenario: [边界场景]
    Given [异常前置条件]
    When [动作]
    Then [错误处理结果]

  Scenario: [异常场景]
    Given [故障条件]
    When [动作]
    Then [容错结果]
```

**示例**: 订单创建功能
```gherkin
Feature: Order Creation
  As a customer
  I want to create an order from my cart
  So that I can purchase the items

  Scenario: Successfully create order
    Given the user is logged in
    And the cart contains valid items
    When the user clicks "Checkout"
    Then the order is created with status "pending"
    And the inventory is locked
    And the order total is calculated correctly

  Scenario: Create order with empty cart
    Given the user is logged in
    And the cart is empty
    When the user clicks "Checkout"
    Then an error "Cart is empty" is displayed
    And no order is created

  Scenario: Create order with insufficient inventory
    Given the user is logged in
    And the cart contains items with insufficient stock
    When the user clicks "Checkout"
    Then an error "Item out of stock" is displayed
    And the problematic items are highlighted
```

---

### 方法 2: 需求 ID 系统

**格式**:
```
{TYPE}-{DOMAIN}-{NUMBER}

TYPE:
  FR  = Functional Requirement (功能需求)
  NFR = Non-Functional Requirement (非功能需求)
  BR  = Business Rule (业务规则)
  ER  = External Dependency (外部依赖)

DOMAIN:
  AUTH   = Authentication/Authorization
  ORDER  = Order Management
  PAY    = Payment
  USER   = User Management
  INVT   = Inventory
  PERF   = Performance
  SEC    = Security
  etc.

NUMBER:
  001, 002, 003, ... (三位数字，各域独立编号)
```

**示例**:
```
FR-ORDER-001    # 创建订单功能
FR-ORDER-002    # 取消订单功能
NFR-PERF-001    # 响应时间要求
NFR-SEC-001     # 数据加密要求
BR-PAY-001      # 退款业务规则
```

**文件命名**:
```
specs/requirements/
├── FR-001-user-registration.md
├── FR-002-user-login.md
├── FR-003-password-reset.md
├── NFR-001-performance.md
├── NFR-002-security.md
└── BR-001-refund-policy.md
```

---

### 方法 3: 约束清单 (Constraints Checklist)

**技术约束**:
- [ ] **编程语言/版本**: C++17, Python 3.9+, etc.
- [ ] **框架/库**: 必须使用的技术栈
- [ ] **平台支持**: Linux, macOS, Windows, iOS, Android
- [ ] **编译器**: GCC 9+, Clang 10+, MSVC 2019+

**业务约束**:
- [ ] **法规合规**: GDPR, HIPAA, PCI-DSS
- [ ] **行业标准**: ISO 27001, SOC 2
- [ ] **公司政策**: 代码审查要求、安全扫描

**性能约束**:
- [ ] **响应时间**: P99 < 200ms
- [ ] **吞吐量**: > 1000 req/s
- [ ] **资源使用**: CPU < 70%, Memory < 1GB
- [ ] **可用性**: 99.99% uptime

**安全约束**:
- [ ] **认证**: OAuth 2.0, JWT
- [ ] **授权**: RBAC, ABAC
- [ ] **加密**: TLS 1.3, AES-256
- [ ] **审计**: 所有操作日志记录

**时间约束**:
- [ ] **里程碑**: 原型日期、测试日期、发布日期
- [ ] **迭代周期**: Sprint 长度
- [ ] **维护周期**: LTS 支持时间

---

## 需求文档模板

```markdown
# FR-{XXX}: [需求标题]

## Metadata
- **ID**: FR-{DOMAIN}-{NUMBER}
- **Title**: [需求标题]
- **Type**: FR | NFR | BR
- **Priority**: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
- **Status**: Draft | Review | Approved | Implemented | Deprecated
- **Created**: YYYY-MM-DD
- **Author**: [Name]

## Description
[一句话描述需求]

## GWT Specifications
### Scenario 1: [场景名称]
```gherkin
Given [前置条件]
When [动作]
Then [预期结果]
```

**验收标准**:
- [ ] [可检查的条件 1]
- [ ] [可检查的条件 2]

### Scenario 2: [边界场景]
...

## Interface Requirements
[如果是 NFR，描述性能/安全指标]
[如果是 FR，描述接口方法]

### Methods
#### `method_name(params) -> return_type`
- **Purpose**: [用途]
- **Parameters**: [参数列表]
- **Returns**: [返回值]
- **Preconditions**: [前置条件]
- **Postconditions**: [后置条件]
- **Error Handling**: [错误处理]

## Constraints
### Performance
- [指标]: [目标值]

### Technical
- [约束]: [要求]

## Dependencies
### Requires
- [依赖的需求 ID]

### Required By
- [被哪个需求依赖]

## Traceability
### Implementation References
- [代码文件路径]

### Test References
- [测试文件路径]

## Notes
[设计考虑、示例代码、开放问题]

## Change Log
| Date | Version | Author | Changes |
|------|---------|--------|---------|
```

---

## 示例: 完整需求文档

详见 [../09-examples/taskqueue-threadpool/specs/requirements/](../09-examples/taskqueue-threadpool/specs/requirements/)

---

## 常见陷阱

### 陷阱 1: 需求过于笼统
❌ **错误**:
```
系统应该很快。
```

✓ **正确**:
```
API 响应时间 P99 < 200ms（在 1000 concurrent users 下）。
```

### 陷阱 2: 需求包含实现细节
❌ **错误**:
```
使用 Redis 缓存用户数据。
```

✓ **正确**:
```
用户数据读取延迟 < 10ms。
（具体实现：可考虑 Redis、本地缓存等）
```

### 陷阱 3: 忽视边界情况
❌ **错误**:
只写正向场景。

✓ **正确**:
必须包含:
- 正向场景 (Happy Path)
- 边界场景 (Edge Cases)
- 异常场景 (Error Cases)

---

## 工具推荐

| 工具 | 用途 | 示例 |
|------|------|------|
| Gherkin | 需求描述 | `.feature` 文件 |
| YAML | 结构化需求 | `requirements.yaml` |
| Markdown | 文档 | `.md` 文件 |
| Jira/Linear | 需求跟踪 | 与代码仓库关联 |

---

## 验收清单

- [ ] 每个需求都有唯一 ID
- [ ] 每个需求都有 GWT 场景
- [ ] 包含正向、边界、异常场景
- [ ] 约束清单完整
- [ ] 可追溯性信息填写
- [ ] 需求之间依赖关系清晰

---

## 下一章

→ [继续阅读: 04-phase-design - 规范设计阶段](../04-phase-design/README.md)

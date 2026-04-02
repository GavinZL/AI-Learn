# Spec Coding 方法论文档创建工作计划

## TL;DR

创建一套完整的 Spec Coding + Harness Engineering 方法论文档，包括：
- 8个核心章节文档（多文件目录结构）
- 完整的代码示例和可执行脚本
- 可直接使用的模板和配置文件

**输出位置**: `/Volumes/LiSSD/AI_Learn/spec-coding-methodology/`

---

## Context

基于用户的研究和确认，需要将 `.sisyphus/drafts/spec-coding-methodology-plan.md` 中的规划内容转化为正式的文档体系。

**用户需求**:
- ✅ 大纲方向正确
- ✅ 多文件目录结构
- ✅ 需要完整代码示例和可执行脚本

**参考来源**: `.sisyphus/drafts/spec-coding-methodology-plan.md`

---

## Work Objectives

### Core Objective
创建一套结构清晰、可落地的 Spec Coding 方法论文档体系，包含理论阐述、实践案例、代码示例和工具模板。

### Concrete Deliverables
1. 主 README.md（总览和导航）
2. 01-overview/（宏观概念）
3. 02-framework/（方法论框架）
4. 03-phase-define/（需求定义阶段）
5. 04-phase-design/（规范设计阶段）
6. 05-phase-decompose/（任务分解阶段）
7. 06-phase-develop/（编码实现阶段）
8. 07-phase-deliver/（验证部署阶段）
9. 08-tools/（工具链和模板）
10. 09-examples/（完整项目示例）
11. scripts/（可执行工具脚本）

### Definition of Done
- [ ] 所有文档章节完整创建
- [ ] 代码示例可运行
- [ ] 模板文件可用
- [ ] 脚本可执行
- [ ] 主 README 索引完整

---

## Verification Strategy

### QA Policy
- 每个任务完成后验证文件存在且内容完整
- 代码示例语法正确
- 脚本可执行（如有 shebang 或执行权限）

---

## Execution Strategy

### 并行执行方案

```
Wave 1 (基础结构):
├── Task 1: 创建目录结构
├── Task 2: 创建主 README.md
└── Task 3: 创建第一部分（概述）

Wave 2 (核心内容 - 可并行):
├── Task 4: 创建第二部分（方法论框架）
├── Task 5: 创建第三部分（需求定义）
├── Task 6: 创建第四部分（规范设计）
└── Task 7: 创建第五部分（任务分解）

Wave 3 (实现细节 - 可并行):
├── Task 8: 创建第六部分（编码实现）
├── Task 9: 创建第七部分（验证部署）
└── Task 10: 创建第八部分（工具链）

Wave 4 (示例和脚本):
├── Task 11: 创建第九部分（项目示例）
├── Task 12: 创建 scripts/ 工具脚本
└── Task 13: 验证和索引更新
```

---

## TODOs

- [ ] 1. 创建目录结构

  **What to do**:
  - 在 `/Volumes/LiSSD/AI_Learn/` 下创建 `spec-coding-methodology/` 目录
  - 创建子目录结构：01-overview/ 到 09-examples/ 和 scripts/
  
  **Acceptance Criteria**:
  - [ ] 目录结构完整存在
  - [ ] 使用 `ls -la` 验证
  
  **Commit**: NO（与其他任务一起提交）

- [ ] 2. 创建主 README.md

  **What to do**:
  - 创建项目总览文档
  - 包含导航链接到各章节
  - 快速开始指南
  
  **References**:
  - 参考草稿第一部分和第三部分
  
  **Acceptance Criteria**:
  - [ ] README.md 存在且包含完整导航
  - [ ] 使用 `head -50` 验证内容
  
  **Commit**: YES
  - Message: `docs: add main README with navigation`
  - Files: `README.md`

- [ ] 3. 创建 01-overview/（宏观视角）

  **What to do**:
  - 创建 `01-overview/README.md`
  - 内容：Spec Coding 定义、Harness Engineering 定义、两者关系
  - 包含实际案例（OpenAI Codex、Stripe、Vercel 等）
  
  **References**:
  - 草稿第一部分和第二部分
  
  **Acceptance Criteria**:
  - [ ] 文件创建成功
  - [ ] 包含所有6个工程案例
  
  **Commit**: YES
  - Message: `docs(overview): add spec coding and harness engineering overview`

- [ ] 4. 创建 02-framework/（方法论框架）

  **What to do**:
  - 创建 `02-framework/README.md`
  - 金字塔三层结构图解
  - Four Pillars 详解
  - MECE 五阶段方法论总览
  
  **References**:
  - 草稿第三部分和第四部分
  
  **Acceptance Criteria**:
  - [ ] 包含金字塔结构图
  - [ ] Four Pillars 完整阐述
  
  **Commit**: YES
  - Message: `docs(framework): add methodology framework with four pillars`

- [ ] 5. 创建 03-phase-define/（需求定义阶段）

  **What to do**:
  - 创建 `03-phase-define/README.md`
  - GWT 用户故事模板
  - 需求 ID 系统规范
  - 约束清单模板
  - 电商订单系统完整示例（YAML格式）
  
  **Acceptance Criteria**:
  - [ ] 包含完整的示例代码
  - [ ] 模板可直接复制使用
  
  **Commit**: YES
  - Message: `docs(phase-define): add requirements definition phase with examples`

- [ ] 6. 创建 04-phase-design/（规范设计阶段）

  **What to do**:
  - 创建 `04-phase-design/README.md`
  - OpenAPI/TypeSpec API-First 设计
  - ADR 架构决策记录模板
  - 领域模型图（PlantUML）
  - 完整 Spec 文档结构示例
  
  **Acceptance Criteria**:
  - [ ] 包含 openapi.yaml 示例
  - [ ] 包含 ADR 模板
  
  **Commit**: YES
  - Message: `docs(phase-design): add specification design phase`

- [ ] 7. 创建 05-phase-decompose/（任务分解阶段）

  **What to do**:
  - 创建 `05-phase-decompose/README.md`
  - 任务分解 YAML 模板
  - 依赖图可视化（Mermaid）
  - 并行任务识别方法
  - Stripe Minions 任务分解示例
  
  **Acceptance Criteria**:
  - [ ] 包含 Gantt 图示例
  - [ ] 拓扑排序伪代码
  
  **Commit**: YES
  - Message: `docs(phase-decompose): add task decomposition phase`

- [ ] 8. 创建 06-phase-develop/（编码实现阶段）

  **What to do**:
  - 创建 `06-phase-develop/README.md`
  - AI 代码生成流程图
  - Harness 配置文件示例（YAML）
  - 代码注释规范（Spec 追溯）
  - 完整 AI 辅助编码会话示例
  
  **Acceptance Criteria**:
  - [ ] harness.yaml 配置完整
  - [ ] Go 代码示例包含 @require 标签
  
  **Commit**: YES
  - Message: `docs(phase-develop): add development phase with harness config`

- [ ] 9. 创建 07-phase-deliver/（验证部署阶段）

  **What to do**:
  - 创建 `07-phase-deliver/README.md`
  - 验证矩阵表格
  - 蓝绿部署配置
  - 持续评估管道代码（Python）
  - CI/CD 工作流示例
  
  **Acceptance Criteria**:
  - [ ] 验证矩阵完整
  - [ ] GitHub Actions workflow 可用
  
  **Commit**: YES
  - Message: `docs(phase-deliver): add delivery phase with CI/CD examples`

- [ ] 10. 创建 08-tools/（工具链和检查清单）

  **What to do**:
  - 创建 `08-tools/README.md`
  - 工具推荐表格（Spec定义、AI生成、Harness、验证）
  - 实践检查清单（项目启动、代码提交、生产发布）
  - 常见陷阱与对策
  
  **Acceptance Criteria**:
  - [ ] 所有检查清单可用
  - [ ] 陷阱和对策完整
  
  **Commit**: YES
  - Message: `docs(tools): add tools, checklists and anti-patterns`

- [ ] 11. 创建 09-examples/（完整项目示例）

  **What to do**:
  - 创建 `09-examples/` 目录
  - **C++ 任务队列 + 线程池系统** 完整示例（类似 iOS GCD）
    - specs/ 目录（requirements/、architecture/、interface/）
    - src/ 目录（frontend/、backend/、threadpool/）
    - tests/ 目录（unit/、integration/）
    - CMakeLists.txt、harness.yaml
  
  **系统架构设计**:
  
  1. **Frontend API（对外接口）**:
     - `TaskQueue` 类：提供 sync/async/after/wait/notify 接口
     - `TaskGroup` 类：任务组管理
     - 队列类型：SerialQueue、ConcurrentQueue、ParallelQueue
  
  2. **Backend Implementation（后端实现）**:
     - `IQueueImpl` 基类：队列实现接口
     - `SerialQueueImpl`：串行队列实现（独占线程）
     - `ConcurrentQueueImpl`：串行并行队列（多线程执行但任务有序）
     - `GroupImpl`：任务组实现
  
  3. **Task Operator（任务操作符）**:
     - `TaskOperator` 基类：任务操作基类
     - `TaskBarrierOperator`：同步屏障操作
     - `TaskDelayOperator`：延时操作
     - `ConsumableOperator`：可消费任务操作
  
  4. **Thread Pool（线程池）**:
     - `IThreadPool` 基类：线程池接口
     - `ConcurrencyThreadPool`：并行线程池
     - `SerialThreadPool`：串行独占线程池（如 GLES 渲染专用）
     - `WorkThread`：具体执行线程
  
  5. **队列类型分类**:
     - **Type 1 - 串行独占队列**: 一个队列绑定一条专用线程
     - **Type 2 - 串行并行队列**: 任务有序，但可由多条线程执行
     - **Type 3 - 并行队列**: 多任务分发到多线程执行
  
  **Spec Coding 示例结构**:
  
  ```
  09-examples/taskqueue-threadpool/
  ├── specs/
  │   ├── requirements/
  │   │   ├── FR-001-task-execution.md      # 任务执行需求
  │   │   ├── FR-002-queue-types.md         # 队列类型需求
  │   │   ├── FR-003-thread-pool.md         # 线程池需求
  │   │   ├── FR-004-task-group.md          # 任务组需求
  │   │   └── NFR-001-performance.md        # 性能需求
  │   ├── architecture/
  │   │   ├── ADR-001-class-hierarchy.md    # 类层次架构决策
  │   │   ├── ADR-002-queue-impl-strategy.md # 队列实现策略
  │   │   └── ADR-003-thread-scheduling.md   # 线程调度策略
  │   └── interface/
  │       ├── TaskQueue.spec.yaml           # 接口规范
  │       └── TaskGroup.spec.yaml
  ├── src/
  │   ├── frontend/                         # @require FR-001
  │   │   ├── TaskQueue.h/.cpp
  │   │   ├── TaskGroup.h/.cpp
  │   │   └── QueueFactory.h/.cpp
  │   ├── backend/                          # @require FR-002
  │   │   ├── IQueueImpl.h
  │   │   ├── SerialQueueImpl.h/.cpp
  │   │   ├── ConcurrentQueueImpl.h/.cpp
  │   │   └── GroupImpl.h/.cpp
  │   ├── operator/                         # @require FR-001
  │   │   ├── TaskOperator.h
  │   │   ├── TaskBarrierOperator.h/.cpp
  │   │   ├── TaskDelayOperator.h/.cpp
  │   │   └── ConsumableOperator.h/.cpp
  │   └── threadpool/                       # @require FR-003
  │       ├── IThreadPool.h
  │       ├── ConcurrencyThreadPool.h/.cpp
  │       ├── SerialThreadPool.h/.cpp
  │       └── WorkThread.h/.cpp
  ├── tests/
  │   ├── unit/
  │   │   ├── test_task_queue.cpp
  │   │   ├── test_task_group.cpp
  │   │   ├── test_operators.cpp
  │   │   └── test_thread_pool.cpp
  │   └── integration/
  │       ├── test_concurrent_execution.cpp
  │       └── test_performance.cpp
  ├── CMakeLists.txt
  └── harness.yaml                          # Harness 配置
  ```
  
  **Acceptance Criteria**:
  - [ ] 目录结构完整
  - [ ] 包含完整的类层次代码（h/.cpp）
  - [ ] Spec 文件可追溯（包含 @require 标签）
  - [ ] CMake 配置可编译
  - [ ] 包含测试用例
  
  **Commit**: YES
  - Message: `docs(examples): add C++ task queue and thread pool example with full specs`

- [ ] 12. 创建 scripts/（工具脚本）

  **What to do**:
  - 创建 `scripts/` 目录
  - check_traceability.py：检查代码 @require 标签
  - generate_task_graph.py：生成任务依赖图
  - validate_spec.py：验证 Spec 完整性
  - setup_harness.py：初始化 Harness 配置
  
  **Acceptance Criteria**:
  - [ ] 所有脚本可执行
  - [ ] 脚本包含帮助信息
  
  **Commit**: YES
  - Message: `feat(scripts): add utility scripts for spec coding`

- [ ] 13. 最终验证和索引更新

  **What to do**:
  - 验证所有文件存在
  - 更新主 README 索引链接
  - 检查代码语法
  - 统计文档字数和代码行数
  
  **Acceptance Criteria**:
  - [ ] 所有文件存在
  - [ ] 主 README 链接有效
  - [ ] 统计信息完整
  
  **Commit**: YES
  - Message: `docs: finalize documentation and update index`

---

## Final Verification Wave

- [ ] F1. 文件完整性检查
  - 验证所有 9 个章节 + scripts 目录存在
  - 验证主 README 导航完整
  
- [ ] F2. 代码质量检查
  - 所有 YAML 文件语法正确
  - 所有 Python 脚本可解析
  - 所有 Markdown 文件渲染正常

- [ ] F3. 统计汇报
  - 文档总字数
  - 代码示例行数
  - 脚本文件数量

---

## Commit Strategy

每个任务完成后提交，使用 conventional commits 格式：
- `docs(scope): description` - 文档更新
- `feat(scripts): description` - 脚本添加
- `docs: finalize documentation` - 最终提交

---

## Success Criteria

### Verification Commands
```bash
# 验证目录结构
ls -la /Volumes/LiSSD/AI_Learn/spec-coding-methodology/

# 统计文件数量
find /Volumes/LiSSD/AI_Learn/spec-coding-methodology/ -type f | wc -l

# 验证代码语法
python -m py_compile scripts/*.py

# 验证 YAML 语法
python -c "import yaml; yaml.safe_load(open('09-examples/specs/openapi.yaml'))"
```

### Final Checklist
- [ ] 所有 13 个任务完成
- [ ] 目录结构完整
- [ ] 代码示例可运行
- [ ] 脚本可执行
- [ ] 主 README 索引完整

---

## Appendix A: C++ TaskQueue + ThreadPool Example 详细设计

本附录详细描述 09-examples/taskqueue-threadpool/ 的 Spec Coding 实现流程，展示如何将方法论应用于实际 C++ 项目。

### A.1 Phase 1: 需求定义 (Define)

#### FR-001: 任务执行基础功能
```yaml
# specs/requirements/FR-001-task-execution.md
id: FR-001
title: 任务执行基础功能
description: 系统必须支持同步和异步执行任务

gwt: |
  Scenario: 异步执行任务
    Given 任务队列已创建
    When 调用 async() 提交任务
    Then 任务在后台执行
    And 调用者可继续执行而不等待

  Scenario: 同步执行任务
    Given 任务队列已创建
    When 调用 sync() 提交任务
    Then 任务执行完成
    And 调用者阻塞直到任务完成

acceptance_criteria:
  - async() 必须立即返回
  - sync() 必须等待任务完成
  - 任务必须是可调用对象（std::function）
  - 支持任务返回值获取

constraints:
  - 最小延迟开销 < 10μs
  - 支持 C++17 及以上
```

#### FR-002: 队列类型支持
```yaml
# specs/requirements/FR-002-queue-types.md
id: FR-002
title: 队列类型支持
description: 支持三种队列类型满足不同并发需求

gwt: |
  Scenario: 串行独占队列
    Given 创建 SerialQueue
    When 提交多个任务
    Then 任务按提交顺序执行
    And 所有任务在同一线程执行

  Scenario: 串行并行队列
    Given 创建 ConcurrentQueue
    When 提交多个任务
    Then 任务按提交顺序执行
    And 任务可由不同线程执行

  Scenario: 并行队列
    Given 创建 ParallelQueue
    When 提交多个任务
    Then 任务可并行执行
    And 不保证执行顺序
```

#### FR-003: 线程池管理
```yaml
# specs/requirements/FR-003-thread-pool.md
id: FR-003
title: 线程池管理
description: 高效管理线程生命周期和任务调度

gwt: |
  Scenario: 并发线程池
    Given 创建 ConcurrencyThreadPool
    When 提交大量任务
    Then 任务分发到多个工作线程
    And 线程数根据负载动态调整

  Scenario: 串行线程池
    Given 创建 SerialThreadPool
    When 创建多个串行队列
    Then 每个队列绑定独立线程
    And 线程专用于该队列

acceptance_criteria:
  - 支持线程数动态调整
  - 支持优雅关闭（等待任务完成）
  - 支持紧急关闭（立即终止）
  - 线程命名便于调试
```

#### FR-004: 任务组管理
```yaml
# specs/requirements/FR-004-task-group.md
id: FR-004
title: 任务组管理
description: 支持将多个任务组织为组进行统一管理

gwt: |
  Scenario: 任务组同步
    Given 创建 TaskGroup
    And 向组内添加多个任务
    When 调用 wait() 等待组内所有任务
    Then 阻塞直到所有任务完成

  Scenario: 任务组通知
    Given 创建 TaskGroup
    And 设置完成回调
    When 组内所有任务完成
    Then 触发完成回调
```

### A.2 Phase 2: 规范设计 (Design)

#### ADR-001: 类层次架构决策
```markdown
# ADR-001: 类层次架构设计

## Status
Accepted (2024-03-15)

## Context
需要设计清晰的类层次结构，分离：
1. 对外 API（Frontend）
2. 后端实现（Backend）
3. 线程池（ThreadPool）

## Decision
采用三层架构：

```
Frontend (TaskQueue, TaskGroup)
    │
    ▼
TaskOperator (中间层，封装操作)
    │
    ▼
Backend (IQueueImpl 实现)
    │
    ▼
ThreadPool (IThreadPool 实现)
```

## Rationale
- Frontend 提供简洁 API，隐藏复杂性
- TaskOperator 作为中间层，支持扩展操作类型
- Backend 负责队列逻辑
- ThreadPool 负责线程管理

## Consequences
### Positive
- 关注点分离
- 易于测试（可 Mock 各层）
- 支持新队列类型而不改 API

### Negative
- 增加抽象层次
- 性能可能有轻微影响（通过内联缓解）

## Compliance
- 符合 FR-001（异步/同步执行）
- 符合 FR-002（队列类型）
- 符合 NFR-001（性能要求）
```

#### Interface Specification (YAML)
```yaml
# specs/interface/TaskQueue.spec.yaml
interface:
  name: TaskQueue
  description: 任务队列对外接口
  
  methods:
    - name: async
      signature: "template<typename F> auto async(F&& f) -> TaskFuture"
      description: 异步执行任务
      requirement_ref: FR-001
      preconditions:
        - 队列未关闭
      postconditions:
        - 任务已提交到队列
        - 返回 TaskFuture 可用于获取结果
      
    - name: sync
      signature: "template<typename F> auto sync(F&& f) -> decltype(f())"
      description: 同步执行任务
      requirement_ref: FR-001
      preconditions:
        - 队列未关闭
      postconditions:
        - 任务已执行完成
        - 返回任务执行结果
      
    - name: after
      signature: "template<typename F> auto after(Duration d, F&& f) -> TaskFuture"
      description: 延时执行任务
      requirement_ref: FR-001
      parameters:
        - name: d
          type: std::chrono::duration
          description: 延迟时间
      
    - name: wait
      signature: "void wait()"
      description: 等待所有任务完成
      requirement_ref: FR-001

  types:
    - name: QueueType
      definition: enum class QueueType { Serial, Concurrent, Parallel }
      requirement_ref: FR-002
```

### A.3 Phase 3: 任务分解 (Decompose)

```yaml
# tasks/task-breakdown.yaml
tasks:
  - id: T-001
    title: 实现 Frontend API 基础类
    description: TaskQueue, TaskGroup 类实现
    requirement_ref: FR-001
    dependencies: []
    estimated_hours: 8
    files:
      - src/frontend/TaskQueue.h
      - src/frontend/TaskQueue.cpp
      - src/frontend/TaskGroup.h
      - src/frontend/TaskGroup.cpp

  - id: T-002
    title: 实现 TaskOperator 基类
    description: 任务操作符基类及派生类
    requirement_ref: FR-001
    dependencies: [T-001]
    estimated_hours: 6
    files:
      - src/operator/TaskOperator.h
      - src/operator/TaskBarrierOperator.h/cpp
      - src/operator/TaskDelayOperator.h/cpp
      - src/operator/ConsumableOperator.h/cpp

  - id: T-003
    title: 实现 Backend 队列接口
    description: IQueueImpl 及派生实现
    requirement_ref: FR-002
    dependencies: [T-002]
    estimated_hours: 12
    files:
      - src/backend/IQueueImpl.h
      - src/backend/SerialQueueImpl.h/cpp
      - src/backend/ConcurrentQueueImpl.h/cpp
      - src/backend/GroupImpl.h/cpp

  - id: T-004
    title: 实现 Thread Pool
    description: IThreadPool 及派生实现
    requirement_ref: FR-003
    dependencies: [T-003]
    estimated_hours: 10
    files:
      - src/threadpool/IThreadPool.h
      - src/threadpool/ConcurrencyThreadPool.h/cpp
      - src/threadpool/SerialThreadPool.h/cpp
      - src/threadpool/WorkThread.h/cpp

  - id: T-005
    title: 单元测试
    description: 核心功能单元测试
    requirement_ref: FR-001, FR-002, FR-003, FR-004
    dependencies: [T-004]
    estimated_hours: 8
    files:
      - tests/unit/test_task_queue.cpp
      - tests/unit/test_task_group.cpp
      - tests/unit/test_operators.cpp
      - tests/unit/test_thread_pool.cpp

  - id: T-006
    title: 集成测试和性能测试
    description: 并发场景和性能基准测试
    requirement_ref: NFR-001
    dependencies: [T-005]
    estimated_hours: 6
    files:
      - tests/integration/test_concurrent_execution.cpp
      - tests/integration/test_performance.cpp
```

### A.4 Phase 4: 编码实现 (Develop)

#### Frontend API 示例 (with Spec Tags)
```cpp
// src/frontend/TaskQueue.h
// @require FR-001
// @require FR-002
// @adr ADR-001

#pragma once
#include <functional>
#include <future>
#include <memory>
#include <chrono>

namespace taskqueue {

// Forward declarations
class IQueueImpl;
class TaskOperator;

/**
 * @brief Task execution queue with support for async/sync operations
 * 
 * Requirements:
 *   - FR-001: Supports async() and sync() task execution
 *   - FR-002: Supports Serial, Concurrent, and Parallel queue types
 * 
 * Architecture:
 *   - See ADR-001 for class hierarchy design
 *   - Delegates to IQueueImpl for actual execution
 */
class TaskQueue {
public:
    enum class Type {
        Serial,      ///< @require FR-002: Exclusive thread per queue
        Concurrent,  ///< @require FR-002: Ordered execution, multiple threads
        Parallel     ///< @require FR-002: Unordered parallel execution
    };

    explicit TaskQueue(Type type = Type::Concurrent);
    ~TaskQueue();

    // Non-copyable, movable
    TaskQueue(const TaskQueue&) = delete;
    TaskQueue& operator=(const TaskQueue&) = delete;
    TaskQueue(TaskQueue&&) noexcept;
    TaskQueue& operator=(TaskQueue&&) noexcept;

    /**
     * @brief Execute task asynchronously
     * @require FR-001
     * @param f Callable object to execute
     * @return Future for retrieving result
     */
    template<typename F>
    auto async(F&& f) -> std::future<std::invoke_result_t<F>>;

    /**
     * @brief Execute task synchronously
     * @require FR-001
     * @param f Callable object to execute
     * @return Result of task execution
     */
    template<typename F>
    auto sync(F&& f) -> std::invoke_result_t<F>;

    /**
     * @brief Execute task after delay
     * @require FR-001
     * @param delay Time to wait before execution
     * @param f Callable object to execute
     * @return Future for retrieving result
     */
    template<typename Rep, typename Period, typename F>
    auto after(std::chrono::duration<Rep, Period> delay, F&& f) 
        -> std::future<std::invoke_result_t<F>>;

    /**
     * @brief Wait for all pending tasks to complete
     * @require FR-001
     */
    void wait();

private:
    std::unique_ptr<IQueueImpl> impl_;
};

} // namespace taskqueue
```

#### Harness Configuration
```yaml
# harness.yaml
harness:
  name: taskqueue-threadpool
  version: 1.0.0
  
  context:
    max_tokens: 10000
    include_files:
      - specs/**/*.yaml
      - specs/**/*.md
      - src/**/*.h
    exclude_patterns:
      - "*.cpp"  # Implementation files generated by AI
      - "build/"
      - "tests/*_test.cpp"
  
  verification:
    steps:
      - name: cmake_configure
        command: "cmake -B build -S ."
        must_pass: true
        
      - name: compile
        command: "cmake --build build -j"
        must_pass: true
        
      - name: unit_tests
        command: "cd build && ctest --output-on-failure"
        must_pass: true
        
      - name: check_traceability
        command: "python scripts/check_requirement_tags.py src/"
        must_pass: true
  
  cost:
    max_tokens_per_task: 50000
    max_api_calls_per_task: 20
```

### A.5 Phase 5: 验证部署 (Deliver)

#### CI/CD Pipeline
```yaml
# .github/workflows/taskqueue-ci.yml
name: TaskQueue CI

on: [push, pull_request]

jobs:
  spec-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate Specs
        run: |
          python scripts/validate_spec.py specs/
      
      - name: Check Traceability
        run: |
          python scripts/check_requirement_tags.py src/

  build-and-test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        compiler: [gcc, clang]
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure
        run: cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
      
      - name: Build
        run: cmake --build build -j
      
      - name: Test
        run: cd build && ctest --output-on-failure
      
      - name: Performance Test
        run: ./build/tests/performance_test
```

### A.6 关键设计决策摘要

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 智能指针 | unique_ptr | 明确所有权，防止内存泄漏 |
| 线程同步 | condition_variable + mutex | 标准且高效 |
| 任务存储 | deque | 两端操作 O(1) |
| 线程池策略 | work-stealing | 负载均衡 |
| C++ 标准 | C++17 | 平衡特性与兼容性 |

### A.7 性能指标 (NFR-001)

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 任务提交延迟 | < 10μs | benchmarks/latency.cpp |
| 吞吐量 | > 1M tasks/sec | benchmarks/throughput.cpp |
| 内存开销 | < 1KB per thread | valgrind massif |
| 上下文切换 | < 1μs | perf stat |

---

## Appendix B: 脚本功能说明

### check_traceability.py
检查源码中的 @require 和 @adr 标签，确保：
1. 所有代码文件都有对应的 requirement_ref
2. 引用的需求 ID 存在于 specs/ 目录
3. 引用的 ADR 存在于 specs/architecture/

### validate_spec.py
验证 Spec 文件格式：
1. YAML 语法正确
2. 必需的字段存在（id, title, description）
3. 需求 ID 格式正确

### generate_task_graph.py
根据 tasks/*.yaml 生成：
1. Mermaid 甘特图
2. 依赖关系图
3. 关键路径分析

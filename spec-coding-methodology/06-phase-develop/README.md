# Phase 4: 编码实现 (Develop)

## 目标

在 Harness 的约束和验证下，**可靠地将设计转化为代码**。

**关键产出**:
- 可运行的代码
- 自动化测试
- 技术文档
- 代码审查记录

---

## 可执行方法

### 方法 1: AI 代码生成流程

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  1. 加载 Spec │ ──►│  2. 生成提示 │ ──►│  3. AI 生成  │ ──►│  4. 验证循环 │
│              │    │              │    │              │    │              │
│  - 需求文档   │    │  - 系统提示   │    │  - 代码草案   │    │  - 编译检查   │
│  - ADR       │    │  - 上下文     │    │  - 测试草案   │    │  - 单元测试   │
│  - 接口规范   │    │  - 任务描述   │    │  - 文档草案   │    │  - 类型检查   │
│  - 现有代码   │    │              │    │              │    │  - Lint      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                     │
                                                                     ▼
                                                              ┌──────────────┐
                                                              │  5. 人工审查  │
                                                              │  6. 提交代码  │
                                                              └──────────────┘
```

---

### 方法 2: Harness 配置

**harness.yaml**:
```yaml
harness:
  name: taskqueue-project
  version: 1.0.0
  
  # 上下文工程
  context:
    max_tokens: 10000
    include_files:
      - specs/requirements/*.md
      - specs/architecture/*.md
      - specs/api/*.yaml
      - src/types/*.h
    exclude_patterns:
      - "*_test.cpp"
      - "build/"
      - ".git/"
    
  # 工具编排
  tools:
    - name: file_read
      description: 读取文件内容
    - name: file_write
      description: 写入文件内容
    - name: test_run
      description: 运行测试
    - name: lint_check
      description: 代码风格检查
  
  # 验证循环
  verification:
    steps:
      - name: cmake_configure
        command: "cmake -B build -S . -DCMAKE_BUILD_TYPE=Release"
        must_pass: true
        timeout: 60
        
      - name: compile
        command: "cmake --build build -j$(nproc)"
        must_pass: true
        timeout: 300
        
      - name: unit_tests
        command: "cd build && ctest --output-on-failure"
        must_pass: true
        min_coverage: 80
        
      - name: lint
        command: "clang-tidy src/**/*.cpp"
        must_pass: true
        
      - name: traceability_check
        command: "python scripts/check_requirement_tags.py src/"
        must_pass: true
  
  # 成本控制
  cost:
    max_tokens_per_task: 50000
    max_api_calls_per_task: 20
    alert_threshold: 0.8
    
    budgets:
      simple_task:
        max_tokens: 10000
      complex_task:
        max_tokens: 30000
        max_api_calls: 15
  
  # 可观测性
  observability:
    log_level: debug
    trace_format: structured
    output_dir: ./logs/harness
    
    metrics:
      - tokens_used
      - api_calls
      - duration_ms
      - verification_pass_rate
      - error_count
```

---

### 方法 3: 代码注释规范（Spec 追溯）

**文件头注释**:
```cpp
/**
 * @file TaskQueue.h
 * @brief Task execution queue with async/sync support
 * 
 * Requirements:
 *   - @require FR-001: Task execution functionality
 *   - @require FR-002: Queue type support
 * 
 * Architecture:
 *   - @adr ADR-001: Class hierarchy design
 *   - @adr ADR-002: Queue implementation strategy
 * 
 * Dependencies:
 *   - src/backend/IQueueImpl.h
 *   - src/operator/TaskOperator.h
 * 
 * Tests:
 *   - tests/unit/test_task_queue.cpp
 *   - tests/integration/test_concurrent_execution.cpp
 * 
 * @author Dev Team
 * @date 2024-03-15
 */
```

**类注释**:
```cpp
/**
 * @class TaskQueue
 * @brief High-level API for task execution
 * 
 * @require FR-001
 * @require FR-002
 * @adr ADR-001
 * 
 * This class provides a thread-safe interface for submitting tasks
 * to be executed asynchronously or synchronously.
 * 
 * Thread Safety: All methods are thread-safe.
 * 
 * Example:
 * @code
 *   TaskQueue queue(TaskQueue::Type::Concurrent);
 *   auto future = queue.async([]() { return 42; });
 *   int result = future.get();
 * @endcode
 */
class TaskQueue {
    // ...
};
```

**方法注释**:
```cpp
/**
 * @brief Execute a task asynchronously
 * 
 * @require FR-001
 * 
 * Submits the task for asynchronous execution and returns immediately
 * with a future that can be used to retrieve the result.
 * 
 * @tparam F Callable type
 * @param f Task to execute
 * @return TaskFuture<std::invoke_result_t<F>> Future for result retrieval
 * 
 * @pre Queue is not shut down
 * @post Task is queued for execution
 * 
 * @throws QueueClosedException if queue has been shut down
 * @throws std::bad_alloc if memory allocation fails
 * 
 * @complexity O(1) amortized
 * @threadsafe Yes
 * 
 * @see sync() for synchronous execution
 * @see after() for delayed execution
 */
template<typename F>
auto async(F&& f) -> TaskFuture<std::invoke_result_t<F>>;
```

---

### 方法 4: 代码审查清单

**自我审查** (提交前):
- [ ] 代码编译无警告 (`-Wall -Werror`)
- [ ] 所有需求都有 `@require` 标签
- [ ] 单元测试覆盖率 > 80%
- [ ] 文档注释完整
- [ ] 无内存泄漏 (通过 valgrind)
- [ ] 代码符合项目风格 (通过 clang-format)

**同行审查**:
- [ ] 架构决策是否被正确实现
- [ ] 边界情况是否处理
- [ ] 错误处理是否完整
- [ ] 性能考虑是否充分
- [ ] 命名是否清晰

---

## AI 辅助编码最佳实践

### 1. 上下文准备

**加载必要文件**:
```
System: Loading context for task T-003
- specs/requirements/FR-002-queue-types.md
- specs/architecture/ADR-002-queue-impl-strategy.md
- src/backend/IQueueImpl.h
- src/operator/TaskOperator.h
```

### 2. 提示工程

**结构化 Prompt**:
```markdown
## Task
实现 SerialQueueImpl 类

## Requirements
- @require FR-002: 串行队列实现

## Architecture
- 继承 IQueueImpl 接口
- 每个队列绑定一个专用线程
- 使用 thread_local 任务队列

## Interface
```cpp
class SerialQueueImpl : public IQueueImpl {
public:
    void submit(std::unique_ptr<TaskOperator> task) override;
    void run() override;
    void stop() override;
private:
    // TODO: implementation
};
```

## Constraints
- C++17
- Thread-safe
- Exception-safe
- No busy waiting

## Deliverables
- src/backend/SerialQueueImpl.h
- src/backend/SerialQueueImpl.cpp
- Tests in tests/unit/test_serial_queue.cpp
```

### 3. 验证驱动

**先生成测试，后生成实现**:
```
Step 1: AI generates test cases based on spec
Step 2: AI implements code to pass tests
Step 3: Harness runs tests to verify
Step 4: If tests fail, AI fixes code
Step 5: Repeat until all tests pass
```

---

## 代码提交规范

**提交信息格式**:
```
{type}({scope}): {subject}

{body}

Refs: {FR-XXX}, {ADR-XXX}
```

**示例**:
```
feat(backend): implement SerialQueueImpl

- Add SerialQueueImpl class inheriting IQueueImpl
- Implement task submission with thread-safe queue
- Implement dedicated thread management
- Add graceful shutdown support

- All methods are thread-safe
- Uses condition_variable for efficient waiting
- Exception handling for task execution

Refs: FR-002, ADR-002
Test: tests/unit/test_serial_queue.cpp
```

**Type 分类**:
- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 重构
- `test`: 测试
- `docs`: 文档
- `perf`: 性能优化
- `chore`: 构建/工具

---

## 检查清单

- [ ] 代码有完整的文档注释
- [ ] 所有需求都有 `@require` 标签
- [ ] 通过 Harness 所有验证步骤
- [ ] 单元测试覆盖率达标
- [ ] 代码审查通过
- [ ] 提交信息规范
- [ ] 与 Spec 保持同步

---

## 下一章

→ [继续阅读: 07-phase-deliver - 验证部署阶段](../07-phase-deliver/README.md)

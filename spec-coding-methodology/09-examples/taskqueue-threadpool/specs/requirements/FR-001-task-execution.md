# FR-001: 任务执行基础功能

## Metadata

- **ID**: FR-001
- **Title**: 任务执行基础功能
- **Type**: Functional Requirement
- **Priority**: P0 (Critical)
- **Status**: Draft
- **Created**: 2024-03-15
- **Author**: System Architect

---

## Description

系统必须支持同步和异步执行任务的完整生命周期管理，包括任务的提交、执行、完成和结果获取。

---

## GWT Specifications

### Scenario 1: 异步执行任务

```gherkin
Given 任务队列已创建且处于活跃状态
When 调用 async() 提交一个 Lambda 函数
Then 任务被放入队列
And 函数立即返回一个 TaskFuture 对象
And 调用者可继续执行而不阻塞
And 任务在后台线程执行
```

**验收标准**:
- [ ] async() 返回时间 < 10μs
- [ ] 返回的 TaskFuture 可用于获取结果
- [ ] 任务最终被执行（至多延迟 1ms）

### Scenario 2: 同步执行任务

```gherkin
Given 任务队列已创建且处于活跃状态
When 调用 sync() 提交一个 Lambda 函数
Then 调用者线程阻塞
And 任务被立即执行
And 任务完成后返回执行结果
And 调用者继续执行
```

**验收标准**:
- [ ] sync() 阻塞直到任务完成
- [ ] 返回任务执行结果
- [ ] 异常被传播到调用者

### Scenario 3: 延时执行任务

```gherkin
Given 任务队列已创建
When 调用 after(delay, task) 提交延时任务
Then 任务在指定延迟后执行
And 函数立即返回 TaskFuture
And 在延迟期间任务处于等待状态
```

**验收标准**:
- [ ] 任务至少在指定延迟后执行
- [ ] 延迟精度误差 < 5%
- [ ] 支持取消未执行的延时任务

### Scenario 4: 等待所有任务完成

```gherkin
Given 队列中有多个待执行或执行中的任务
When 调用 wait() 方法
Then 阻塞直到所有已提交任务完成
And 包括异步、同步和延时任务
```

**验收标准**:
- [ ] 等待所有已提交任务
- [ ] 新提交的任务不影响当前 wait()
- [ ] 支持超时参数

---

## Interface Requirements

### Methods

#### `async(F&& f) -> TaskFuture<ReturnType>`

**Purpose**: 异步执行任务

**Parameters**:
- `f`: 可调用对象（Callable），支持 Lambda、函数指针、std::function

**Returns**:
- `TaskFuture<ReturnType>`: 用于获取异步任务结果的未来对象

**Preconditions**:
- 队列未关闭（not shutdown）
- 线程池处于活跃状态

**Postconditions**:
- 任务已提交到内部队列
- TaskFuture 已关联到该任务

**Error Handling**:
- 队列关闭时抛出 `QueueClosedException`
- 内存不足时抛出 `std::bad_alloc`

#### `sync(F&& f) -> ReturnType`

**Purpose**: 同步执行任务

**Parameters**:
- `f`: 可调用对象

**Returns**:
- `ReturnType`: 任务执行结果

**Preconditions**:
- 队列未关闭

**Postconditions**:
- 任务已执行完成
- 结果已返回

**Error Handling**:
- 任务异常传播到调用者
- 队列关闭时抛出异常

#### `after(Duration d, F&& f) -> TaskFuture<ReturnType>`

**Purpose**: 延时执行任务

**Parameters**:
- `d`: 延迟时间，`std::chrono::duration` 类型
- `f`: 可调用对象

**Returns**:
- `TaskFuture<ReturnType>`: 用于获取结果

**Preconditions**:
- 队列未关闭
- 延迟时间为正值

**Postconditions**:
- 任务已调度，将在延迟后执行

#### `wait()` 和 `wait_for(Duration)`

**Purpose**: 等待任务完成

**Parameters**:
- `timeout` (optional): 最大等待时间

**Returns**:
- `void` 或 `bool` (是否超时)

**Postconditions**:
- 调用返回时，所有已提交任务已完成

---

## Constraints

### 性能约束
- **任务提交延迟**: < 10μs (P99)
- **上下文切换**: < 1μs
- **内存分配**: 每个任务 < 256 bytes

### 技术约束
- **C++ 标准**: C++17 或更高
- **编译器**: GCC 9+, Clang 10+, MSVC 2019+
- **平台**: Linux, macOS, Windows

### 资源约束
- **线程数**: 可配置，默认硬件并发数
- **队列深度**: 默认无限制，可配置上限
- **内存**: 可配置最大内存使用

---

## Dependencies

### Requires
- [FR-002: 队列类型支持](FR-002-queue-types.md) - 需要队列实现作为基础
- [FR-003: 线程池管理](FR-003-thread-pool.md) - 需要线程池执行任务

### Required By
- [FR-004: 任务组管理](FR-004-task-group.md) - 任务组依赖基础任务执行

---

## Traceability

### Implementation References
- `src/frontend/TaskQueue.h` - 主要接口定义
- `src/frontend/TaskQueue.cpp` - 实现
- `src/operator/TaskOperator.h` - 任务操作基类
- `src/operator/ConsumableOperator.h` - 可消费任务实现

### Test References
- `tests/unit/test_task_queue.cpp` - 单元测试
- `tests/integration/test_concurrent_execution.cpp` - 并发测试

### Commit References
- Future commits should reference this requirement as `Refs: FR-001`

---

## Notes

### Design Considerations

1. **异常安全**: 所有操作必须提供强异常保证
2. **死锁避免**: 禁止在任务中调用 sync() 提交到同一队列
3. **返回值优化**: 支持移动语义，避免不必要拷贝

### Example Usage

```cpp
// @require FR-001
#include "frontend/TaskQueue.h"

using namespace taskqueue;

TaskQueue queue(TaskQueue::Type::Concurrent);

// Async execution
auto future = queue.async([]() {
    return compute_something();
});
int result = future.get();  // Wait and get result

// Sync execution
int result2 = queue.sync([]() {
    return compute_something_else();
});

// Delayed execution
auto delayed_future = queue.after(
    std::chrono::seconds(5),
    []() { return "delayed"; }
);

// Wait for all
queue.wait();
```

### Open Questions

1. 是否需要支持任务优先级？
2. 是否需要支持任务取消（已开始的任务）？
3. 是否需要支持任务超时自动取消？

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2024-03-15 | 0.1 | System Architect | Initial draft |

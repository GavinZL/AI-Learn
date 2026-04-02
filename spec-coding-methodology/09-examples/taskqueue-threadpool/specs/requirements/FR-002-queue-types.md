# FR-002: 队列类型支持

## Metadata

- **ID**: FR-002
- **Title**: 队列类型支持
- **Type**: Functional Requirement
- **Priority**: P0 (Critical)
- **Status**: Draft
- **Created**: 2024-03-15
- **Author**: System Architect

---

## Description

系统必须支持三种队列类型，以满足不同的并发执行需求：串行独占队列、串行并行队列和并行队列。

---

## GWT Specifications

### Scenario 1: 串行独占队列 (Serial Queue)

```gherkin
Given 创建一个 SerialQueue
When 提交多个任务 A、B、C
Then 任务按 A→B→C 顺序执行
And 所有任务在同一线程执行
And 任务之间无并发
```

**适用场景**:
- OpenGL/Vulkan 渲染（必须在同一线程）
- 文件 I/O 操作（避免竞争）
- 状态机执行（保证状态一致性）

**验收标准**:
- [ ] 任务严格按提交顺序执行
- [ ] 所有任务在同一物理线程
- [ ] 支持线程命名便于调试

### Scenario 2: 串行并行队列 (Concurrent Queue)

```gherkin
Given 创建一个 ConcurrentQueue
When 提交多个任务 A、B、C
Then 任务按 A→B→C 顺序开始执行
And 任务可由不同线程执行
And 任务可能重叠执行（B 在 A 完成前开始）
```

**适用场景**:
- 网络请求（有序发起，并行执行）
- 数据处理管道（有序但并行）
- 缓存更新（保证顺序，提高吞吐）

**验收标准**:
- [ ] 任务按提交顺序开始
- [ ] 多线程并行执行
- [ ] 任务完成顺序可能不同于提交顺序

### Scenario 3: 并行队列 (Parallel Queue)

```gherkin
Given 创建一个 ParallelQueue
When 提交多个任务 A、B、C
Then 任务可立即并行执行
And 不保证执行顺序
And 最大化并行度
```

**适用场景**:
- 独立计算任务
- 批量数据处理
- 并行算法

**验收标准**:
- [ ] 任务立即分配可用线程
- [ ] 最大化利用所有工作线程
- [ ] 执行顺序不确定

---

## Interface Requirements

### QueueType 枚举

```cpp
enum class QueueType {
    Serial,      ///< 串行独占队列
    Concurrent,  ///< 串行并行队列
    Parallel     ///< 并行队列
};
```

### TaskQueue 构造

```cpp
// 指定队列类型创建
TaskQueue queue(TaskQueue::Type::Serial);
TaskQueue queue(TaskQueue::Type::Concurrent);
TaskQueue queue(TaskQueue::Type::Parallel);

// 可选：命名队列（用于调试）
TaskQueue queue(TaskQueue::Type::Serial, "RenderQueue");
```

---

## Constraints

### 性能约束
- **SerialQueue 任务切换**: < 1μs
- **ConcurrentQueue 顺序保证**: 零额外开销
- **ParallelQueue 负载均衡**: 任务均匀分布

### 资源约束
- **SerialQueue**: 每个队列独占 1 个线程
- **ConcurrentQueue**: 共享线程池
- **ParallelQueue**: 共享线程池

---

## Dependencies

### Requires
- [FR-003: 线程池管理](FR-003-thread-pool.md)

### Required By
- [FR-001: 任务执行基础功能](FR-001-task-execution.md)

---

## Traceability

### Implementation References
- `src/backend/SerialQueueImpl.h` - 串行独占队列实现
- `src/backend/ConcurrentQueueImpl.h` - 串行并行队列实现
- `src/backend/ParallelQueueImpl.h` - 并行队列实现

### Test References
- `tests/unit/test_queue_types.cpp`

---

## Notes

### 设计考虑

**SerialQueue 实现要点**:
- 每个队列一个专用线程
- 使用 thread_local 存储队列状态
- 线程生命周期与队列绑定

**ConcurrentQueue 实现要点**:
- 全局队列保证提交顺序
- Ticket lock 或序号机制保证开始顺序
- 工作线程池共享

**ParallelQueue 实现要点**:
- Work-stealing 队列
- 无锁数据结构
- 最小化同步开销

### 示例代码

```cpp
// @require FR-002

// Serial queue for OpenGL rendering
TaskQueue render_queue(TaskQueue::Type::Serial, "RenderThread");
render_queue.async([]() { initialize_gl(); });
render_queue.async([]() { draw_frame(); });

// Concurrent queue for ordered network requests
TaskQueue net_queue(TaskQueue::Type::Concurrent);
for (auto& url : urls) {
    net_queue.async([url]() { download(url); });
}

// Parallel queue for batch processing
TaskQueue compute_queue(TaskQueue::Type::Parallel);
for (auto& data : dataset) {
    compute_queue.async([data]() { process(data); });
}
```

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2024-03-15 | 0.1 | System Architect | Initial draft |

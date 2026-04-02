# ADR-002: 队列实现策略

## Status

- **Status**: Accepted
- **Date**: 2024-03-15
- **Deciders**: System Architect, Performance Engineer

## Context

需要为三种队列类型（Serial、Concurrent、Parallel）选择合适的底层数据结构和同步机制。关键考虑：

1. SerialQueue 如何保证单线程执行？
2. ConcurrentQueue 如何保证顺序开始但并行执行？
3. ParallelQueue 如何最大化吞吐量？
4. 如何最小化锁竞争和内存分配？

## Decision

### SerialQueue - 专用线程 + thread_local 队列

```cpp
class SerialQueueImpl : public IQueueImpl {
private:
    std::thread dedicated_thread_;
    // 使用 thread_local 存储队列状态
    struct ThreadLocalQueue {
        std::deque<std::unique_ptr<TaskOperator>> tasks;
        std::mutex mutex;
        std::condition_variable cv;
    };
    ThreadLocalQueue queue_;
};
```

**策略**:
- 每个 SerialQueue 创建一个专用线程
- 使用 `std::condition_variable` 等待任务
- 无锁竞争（单线程访问队列）

### ConcurrentQueue - 全局队列 + Ticket Lock

```cpp
class ConcurrentQueueImpl : public IQueueImpl {
private:
    // 保证提交顺序
    std::queue<std::unique_ptr<TaskOperator>> submit_queue_;
    
    // Ticket 系统保证开始顺序
    std::atomic<uint64_t> next_ticket_{0};
    std::atomic<uint64_t> now_serving_{0};
    
    // 线程池共享
    ConcurrencyThreadPool& pool_;
};
```

**策略**:
- 使用 ticket lock 保证开始顺序
- 任务实际执行由线程池调度
- 完成顺序可能不同于开始顺序

### ParallelQueue - Work-Stealing 队列

```cpp
class ParallelQueueImpl : public IQueueImpl {
private:
    // 每个工作线程一个队列
    std::vector<std::unique_ptr<WorkStealingQueue>> local_queues_;
    
    // 全局队列用于溢出
    std::queue<std::unique_ptr<TaskOperator>> global_queue_;
};

// Work-Stealing Queue 实现
template<typename T>
class WorkStealingQueue {
    std::vector<T> buffer_;
    std::atomic<size_t> top_{0};
    std::atomic<size_t> bottom_{0};
public:
    void push(T item);
    std::optional<T> pop();      // Owner only
    std::optional<T> steal();     // Other threads
};
```

**策略**:
- 每个工作线程维护自己的双端队列
- Push/Pop 在队列底部（无锁）
- Steal 从队列顶部（需要 CAS）

## Consequences

### Positive

- **SerialQueue**: 零竞争，最小延迟
- **ConcurrentQueue**: 保证顺序，充分利用并行
- **ParallelQueue**: 最大化吞吐量，最小化同步

### Negative

- **SerialQueue**: 线程不能复用，资源利用率低
- **ConcurrentQueue**: Ticket lock 可能成为瓶颈
- **ParallelQueue**: 复杂度高，调试困难

## Performance Characteristics

| 队列类型 | 提交延迟 | 执行顺序 | 适用场景 |
|---------|---------|---------|---------|
| Serial | < 1μs | 严格有序 | 渲染、状态机 |
| Concurrent | < 2μs | 开始有序 | 网络请求、管道 |
| Parallel | < 1μs | 无序 | 计算密集型 |

## Alternatives Considered

### Alternative 1: 统一使用线程池
所有队列类型共享线程池。

**Rejected**: SerialQueue 难以保证严格单线程执行。

### Alternative 2: 所有队列使用专用线程
每个队列创建自己的线程。

**Rejected**: 资源浪费，无法支持大量队列。

## Compliance

- Satisfies [FR-002](FR-002-queue-types.md)
- Related to [ADR-003](ADR-003-thread-scheduling.md)

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2024-03-15 | 1.0 | Initial acceptance |

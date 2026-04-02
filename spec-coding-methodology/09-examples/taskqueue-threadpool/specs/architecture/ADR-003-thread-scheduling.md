# ADR-003: 线程调度策略

## Status

- **Status**: Accepted
- **Date**: 2024-03-15
- **Deciders**: System Architect, Performance Engineer

## Context

需要设计线程池的调度策略，以满足不同队列类型的需求：

1. ConcurrencyThreadPool 如何高效调度任务？
2. 如何实现动态线程数调整？
3. 空闲线程如何管理？
4. 如何保证负载均衡？

## Decision

### ConcurrencyThreadPool - Work-Stealing + 动态调整

```cpp
class ConcurrencyThreadPool : public IThreadPool {
private:
    // 工作线程
    std::vector<std::unique_ptr<WorkThread>> workers_;
    
    // 动态调整参数
    struct Config {
        size_t min_threads;
        size_t max_threads;
        std::chrono::milliseconds idle_timeout;
        double scale_up_threshold = 0.8;  // 80% 忙碌时扩容
        double scale_down_threshold = 0.3; // 30% 忙碌时缩容
    } config_;
    
    // 监控线程
    std::thread monitor_thread_;
    std::atomic<bool> running_{false};
};
```

**调度算法**:

1. **任务提交**:
   ```cpp
   void submit(std::function<void()> task) {
       // 1. 尝试推送到随机工作线程
       auto& worker = workers_[random() % workers_.size()];
       if (worker->try_push(task)) return;
       
       // 2. 失败则推送到全局队列
       global_queue_.push(task);
       
       // 3. 通知等待的线程
       cv_.notify_one();
       
       // 4. 检查是否需要扩容
       maybe_scale_up();
   }
   ```

2. **任务获取** (Work-Stealing):
   ```cpp
   std::optional<Task> WorkThread::get_task() {
       // 1. 先尝试自己的队列
       if (auto task = local_queue_.pop()) {
           return task;
       }
       
       // 2. 尝试全局队列
       if (auto task = pool_.global_queue_.try_pop()) {
           return task;
       }
       
       // 3. 尝试偷取其他线程的任务
       for (auto& other : pool_.workers_) {
           if (other.get() != this) {
               if (auto task = other->steal()) {
                   return task;
               }
           }
       }
       
       // 4. 无任务，等待
       return std::nullopt;
   }
   ```

3. **动态调整**:
   ```cpp
   void monitor_thread() {
       while (running_) {
           std::this_thread::sleep_for(std::chrono::seconds(5));
           
           double utilization = calculate_utilization();
           
           if (utilization > config_.scale_up_threshold && 
               workers_.size() < config_.max_threads) {
               add_worker();
           } else if (utilization < config_.scale_down_threshold && 
                      workers_.size() > config_.min_threads) {
               remove_idle_worker();
           }
       }
   }
   ```

### SerialThreadPool - 一对一绑定

```cpp
class SerialThreadPool : public IThreadPool {
private:
    // 每个队列一个线程，无共享
    std::thread thread_;
    std::queue<std::function<void()>> tasks_;
    std::mutex mutex_;
    std::condition_variable cv_;
    bool shutdown_ = false;
};
```

**策略**:
- 每个 SerialQueue 独占一个线程
- 简单的生产者-消费者模型
- 无负载均衡需求

## Consequences

### Positive

- **高吞吐量**: Work-stealing 最小化竞争
- **负载均衡**: 自动任务重新分配
- **弹性**: 动态调整适应负载变化
- **低延迟**: 无锁操作路径

### Negative

- **复杂性**: 实现复杂，调试困难
- **内存开销**: 每个线程维护自己的队列
- **调参**: 需要调整 scale up/down 阈值

## Configuration Recommendations

```cpp
// CPU 密集型任务
ConcurrencyPoolConfig cpu_config{
    .min_threads = std::thread::hardware_concurrency(),
    .max_threads = std::thread::hardware_concurrency(),
    .idle_timeout = std::chrono::minutes(5)
};

// IO 密集型任务
ConcurrencyPoolConfig io_config{
    .min_threads = 4,
    .max_threads = 64,
    .idle_timeout = std::chrono::seconds(30)
};
```

## Compliance

- Satisfies [FR-003](FR-003-thread-pool.md)
- Related to [ADR-002](ADR-002-queue-impl-strategy.md)

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2024-03-15 | 1.0 | Initial acceptance |

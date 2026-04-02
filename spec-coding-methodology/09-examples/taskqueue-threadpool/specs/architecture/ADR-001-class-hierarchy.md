# ADR-001: 类层次架构设计

## Status

- **Status**: Accepted
- **Date**: 2024-03-15
- **Deciders**: System Architect, Tech Lead

## Context

我们需要设计一个清晰的类层次结构来组织 TaskQueue 系统的各个组件。主要挑战：

1. 如何将 Frontend API 与 Backend 实现解耦？
2. 如何支持多种队列类型而不重复代码？
3. 如何设计中间层支持扩展操作（延时、屏障等）？
4. 如何与线程池集成？

## Decision

采用**四层架构**：

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Frontend API                                      │
│  - TaskQueue                                                │
│  - TaskGroup                                                │
│  职责: 提供简洁的公共接口，隐藏实现复杂性                      │
└───────────────────────────┬─────────────────────────────────┘
                            │ 使用
┌───────────────────────────▼─────────────────────────────────┐
│  Layer 2: Operator (中间层)                                  │
│  - TaskOperator (基类)                                       │
│  - TaskBarrierOperator                                       │
│  - TaskDelayOperator                                         │
│  - ConsumableOperator                                        │
│  职责: 封装任务操作，支持扩展和组合                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ 提交到
┌───────────────────────────▼─────────────────────────────────┐
│  Layer 3: Backend Implementation                             │
│  - IQueueImpl (接口)                                         │
│  - SerialQueueImpl                                           │
│  - ConcurrentQueueImpl                                       │
│  - ParallelQueueImpl                                         │
│  - GroupImpl                                                 │
│  职责: 实现具体队列逻辑，管理任务调度                          │
└───────────────────────────┬─────────────────────────────────┘
                            │ 使用
┌───────────────────────────▼─────────────────────────────────┐
│  Layer 4: Thread Pool                                        │
│  - IThreadPool (接口)                                        │
│  - ConcurrencyThreadPool                                     │
│  - SerialThreadPool                                          │
│  - WorkThread                                                │
│  职责: 管理线程生命周期，执行任务                             │
└─────────────────────────────────────────────────────────────┘
```

### 详细设计

**Layer 1 - Frontend**:
```cpp
class TaskQueue {
public:
    template<typename F> auto async(F&& f);
    template<typename F> auto sync(F&& f);
    // ...
private:
    std::unique_ptr<IQueueImpl> impl_;
};
```

**Layer 2 - Operator**:
```cpp
class TaskOperator {
public:
    virtual void execute() = 0;
    virtual void cancel() = 0;
    virtual ~TaskOperator() = default;
};

class TaskDelayOperator : public TaskOperator {
    std::chrono::time_point<std::chrono::steady_clock> when_;
    std::unique_ptr<TaskOperator> inner_;
public:
    void execute() override;
};
```

**Layer 3 - Backend**:
```cpp
class IQueueImpl {
public:
    virtual void submit(std::unique_ptr<TaskOperator> task) = 0;
    virtual void run() = 0;
    virtual void stop() = 0;
    virtual ~IQueueImpl() = default;
};
```

**Layer 4 - ThreadPool**:
```cpp
class IThreadPool {
public:
    virtual void submit(std::function<void()> task) = 0;
    virtual void shutdown() = 0;
    virtual ~IThreadPool() = default;
};
```

## Consequences

### Positive

- **关注点分离**: 每层职责清晰，易于理解和维护
- **可测试性**: 可以独立测试各层，Mock 依赖
- **可扩展性**: 新队列类型只需实现 IQueueImpl
- **灵活性**: 支持不同的线程池策略

### Negative

- **性能开销**: 额外的抽象层次可能带来轻微性能损失
  - 缓解: 使用内联函数和编译器优化
- **复杂性**: 初学者需要理解多层架构
  - 缓解: 完善的文档和示例
- **内存开销**: 额外的虚函数表和指针
  - 缓解: 使用 unique_ptr 管理生命周期

### Neutral

- **编译时间**: 模板使用增加编译时间
- **二进制大小**: 模板实例化增加代码体积

## Alternatives Considered

### Alternative 1: 单层直接实现
所有功能在一个类中实现。

**Pros**:
- 简单直接
- 性能最优

**Cons**:
- 代码重复（每种队列类型重复实现）
- 难以测试
- 无法扩展

**Rejected**: 不满足可维护性和可扩展性要求。

### Alternative 2: 三层架构（无 Operator 层）
Frontend 直接调用 Backend，Backend 直接调用 ThreadPool。

**Pros**:
- 更简单

**Cons**:
- 难以支持延时、屏障等高级功能
- 操作逻辑分散在各处

**Rejected**: 不满足功能需求。

## Compliance

### Satisfies Requirements
- [FR-001](FR-001-task-execution.md): 通过 Frontend API 提供 async/sync 功能
- [FR-002](FR-002-queue-types.md): 通过不同 IQueueImpl 实现支持多种队列
- [FR-004](FR-004-task-group.md): 通过 GroupImpl 实现任务组

### Related Decisions
- [ADR-002](ADR-002-queue-impl-strategy.md): Backend 具体实现策略
- [ADR-003](ADR-003-thread-scheduling.md): ThreadPool 调度策略

## Notes

### Implementation Guidelines

1. **Pimpl 模式**: Frontend 使用 Pimpl 隐藏实现细节
2. **工厂模式**: 使用 QueueFactory 创建具体队列实现
3. **依赖注入**: ThreadPool 通过构造函数注入

### References
- [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/)
- [Modern C++ Design Patterns](https://refactoring.guru/design-patterns/cpp)

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2024-03-15 | 1.0 | Initial acceptance |

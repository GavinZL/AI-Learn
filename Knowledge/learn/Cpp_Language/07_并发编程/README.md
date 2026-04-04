# C++ 并发编程模块 - 导航文档

> **核心说明**：本模块的完整内容已在 **[../thread/](../thread/)** 目录中深度覆盖。此文档提供导航索引、C++17+ 新增特性摘要与学习路径建议。

---

## 目录

1. [完整文档索引](#1-完整文档索引)
2. [C++17 并发新特性](#2-c17-并发新特性)
3. [C++20 并发新特性预览](#3-c20-并发新特性预览)
4. [学习路径建议](#4-学习路径建议)
5. [面试要点速查](#5-面试要点速查)

---

## 1. 完整文档索引

> 以下所有文档位于 **[../thread/](../thread/)** 目录

### 主文章

| 文件 | 描述 | 行数 |
|------|------|------|
| **[Cpp_Multithreading_深度解析.md](../thread/Cpp_Multithreading_深度解析.md)** | 多线程编程的全景概览：核心挑战、技术体系、同步原语、跨平台差异与性能数据 | ~520 |

### 线程基础与内存模型

| 文件 | 描述 | 行数 |
|------|------|------|
| [C++线程库与线程管理_详细解析.md](../thread/01_线程基础与内存模型/C++线程库与线程管理_详细解析.md) | std::thread 创建与销毁、joinable/detach 语义、线程属性设置、jthread 自动管理 | ~500 |
| [内存模型与原子操作_详细解析.md](../thread/01_线程基础与内存模型/内存模型与原子操作_详细解析.md) | happens-before 关系、memory_order 六种语义、acquire-release 同步、原子操作 | ~600 |

### 同步机制与锁优化

| 文件 | 描述 | 行数 |
|------|------|------|
| [互斥锁与读写锁_详细解析.md](../thread/02_同步机制与锁优化/互斥锁与读写锁_详细解析.md) | mutex 家族、lock_guard/unique_lock/scoped_lock、死锁避免策略、锁粒度优化 | ~550 |
| [条件变量与同步模式_详细解析.md](../thread/02_同步机制与锁优化/条件变量与同步模式_详细解析.md) | condition_variable 正确用法、spurious wakeup 处理、C++20 semaphore/latch/barrier | ~500 |

### 无锁编程与高性能并发

| 文件 | 描述 | 行数 |
|------|------|------|
| [无锁数据结构_详细解析.md](../thread/03_无锁编程与高性能并发/无锁数据结构_详细解析.md) | lock-free 队列/栈、hazard pointer、RCU 机制、epoch-based reclamation | ~600 |
| [并发设计模式_详细解析.md](../thread/03_无锁编程与高性能并发/并发设计模式_详细解析.md) | std::atomic 完整 API、compare_exchange 语义、ABA 问题与解决方案、并发模式 | ~550 |

### 线程池与任务调度

| 文件 | 描述 | 行数 |
|------|------|------|
| [线程池设计与实现_详细解析.md](../thread/04_线程池与任务调度/线程池设计与实现_详细解析.md) | 工作窃取算法、任务队列设计、动态伸缩策略、优先级调度、std::future/promise、异步编程 | ~550 |

### 跨平台多线程实践

| 文件 | 描述 | 行数 |
|------|------|------|
| [Android_NDK多线程_详细解析.md](../thread/05_跨平台多线程实践/Android_NDK多线程_详细解析.md) | NDK 线程创建、JNI 线程安全、Looper/Handler 协作、ANR 避免 | ~600 |
| [iOS多线程_详细解析.md](../thread/05_跨平台多线程实践/iOS多线程_详细解析.md) | GCD 核心概念、dispatch_queue 类型、pthread 与 C++ 互操作、QoS 优先级 | ~550 |

### 工程应用实战

| 文件 | 描述 | 行数 |
|------|------|------|
| [音视频多线程架构_详细解析.md](../thread/06_工程应用实战/音视频多线程架构_详细解析.md) | 采集/编码/传输流水线设计、帧同步策略、音视频同步、低延迟优化 | ~600 |
| [图像处理并行化_详细解析.md](../thread/06_工程应用实战/图像处理并行化_详细解析.md) | 图像处理多线程、并行算法、SIMD 优化、任务分解策略 | ~550 |
| [网络通信多线程模型_详细解析.md](../thread/06_工程应用实战/网络通信多线程模型_详细解析.md) | Reactor/Proactor 模式、IO 多路复用、线程模型选择、连接池设计 | ~550 |

### 调试测试与性能分析

| 文件 | 描述 | 行数 |
|------|------|------|
| [多线程Bug排查_详细解析.md](../thread/07_调试测试与性能分析/多线程Bug排查_详细解析.md) | TSan 使用、死锁检测工具、race condition 定位方法、日志设计 | ~500 |
| [性能分析与调优_详细解析.md](../thread/07_调试测试与性能分析/性能分析与调优_详细解析.md) | 伪共享检测与消除、锁竞争分析、CPU 亲和性设置、性能 profiling | ~550 |

---

## 2. C++17 并发新特性

### 2.1 std::shared_mutex（读写锁）

```cpp
// C++17 - 读写锁实现读写分离
#include <shared_mutex>
#include <map>
#include <string>

class ThreadSafeCache {
    mutable std::shared_mutex mtx;
    std::map<std::string, int> cache;
public:
    // 读操作：共享锁，允许多线程并发读
    int get(const std::string& key) const {
        std::shared_lock lock(mtx);  // 共享锁
        auto it = cache.find(key);
        return it != cache.end() ? it->second : -1;
    }
    
    // 写操作：独占锁，阻塞所有读写
    void set(const std::string& key, int value) {
        std::unique_lock lock(mtx);  // 独占锁
        cache[key] = value;
    }
    
    // C++17: try_lock_for 版本
    bool try_set(const std::string& key, int value) {
        if (mtx.try_lock()) {
            std::lock_guard<std::shared_mutex> lock(mtx, std::adopt_lock);
            cache[key] = value;
            return true;
        }
        return false;
    }
};
```

**适用场景**：读多写少（如缓存、配置管理），可显著提升并发性能。

### 2.2 std::scoped_lock（多锁管理）

```cpp
// C++17 - 死锁安全的多锁获取
#include <mutex>

class BankAccount {
public:
    std::mutex mtx;
    int balance{0};
};

void transfer(BankAccount& from, BankAccount& to, int amount) {
    // C++11: 容易死锁的写法
    // std::lock_guard<std::mutex> lock1(from.mtx);  // 如果此时上下文切换...
    // std::lock_guard<std::mutex> lock2(to.mtx);    // 死锁！
    
    // C++11 正确但繁琐
    // std::lock(from.mtx, to.mtx);
    // std::lock_guard<std::mutex> lock1(from.mtx, std::adopt_lock);
    // std::lock_guard<std::mutex> lock2(to.mtx, std::adopt_lock);
    
    // C++17: 简洁且死锁安全
    std::scoped_lock lock(from.mtx, to.mtx);  // 使用 std::lock 算法
    
    from.balance -= amount;
    to.balance += amount;
}
```

### 2.3 std::execution 并行策略

```cpp
// C++17 - 并行算法执行策略
#include <algorithm>
#include <execution>
#include <vector>
#include <numeric>

void parallel_algorithms() {
    std::vector<int> v(1'000'000);
    std::iota(v.begin(), v.end(), 1);
    
    // 四种执行策略
    std::execution::sequenced_policy;     // 顺序执行
    std::execution::parallel_policy;       // 并行执行
    std::execution::parallel_unsequenced_policy;  // 并行+向量化
    
    // 并行排序
    std::sort(std::execution::par, v.begin(), v.end());
    
    // 并行归约（新增算法）
    int sum = std::reduce(std::execution::par, v.begin(), v.end(), 0);
    
    // 并行转换归约
    int sum_of_squares = std::transform_reduce(
        std::execution::par, v.begin(), v.end(), 0,
        std::plus<>(), [](int x) { return x * x; });
}
```

### 2.4 std::any/optional/variant 线程安全性

```cpp
// C++17 - 类型安全容器的线程安全性
#include <any>
#include <optional>
#include <variant>
#include <mutex>

// std::any: 需要外部同步
std::any global_any;
std::mutex any_mutex;

void set_any(const std::any& value) {
    std::lock_guard lock(any_mutex);
    global_any = value;
}

// std::optional: 需要外部同步
std::optional<int> find_value(int key) {
    static std::map<int, int> cache;
    static std::mutex cache_mutex;
    
    std::lock_guard lock(cache_mutex);
    auto it = cache.find(key);
    if (it != cache.end()) {
        return it->second;
    }
    return std::nullopt;
}

// std::variant: 需要外部同步
std::variant<int, std::string, double> data;
// 多线程访问时需要加锁
```

**结论**：C++17 的类型安全容器本身**不是线程安全的**，需要外部同步。

---

## 3. C++20 并发新特性预览

### 3.1 std::jthread（自动 join）

```cpp
// C++20 - 自动 join 的线程
#include <thread>

void jthread_demo() {
    // C++11: 需要手动 join 或 detach
    // std::thread t([]{ /* ... */ });
    // t.join();  // 必须调用，否则 terminate
    
    // C++20: 析构时自动 join
    std::jthread t([]{ /* ... */ });
    // 析构时自动 join，无需手动管理
    
    // 支持 cooperative interruption
    std::jthread worker([](std::stop_token st) {
        while (!st.stop_requested()) {
            // 工作循环
        }
    });
    
    worker.request_stop();  // 请求停止
}
```

### 3.2 同步原语增强

```cpp
// C++20 - semaphore, latch, barrier
#include <semaphore>
#include <latch>
#include <barrier>

void sync_primitives() {
    // std::latch: 一次性计数器
    std::latch done{3};
    done.count_down();  // 减 1
    done.wait();        // 等待归零
    
    // std::barrier: 可重置的同步点
    std::barrier sync_point{3, []() noexcept {
        // 所有线程到达后执行的回调
    }};
    sync_point.arrive_and_wait();
    
    // std::counting_semaphore: 计数信号量
    std::counting_semaphore<10> sem{3};
    sem.acquire();  // P 操作
    sem.release();  // V 操作
}
```

### 3.3 std::atomic_ref

```cpp
// C++20 - 对现有变量的原子引用
#include <atomic>

void atomic_ref_demo() {
    int value = 0;
    
    // std::atomic_ref: 不需要修改原变量类型
    std::atomic_ref<int> ref(value);
    ref.store(42);
    int v = ref.load();
    
    // 适用于无法修改变量类型的场景
    // 如：第三方库的变量、全局变量
}
```

---

## 4. 学习路径建议

### 路径一：快速入门（1-2天）

```
Cpp_Multithreading_深度解析.md（全文）
    │
    ├─→ C++线程库与线程管理_详细解析.md（核心部分）
    │
    └─→ 互斥锁与读写锁_详细解析.md（常用 API）
```

### 路径二：深入原理（1-2周）

```
Cpp_Multithreading_深度解析.md
    │
    ├─→ 内存模型与原子操作_详细解析.md
    │
    ├─→ 并发设计模式_详细解析.md
    │
    └─→ 无锁数据结构_详细解析.md
```

### 路径三：工程实践导向（3-5天）

```
Cpp_Multithreading_深度解析.md（第四、五部分重点）
    │
    ├─→ 线程池设计与实现_详细解析.md
    │
    ├─→ 音视频多线程架构_详细解析.md
    │
    └─→ 性能分析与调优_详细解析.md
```

### 路径四：C++17+ 新特性专项学习（1天）

```
本 README.md（第二、三部分）
    │
    ├─→ 互斥锁与读写锁_详细解析.md（scoped_lock 部分）
    │
    └─→ 条件变量与同步模式_详细解析.md（semaphore/latch/barrier）
```

---

## 5. 面试要点速查

### Q1: std::shared_mutex 适用于什么场景？

**答案**：读多写少的场景（如缓存、配置管理）。多读线程可共享锁并发访问，写线程独占锁保证数据一致性。

### Q2: std::scoped_lock 如何避免死锁？

**答案**：内部使用 `std::lock()` 算法，该算法尝试以不同顺序获取锁，直到成功或全部失败，避免循环等待。

### Q3: C++17 并行算法的注意事项？

**答案**：
1. 操作必须是线程安全的（无数据竞争）
2. 小数据量时并行可能更慢
3. `par_unseq` 要求函数不阻塞
4. 使用 `reduce` 而非手动 `for_each + 原子操作`

### Q4: std::any/optional/variant 是线程安全的吗？

**答案**：**不是**。这些类型安全容器不提供内部同步，多线程访问时需要外部加锁。

---

## 参考资源

- [../thread/](../thread/) - 完整并发编程文档
- cppreference.com - Thread support library (C++17/20)
- 《C++ Concurrency in Action》Anthony Williams

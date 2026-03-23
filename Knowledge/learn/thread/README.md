# C++ 多线程编程深度解析 - 文档导航

> 本目录包含关于 C++ 多线程编程原理、同步机制、无锁编程与跨平台工程实践的系统性深度文章

---

## 文档结构

本文档采用**金字塔结构**组织，主文章提供全景视图，子文件深入关键概念。

### 主文章

| 文件 | 描述 | 行数 |
|------|------|------|
| **[Cpp_Multithreading_深度解析.md](./Cpp_Multithreading_深度解析.md)** | 多线程编程的全景概览：核心挑战、技术体系、同步原语、跨平台差异与性能数据 | ~520 |

### 子文件（按主题分类）

#### 线程基础与内存模型

| 文件 | 描述 | 行数 |
|------|------|------|
| [C++线程库与线程管理_详细解析.md](./01_线程基础与内存模型/C++线程库与线程管理_详细解析.md) | std::thread 创建与销毁、joinable/detach 语义、线程属性设置、jthread 自动管理 | ~500 |
| [内存模型与原子操作_详细解析.md](./01_线程基础与内存模型/内存模型与原子操作_详细解析.md) | happens-before 关系、memory_order 六种语义、acquire-release 同步、原子操作 | ~600 |

#### 同步机制与锁优化

| 文件 | 描述 | 行数 |
|------|------|------|
| [互斥锁与读写锁_详细解析.md](./02_同步机制与锁优化/互斥锁与读写锁_详细解析.md) | mutex 家族、lock_guard/unique_lock/scoped_lock、死锁避免策略、锁粒度优化 | ~550 |
| [条件变量与同步模式_详细解析.md](./02_同步机制与锁优化/条件变量与同步模式_详细解析.md) | condition_variable 正确用法、spurious wakeup 处理、C++20 semaphore/latch/barrier | ~500 |

#### 无锁编程与高性能并发

| 文件 | 描述 | 行数 |
|------|------|------|
| [无锁数据结构_详细解析.md](./03_无锁编程与高性能并发/无锁数据结构_详细解析.md) | lock-free 队列/栈、hazard pointer、RCU 机制、epoch-based reclamation | ~600 |
| [并发设计模式_详细解析.md](./03_无锁编程与高性能并发/并发设计模式_详细解析.md) | std::atomic 完整 API、compare_exchange 语义、ABA 问题与解决方案、并发模式 | ~550 |

#### 线程池与任务调度

| 文件 | 描述 | 行数 |
|------|------|------|
| [线程池设计与实现_详细解析.md](./04_线程池与任务调度/线程池设计与实现_详细解析.md) | 工作窃取算法、任务队列设计、动态伸缩策略、优先级调度、std::future/promise、异步编程 | ~550 |

#### 跨平台多线程实践

| 文件 | 描述 | 行数 |
|------|------|------|
| [Android_NDK多线程_详细解析.md](./05_跨平台多线程实践/Android_NDK多线程_详细解析.md) | NDK 线程创建、JNI 线程安全、Looper/Handler 协作、ANR 避免 | ~600 |
| [iOS多线程_详细解析.md](./05_跨平台多线程实践/iOS多线程_详细解析.md) | GCD 核心概念、dispatch_queue 类型、pthread 与 C++ 互操作、QoS 优先级 | ~550 |

#### 工程应用实战

| 文件 | 描述 | 行数 |
|------|------|------|
| [音视频多线程架构_详细解析.md](./06_工程应用实战/音视频多线程架构_详细解析.md) | 采集/编码/传输流水线设计、帧同步策略、音视频同步、低延迟优化 | ~600 |
| [图像处理并行化_详细解析.md](./06_工程应用实战/图像处理并行化_详细解析.md) | 图像处理多线程、并行算法、SIMD 优化、任务分解策略 | ~550 |
| [网络通信多线程模型_详细解析.md](./06_工程应用实战/网络通信多线程模型_详细解析.md) | Reactor/Proactor 模式、IO 多路复用、线程模型选择、连接池设计 | ~550 |

#### 调试测试与性能分析

| 文件 | 描述 | 行数 |
|------|------|------|
| [多线程Bug排查_详细解析.md](./07_调试测试与性能分析/多线程Bug排查_详细解析.md) | TSan 使用、死锁检测工具、race condition 定位方法、日志设计 | ~500 |
| [性能分析与调优_详细解析.md](./07_调试测试与性能分析/性能分析与调优_详细解析.md) | 伪共享检测与消除、锁竞争分析、CPU 亲和性设置、性能 profiling | ~550 |

---

## 学习路径

根据不同的学习目标，推荐以下学习路径：

### 路径一：快速入门（1-2天）

适合：想快速了解 C++ 多线程全貌的开发者

```
Cpp_Multithreading_深度解析.md（全文）
    │
    ├─→ C++线程库与线程管理_详细解析.md（核心部分）
    │
    └─→ 互斥锁与读写锁_详细解析.md（常用 API）
```

### 路径二：深入原理（1-2周）

适合：需要理解多线程底层机制的工程师

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

适合：需要在项目中设计多线程架构的开发者

```
Cpp_Multithreading_深度解析.md（第四、五部分重点）
    │
    ├─→ 线程池设计与实现_详细解析.md
    │
    ├─→ 音视频多线程架构_详细解析.md
    │
    └─→ 性能分析与调优_详细解析.md
```

### 路径四：跨平台开发（3-5天）

适合：需要在 Android/iOS 平台开发多线程应用的移动端工程师

```
Cpp_Multithreading_深度解析.md
    │
    ├─→ Android_NDK多线程_详细解析.md（Android 开发者）
    │
    ├─→ iOS多线程_详细解析.md（iOS 开发者）
    │
    └─→ 多线程Bug排查_详细解析.md
```

---

## 写作原则

本系列文档遵循以下写作原则：

### 1. 金字塔结构
- 主文章提供全景概览，明确"做什么"和"为什么"
- 子文件深入细节，解释"怎么做"和"如何优化"
- 每篇文章开头有核心结论，便于快速把握要点

### 2. 面向实践
- 避免纯理论推导，强调概念与实际应用的关联
- 提供具体的代码示例，使用现代 C++17/20 标准
- 包含常见问题、踩坑点和最佳实践

### 3. 类比优先
- 使用生活中的类比帮助理解抽象概念
- 例如：mutex = "单人卫生间的门锁"
- 降低入门门槛，建立直觉理解

### 4. 渐进深入
- 每个概念先给出直观解释，再展开技术细节
- 公式推导点到为止，重点是理解物理意义
- 提供"进一步阅读"指引，满足深入学习需求

---

## 目标读者

本系列文档面向以下读者：

| 读者类型 | 背景假设 | 重点章节 |
|---------|---------|---------|
| **应用开发者** | 有 C++ 基础，需要使用多线程功能 | 主文章、线程基础、同步原语 |
| **性能工程师** | 熟悉多线程，需要深入优化 | 内存模型、无锁编程、性能分析 |
| **移动端工程师** | 需要在 Android/iOS 开发高性能模块 | 跨平台实践、音视频架构 |
| **技术管理者** | 需要做架构设计和技术选型 | 主文章、工程实战、性能数据 |

**前置知识**：
- 熟悉 C++ 基本语法（类、模板、智能指针）
- 了解操作系统基本概念（进程、线程、内存）
- 不要求深入的操作系统或汇编背景（文中会解释必要概念）

---

## 核心概念速查表

| 术语 | 英文 | 简要解释 | 详见 |
|------|------|---------|------|
| 线程 | Thread | 操作系统调度的基本单位 | 线程生命周期 |
| 竞态条件 | Race Condition | 结果依赖于执行顺序的 bug | 主文章 |
| 数据竞争 | Data Race | 并发无同步访问导致的 UB | 主文章 |
| 互斥量 | Mutex | 保护临界区的同步原语 | 互斥量与锁 |
| 死锁 | Deadlock | 线程相互等待导致永久阻塞 | 互斥量与锁 |
| 条件变量 | Condition Variable | 线程间的等待/通知机制 | 条件变量与信号量 |
| 虚假唤醒 | Spurious Wakeup | 无信号却被唤醒的情况 | 条件变量与信号量 |
| 原子操作 | Atomic Operation | 不可分割的内存操作 | 原子操作与CAS |
| CAS | Compare-And-Swap | 原子比较并交换指令 | 原子操作与CAS |
| ABA 问题 | ABA Problem | CAS 无法检测中间变化 | 原子操作与CAS |
| 内存序 | Memory Order | 操作的可见性和顺序保证 | 内存模型 |
| happens-before | Happens-Before | 操作间的偏序关系 | 内存模型 |
| 顺序一致性 | Sequential Consistency | 最强的内存序保证 | 内存模型 |
| acquire-release | Acquire-Release | 配对使用的同步语义 | 内存模型 |
| 无锁 | Lock-Free | 至少一个线程保证前进 | 无锁数据结构 |
| 线程池 | Thread Pool | 复用线程的任务调度机制 | 线程池设计 |
| 工作窃取 | Work Stealing | 空闲线程窃取其他线程任务 | 线程池设计 |
| Future | Future | 异步操作结果的占位符 | 异步编程模型 |
| Promise | Promise | 设置 Future 值的通道 | 异步编程模型 |
| 伪共享 | False Sharing | 不同数据共享缓存行导致的争用 | 性能分析 |
| 缓存行 | Cache Line | CPU 缓存的最小单位（通常 64B） | 性能分析 |
| TSan | ThreadSanitizer | 数据竞争检测工具 | 调试与定位 |
| GCD | Grand Central Dispatch | Apple 的任务调度框架 | iOS 实践 |
| JNI | Java Native Interface | Android Java 与 Native 交互 | Android 实践 |
| Reactor | Reactor Pattern | 事件驱动的 IO 处理模式 | 服务器模型 |
| Proactor | Proactor Pattern | 异步 IO 完成通知模式 | 服务器模型 |
| barrier | Barrier | 多线程同步点 | 条件变量与信号量 |
| latch | Latch | 一次性计数同步 | 条件变量与信号量 |
| semaphore | Semaphore | 计数型同步原语 | 条件变量与信号量 |

---

## 参考资源

### 标准文档
- ISO/IEC 14882:2020 (C++20) - Thread support library
- POSIX.1-2017 - Threads (pthread)
- Apple Developer Documentation - Grand Central Dispatch

### 权威书籍
- Williams, A. - *C++ Concurrency in Action* (2nd Edition)
- Sutter, H. & Alexandrescu, A. - *C++ Coding Standards*
- Meyers, S. - *Effective Modern C++* (Items 35-40)

### 开源项目
- folly (Facebook): https://github.com/facebook/folly
- TBB (Intel): https://github.com/oneapi-src/oneTBB
- libcds: https://github.com/khizmax/libcds

### 在线资源
- cppreference.com - Thread support library
- Preshing on Programming - Lock-Free Programming
- CppCon YouTube Channel - Concurrency talks

---

## 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-03-22 | v1.0 | 创建主文章和文档导航 |

---

> 如有问题或建议，欢迎反馈。

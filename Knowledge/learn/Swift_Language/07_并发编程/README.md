# Swift 并发编程模块 - 导航文档

> **核心说明**：Swift Concurrency 是 Apple 于 WWDC 2021 推出的语言级并发模型，通过 **async/await、Actor 模型、结构化并发** 三大支柱，将并发编程从「手动线程管理」提升为「编译器保障的安全并发」。本模块的深度解析内容已在 **iOS_Framework_Architecture** 与 **thread** 目录中完整覆盖，此文档提供导航索引、Swift 6 严格并发补充与 C++ 对比。

---

## 目录

1. [Swift Concurrency 概览](#1-swift-concurrency-概览)
2. [核心概念速览表](#2-核心概念速览表)
3. [详细文档链接](#3-详细文档链接)
4. [Swift 6 严格并发（语言层补充）](#4-swift-6-严格并发语言层补充)
5. [与 C++ 并发模型对比](#5-与-c-并发模型对比)
6. [面试考点速查](#6-面试考点速查)

---

## 1. Swift Concurrency 概览

### 1.1 三大支柱

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Swift Concurrency 三大支柱                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │   async/await     │  │   Actor 模型      │  │   结构化并发      │   │
│  │                   │  │                   │  │                   │   │
│  │ • 协程式异步编程   │  │ • 数据隔离保护    │  │ • TaskGroup       │   │
│  │ • 编译器状态机变换 │  │ • 编译器保证安全  │  │ • 生命周期绑定    │   │
│  │ • 取代回调地狱     │  │ • 可重入性语义    │  │ • 取消自动传播    │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
│                                                                      │
│  设计哲学：编译器保障的安全并发（Compile-time Safety）                │
│  调度模型：Cooperative Thread Pool（合作式线程池，固定线程数）         │
│  演进方向：Swift 6 默认严格并发检查                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 设计哲学

**核心思想**：将并发安全从「运行时崩溃」前移到「编译时报错」。

| 传统并发（GCD / pthread） | Swift Concurrency |
|---------------------------|-------------------|
| 手动管理线程生命周期 | 编译器自动管理 Task 生命周期 |
| 数据竞争靠开发者经验 | Sendable 协议编译期检查 |
| 回调嵌套导致回调地狱 | async/await 线性代码流 |
| 优先级反转难以诊断 | Actor 隔离自动处理 |
| 线程爆炸（Thread Explosion） | 合作式线程池，固定线程数 |

---

## 2. 核心概念速览表

| 概念 | 类别 | 关键说明 | 引入版本 |
|------|------|---------|---------|
| **async/await** | 基础语法 | 编译器将 async 函数变换为状态机（CPS 变换），suspension point 处保存 continuation | Swift 5.5 |
| **Actor** | 隔离模型 | 通过 actor isolation 保证内部状态互斥访问，核心陷阱是可重入性 | Swift 5.5 |
| **@MainActor** | 全局 Actor | 标记必须在主线程执行的代码，替代 DispatchQueue.main | Swift 5.5 |
| **TaskGroup** | 结构化并发 | 子任务生命周期不超出父任务，取消自动传播 | Swift 5.5 |
| **AsyncSequence** | 异步序列 | 异步拉取模型，天然支持背压，替代 Combine 推送模型 | Swift 5.5 |
| **AsyncStream** | 异步流 | 桥接回调/委托模式到 AsyncSequence 的适配器 | Swift 5.5 |
| **Sendable** | 安全检查 | 编译器静态检查跨并发边界的数据安全性 | Swift 5.5 |
| **Task** | 任务单元 | 并发执行的基本单元，支持取消、优先级 | Swift 5.5 |
| **Continuation** | 桥接机制 | withCheckedContinuation / withUnsafeContinuation 桥接旧异步 API | Swift 5.5 |
| **Cooperative Thread Pool** | 调度模型 | 固定线程数（= CPU 核心数），避免线程爆炸 | Swift 5.5 |
| **@Sendable** | 闭包标记 | 标记可安全跨并发边界传递的闭包 | Swift 5.5 |
| **GlobalActor** | 自定义 Actor | 允许定义自定义全局 Actor，如 @DatabaseActor | Swift 5.5 |
| **Task.detached** | 非结构化 | 创建不继承父任务上下文的独立任务 | Swift 5.5 |
| **#isolation** | 隔离推断 | Swift 5.9+ 支持隔离参数推断 | Swift 5.9 |
| **Strict Concurrency** | 编译检查 | Swift 6 默认启用完整并发安全检查 | Swift 6.0 |

---

## 3. 详细文档链接

> 以下文档已覆盖 Swift Concurrency 的深度原理与实践

### 核心深度解析

| 文件 | 描述 | 行数 |
|------|------|------|
| **[Swift_Concurrency深度解析_详细解析.md](../../iOS_Framework_Architecture/05_并发与网络框架/Swift_Concurrency深度解析_详细解析.md)** | async/await 编译原理（CPS 变换、状态机）、Actor 隔离与可重入性、结构化并发语义、AsyncSequence/AsyncStream、Sendable 检查、Task 调度模型 | ~886 |

### GCD 与 pthread 基础

| 文件 | 描述 | 行数 |
|------|------|------|
| **[iOS多线程_详细解析.md](../../thread/05_跨平台多线程实践/iOS多线程_详细解析.md)** | GCD 核心概念、dispatch_queue 类型、QoS 优先级、pthread 与 C++ 互操作、NSOperation 框架 | ~550 |

### 相关参考

| 文件 | 描述 |
|------|------|
| [Swift运行时与ABI稳定性_详细解析.md](../../iOS_Framework_Architecture/04_底层运行机制/Swift运行时与ABI稳定性_详细解析.md) | 方法派发机制（Direct / VTable / Message）、运行时元数据 |
| [Cpp_Multithreading_深度解析.md](../../thread/Cpp_Multithreading_深度解析.md) | C++ 并发编程全景，可与 Swift Concurrency 对比学习 |

---

## 4. Swift 6 严格并发（语言层补充）

> 本节补充 Swift 6 对并发安全的语言级强化，是对深度解析文档中 Sendable 部分的扩展。

### 4.1 Swift 6 默认严格并发检查

**Swift 6 最重大的变化**：`StrictConcurrency` 从 opt-in 变为默认启用。

```swift
// Swift 5 模式：Sendable 警告（可忽略）
// Swift 6 模式：Sendable 错误（必须修复）

class UserManager {
    var users: [String] = []  // ❌ Swift 6: 'UserManager' 不符合 Sendable
    
    func addUser(_ name: String) {
        users.append(name)
    }
}

// 在 Task 中使用会触发编译错误
Task {
    let manager = UserManager()
    manager.addUser("Alice")  // ❌ Capture of non-sendable type
}
```

### 4.2 从 Swift 5 迁移到 Swift 6 的策略

```
┌─────────────────────────────────────────────────────────────────┐
│               Swift 5 → Swift 6 并发迁移路径                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  阶段一：开启警告                                                 │
│  • 设置 -strict-concurrency=targeted                             │
│  • 修复明显的 Sendable 违规                                       │
│                                                                  │
│  阶段二：完全警告                                                 │
│  • 设置 -strict-concurrency=complete                             │
│  • 处理所有 Sendable 警告                                        │
│  • 审查跨 Actor 的数据传递                                        │
│                                                                  │
│  阶段三：切换语言模式                                             │
│  • 设置 Swift Language Version = 6                               │
│  • 所有并发违规变为编译错误                                       │
│                                                                  │
│  关键：渐进式迁移，不要一步到位                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Sendable 严格模式的实践建议

```swift
// ✅ 方案一：使用 Actor 隔离
actor UserManager {
    var users: [String] = []
    func addUser(_ name: String) { users.append(name) }
}

// ✅ 方案二：标记为 @Sendable + 不可变
final class Config: Sendable {
    let apiKey: String      // ✅ let 属性，不可变
    let timeout: TimeInterval
    init(apiKey: String, timeout: TimeInterval) {
        self.apiKey = apiKey
        self.timeout = timeout
    }
}

// ✅ 方案三：@unchecked Sendable（谨慎使用）
final class ThreadSafeCache: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [String: Any] = [:]
    
    func get(_ key: String) -> Any? {
        lock.lock()
        defer { lock.unlock() }
        return storage[key]
    }
}

// ⚠️ 方案四：nonisolated(unsafe)（Swift 6 逃生舱）
nonisolated(unsafe) var legacyGlobal: Int = 0  // 仅用于确认安全的遗留代码
```

### 4.4 常见迁移问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `Non-sendable type captured` | 闭包捕获了非 Sendable 类型 | 改用 Actor 或标记为 Sendable |
| `Global variable is not concurrency-safe` | 全局可变状态 | 改为 Actor 属性或 `nonisolated(unsafe)` |
| `Call to main actor-isolated method` | 非主线程调用 @MainActor 方法 | 添加 `await` 或标记调用方为 @MainActor |
| `Protocol does not conform to Sendable` | 协议未声明 Sendable | 添加 `: Sendable` 约束或使用 `sending` 参数 |
| `Stored property is mutable` | Sendable 类型包含 var 属性 | 改为 let 或使用 Actor |

---

## 5. 与 C++ 并发模型对比

### 5.1 综合对比表

| 维度 | Swift Concurrency | C++ 并发（std::thread / async） |
|------|-------------------|-------------------------------|
| **抽象层级** | 语言级协程（编译器变换） | 库级线程（操作系统线程） |
| **安全保证** | 编译期 Sendable 检查 | 无编译期安全保证 |
| **调度模型** | 合作式线程池（固定线程数） | 1:1 线程映射（可能线程爆炸） |
| **数据隔离** | Actor 自动隔离 | 手动 mutex/lock |
| **取消机制** | Task.cancel() + isCancelled 检查 | 无内建取消（需手动 flag） |
| **错误传播** | async throws 自动传播 | future.get() 抛异常 |
| **生命周期** | 结构化并发保证 | 手动 join/detach |
| **性能开销** | 轻量级（~几百字节/Task） | 重量级（~1MB 栈/线程） |

### 5.2 Actor vs mutex/lock

```swift
// Swift: Actor 隔离 — 编译器保证
actor BankAccount {
    var balance: Int = 0
    func deposit(_ amount: Int) { balance += amount }
    func withdraw(_ amount: Int) -> Bool {
        guard balance >= amount else { return false }
        balance -= amount
        return true
    }
}

// 使用时编译器强制 await
let account = BankAccount()
await account.deposit(100)
```

```cpp
// C++: mutex 保护 — 程序员保证
class BankAccount {
    std::mutex mtx;
    int balance = 0;
public:
    void deposit(int amount) {
        std::lock_guard lock(mtx);  // 忘记加锁 = 数据竞争
        balance += amount;
    }
    bool withdraw(int amount) {
        std::lock_guard lock(mtx);
        if (balance < amount) return false;
        balance -= amount;
        return true;
    }
};
```

**关键差异**：Actor 的安全是编译器强制的（遗漏 `await` 会报错），mutex 的安全依赖程序员纪律。

### 5.3 TaskGroup vs Thread Pool

```swift
// Swift: 结构化并发 — 自动生命周期管理
func processImages(_ urls: [URL]) async throws -> [Image] {
    try await withThrowingTaskGroup(of: Image.self) { group in
        for url in urls {
            group.addTask { try await downloadImage(url) }
        }
        var images: [Image] = []
        for try await image in group {
            images.append(image)
        }
        return images  // 所有子任务保证在此处完成或取消
    }
}
```

```cpp
// C++: 线程池 — 手动生命周期管理
std::vector<Image> processImages(const std::vector<URL>& urls) {
    ThreadPool pool(std::thread::hardware_concurrency());
    std::vector<std::future<Image>> futures;
    for (const auto& url : urls) {
        futures.push_back(pool.submit([&url] {
            return downloadImage(url);  // 引用捕获 — 如果 url 先析构？
        }));
    }
    std::vector<Image> images;
    for (auto& f : futures) {
        images.push_back(f.get());  // 逐个等待，异常处理繁琐
    }
    return images;
}
```

---

## 6. 面试考点速查

### Q1: Swift Concurrency 的 async/await 底层是如何实现的？

**答案**：编译器将 async 函数通过 CPS（Continuation Passing Style）变换为状态机。每个 suspension point（await 处）对应一个状态，执行到 await 时保存当前 continuation（包含局部变量和执行位置），让出线程。当异步操作完成后，恢复 continuation 继续执行。这不是语法糖，而是语言级协程实现。

### Q2: Actor 的可重入性（Reentrancy）会导致什么问题？如何解决？

**答案**：Actor 方法在 await 处会暂停执行，此时其他消息可以被处理（可重入），导致 await 前后的状态假设失效。解决方案：(1) 在 await 后重新检查状态；(2) 使用局部变量保存关键状态；(3) 将多步操作封装为不含 await 的同步方法。

### Q3: Sendable 协议在 Swift 6 中有什么变化？

**答案**：Swift 6 默认启用严格并发检查（`StrictConcurrency = complete`），所有跨并发边界传递的类型必须符合 Sendable。值类型（Struct/Enum）如果所有存储属性都是 Sendable 则自动符合；引用类型必须是 `final class` 且所有属性为 `let`；或使用 `@unchecked Sendable` 手动保证。

### Q4: Swift 的合作式线程池与 GCD 线程池有什么区别？

**答案**：GCD 使用按需创建的线程池，高并发时可能创建数百个线程（Thread Explosion），导致上下文切换开销激增。Swift Concurrency 使用固定大小的合作式线程池（线程数 = CPU 核心数），Task 在 suspension point 主动让出线程，由运行时调度下一个 Task。这避免了线程爆炸，但要求开发者不要在 Actor 中执行阻塞操作。

### Q5: 如何将现有的 GCD/回调异步代码桥接到 Swift Concurrency？

**答案**：使用 `withCheckedContinuation` 或 `withCheckedThrowingContinuation` 包装回调式 API。关键约束：continuation 必须且只能 resume 一次（多次 resume 会崩溃，不 resume 会泄露）。对于持续产生值的 API（如 delegate 回调），使用 `AsyncStream` 桥接。

---

## 学习路径建议

### 路径一：快速入门（1-2天）

```
Swift_Concurrency深度解析_详细解析.md（核心结论 + async/await 部分）
    │
    └─→ 本 README.md（Swift 6 严格并发部分）
```

### 路径二：深入原理（1 周）

```
Swift_Concurrency深度解析_详细解析.md（全文）
    │
    ├─→ iOS多线程_详细解析.md（GCD 基础 + 对比）
    │
    └─→ Swift运行时与ABI稳定性_详细解析.md（方法派发与运行时调度）
```

### 路径三：C++ 开发者快速对比（1天）

```
本 README.md（第五部分：C++ 对比）
    │
    ├─→ Cpp_Multithreading_深度解析.md（C++ 并发全景）
    │
    └─→ Swift_Concurrency深度解析_详细解析.md（Actor 与 Sendable）
```

---

## 参考资源

- [Swift_Concurrency深度解析_详细解析.md](../../iOS_Framework_Architecture/05_并发与网络框架/Swift_Concurrency深度解析_详细解析.md) — 核心深度解析
- [iOS多线程_详细解析.md](../../thread/05_跨平台多线程实践/iOS多线程_详细解析.md) — GCD 与 pthread 基础
- [SE-0302: Sendable and @Sendable closures](https://github.com/apple/swift-evolution/blob/main/proposals/0302-concurrent-value-and-concurrent-closures.md)
- [SE-0401: Remove Actor Isolation Inference](https://github.com/apple/swift-evolution/blob/main/proposals/0401-remove-property-wrapper-isolation.md)
- WWDC 2021/2022/2023 Concurrency Sessions

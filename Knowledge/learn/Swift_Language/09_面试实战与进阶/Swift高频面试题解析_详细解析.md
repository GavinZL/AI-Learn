# Swift 高频面试题解析

> 面向 1-10 年 Swift 开发经验的分级面试题深度解析，覆盖类型系统、POP、泛型、并发、内存管理、性能优化与现代特性

---

## 核心结论 TL;DR

| 主题 | 核心考点 | 难度 | 高频指数 |
|------|----------|------|----------|
| 值类型 vs 引用类型 | struct/class 选择、COW 机制 | 初级-中级 | ★★★★★ |
| Optional 底层实现 | 枚举本质、多层嵌套、IUO | 初级-中级 | ★★★★★ |
| 类型推断机制 | 编译器推断规则、编译时间影响 | 中级 | ★★★☆☆ |
| POP vs OOP | 协议扩展派发、Witness Table | 中级-高级 | ★★★★★ |
| some vs any | Opaque Type、Existential 开销 | 中级-高级 | ★★★★☆ |
| 泛型特化 | 编译器优化、跨模块限制 | 高级 | ★★★☆☆ |
| Actor 隔离 | reentrancy、@MainActor | 高级 | ★★★★★ |
| Sendable 与 Swift 6 | 严格并发检查、迁移策略 | 高级-专家 | ★★★★☆ |
| ARC 与循环引用 | weak/unowned 选择、闭包捕获 | 中级 | ★★★★★ |
| COW 实现 | isKnownUniquelyReferenced | 中级-高级 | ★★★★☆ |
| ~Copyable 所有权 | consuming/borrowing、Rust 对比 | 专家 | ★★★☆☆ |
| 方法派发 | Static/VTable/Message Dispatch | 中级-高级 | ★★★★★ |
| ABI 稳定性 | @frozen、Library Evolution | 专家 | ★★★☆☆ |
| Swift Macros | @Observable 展开、宏分类 | 高级-专家 | ★★★☆☆ |

---

## 目录

- [面试题分级说明](#一面试题分级说明)
- [类型系统与语言基础 Top 3](#二类型系统与语言基础-top-3)
- [面向协议编程 Top 3](#三面向协议编程-top-3)
- [泛型编程 Top 3](#四泛型编程-top-3)
- [并发编程 Top 3](#五并发编程-top-3)
- [内存管理 Top 3](#六内存管理-top-3)
- [性能优化 Top 3](#七性能优化-top-3)
- [现代特性 Top 2](#八现代特性-top-2)
- [综合设计题](#九综合设计题)
- [参考资源](#参考资源)

---

## 一、面试题分级说明

| 级别 | 经验 | 考察重点 | 典型题目 |
|------|------|----------|----------|
| **初级** | 1-3 年 | 语法基础、类型系统、Optional、集合 | 值类型 vs 引用类型、Optional 解包方式 |
| **中级** | 3-5 年 | POP、泛型、内存管理、闭包 | Protocol Extension 派发、ARC 循环引用 |
| **高级** | 5 年+ | 并发、性能优化、编译原理、方法派发 | Actor reentrancy、WMO 优化策略 |
| **专家级** | 架构师 | ABI 稳定性、宏系统、所有权、编译器内部 | ~Copyable、Swift Macros、Library Evolution |

**评估维度**：
- **广度**：是否覆盖语言核心特性
- **深度**：是否理解底层实现原理
- **实战**：是否能结合工程场景分析
- **思维**：是否能权衡 trade-off 做出合理选择

---

## 二、类型系统与语言基础 Top 3

### 题目 1: 值类型与引用类型的区别及选择标准

**难度**: 初级-中级
**考察点**: struct/class 语义差异、COW 机制、内存布局、选择标准

**问题**:
```swift
struct Point {
    var x: Double
    var y: Double
}

class Particle {
    var position: Point
    var velocity: Point
    init(position: Point, velocity: Point) {
        self.position = position
        self.velocity = velocity
    }
}

// 以下代码的输出是什么？
var p1 = Point(x: 1, y: 2)
var p2 = p1
p2.x = 10
print(p1.x) // ?

let particle1 = Particle(position: Point(x: 0, y: 0), velocity: Point(x: 1, y: 1))
let particle2 = particle1
particle2.position.x = 99
print(particle1.position.x) // ?
```

**参考答案**:

1. `p1.x` 输出 `1.0` — struct 是值类型，赋值产生独立副本
2. `particle1.position.x` 输出 `99.0` — class 是引用类型，共享同一实例

**核心区别**：

| 维度 | 值类型 (struct/enum) | 引用类型 (class) |
|------|---------------------|------------------|
| 存储 | 栈（小型）或内联存储 | 堆分配 + 引用计数 |
| 赋值 | 深拷贝（逻辑上） | 浅拷贝（共享引用） |
| 线程安全 | 天然安全（独立副本） | 需要同步保护 |
| 可变性 | var/let 控制值本身 | let 只限引用不可变 |

**选择标准**：
- 默认用 struct，除非需要以下特性：
  - 引用共享语义（如缓存、共享状态）
  - 继承层次结构
  - 与 Objective-C 互操作
  - deinit 析构逻辑

**代码示例**:
```swift
// struct 中包含引用类型属性时的行为（追问 1）
class Storage {
    var data: [Int] = [1, 2, 3]
}

struct Container {
    var storage = Storage()
    var label: String = "default"
}

var c1 = Container()
var c2 = c1            // struct 拷贝，但 storage 是引用类型
c2.label = "modified"  // 独立修改
c2.storage.data.append(4)  // 共享修改！

print(c1.label)         // "default" — 值类型部分独立
print(c1.storage.data)  // [1, 2, 3, 4] — 引用类型部分共享！
// 这是 struct 的「浅拷贝」陷阱
```

**追问链**:

- **Q1: struct 中包含引用类型属性时的行为？**
- A: struct 赋值只拷贝值类型部分，引用类型属性仍共享同一对象。这是「浅拷贝」行为，必须手动实现深拷贝（如通过 `NSCopying` 或自定义 `copy()` 方法）。

- **Q2: COW（Copy-on-Write）的触发条件？**
- A: COW 并非 struct 的默认行为，仅 Swift 标准库的 `Array`、`Dictionary`、`String` 等实现了 COW。触发条件是：当引用计数 > 1 且发生写操作时，底层 buffer 会被复制。单一引用时直接原地修改。

```swift
var arr1 = [1, 2, 3]
var arr2 = arr1  // 此时共享底层 buffer

arr2.append(4)   // 写操作触发 COW，arr2 获得独立 buffer
// arr1 仍然是 [1, 2, 3]
```

- **Q3: 性能对比数据？**
- A: 小型 struct（≤ 3 个机器字长）直接在栈上分配，无堆开销。大型 struct 赋值时有拷贝开销但编译器会优化（内联、消除冗余拷贝）。class 有 ARC 引用计数的原子操作开销（约 10-20 ns/次）。在多线程高频赋值场景下，struct 无锁优势显著。

**评估标准**:
- 初级：能说出栈/堆、值/引用拷贝区别
- 中级：理解引用类型属性嵌套的浅拷贝问题
- 高级：能分析 COW 实现原理并给出性能对比

---

### 题目 2: Optional 的底层实现原理

**难度**: 初级-中级
**考察点**: Optional 枚举实现、模式匹配、IUO、多层嵌套

**问题**:
```swift
let a: Int? = 42
let b: Int?? = a
let c: Int?? = nil

// 以下判断结果是什么？
print(b == nil)  // ?
print(c == nil)  // ?
print(b == .some(nil))  // ?
```

**参考答案**:

```
b == nil  → false    // b 是 .some(.some(42))
c == nil  → true     // c 是 .none
b == .some(nil) → false  // b 是 .some(.some(42))，不是 .some(.none)
```

**Optional 的枚举本质**:

```swift
// Swift 标准库中 Optional 的定义（简化）
@frozen
enum Optional<Wrapped> {
    case none
    case some(Wrapped)
}
```

**代码示例**:
```swift
// 多层 Optional 的完整分析（追问 2）
let x: Int? = 42
let y: Int?? = x        // Optional<Optional<Int>>.some(Optional<Int>.some(42))
let z: Int?? = nil       // Optional<Optional<Int>>.none
let w: Int?? = .some(nil) // Optional<Optional<Int>>.some(Optional<Int>.none)

// 使用 switch 精确匹配
func describe(_ value: Int??) {
    switch value {
    case .some(.some(let v)):
        print("有值: \(v)")
    case .some(.none):
        print("外层有值，内层 nil")
    case .none:
        print("完全为 nil")
    }
}

describe(y) // "有值: 42"
describe(z) // "完全为 nil"
describe(w) // "外层有值，内层 nil"
```

**追问链**:

- **Q1: Optional 是如何用枚举实现的？**
- A: `Optional<Wrapped>` 是一个 `@frozen` 泛型枚举，编译器对其有特殊优化：对于引用类型，`nil` 直接用 0 表示（空指针），不需要额外 tag bit。对于 `Bool?`，编译器使用 0/1/2 三个值表示。

- **Q2: 多层 Optional 的行为？**
- A: 如上代码所示，`Int??` 有三种状态。这在字典查找中常见：`dict[key]` 返回 `Value?`，如果 `Value` 本身是 Optional，结果就是双层 Optional。

- **Q3: IUO（Implicitly Unwrapped Optional）的使用场景和风险？**
- A: IUO（`Type!`）在 Swift 4.1+ 被实现为普通 `Optional<Type>`，只在类型检查时有特殊处理。使用场景：IBOutlet、两阶段初始化。风险：运行时访问 nil 会触发 fatalError。建议仅在初始化后保证有值的场景使用。

```swift
// IUO 典型场景
class ViewController: UIViewController {
    @IBOutlet var label: UILabel!  // viewDidLoad 后保证有值
    
    // 两阶段初始化
    var delegate: SomeDelegate!    // 构造完成后立即设置
}
```

**评估标准**:
- 初级：知道 Optional 是枚举，能使用 if let / guard let
- 中级：理解多层嵌套 Optional 的行为
- 高级：了解编译器对 Optional 的内存优化（nil 用 0 表示）

---

### 题目 3: Swift 的类型推断机制

**难度**: 中级
**考察点**: 类型推断规则、编译器限制、编译时间影响

**问题**:
```swift
// 以下哪些能编译？哪些不能？
let a = 42                        // (1)
let b = [1, 2.0, 3]              // (2)
let c = [1, "hello"]             // (3)
let d = { $0 + $1 }              // (4)
let e: (Int, Int) -> Int = { $0 + $1 }  // (5)
```

**参考答案**:

1. ✅ 推断为 `Int`
2. ✅ 推断为 `[Double]`（Int 字面量可隐式转换为 Double）
3. ❌ 编译错误 — `Int` 和 `String` 无共同类型（需显式标注 `[Any]`）
4. ❌ 编译错误 — 闭包缺少上下文，编译器无法推断 `$0`、`$1` 的类型
5. ✅ 有类型标注，闭包参数类型从上下文推断

**代码示例**:
```swift
// 编译器何时无法推断（追问 1）

// 1. 闭包无上下文
// let f = { $0 * 2 }  // ❌ 无法推断 $0 类型

// 2. 复杂表达式链
// 编译器有 type-check 时间限制（默认 15 秒）
let result = [1, 2, 3]
    .map { $0 * 2 }
    .filter { $0 > 3 }
    .reduce(0, +)
// ✅ 可推断，但链过长时可能超时

// 3. 字面量的歧义
let x = 42          // Int（默认）
let y: Double = 42  // Double（显式标注）

// 4. 复杂泛型嵌套
func process<T, U>(_ a: T, _ b: U) -> (T, U) { (a, b) }
let pair = process(1, "hello")  // ✅ 推断为 (Int, String)
```

**追问链**:

- **Q1: 编译器何时无法推断类型？**
- A: (1) 闭包无足够上下文；(2) 复杂表达式超过类型检查时间限制；(3) 字面量在多协议一致性下有歧义；(4) 循环类型依赖。

- **Q2: 类型推断对编译时间的影响？**
- A: Swift 类型推断采用双向约束求解系统。复杂表达式（尤其是多个运算符链式调用）会导致约束求解空间指数增长。实践建议：对复杂表达式拆分子表达式并添加类型标注，可显著减少编译时间。可用 `-Xfrontend -warn-long-expression-type-checking=100` 检测慢表达式。

```swift
// 反面示例：编译超时
// let slow = a + b * c + d * e + f  // 多个重载 + 时，约束空间爆炸

// 正面示例：拆分并标注
let ab: Double = a + b
let cde: Double = c + d * e
let fast = ab * cde + f
```

**评估标准**:
- 初级：知道 Swift 能自动推断类型
- 中级：理解推断失败的场景
- 高级：能分析类型推断对编译性能的影响并给出优化方案

---

## 三、面向协议编程 Top 3

### 题目 1: POP vs OOP 的核心区别与选择

**难度**: 中级-高级
**考察点**: 协议优先设计、Protocol Extension 派发陷阱、实际重构能力

**问题**:
```swift
protocol Drawable {
    func draw()
}

extension Drawable {
    func draw() { print("Default draw") }
    func description() { print("I am Drawable") }
}

struct Circle: Drawable {
    func draw() { print("Drawing Circle") }
    func description() { print("I am Circle") }
}

let circle = Circle()
let drawable: Drawable = circle

circle.draw()        // ?
drawable.draw()      // ?
circle.description() // ?
drawable.description() // ?
```

**参考答案**:

```
circle.draw()          → "Drawing Circle"
drawable.draw()        → "Drawing Circle"     // Protocol Requirement → 动态派发
circle.description()   → "I am Circle"
drawable.description() → "I am Drawable"       // Extension only → 静态派发！
```

**关键区别**：
- `draw()` 是协议要求（Protocol Requirement），通过 Protocol Witness Table 动态派发
- `description()` 仅在 Extension 中定义，不是协议要求，通过静态类型派发

**这是 Swift 最经典的面试陷阱之一。**

**代码示例**:
```swift
// POP 重构示例（追问 3）

// OOP 方式：继承层次
class Shape {
    func area() -> Double { fatalError("override me") }
    func perimeter() -> Double { fatalError("override me") }
}

class OOPCircle: Shape {
    var radius: Double
    init(radius: Double) { self.radius = radius }
    override func area() -> Double { .pi * radius * radius }
    override func perimeter() -> Double { 2 * .pi * radius }
}

// POP 方式：协议组合
protocol HasArea {
    func area() -> Double
}

protocol HasPerimeter {
    func perimeter() -> Double
}

// 默认实现
extension HasArea where Self: HasPerimeter {
    func description() -> String {
        "Area: \(area()), Perimeter: \(perimeter())"
    }
}

struct POPCircle: HasArea, HasPerimeter {
    var radius: Double
    func area() -> Double { .pi * radius * radius }
    func perimeter() -> Double { 2 * .pi * radius }
}

// 优势：值类型、可组合、无继承耦合
```

**追问链**:

- **Q1: Swift 为什么推荐 POP？**
- A: (1) 值类型支持，避免引用语义复杂性；(2) 协议组合替代多继承；(3) Extension 提供默认实现，避免基类膨胀；(4) 泛型约束配合协议实现零成本抽象。

- **Q2: Protocol Extension 的方法派发行为？**
- A: 协议要求中声明的方法 → Witness Table 动态派发；仅在 Extension 中定义的方法 → 静态派发（基于编译时类型）。这是最常见的 POP 陷阱，必须明确区分。

- **Q3: 给一个设计场景，如何用 POP 重构？**
- A: 如上代码示例。核心思路是将能力拆分为独立协议，通过协议组合表达多重能力，用条件一致性和 where 子句实现精确的默认行为。

**评估标准**:
- 初级：知道协议可以有默认实现
- 中级：理解派发行为差异（关键陷阱题）
- 高级：能从架构层面设计 POP 方案

---

### 题目 2: Protocol Witness Table 的实现原理

**难度**: 高级
**考察点**: Existential Container、PWT、VWT、性能分析

**问题**: 当一个值赋给协议类型变量时，Swift 底层发生了什么？

**参考答案**:

当我们写 `let d: Drawable = Circle()` 时，Swift 创建一个 **Existential Container**：

```
┌───────────────────────────┐
│  Value Buffer (3 words)    │  ← 存储值（小值内联，大值堆分配）
│  [word0] [word1] [word2]   │
├───────────────────────────┤
│  Value Witness Table (VWT) │  ← 管理值的生命周期（copy/destroy/size）
├───────────────────────────┤
│  Protocol Witness Table    │  ← 方法函数指针表（类似 C++ vtable）
│  (PWT)                     │
└───────────────────────────┘
```

**代码示例**:
```swift
protocol Shape {
    func area() -> Double
}

struct SmallShape: Shape { // ≤ 24 bytes，内联存储
    var radius: Double     // 8 bytes
    func area() -> Double { .pi * radius * radius }
}

struct LargeShape: Shape { // > 24 bytes，堆分配
    var a: Double, b: Double, c: Double, d: Double // 32 bytes
    func area() -> Double { a * b }
}

// 两者都可赋给 Shape，但存储方式不同
let s1: Shape = SmallShape(radius: 5)   // 内联到 Value Buffer
let s2: Shape = LargeShape(a: 1, b: 2, c: 3, d: 4) // 堆分配 + 指针
```

**追问链**:

- **Q1: Existential Container 的内存布局？**
- A: 固定大小 5 个机器字（40 bytes on 64-bit）：3 words Value Buffer + 1 word VWT 指针 + 1 word PWT 指针。值 ≤ 24 bytes 内联存储，否则堆分配并在 Buffer 中存指针。

- **Q2: 协议类型 vs 泛型约束的性能差异？**
- A: 协议类型（Existential）有间接调用、可能的堆分配开销。泛型约束在编译时单态化（Specialization），零成本抽象，等价于直接调用具体类型方法。

```swift
// 协议类型：运行时开销
func drawAny(_ shape: any Shape) {
    shape.area() // 通过 PWT 间接调用
}

// 泛型约束：编译时特化，零开销
func drawGeneric<T: Shape>(_ shape: T) {
    shape.area() // 特化后直接调用
}
```

**评估标准**:
- 中级：知道协议类型有额外开销
- 高级：能画出 Existential Container 布局
- 专家：能分析特化前后的性能差异并给出建议

---

### 题目 3: 条件一致性（Conditional Conformance）的使用

**难度**: 高级
**考察点**: where 子句、标准库应用、类型擦除关系

**问题**:
```swift
// 为什么 [Int] 可以是 Equatable，但 [UIView] 不行？
let a = [1, 2, 3]
let b = [1, 2, 3]
print(a == b)  // ✅

// let views1: [UIView] = ...
// let views2: [UIView] = ...
// print(views1 == views2) // ❌ 编译错误
```

**参考答案**:

Swift 标准库对 `Array` 的 `Equatable` 遵循使用了条件一致性：

```swift
// 标准库中的声明（简化）
extension Array: Equatable where Element: Equatable {
    static func == (lhs: [Element], rhs: [Element]) -> Bool { ... }
}
```

只有当 `Element` 满足 `Equatable` 时，`Array<Element>` 才满足 `Equatable`。`Int` 是 `Equatable`，所以 `[Int]` 是 `Equatable`；`UIView` 不是 `Equatable`，所以 `[UIView]` 不是。

**代码示例**:
```swift
// 标准库中的条件一致性示例（追问 1）

// Array 的多个条件一致性
extension Array: Hashable where Element: Hashable { }
extension Array: Encodable where Element: Encodable { }
extension Array: Decodable where Element: Decodable { }
extension Array: Sendable where Element: Sendable { }

// Optional 的条件一致性
extension Optional: Equatable where Wrapped: Equatable { }
extension Optional: Hashable where Wrapped: Hashable { }

// 自定义条件一致性
struct Stack<Element> {
    private var storage: [Element] = []
    mutating func push(_ e: Element) { storage.append(e) }
    mutating func pop() -> Element? { storage.popLast() }
}

extension Stack: Equatable where Element: Equatable { }
extension Stack: CustomStringConvertible where Element: CustomStringConvertible {
    var description: String {
        storage.map(\.description).joined(separator: ", ")
    }
}
```

**追问链**:

- **Q1: 标准库中有哪些条件一致性的例子？**
- A: 如上所示，Array/Optional/Dictionary 的 Equatable/Hashable/Codable/Sendable 都是条件一致性。这是 Swift 4.1 引入的核心特性。

- **Q2: 条件一致性与类型擦除的关系？**
- A: 条件一致性让泛型容器在元素满足条件时自动获得协议能力，减少了类型擦除的需求。例如，不再需要 `AnyEquatable` 包装器，`[any Equatable]` 配合条件一致性即可。在 Swift 5.7+ 中，`any` 关键字 + 条件一致性进一步简化了异构集合的处理。

**评估标准**:
- 中级：能使用 where 子句编写条件一致性
- 高级：理解标准库的大量条件一致性设计
- 专家：能分析条件一致性对类型系统整体设计的影响

---

## 四、泛型编程 Top 3

### 题目 1: some vs any 的区别与选择

**难度**: 中级-高级
**考察点**: Opaque Type、Existential Type、性能差异、Swift 5.7+ 语义

**问题**:
```swift
// 以下两个函数有什么区别？
func makeShape1() -> some Shape { Circle(radius: 5) }
func makeShape2() -> any Shape { Circle(radius: 5) }

// 以下能编译吗？
func compare(a: some Equatable, b: some Equatable) -> Bool {
    a == b  // ?
}
```

**参考答案**:

| 维度 | `some Shape` (Opaque Type) | `any Shape` (Existential) |
|------|---------------------------|--------------------------|
| 类型身份 | 编译器知道具体类型（固定） | 运行时任意满足协议的类型 |
| 存储 | 无 Existential Container 开销 | 有 Existential Container 开销 |
| 可替换性 | 每次调用返回相同具体类型 | 每次可返回不同类型 |
| Self/associatedtype | 支持 | Swift 5.7+ 受限支持 |

`compare` 函数 **不能编译** — 两个 `some Equatable` 是不同的 Opaque Type，编译器无法保证它们是同一类型。

**代码示例**:
```swift
// some 的使用场景
protocol Animal {
    associatedtype Food
    func eat(_ food: Food)
}

struct Cat: Animal {
    func eat(_ food: String) { print("Cat eats \(food)") }
}

// some 保留了 associated type 信息
func makePet() -> some Animal { Cat() }
let pet = makePet()
pet.eat("fish") // ✅ 编译器知道 Food == String

// any 的使用场景
func feedAll(_ animals: [any Animal]) {
    // 无法直接调用 eat，因为不知道 Food 类型
    // 需要 type eraser 或 Primary Associated Types (Swift 5.7+)
}

// Primary Associated Types（追问 3）
protocol Collection2<Element> {  // Swift 5.7+
    associatedtype Element
}
func process(_ items: some Collection2<Int>) { }  // 约束 Element 为 Int
```

**追问链**:

- **Q1: 为什么要区分 some 和 any？**
- A: Swift 5.1 引入 `some` 用于零成本抽象（编译器知道具体类型）。Swift 5.6 引入 `any` 作为显式标记，提醒开发者 Existential 有性能开销。强制区分让开发者有意识地选择性能 vs 灵活性。

- **Q2: Existential 的性能开销？**
- A: (1) 40 bytes Existential Container；(2) 通过 PWT 间接方法调用；(3) 大值类型需堆分配；(4) 阻止编译器内联和特化优化。在热路径上可能有 2-10x 性能差异。

- **Q3: Primary Associated Types 如何简化使用？**
- A: Swift 5.7 允许协议声明主要关联类型：`protocol Collection<Element>`，使得 `some Collection<Int>` 和 `any Collection<Int>` 可以约束关联类型，大幅简化泛型代码。

**评估标准**:
- 中级：知道 some/any 的基本区别
- 高级：理解性能差异和 Existential Container
- 专家：能在架构设计中合理选择，理解 Primary Associated Types

---

### 题目 2: 泛型特化的原理与性能影响

**难度**: 高级
**考察点**: 编译器特化策略、WMO、跨模块限制

**问题**: 泛型函数在运行时是如何被调用的？何时会被特化？

**参考答案**:

Swift 泛型有两种执行方式：
1. **未特化**：通过 Value Witness Table 操作值，间接调用方法
2. **特化（Specialization）**：编译器为具体类型生成独立函数副本，等价于手写具体类型代码

```swift
// 泛型函数
func swapValues<T>(_ a: inout T, _ b: inout T) {
    let temp = a
    a = b
    b = temp
}

// 特化后（编译器自动生成）
func swapValues_Int(_ a: inout Int, _ b: inout Int) {
    let temp = a
    a = b
    b = temp
}
```

**代码示例**:
```swift
// @_specialize 提示编译器特化（非官方 API）
@_specialize(where T == Int)
@_specialize(where T == Double)
func genericSum<T: Numeric>(_ array: [T]) -> T {
    array.reduce(0, +)
}

// @inlinable 允许跨模块特化
@inlinable
public func publicGenericFunction<T: Comparable>(_ a: T, _ b: T) -> T {
    a > b ? a : b
}
```

**追问链**:

- **Q1: 编译器何时会特化？**
- A: (1) 同模块内，编译器在优化级别 `-O` 以上自动特化高频泛型调用；(2) WMO（Whole Module Optimization）开启时特化范围扩大到整个模块；(3) 跨模块需要 `@inlinable` 暴露函数体。

- **Q2: 跨模块特化的限制？**
- A: 默认情况下，模块 A 的泛型函数在模块 B 中无法特化，因为 B 看不到 A 的函数体。解决方案：(1) `@inlinable` 标记将函数体暴露给调用方模块；(2) 代价是函数体成为 ABI 的一部分，修改会破坏二进制兼容性。

**评估标准**:
- 中级：知道泛型有运行时开销
- 高级：理解特化原理和 WMO 的作用
- 专家：能分析跨模块特化的 ABI 影响

---

### 题目 3: 类型擦除的三种实现模式

**难度**: 高级
**考察点**: 类型擦除必要性、Box 模式、闭包模式、any 关键字

**问题**: 什么时候需要类型擦除？有哪些实现方式？

**参考答案**:

当协议有 `associatedtype` 或 `Self` 要求时，不能直接用作类型（Swift 5.6 之前），需要类型擦除。

**三种模式**:

```swift
// 协议定义
protocol DataSource {
    associatedtype Item
    func fetch() -> [Item]
}

// === 模式 1: Box/Wrapper 模式（经典）===
struct AnyDataSource<Item>: DataSource {
    private let _fetch: () -> [Item]
    
    init<D: DataSource>(_ source: D) where D.Item == Item {
        _fetch = source.fetch
    }
    
    func fetch() -> [Item] { _fetch() }
}

// === 模式 2: 闭包擦除模式 ===
struct ClosureDataSource<Item>: DataSource {
    private let fetchClosure: () -> [Item]
    
    init(fetch: @escaping () -> [Item]) {
        fetchClosure = fetch
    }
    
    func fetch() -> [Item] { fetchClosure() }
}

// === 模式 3: any 关键字（Swift 5.7+）===
func processAny(_ source: any DataSource) {
    // 编译器自动处理类型擦除
}

// 配合 Primary Associated Types
protocol DataSource2<Item> {
    associatedtype Item
    func fetch() -> [Item]
}

func processTyped(_ source: any DataSource2<String>) {
    let items = source.fetch() // items: [String]
}
```

**追问链**:

- **Q1: AnyPublisher 是如何实现的？**
- A: Combine 的 `AnyPublisher` 使用 Box 模式，内部持有一个 `Box` 基类的引用，通过子类化（`PublisherBox<P>`）存储具体 Publisher 实例。`eraseToAnyPublisher()` 创建此包装。

- **Q2: Swift 5.7+ 的 any 关键字如何简化类型擦除？**
- A: `any Protocol` 让编译器自动生成 Existential Container，无需手写 AnyXxx 包装器。配合 Primary Associated Types，可以约束关联类型：`any Collection<Int>`。但仍有 Existential 性能开销，热路径建议用 `some`。

**评估标准**:
- 中级：知道类型擦除的必要性
- 高级：能实现 Box 模式和闭包模式
- 专家：理解 any 的内部实现及性能 trade-off

---

## 五、并发编程 Top 3

### 题目 1: Actor 的隔离机制与 reentrancy 陷阱

**难度**: 高级
**考察点**: Actor 隔离、reentrancy、@MainActor、与 GCD 对比

**问题**:
```swift
actor BankAccount {
    var balance: Int = 1000
    
    func withdraw(_ amount: Int) async -> Bool {
        guard balance >= amount else { return false }
        // 假设这里有一个 await 操作
        try? await Task.sleep(nanoseconds: 1_000_000)
        balance -= amount
        return true
    }
}

// 这段代码有什么问题？
let account = BankAccount()
async let r1 = account.withdraw(800)
async let r2 = account.withdraw(800)
let results = await (r1, r2)
// 可能两次都返回 true 吗？
```

**参考答案**:

**是的，两次都可能返回 true！** 这就是 Actor 的 reentrancy 陷阱。

Actor 保证一次只有一个任务执行其方法，但 **`await` 是挂起点**。当 `withdraw` 在 `await Task.sleep` 处挂起时，另一个 `withdraw` 调用可以开始执行。两个调用都可能在 `balance >= amount` 检查时看到 `balance == 1000`，然后各扣 800，导致余额变为 -600。

**代码示例**:
```swift
// 修复方案：将检查和修改合并为同步操作
actor SafeBankAccount {
    var balance: Int = 1000
    
    // 方案 1: 避免在关键区间 await
    func withdraw(_ amount: Int) -> Bool {
        guard balance >= amount else { return false }
        balance -= amount  // 检查和修改之间没有 await
        return true
    }
    
    // 方案 2: 如果必须 await，使用状态机
    private var pendingWithdrawals: Int = 0
    
    func safeWithdraw(_ amount: Int) async -> Bool {
        let available = balance - pendingWithdrawals
        guard available >= amount else { return false }
        pendingWithdrawals += amount
        
        // 可以安全 await，因为已预留额度
        try? await Task.sleep(nanoseconds: 1_000_000)
        
        balance -= amount
        pendingWithdrawals -= amount
        return true
    }
}
```

**追问链**:

- **Q1: Actor 与 GCD 串行队列的区别？**
- A: (1) Actor 基于协作式调度（cooperative），不阻塞线程；GCD 串行队列是抢占式的；(2) Actor 在 `await` 处可能让出执行权（reentrancy），串行队列保证 FIFO 执行；(3) Actor 有编译器隔离检查，GCD 无静态安全保证；(4) Actor 与 Swift 并发模型深度集成。

- **Q2: reentrancy 会导致什么问题？如何解决？**
- A: 如上所示，reentrancy 导致 TOCTOU（Time-of-Check-to-Time-of-Use）竞态。解决方案：(1) 将状态检查和修改放在同一个同步代码块中（无 await）；(2) 使用预留/锁定模式；(3) 使用事务性状态更新。

- **Q3: @MainActor 的实现原理？**
- A: `@MainActor` 是一个全局 Actor，其 executor 绑定到主线程的 RunLoop。标记 `@MainActor` 的方法/属性保证在主线程执行。编译器在需要跨 Actor 调用时自动插入 `await` hop。SwiftUI 的 View 协议隐式是 `@MainActor`。

```swift
@MainActor
class ViewModel: ObservableObject {
    @Published var items: [String] = []
    
    func loadItems() async {
        let data = await fetchFromNetwork()  // 后台执行
        items = data  // 自动回到主线程（@MainActor 保证）
    }
}
```

**评估标准**:
- 中级：知道 Actor 保证线程安全
- 高级：理解 reentrancy 陷阱并能给出修复方案
- 专家：能对比 Actor 与 GCD 的调度模型差异

---

### 题目 2: Sendable 协议的作用与 Swift 6 的严格模式

**难度**: 高级-专家
**考察点**: 并发安全、Sendable 推断、迁移策略

**问题**:
```swift
class UserCache {
    var users: [String: User] = [:]
}

// 以下代码在 Swift 6 严格并发模式下能编译吗？
let cache = UserCache()
Task {
    cache.users["alice"] = User(name: "Alice") // ?
}
```

**参考答案**:

**不能编译。** Swift 6 严格并发检查模式下，`UserCache` 不满足 `Sendable`（可变 class），跨并发域（Task 边界）传递非 Sendable 类型会报错。

**代码示例**:
```swift
// 什么类型自动满足 Sendable？（追问 1）

// ✅ 自动 Sendable
struct Point: Sendable {  // 值类型，所有属性也是 Sendable
    var x: Double
    var y: Double
}

enum Direction: Sendable { // 枚举，关联值都是 Sendable
    case north, south, east, west
}

// ❌ 不自动 Sendable
class MutableState { // class 默认不是 Sendable
    var count = 0
}

// ✅ 让 class 成为 Sendable 的方式
final class ImmutableConfig: Sendable { // final + 所有属性不可变
    let apiKey: String
    let timeout: TimeInterval
    init(apiKey: String, timeout: TimeInterval) {
        self.apiKey = apiKey
        self.timeout = timeout
    }
}

// @unchecked Sendable（追问 2）
final class ThreadSafeCache: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [String: Any] = [:]
    
    func get(_ key: String) -> Any? {
        lock.lock()
        defer { lock.unlock() }
        return storage[key]
    }
    
    func set(_ key: String, value: Any) {
        lock.lock()
        defer { lock.unlock() }
        storage[key] = value
    }
}
```

**追问链**:

- **Q1: 什么类型自动满足 Sendable？**
- A: (1) 值类型（struct/enum），且所有存储属性/关联值都是 Sendable；(2) Actor 类型；(3) `final class`，所有存储属性都是不可变的 `let` 且类型为 Sendable；(4) 函数/闭包（标记 `@Sendable` 时）。

- **Q2: @unchecked Sendable 的使用场景和风险？**
- A: 当类型通过内部同步机制（锁、原子操作）保证线程安全，但编译器无法静态验证时使用。风险：编译器放弃检查，线程安全由开发者保证。误用会导致数据竞争。

- **Q3: 从 Swift 5 迁移到 Swift 6 的主要挑战？**
- A: (1) 现有 class 需评估 Sendable 兼容性；(2) 闭包捕获需标记 `@Sendable`；(3) 全局可变状态需迁移到 Actor 或 Sendable 类型；(4) 第三方库可能未适配。建议渐进式迁移：先开启 `-strict-concurrency=targeted`，再升级到 `complete`。

**评估标准**:
- 中级：知道 Sendable 用于并发安全
- 高级：理解自动推断规则和 @unchecked 场景
- 专家：能制定 Swift 6 迁移策略

---

### 题目 3: 结构化并发 vs 非结构化任务

**难度**: 高级
**考察点**: TaskGroup、Task.detached、取消传播、生命周期管理

**问题**:
```swift
// 以下三种方式有什么区别？
// 方式 1: 结构化并发
func fetchAll() async throws -> [Data] {
    try await withThrowingTaskGroup(of: Data.self) { group in
        for url in urls {
            group.addTask { try await fetch(url) }
        }
        return try await group.reduce(into: []) { $0.append($1) }
    }
}

// 方式 2: 非结构化任务
func startFetch() {
    Task { try await fetch(url) }
}

// 方式 3: 分离任务
func startDetached() {
    Task.detached { try await fetch(url) }
}
```

**参考答案**:

| 维度 | TaskGroup | Task { } | Task.detached |
|------|-----------|----------|---------------|
| 生命周期 | 受 withTaskGroup 作用域管理 | 继承当前 Actor 上下文 | 完全独立 |
| 取消传播 | 父取消 → 自动取消所有子任务 | 继承父任务取消 | 不继承取消 |
| Actor 继承 | 继承 | 继承（@MainActor 等） | **不继承** |
| 优先级 | 继承 | 继承 | 可独立设置 |

**代码示例**:
```swift
// TaskGroup 的生命周期保证（追问 1）
func processImages(_ images: [UIImage]) async -> [UIImage] {
    await withTaskGroup(of: (Int, UIImage).self) { group in
        for (index, image) in images.enumerated() {
            group.addTask {
                let processed = await applyFilter(image)
                return (index, processed)
            }
        }
        
        var results = [UIImage?](repeating: nil, count: images.count)
        for await (index, image) in group {
            results[index] = image
        }
        return results.compactMap { $0 }
    }
    // 到达这里时，所有子任务保证完成或取消
}

// 取消传播机制（追问 3）
func fetchWithCancellation() async throws -> Data {
    try await withThrowingTaskGroup(of: Data.self) { group in
        group.addTask {
            try await fetchFromServer1()
        }
        group.addTask {
            try await fetchFromServer2()
        }
        
        // 取第一个成功的结果
        let first = try await group.next()!
        group.cancelAll()  // 手动取消剩余任务
        return first
    }
}

// Task.detached 的使用场景（追问 2）
@MainActor
class ViewController {
    func exportFile() {
        // 不想在主线程执行，也不想继承 @MainActor
        Task.detached(priority: .background) {
            let data = await self.prepareExport()
            await self.saveToFile(data)
        }
    }
}
```

**追问链**:

- **Q1: TaskGroup 的生命周期保证？**
- A: `withTaskGroup` 作用域结束前，所有子任务必须完成（正常完成或被取消）。这是结构化并发的核心：任务树形结构，父任务绝不会在子任务运行时结束。

- **Q2: Task.detached 的使用场景？**
- A: (1) 不想继承当前 Actor 上下文时（如避免 @MainActor）；(2) 需要独立优先级的后台任务；(3) fire-and-forget 日志、分析上报。注意：过度使用会丧失结构化并发的取消传播和生命周期保证优势。

- **Q3: 取消传播机制如何工作？**
- A: 取消是协作式的：(1) 父任务取消 → 所有子任务标记为取消；(2) 子任务通过 `Task.isCancelled` 或 `try Task.checkCancellation()` 检测；(3) 取消不会强制中断，任务代码需主动响应。`withTaskGroup` 在作用域退出时自动取消未完成的子任务。

**评估标准**:
- 中级：知道 TaskGroup 的基本用法
- 高级：理解取消传播和 Actor 继承行为
- 专家：能在复杂场景中选择合适的并发原语

---

## 六、内存管理 Top 3

### 题目 1: ARC 的工作原理与循环引用的解决方案

**难度**: 中级
**考察点**: 引用计数、weak/unowned 选择、闭包捕获列表

**问题**:
```swift
class Person {
    let name: String
    var apartment: Apartment?
    init(name: String) { self.name = name }
    deinit { print("\(name) is being deinitialized") }
}

class Apartment {
    let unit: String
    var tenant: Person?
    init(unit: String) { self.unit = unit }
    deinit { print("Apartment \(unit) is being deinitialized") }
}

var john: Person? = Person(name: "John")
var unit4A: Apartment? = Apartment(unit: "4A")
john?.apartment = unit4A
unit4A?.tenant = john

john = nil    // deinit 会调用吗？
unit4A = nil  // deinit 会调用吗？
```

**参考答案**:

**两个 deinit 都不会调用** — 存在循环强引用。`Person` → `Apartment`，`Apartment` → `Person`，引用计数无法归零。

**代码示例**:
```swift
// 修复方案
class FixedApartment {
    let unit: String
    weak var tenant: Person?  // weak 打破循环
    init(unit: String) { self.unit = unit }
    deinit { print("Apartment \(unit) is being deinitialized") }
}

// 闭包中的循环引用（追问 2）
class NetworkManager {
    var onComplete: (() -> Void)?
    
    func fetch() {
        // ❌ 循环引用: self → onComplete → self
        onComplete = {
            self.handleResult()
        }
        
        // ✅ 方案 1: [weak self]
        onComplete = { [weak self] in
            guard let self else { return }
            self.handleResult()
        }
        
        // ✅ 方案 2: [unowned self]（确定 self 生命周期更长时）
        onComplete = { [unowned self] in
            self.handleResult()
        }
    }
    
    func handleResult() { }
}
```

**追问链**:

- **Q1: weak 和 unowned 的区别？选择标准？**
- A:

| 维度 | `weak` | `unowned` |
|------|--------|-----------|
| 类型 | Optional（自动变 nil） | Non-Optional |
| 性能 | 略慢（需 side table 管理） | 略快（直接引用） |
| 安全性 | 安全（访问 nil 不崩溃） | 不安全（对象释放后访问崩溃） |
| 选择 | 引用对象可能先释放 | 引用对象保证同生命周期或更长 |

- **Q2: 闭包中的 [weak self] vs [unowned self]？**
- A: `[weak self]` 更安全，适用于异步回调（网络请求、定时器）。`[unowned self]` 适用于闭包与 self 同生命周期的场景（如 lazy 属性的闭包）。Swift 5.7+ 支持 `guard let self` 简化 weak self 解包。

- **Q3: 如何用 Instruments 检测内存泄漏？**
- A: (1) Xcode Memory Graph Debugger（Debug Navigator → Memory）查看对象引用关系；(2) Instruments → Leaks 模板实时监测泄漏；(3) Instruments → Allocations 追踪对象生命周期。关注 malloc/free 不匹配和 Persistent 对象数量持续增长。

**评估标准**:
- 初级：知道 ARC 自动管理引用计数
- 中级：能识别和修复循环引用
- 高级：能选择 weak/unowned 并使用 Instruments 分析

---

### 题目 2: COW（写时复制）的实现机制

**难度**: 中级-高级
**考察点**: isKnownUniquelyReferenced、自定义 COW、性能分析

**问题**: 如何为自定义类型实现 COW？

**参考答案**:

```swift
// 自定义 COW 实现（追问 2）
final class StorageBuffer<Element> {
    var elements: [Element]
    init(_ elements: [Element]) { self.elements = elements }
}

struct COWArray<Element> {
    private var buffer: StorageBuffer<Element>
    
    init(_ elements: [Element] = []) {
        buffer = StorageBuffer(elements)
    }
    
    var count: Int { buffer.elements.count }
    
    // 读操作：直接访问
    subscript(index: Int) -> Element {
        get { buffer.elements[index] }
        set {
            // 写操作：检查唯一引用
            copyIfNeeded()
            buffer.elements[index] = newValue
        }
    }
    
    mutating func append(_ element: Element) {
        copyIfNeeded()
        buffer.elements.append(element)
    }
    
    // 核心：写前检查唯一引用
    private mutating func copyIfNeeded() {
        if !isKnownUniquelyReferenced(&buffer) {
            buffer = StorageBuffer(buffer.elements)
        }
    }
}

// 使用
var a = COWArray([1, 2, 3])
var b = a           // 共享 buffer
b.append(4)         // b 触发 COW，获得独立 buffer
print(a.count)      // 3 — a 不受影响
print(b.count)      // 4
```

**追问链**:

- **Q1: isKnownUniquelyReferenced 的作用？**
- A: 检查引用类型实例是否只有一个强引用。返回 true 时可安全原地修改（无需拷贝），返回 false 时必须拷贝。这是 COW 的核心判断。注意：仅对 Swift 原生 class 有效，对 NSObject 子类始终返回 false。

- **Q2: 如何实现自定义 COW 类型？**
- A: 如上代码。关键三步：(1) 用 class 存储底层数据；(2) 所有 mutating 操作前调用 `isKnownUniquelyReferenced`；(3) 非唯一引用时复制底层存储。

- **Q3: COW 对性能的影响？**
- A: 优点：避免不必要的拷贝，大幅减少大型集合的赋值开销。开销：`isKnownUniquelyReferenced` 本身很轻量（检查引用计数），但首次写时的拷贝是 O(n)。最佳实践：避免不必要的中间变量赋值，减少 COW 触发次数。

**评估标准**:
- 中级：知道 Array 有 COW 优化
- 高级：能手写 isKnownUniquelyReferenced + COW 实现
- 专家：能分析 COW 在不同场景下的性能 trade-off

---

### 题目 3: ~Copyable 类型与所有权系统（Swift 5.9+/6.0）

**难度**: 专家
**考察点**: 非可复制类型、consuming/borrowing、与 Rust 对比

**问题**: Swift 为什么引入 ~Copyable？有什么典型应用场景？

**参考答案**:

`~Copyable` 表示类型不自动支持复制。这让 Swift 可以在值类型层面管理独占资源（文件句柄、数据库连接、锁），保证资源不会被意外复制。

**代码示例**:
```swift
// ~Copyable 基础
struct FileHandle: ~Copyable {
    private let fd: Int32
    
    init(path: String) {
        fd = open(path, O_RDONLY)
    }
    
    // consuming 方法：调用后 self 被消耗，不可再用
    consuming func close() {
        Darwin.close(fd)
    }
    
    // borrowing 方法：只读借用 self
    borrowing func read(count: Int) -> Data {
        var buffer = [UInt8](repeating: 0, count: count)
        Darwin.read(fd, &buffer, count)
        return Data(buffer)
    }
    
    deinit {
        Darwin.close(fd)
    }
}

// 使用
func processFile() {
    let handle = FileHandle(path: "/tmp/test.txt")
    let data = handle.read(count: 1024)  // borrowing：handle 仍可用
    handle.close()                        // consuming：handle 被消耗
    // handle.read(count: 1)              // ❌ 编译错误：handle 已被消耗
}
```

**追问链**:

- **Q1: consuming vs borrowing 参数的区别？**
- A:

| 修饰符 | 语义 | 调用后 |
|--------|------|--------|
| `borrowing` | 只读借用，不转移所有权 | 调用者仍持有值 |
| `consuming` | 转移所有权到被调函数 | 调用者不再持有值 |
| `inout` | 独占可变借用 | 调用者仍持有修改后的值 |

- **Q2: ~Copyable 的典型应用场景？**
- A: (1) 系统资源管理（文件、socket、GPU buffer）；(2) 独占锁/信号量；(3) 一次性令牌（如网络请求 token）；(4) 状态机中不可重复的状态转换。核心价值：编译期保证资源不被复制或使用后访问。

- **Q3: 与 Rust 所有权系统的对比？**
- A:

| 维度 | Swift ~Copyable | Rust Ownership |
|------|----------------|----------------|
| 默认行为 | 可复制（opt-out） | 不可复制（opt-in Copy） |
| 借用检查 | 编译期（有限） | 编译期（完整 borrow checker） |
| 生命周期标注 | 无（靠 ARC） | 显式 lifetime annotation |
| 适用范围 | struct/enum | 所有类型 |
| 成熟度 | 早期阶段（Swift 5.9+） | 成熟（Rust 1.0+） |

Swift 采用了更渐进的方式：默认可复制，通过 `~Copyable` 显式退出。Rust 则从底层就构建了完整的所有权系统。

**评估标准**:
- 高级：知道 ~Copyable 的存在和基本语义
- 专家：能实现 ~Copyable 类型并对比 Rust 所有权模型

---

## 七、性能优化 Top 3

### 题目 1: Swift 方法派发的三种方式及性能影响

**难度**: 中级-高级
**考察点**: Static Dispatch / VTable Dispatch / Message Dispatch

**问题**: 以下每个方法调用使用什么派发方式？

```swift
protocol Runnable {
    func run()
}

class Animal {
    func speak() { }           // (1)
    final func breathe() { }   // (2)
}

class Dog: Animal, Runnable {
    override func speak() { }  // (3)
    func run() { }             // (4)
    func fetch() { }           // (5)
}

extension Animal {
    func sleep() { }           // (6)
}

extension Runnable {
    func warmUp() { }          // (7) 非协议要求
}

struct Cat: Runnable {
    func run() { }             // (8)
    func purr() { }            // (9)
}
```

**参考答案**:

| 方法 | 派发方式 | 原因 |
|------|----------|------|
| (1) `Animal.speak()` | VTable | class 方法默认 VTable |
| (2) `Animal.breathe()` | Static | `final` 关键字 |
| (3) `Dog.speak()` | VTable | override → VTable |
| (4) `Dog.run()` | VTable + Witness Table | class 遵循协议 |
| (5) `Dog.fetch()` | VTable | class 新增方法 |
| (6) `Animal.sleep()` | Static | Extension 中的方法 |
| (7) `Runnable.warmUp()` | Static | Extension 中非协议要求 |
| (8) `Cat.run()` | Static / Witness Table | struct → 直接调用/通过协议时 PWT |
| (9) `Cat.purr()` | Static | struct 方法 |

**派发方式对比**:

| 派发方式 | 性能 | 可 inline | 使用场景 |
|----------|------|-----------|----------|
| Static | 最快 | ✅ | struct 方法、final、Extension |
| VTable | 中等 | ❌ | class 方法、override |
| Message | 最慢 | ❌ | @objc dynamic、NSObject 子类 |

**代码示例**:
```swift
// final 对性能的影响（追问 2）
class BaseProcessor {
    func process(_ data: Data) -> Data { data }       // VTable
    final func validate(_ data: Data) -> Bool { true } // Static
}

// 编译器在 WMO 模式下，如果发现 process() 没有被 override，
// 会自动将其优化为 Static Dispatch（去虚拟化 devirtualization）

// Extension 中方法的派发方式（追问 3）
class MyView: UIView {
    func customMethod() { }  // VTable
}

extension MyView {
    func extensionMethod() { }  // Static Dispatch!
    // 如果子类「override」这个方法，不会生效（静态派发不走 VTable）
}
```

**追问链**:

- **Q1: 如何确定一个方法使用哪种派发？**
- A: 规则：struct/enum → Static；class 方法 → VTable；`final`/`private`/Extension → Static；`@objc dynamic` → Message。可通过 SIL（Swift Intermediate Language）输出确认：`swiftc -emit-sil file.swift`。

- **Q2: final 关键字对性能的影响？**
- A: `final` 强制 Static Dispatch，允许编译器内联。在热路径上，将不需要 override 的方法标记 `final` 可提升约 5-20% 性能。WMO 模式下编译器会自动对内部方法做 devirtualization。

- **Q3: Extension 中方法的派发方式？**
- A: 始终是 Static Dispatch。即使看起来「覆盖」了父类 Extension 中的方法，实际上不走 VTable。这是常见的坑：子类 Extension 中定义同名方法，通过父类引用调用时仍执行父类版本。

**评估标准**:
- 中级：知道 struct 和 class 的派发区别
- 高级：能准确判断每种场景的派发方式
- 专家：能通过 SIL 验证并给出性能优化建议

---

### 题目 2: 编译器优化策略（WMO / 内联 / 泛型特化）

**难度**: 高级-专家
**考察点**: Whole Module Optimization、@inlinable、编译时间分析

**问题**: Swift 编译器有哪些主要优化策略？如何配合使用？

**参考答案**:

| 优化策略 | 原理 | 开启方式 | 效果 |
|----------|------|----------|------|
| WMO | 跨文件分析整个模块 | `-whole-module-optimization` | 更多 devirtualization、内联 |
| 内联 | 将函数体插入调用处 | 自动 / `@inline(__always)` | 消除调用开销 |
| 泛型特化 | 为具体类型生成专用代码 | 自动 / `@_specialize` | 消除泛型间接开销 |
| 去虚拟化 | VTable 调用 → 直接调用 | WMO 自动 | 消除 VTable 查找 |

**代码示例**:
```swift
// @inlinable 的使用（追问 2）
// 在库模块中：
public struct Matrix {
    var storage: [Double]
    
    // @inlinable 暴露函数体给调用方模块
    @inlinable
    public func transposed() -> Matrix {
        // 调用方模块可以内联此方法
        // 但此实现成为 ABI 的一部分！
        var result = Matrix(storage: Array(repeating: 0, count: storage.count))
        // ... 转置逻辑
        return result
    }
    
    // @usableFromInline 暴露内部符号给 @inlinable
    @usableFromInline
    internal func _internalHelper() { }
}

// WMO 的原理（追问 1）
// 无 WMO：编译器逐文件编译，只能在文件内优化
// 有 WMO：编译器看到整个模块，可以：
// - 发现 internal class 没有子类 → devirtualize
// - 发现 internal func 只有一处调用 → inline
// - 分析整个调用图进行常量折叠

// 分析编译时间（追问 3）
// 在终端执行：
// xcodebuild -buildWithTimingSummary
// 或使用 Xcode Build Settings:
// OTHER_SWIFT_FLAGS = -Xfrontend -warn-long-function-bodies=100
//                     -Xfrontend -warn-long-expression-type-checking=100
```

**追问链**:

- **Q1: WMO 的原理和使用场景？**
- A: WMO 让编译器分析整个模块的源码（而非逐文件），获得全局信息进行优化。Release 默认开启。开发时关闭（增量编译更快）。对 `internal` 访问级别的优化效果最显著。

- **Q2: @inlinable 的使用场景和 ABI 影响？**
- A: 用于性能关键的公共 API（如标准库的 `map`、`filter`）。使函数体成为模块公共接口的一部分，调用方可内联。**代价**：修改实现需要调用方重新编译，否则仍用旧版本。用于 Library Evolution 时需格外谨慎。

- **Q3: 如何分析和减少 Swift 编译时间？**
- A: (1) 编译器诊断：`-warn-long-expression-type-checking`；(2) 拆分复杂表达式并添加类型标注；(3) 减少协议一致性和泛型嵌套深度；(4) WMO 在 Release 开启，Debug 关闭；(5) 使用 Xcode Build Timeline 定位慢文件。

**评估标准**:
- 中级：知道 Release/Debug 优化差异
- 高级：理解 WMO 和 @inlinable 的原理
- 专家：能分析和优化模块级编译性能

---

### 题目 3: ABI 稳定性与 Library Evolution

**难度**: 专家
**考察点**: @frozen、resilience、二进制框架分发

**问题**: 什么是 ABI 稳定性？Library Evolution 模式有什么影响？

**参考答案**:

**ABI 稳定性**（Swift 5.0+）：不同版本 Swift 编译器产生的二进制能互相调用。系统 Swift runtime 内置于 OS，App 无需打包 runtime。

**Library Evolution**（Build Libraries for Distribution）：库的新版本可以替换旧版本，无需重新编译使用方。

**代码示例**:
```swift
// @frozen 的作用（追问 1）
// 不使用 @frozen：编译器预留弹性空间
public enum NetworkError: Error {
    case timeout
    case noConnection
    // 未来可以添加新 case，不破坏 ABI
    // 但调用方必须有 default 分支
}

// 使用 @frozen：承诺不再修改
@frozen
public enum Direction {
    case north, south, east, west
    // 不能再添加新 case
    // 好处：调用方可以 exhaustive switch（无需 default）
    // 好处：编译器可以优化内存布局
}

// @frozen struct
@frozen
public struct Point {
    public var x: Double
    public var y: Double
    // 不能添加新存储属性
    // 好处：调用方可以直接访问内存布局（更快）
}
```

**追问链**:

- **Q1: @frozen 的作用和代价？**
- A: `@frozen` 承诺类型的内存布局不再变化。好处：编译器直接内联布局信息，无间接访问开销。代价：不能添加/删除/重排成员，否则破坏 ABI。标准库中 `Optional`、`Array`、`Bool` 都是 `@frozen`。

- **Q2: 二进制框架分发的配置要点？**
- A: (1) Xcode Build Settings 开启 `BUILD_LIBRARY_FOR_DISTRIBUTION = YES`；(2) 生成 `.swiftinterface` 文件（文本格式的模块接口）；(3) 公共 API 需考虑 resilience：非 @frozen 类型有运行时开销；(4) 使用 `@inlinable`、`@usableFromInline` 优化热路径；(5) 测试不同 Swift 版本的兼容性。

**评估标准**:
- 高级：知道 ABI 稳定性的含义
- 专家：能配置二进制框架分发并理解 @frozen 的 trade-off

---

## 八、现代特性 Top 2

### 题目 1: Property Wrappers 的工作原理

**难度**: 中级-高级
**考察点**: wrappedValue、projectedValue、编译器展开

**问题**:
```swift
@propertyWrapper
struct Clamped<Value: Comparable> {
    var wrappedValue: Value {
        didSet { wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound) }
    }
    let range: ClosedRange<Value>
    
    var projectedValue: ClosedRange<Value> { range }
    
    init(wrappedValue: Value, _ range: ClosedRange<Value>) {
        self.range = range
        self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
    }
}

struct Volume {
    @Clamped(0...100) var level: Int = 50
}

var v = Volume()
v.level = 150
print(v.level)     // ?
print(v.$level)    // ?
```

**参考答案**:

```
v.level  → 100    // Clamped 将 150 限制到 0...100
v.$level → 0...100  // projectedValue 返回范围
```

**编译器展开（追问 2）**:
```swift
// @Clamped(0...100) var level: Int = 50
// 编译器展开为：
struct Volume {
    private var _level: Clamped<Int> = Clamped(wrappedValue: 50, 0...100)
    
    var level: Int {
        get { _level.wrappedValue }
        set { _level.wrappedValue = newValue }
    }
    
    var $level: ClosedRange<Int> {
        _level.projectedValue
    }
}
```

**代码示例**:
```swift
// 实际应用：UserDefaults Property Wrapper
@propertyWrapper
struct UserDefault<Value> {
    let key: String
    let defaultValue: Value
    let container: UserDefaults
    
    var wrappedValue: Value {
        get { container.object(forKey: key) as? Value ?? defaultValue }
        set { container.set(newValue, forKey: key) }
    }
    
    // projectedValue 提供 UserDefaults 本身的访问
    var projectedValue: UserDefaults { container }
    
    init(wrappedValue: Value, _ key: String, container: UserDefaults = .standard) {
        self.key = key
        self.defaultValue = wrappedValue
        self.container = container
    }
}

struct Settings {
    @UserDefault("dark_mode") var isDarkMode: Bool = false
    @UserDefault("font_size") var fontSize: Int = 14
}
```

**追问链**:

- **Q1: wrappedValue 和 projectedValue 的关系？**
- A: `wrappedValue` 是属性的「值」，通过属性名访问（`v.level`）。`projectedValue` 是属性的「元数据」，通过 `$` 前缀访问（`v.$level`）。projectedValue 可以是任意类型，SwiftUI 中 `@State` 的 projectedValue 是 `Binding<Value>`。

- **Q2: 编译器如何展开 Property Wrapper？**
- A: 如上代码所示，编译器将 `@Wrapper var x: T = value` 展开为：私有的 `_x: Wrapper<T>` 存储 + computed property `x` 代理到 `wrappedValue` + `$x` 代理到 `projectedValue`。

**评估标准**:
- 中级：能使用 Property Wrapper
- 高级：理解编译器展开原理和 projectedValue 机制
- 专家：能设计复杂的组合 Property Wrapper

---

### 题目 2: Swift Macros 的分类与应用

**难度**: 高级-专家
**考察点**: 宏分类、@Observable 展开、编译器插件

**问题**: Swift 5.9 引入的 Macros 有哪些分类？@Observable 宏做了什么？

**参考答案**:

**Swift Macros 分类**:

| 宏类型 | 标注 | 作用 |
|--------|------|------|
| Freestanding Expression | `#expression` | 生成表达式 |
| Freestanding Declaration | `#declaration` | 生成声明 |
| Attached Peer | `@PeerMacro` | 在同级添加声明 |
| Attached Member | `@MemberMacro` | 在类型内添加成员 |
| Attached Accessor | `@AccessorMacro` | 添加属性访问器 |
| Attached MemberAttribute | `@MemberAttributeMacro` | 给成员添加属性 |
| Attached Conformance | `@ConformanceMacro` | 添加协议一致性 |

**代码示例**:
```swift
// @Observable 宏展开后生成了什么？（追问 1）

// 源代码
@Observable
class UserModel {
    var name: String = ""
    var age: Int = 0
}

// @Observable 宏展开后（近似）：
class UserModel: Observable {
    // 原始属性变为 computed property + 私有存储
    var name: String {
        get {
            access(keyPath: \.name)  // 注册观察
            return _name
        }
        set {
            withMutation(keyPath: \.name) {  // 通知变更
                _name = newValue
            }
        }
    }
    
    var age: Int {
        get {
            access(keyPath: \.age)
            return _age
        }
        set {
            withMutation(keyPath: \.age) {
                _age = newValue
            }
        }
    }
    
    // 生成私有存储
    private var _name: String = ""
    private var _age: Int = 0
    
    // 生成观察基础设施
    @ObservationIgnored private let _$observationRegistrar = ObservationRegistrar()
    
    internal nonisolated func access<Member>(keyPath: KeyPath<UserModel, Member>) {
        _$observationRegistrar.access(self, keyPath: keyPath)
    }
    
    internal nonisolated func withMutation<Member, MutationResult>(
        keyPath: KeyPath<UserModel, Member>,
        _ mutation: () throws -> MutationResult
    ) rethrows -> MutationResult {
        try _$observationRegistrar.withMutation(of: self, keyPath: keyPath, mutation)
    }
}
```

**追问链**:

- **Q1: @Observable 宏展开后生成了什么？**
- A: 如上所示。核心：(1) 将存储属性转为 computed + 私有存储；(2) 在 getter 中注册属性访问（观察追踪）；(3) 在 setter 中发送变更通知；(4) 添加 ObservationRegistrar 基础设施。这比 `@Published` + `ObservableObject` 更高效，因为只追踪实际访问的属性。

- **Q2: 宏与 Protocol Extension 的使用场景对比？**
- A:

| 维度 | Macros | Protocol Extension |
|------|--------|--------------------|
| 能力 | 代码生成、语法变换 | 默认方法实现 |
| 时机 | 编译前展开 | 编译时链接 |
| 灵活性 | 可生成任意代码 | 受限于协议接口 |
| 调试 | 可查看展开代码 | 隐式行为 |
| 适用 | 样板代码消除、DSL | 共享行为、多态 |

Protocol Extension 适合提供默认行为，Macros 适合消除样板代码和实现编译时代码生成。

**评估标准**:
- 中级：知道 @Observable 的使用方式
- 高级：理解宏展开后的代码
- 专家：能实现自定义 Macro

---

## 九、综合设计题

### 设计题 1: 线程安全的缓存系统

**难度**: 高级
**考察点**: Actor + 泛型 + async/await + 过期策略

**问题**: 设计一个线程安全、支持过期策略的泛型缓存系统。

**参考答案**:

```swift
actor Cache<Key: Hashable & Sendable, Value: Sendable> {
    private struct Entry {
        let value: Value
        let expiration: Date
        let cost: Int
    }
    
    private var storage: [Key: Entry] = [:]
    private let maxCost: Int
    private var currentCost: Int = 0
    
    init(maxCost: Int = .max) {
        self.maxCost = maxCost
    }
    
    // MARK: - 基本操作
    
    func get(_ key: Key) -> Value? {
        guard let entry = storage[key] else { return nil }
        // 检查过期
        if entry.expiration < Date() {
            storage.removeValue(forKey: key)
            currentCost -= entry.cost
            return nil
        }
        return entry.value
    }
    
    func set(_ key: Key, value: Value, cost: Int = 1, ttl: TimeInterval = 300) {
        // 驱逐策略：超过最大 cost 时移除最早过期的
        if currentCost + cost > maxCost {
            evict(neededCost: cost)
        }
        
        // 如果已存在旧值，先减去旧 cost
        if let existing = storage[key] {
            currentCost -= existing.cost
        }
        
        storage[key] = Entry(
            value: value,
            expiration: Date().addingTimeInterval(ttl),
            cost: cost
        )
        currentCost += cost
    }
    
    func remove(_ key: Key) {
        if let entry = storage.removeValue(forKey: key) {
            currentCost -= entry.cost
        }
    }
    
    func removeAll() {
        storage.removeAll()
        currentCost = 0
    }
    
    // MARK: - 驱逐策略
    
    private func evict(neededCost: Int) {
        // 1. 先移除已过期的
        let now = Date()
        let expiredKeys = storage.filter { $0.value.expiration < now }.map(\.key)
        for key in expiredKeys {
            if let entry = storage.removeValue(forKey: key) {
                currentCost -= entry.cost
            }
        }
        
        // 2. 如果还不够，按过期时间排序移除最早的
        if currentCost + neededCost > maxCost {
            let sorted = storage.sorted { $0.value.expiration < $1.value.expiration }
            for (key, entry) in sorted {
                storage.removeValue(forKey: key)
                currentCost -= entry.cost
                if currentCost + neededCost <= maxCost { break }
            }
        }
    }
    
    // MARK: - 批量操作
    
    func getOrSet(_ key: Key, ttl: TimeInterval = 300, factory: () async throws -> Value) async rethrows -> Value {
        if let cached = get(key) {
            return cached
        }
        let value = try await factory()
        set(key, value: value, ttl: ttl)
        return value
    }
    
    var count: Int { storage.count }
}

// 使用示例
func demo() async {
    let cache = Cache<String, Data>(maxCost: 1024 * 1024) // 1MB
    
    let data = await cache.getOrSet("user_profile") {
        try await fetchUserProfile()
    }
    
    if let cached = await cache.get("user_profile") {
        print("Cache hit: \(cached.count) bytes")
    }
}
```

**评估标准**:
- 线程安全：使用 Actor，所有访问自动序列化
- 泛型设计：Key 和 Value 参数化，Key 要求 Hashable & Sendable
- 过期策略：TTL + cost-based 驱逐
- API 设计：getOrSet 避免缓存穿透
- Sendable 约束：Value 要求 Sendable，保证跨并发域安全

---

### 设计题 2: 类型安全的网络请求层

**难度**: 高级
**考察点**: Protocol + Generic + Codable + async/await

**问题**: 设计一个类型安全的网络请求层，支持不同的 API endpoint。

**参考答案**:

```swift
// MARK: - 协议定义

protocol APIEndpoint: Sendable {
    associatedtype Response: Decodable & Sendable
    
    var path: String { get }
    var method: HTTPMethod { get }
    var headers: [String: String] { get }
    var queryItems: [URLQueryItem] { get }
    var body: (any Encodable & Sendable)? { get }
}

// 默认实现
extension APIEndpoint {
    var method: HTTPMethod { .get }
    var headers: [String: String] { ["Content-Type": "application/json"] }
    var queryItems: [URLQueryItem] { [] }
    var body: (any Encodable & Sendable)? { nil }
}

enum HTTPMethod: String, Sendable {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
}

// MARK: - 具体 Endpoint

struct UserEndpoint: APIEndpoint {
    typealias Response = User
    var path: String { "/api/users/\(userId)" }
    let userId: Int
}

struct UserListEndpoint: APIEndpoint {
    typealias Response = [User]
    var path = "/api/users"
    var queryItems: [URLQueryItem] {
        [URLQueryItem(name: "page", value: "\(page)")]
    }
    let page: Int
}

struct CreateUserEndpoint: APIEndpoint {
    typealias Response = User
    var path = "/api/users"
    var method: HTTPMethod { .post }
    var body: (any Encodable & Sendable)? { payload }
    let payload: CreateUserPayload
}

// MARK: - 模型

struct User: Codable, Sendable {
    let id: Int
    let name: String
    let email: String
}

struct CreateUserPayload: Encodable, Sendable {
    let name: String
    let email: String
}

// MARK: - 网络客户端

actor APIClient {
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    
    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = JSONDecoder()
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase
    }
    
    func send<E: APIEndpoint>(_ endpoint: E) async throws -> E.Response {
        let request = try buildRequest(for: endpoint)
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(statusCode: httpResponse.statusCode, data: data)
        }
        
        return try decoder.decode(E.Response.self, from: data)
    }
    
    private func buildRequest<E: APIEndpoint>(for endpoint: E) throws -> URLRequest {
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: true)!
        components.path = endpoint.path
        if !endpoint.queryItems.isEmpty {
            components.queryItems = endpoint.queryItems
        }
        
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        endpoint.headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }
        
        if let body = endpoint.body {
            request.httpBody = try JSONEncoder().encode(body)
        }
        
        return request
    }
}

enum APIError: Error, Sendable {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int, data: Data)
    case decodingError(Error)
}

// MARK: - 使用示例

func demo() async throws {
    let client = APIClient(baseURL: URL(string: "https://api.example.com")!)
    
    // 类型安全：编译器自动推断返回类型
    let user: User = try await client.send(UserEndpoint(userId: 42))
    let users: [User] = try await client.send(UserListEndpoint(page: 1))
    let newUser: User = try await client.send(
        CreateUserEndpoint(payload: CreateUserPayload(name: "Alice", email: "alice@example.com"))
    )
}
```

**评估标准**:
- 类型安全：每个 Endpoint 关联具体 Response 类型，编译器推断返回值
- 协议设计：APIEndpoint 使用 associatedtype + 默认实现
- 泛型运用：`send<E: APIEndpoint>` 自动特化
- 并发安全：APIClient 用 Actor 隔离，模型满足 Sendable
- 可扩展性：新增 API 只需定义新的 Endpoint struct

---

## 参考资源

- [Swift Language Guide](https://docs.swift.org/swift-book/)
- [Swift Evolution Proposals](https://github.com/apple/swift-evolution)
- [Swift Standard Library Source](https://github.com/apple/swift/tree/main/stdlib)
- [WWDC Sessions on Swift](https://developer.apple.com/videos/swift)
- [Swift Forums - Using Swift](https://forums.swift.org/c/swift-users/)
- 相关模块文档：
  - [01_类型系统与语言基础](../01_类型系统与语言基础/)
  - [02_面向对象与面向协议编程](../02_面向对象与面向协议编程/)
  - [03_泛型编程](../03_泛型编程/)
  - [04_现代Swift核心特性](../04_现代Swift核心特性/)
  - [05_内存管理与资源安全](../05_内存管理与资源安全/)
  - [07_并发编程](../07_并发编程/)
  - [08_性能优化与编译技术](../08_性能优化与编译技术/)

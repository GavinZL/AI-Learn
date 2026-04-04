# C++ 高频面试题解析

> 面向 3 年以上 C++ 开发经验的高级/专家级面试题深度解析

---

## 目录

- [类型系统与语言基础](#一类型系统与语言基础)
- [面向对象与多态](#二面向对象与多态)
- [模板与泛型编程](#三模板与泛型编程)
- [现代 C++ 特性](#四现代c特性)
- [内存管理](#五内存管理)
- [STL](#六stl)
- [并发编程](#七并发编程)
- [性能优化](#八性能优化)
- [方案设计题](#九方案设计题)

---

## 一、类型系统与语言基础

### 题目 1: auto 推导陷阱与初始化列表

**难度**: 高级
**考察点**: auto 类型推导规则、std::initializer_list 语义、类型推导边界

**问题**:
```cpp
auto x = {1, 2, 3};       // x 的类型是什么？
auto y{1, 2, 3};          // C++17 之前和之后有什么区别？
auto z = 1;               // z 的类型是什么？
auto& r = z;              // r 的类型是什么？
auto&& rr = z;            // rr 的类型是什么？（万能引用折叠）
```

**参考答案**:

1. `auto x = {1, 2, 3};` → `std::initializer_list<int>`
   - 当 auto 变量使用 `=` 和 `{}` 初始化时，推导为 `std::initializer_list<T>`
   - 这是 auto 推导的特殊规则，不同于模板实参推导

2. `auto y{1, 2, 3};` → C++17 之前编译错误，C++17 起推导为 `std::initializer_list<int>`
   - C++11/14：直接列表初始化 auto 变量，只能有一个元素
   - C++17：放宽限制，支持多元素初始化列表

3. `auto z = 1;` → `int`
   - auto 忽略顶层 const，忽略引用

4. `auto& r = z;` → `int&`
   - 显式声明引用，保留 const 和引用属性

5. `auto&& rr = z;` → `int&`（左值引用）
   - 万能引用（Universal Reference）：根据初始化表达式推导
   - 左值 → 左值引用，右值 → 右值引用

**代码示例**:
```cpp
#include <iostream>
#include <type_traits>
#include <initializer_list>

int main() {
    auto x = {1, 2, 3};
    static_assert(std::is_same_v<decltype(x), std::initializer_list<int>>);
    
    auto z = 1;
    auto& r = z;
    auto&& rr = z;  // int&（左值）
    auto&& rrv = 42; // int&&（右值）
    
    std::cout << "rr is lvalue ref: " << std::is_lvalue_reference_v<decltype(rr)> << "\n";
    std::cout << "rrv is rvalue ref: " << std::is_rvalue_reference_v<decltype(rrv)> << "\n";
}
```

**常见错误**:
- 混淆 auto 推导与模板实参推导的差异
- 万能引用被误用为右值引用（需要 `T&&` 在模板参数推导上下文中才是万能引用）
- 忽略 C++17 对直接列表初始化的放宽

**追问**:
- Q: `decltype(auto)` 是什么？
- A: C++14 引入，使用 decltype 规则进行 auto 推导，保留引用和 cv 限定符
- Q: `auto x = {1};` 和 `auto x{1};` 的区别？
- A: 前者是 initializer_list<int>，后者是 int（C++17 之前）

---

### 题目 2: 类型转换安全性分析

**难度**: 高级
**考察点**: 四种 cast 的适用场景、UB 边界、运行时开销

**问题**:
```cpp
class Base { public: virtual ~Base() = default; int x = 10; };
class Derived : public Base { public: int y = 20; };
class Unrelated { public: int z = 30; };

void test_casts() {
    Base* b = new Derived();
    
    // 以下转换哪些安全？哪些有 UB？
    Derived* d1 = static_cast<Derived*>(b);
    Derived* d2 = dynamic_cast<Derived*>(b);
    Derived* d3 = reinterpret_cast<Derived*>(b);
    
    Base* b2 = new Base();
    Derived* d4 = static_cast<Derived*>(b2);  // 安全吗？
    Derived* d5 = dynamic_cast<Derived*>(b2); // 结果是什么？
    
    // const_cast 的使用场景
    const int ci = 42;
    int* p = const_cast<int*>(&ci);
    *p = 100;  // 会发生什么？
    
    // reinterpret_cast 的危险
    Unrelated* u = reinterpret_cast<Unrelated*>(b);
    std::cout << u->z;  // 会发生什么？
}
```

**参考答案**:

1. **static_cast**: 编译期检查，用于相关类型间的转换
   - `d1`: 安全，b 实际指向 Derived 对象
   - `d4`: **UB**！b2 实际指向 Base 对象，static_cast 不会检查运行时类型

2. **dynamic_cast**: 运行时类型检查，仅用于多态类（有虚函数）
   - `d2`: 安全，返回正确的 Derived 指针
   - `d5`: 返回 nullptr，因为 b2 实际不是 Derived 类型
   - 需要 RTTI，有运行时开销

3. **reinterpret_cast**: 位重新解释，最危险
   - `d3`: 语法允许但逻辑错误，结果未定义
   - `u->z`: **UB**！访问不相关类型的内存

4. **const_cast**: 移除 const/volatile
   - `*p = 100`: **UB**！修改真正的 const 对象
   - 合法场景：调用需要非 const 参数的遗留 API，且确定不会修改

**代码示例**:
```cpp
#include <iostream>

class Base { 
public: 
    virtual ~Base() = default; 
    int x = 10; 
};

class Derived : public Base { 
public: 
    int y = 20; 
};

void safe_cast_demo() {
    // 正确用法：dynamic_cast 用于向下转型
    Base* b = new Derived();
    if (Derived* d = dynamic_cast<Derived*>(b)) {
        std::cout << "Downcast succeeded, y = " << d->y << "\n";
    }
    delete b;
    
    // 错误用法演示（不要这样做）
    Base* b2 = new Base();
    // Derived* d = static_cast<Derived*>(b2);  // 危险！不要这样做
    if (Derived* d = dynamic_cast<Derived*>(b2)) {
        // 不会执行，d 为 nullptr
    } else {
        std::cout << "Downcast failed as expected\n";
    }
    delete b2;
}
```

**常见错误**:
- 在多态场景使用 static_cast 向下转型
- 认为 const_cast 后修改总是安全的
- 混淆 reinterpret_cast 与 static_cast 的适用场景

**追问**:
- Q: dynamic_cast 的实现原理？
- A: 通过 vptr 访问 type_info，运行时比较类型信息
- Q: 为什么 dynamic_cast 需要虚函数？
- A: 需要 vtable 中的 type_info 信息进行运行时类型检查

---

### 题目 3: 初始化的坑与对象生命周期

**难度**: 专家
**考察点**: 初始化语法差异、UB、静态初始化顺序

**问题**:
```cpp
// 以下初始化的区别是什么？
int a = 1;
int b(1);
int c{1};
int d = {1};

// 聚合初始化
struct Agg { int x; int y; };
Agg agg1{1, 2};      // OK
Agg agg2 = {1, 2};   // OK
// Agg agg3(1, 2);   // 错误？C++20 呢？

// Narrowing conversion
int e = 3.14;        // 警告
// int f{3.14};      // 错误

// 最令人困惑的解析（Most Vexing Parse）
struct Foo { Foo() {} void bar() {} };
Foo g();             // 这是什么？
Foo h{};             // 这是什么？

// 静态初始化顺序
extern int globalA;
int globalB = globalA + 1;  // 安全吗？
```

**参考答案**:

1. **初始化语法差异**:
   - `int a = 1;` - 拷贝初始化
   - `int b(1);` - 直接初始化
   - `int c{1};` - 直接列表初始化（C++11）
   - `int d = {1};` - 拷贝列表初始化

2. **Most Vexing Parse**:
   - `Foo g();` - **函数声明**！返回 Foo，无参数
   - `Foo h{};` - 值初始化，创建对象
   - 解决方案：使用 `{}` 初始化避免歧义

3. **静态初始化顺序问题**:
   - `globalB = globalA + 1` - **不安全**！
   - 不同翻译单元的动态初始化顺序未定义
   - 解决方案：Construct On First Use Idiom

**代码示例**:
```cpp
#include <iostream>

// 解决静态初始化顺序问题
int& getGlobalA() {
    static int instance = computeA();  // 首次调用时初始化
    return instance;
}

int globalB() {
    return getGlobalA() + 1;  // 安全
}

// Most Vexing Parse 演示
struct Foo { 
    Foo() { std::cout << "Foo constructed\n"; }
    void bar() { std::cout << "bar called\n"; }
};

void vexing_parse_demo() {
    Foo g();   // 函数声明！不是对象创建
    // g.bar();  // 编译错误：g 是函数，不是对象
    
    Foo h{};   // 正确创建对象
    h.bar();   // OK
}

// Narrowing conversion 检测
void narrowing_check() {
    int a = 3.14;      // 警告：narrowing
    // int b{3.14};    // 错误：narrowing conversion
    int c{static_cast<int>(3.14)};  // OK：显式转换
}
```

**常见错误**:
- 使用 `()` 初始化时遇到 Most Vexing Parse
- 忽略不同翻译单元间静态初始化的顺序问题
- 混淆聚合初始化与构造函数调用

**追问**:
- Q: 什么是零初始化、值初始化、默认初始化？
- A: 零初始化（= {} 或静态存储期），值初始化（T() 或 T{}），默认初始化（无初始化器）
- Q: 如何确保静态成员的正确初始化顺序？
- A: 使用函数内的 static 变量（Construct On First Use）

---

## 二、面向对象与多态

### 题目 4: 虚函数表内存布局深度分析

**难度**: 专家
**考察点**: vtable/vptr 实现、内存布局、多重继承

**问题**:
```cpp
class Base1 {
    int x;
    virtual void f1() {}
    virtual void f2() {}
};

class Base2 {
    int y;
    virtual void g1() {}
    virtual void g2() {}
};

class Derived : public Base1, public Base2 {
    int z;
    void f1() override {}
    void g1() override {}
    virtual void h() {}
};

// 问题：
// 1. Derived 对象的大小是多少？（64 位系统）
// 2. Derived 有几个 vptr？分别指向什么？
// 3. 以下调用的汇编级实现？
//    Base1* b1 = new Derived(); b1->f1();
//    Base2* b2 = new Derived(); b2->g1();
```

**参考答案**:

1. **Derived 对象大小**（典型 64 位实现）：
   - Base1: vptr(8) + int(4) + padding(4) = 16
   - Base2: vptr(8) + int(4) + padding(4) = 16
   - Derived: int(4) + padding(4) = 8
   - 总计：40 字节（可能因对齐调整）

2. **vptr 数量**：2 个（多重继承每个基类一个 vptr）
   - Base1 子对象：vptr → Derived 的 Base1 vtable
   - Base2 子对象：vptr → Derived 的 Base2 vtable

3. **虚函数调用实现**：
   - `b1->f1()`: 通过 b1 的 vptr 找到 vtable，偏移 0 调用 f1
   - `b2->g1()`: 需要 this 指针调整！先调整 this 指向 Base2 子对象，再调用

**代码示例**:
```cpp
#include <iostream>
#include <cstddef>

class Base1 {
    int x;
    virtual void f1() { std::cout << "Base1::f1\n"; }
    virtual void f2() { std::cout << "Base1::f2\n"; }
};

class Base2 {
    int y;
    virtual void g1() { std::cout << "Base2::g1\n"; }
    virtual void g2() { std::cout << "Base2::g2\n"; }
};

class Derived : public Base1, public Base2 {
    int z;
    void f1() override { std::cout << "Derived::f1\n"; }
    void g1() override { std::cout << "Derived::g1\n"; }
    virtual void h() { std::cout << "Derived::h\n"; }
};

void vtable_demo() {
    std::cout << "sizeof(Base1): " << sizeof(Base1) << "\n";
    std::cout << "sizeof(Base2): " << sizeof(Base2) << "\n";
    std::cout << "sizeof(Derived): " << sizeof(Derived) << "\n";
    
    Derived d;
    // 查看 vptr 位置（实现相关，非标准）
    void** vptr1 = *reinterpret_cast<void***>(&d);
    std::cout << "Base1 vptr: " << vptr1 << "\n";
    
    // Base2 子对象位置
    Base2* b2 = &d;
    void** vptr2 = *reinterpret_cast<void***>(b2);
    std::cout << "Base2 vptr: " << vptr2 << "\n";
}
```

**常见错误**:
- 认为所有类都有 vptr（只有含虚函数的类才有）
- 忽略多重继承下的 this 指针调整
- 认为 vtable 在对象中（vtable 是类级共享的）

**追问**:
- Q: 构造函数可以是虚函数吗？
- A: 不可以，构造时对象类型还未完整，vptr 尚未设置
- Q: 虚析构函数为什么是必要的？
- A: 确保通过基类指针 delete 派生类对象时正确释放资源

---

### 题目 5: 菱形继承与虚继承内存布局

**难度**: 专家
**考察点**: 虚继承实现、内存开销、构造顺序

**问题**:
```cpp
class A { public: int a; virtual void fa() {} };
class B : public A { public: int b; };
class C : public A { public: int c; };
class D : public B, public C { public: int d; };

// 问题：
// 1. sizeof(D) 是多少？（64 位）
// 2. D 对象中有几份 A 子对象？
// 3. d.a = 10; 为什么编译错误？如何解决？

// 使用虚继承后：
class VB : virtual public A { public: int b; };
class VC : virtual public A { public: int c; };
class VD : public VB, public VC { public: int d; };
// 4. sizeof(VD) 是多少？
// 5. VD 的内存布局是怎样的？
```

**参考答案**:

1. **普通菱形继承**：
   - D 包含：B 子对象（含 A）+ C 子对象（含 A）+ d
   - sizeof(D) ≈ 48 字节（两份 A + 两个 vptr）
   - `d.a` 编译错误：二义性，有两份 a

2. **虚继承解决方案**：
   - 共享基类 A 只有一份
   - 通过 vbptr（虚基类指针）间接访问 A
   - sizeof(VD) ≈ 56 字节（更大，需要额外指针）

3. **虚继承内存布局**（典型实现）：
   ```
   VD 对象：
   ┌─────────────────┐
   │ VB 子对象       │
   │ ├─ vbptr        │ ──→ 偏移表
   │ └─ b            │
   ├─────────────────┤
   │ VC 子对象       │
   │ ├─ vbptr        │ ──→ 偏移表
   │ └─ c            │
   ├─────────────────┤
   │ d               │
   ├─────────────────┤
   │ A 子对象（共享）│
   │ ├─ vptr         │
   │ └─ a            │
   └─────────────────┘
   ```

**代码示例**:
```cpp
#include <iostream>

class A { 
public: 
    int a = 1; 
    virtual void fa() {} 
};

// 普通菱形继承
class B : public A { public: int b = 2; };
class C : public A { public: int c = 3; };
class D : public B, public C { public: int d = 4; };

// 虚继承
class VB : virtual public A { public: int b = 2; };
class VC : virtual public A { public: int c = 3; };
class VD : public VB, public VC { public: int d = 4; };

void diamond_demo() {
    std::cout << "sizeof(D): " << sizeof(D) << "\n";
    std::cout << "sizeof(VD): " << sizeof(VD) << "\n";
    
    D d;
    // d.a = 10;  // 错误：二义性
    d.B::a = 10;  // OK：显式指定
    d.C::a = 20;  // OK：另一份 a
    std::cout << "B::a = " << d.B::a << ", C::a = " << d.C::a << "\n";
    
    VD vd;
    vd.a = 10;  // OK：只有一份 a
    std::cout << "VD::a = " << vd.a << "\n";
}
```

**常见错误**:
- 认为虚继承只是语法糖，不理解内存布局变化
- 忽略虚继承的构造顺序（虚基类最先构造）
- 在不需要时滥用虚继承（有性能开销）

**追问**:
- Q: 虚继承的构造函数有什么特殊？
- A: 虚基类由最派生类直接构造，中间类不构造虚基类
- Q: 虚继承的性能开销？
- A: 额外的间接寻址（通过 vbptr），更大的对象大小

---

### 题目 6: 析构函数陷阱与异常安全

**难度**: 高级
**考察点**: 析构函数异常、异常安全等级、RAII

**问题**:
```cpp
class BadResource {
public:
    ~BadResource() {
        // 可能抛出异常的操作
        cleanup();  // 假设可能抛出
    }
};

void problematic() {
    BadResource r1;
    BadResource r2;
    // 如果 r1 析构时抛出异常，r2 的析构会被调用吗？
}

// 异常安全等级
class Container {
    int* data;
    Logger* logger;
public:
    void update(int* newData) {
        delete data;           // 1
        data = newData;        // 2
        logger->log("updated"); // 3 可能抛出
    }
};
// update 的异常安全等级是什么？如何改进？
```

**参考答案**:

1. **析构函数异常**：
   - 析构函数抛出异常 → 程序调用 std::terminate
   - 栈展开期间析构抛出 → 立即 terminate
   - **原则：析构函数绝不能抛出异常**

2. **problematic() 分析**：
   - 如果 r1 析构抛出 → std::terminate，r2 析构不会执行
   - 如果正常执行，析构顺序与构造相反（r2 先析构）

3. **异常安全等级**：
   - **基本保证**：异常后对象处于有效但不确定状态
   - **强保证**：异常后对象状态不变（事务性）
   - **不抛保证**：承诺不抛出异常

4. **update 改进**：
   ```cpp
   void update(int* newData) {
       int* oldData = data;     // 保存旧值
       data = newData;          // 修改指针
       delete oldData;          // 释放旧资源
       logger->log("updated");  // 可能抛出，但数据已安全
   }
   // 改进为强异常安全（copy-and-swap 更佳）
   ```

**代码示例**:
```cpp
#include <iostream>
#include <memory>
#include <utility>

// 正确的 RAII 类
class SafeResource {
    std::unique_ptr<int> data;
public:
    explicit SafeResource(int v) : data(std::make_unique<int>(v)) {}
    ~SafeResource() noexcept {  // 声明 noexcept
        // 不抛出异常的操作
        std::cout << "Resource cleaned up\n";
    }
};

// 强异常安全的 Container
class SafeContainer {
    std::unique_ptr<int> data;
    std::shared_ptr<class Logger> logger;
public:
    void update(std::unique_ptr<int> newData) {
        // copy-and-swap 惯用法
        auto temp = std::move(newData);
        using std::swap;
        swap(data, temp);  // 不抛操作
        // 现在 temp 持有旧数据，析构时自动释放
        
        if (logger) {
            logger->log("updated");  // 即使抛出，data 已更新
        }
    }
};

// 如果必须在析构中处理可能失败的操作
class ComplexResource {
public:
    ~ComplexResource() noexcept {
        try {
            riskyCleanup();
        } catch (...) {
            // 捕获并记录，不传播
            // 或使用 std::terminate 前的最后手段
        }
    }
private:
    void riskyCleanup() { /* 可能抛出 */ }
};
```

**常见错误**:
- 析构函数中调用可能抛出异常的函数
- 忽略异常安全等级的设计
- 在栈展开期间抛出异常

**追问**:
- Q: noexcept 对移动操作有什么影响？
- A: STL 容器优先使用 noexcept 移动操作，否则回退到拷贝
- Q: 如何实现强异常安全？
- A: copy-and-swap 惯用法：先操作副本，再交换

---

## 三、模板与泛型编程

### 题目 7: SFINAE 原理与 enable_if 应用

**难度**: 专家
**考察点**: SFINAE 机制、enable_if、表达式 SFINAE

**问题**:
```cpp
// 以下代码的输出是什么？
template<typename T>
typename std::enable_if<std::is_integral<T>::value, T>::type
foo(T t) { return t; }

template<typename T>
typename std::enable_if<!std::is_integral<T>::value, T>::type
foo(T t) { return t; }

// C++14/17 简化写法
template<typename T>
std::enable_if_t<std::is_integral_v<T>, T> bar(T t) { return t; }

// 表达式 SFINAE
struct HasFoo { void foo(); };
struct NoFoo {};

template<typename T>
auto call_foo(T t) -> decltype(t.foo(), void()) {
    t.foo();
}

// 问题：
// 1. SFINAE 的全称和原理？
// 2. 为什么需要 decltype(t.foo(), void())？
// 3. C++20 concepts 如何改进？
```

**参考答案**:

1. **SFINAE**（Substitution Failure Is Not An Error）：
   - 模板实参替换失败不是编译错误，只是从重载集中移除
   - 允许基于类型特征进行条件模板重载

2. **decltype(t.foo(), void())**：
   - 逗号运算符：求值 t.foo()，返回 void()
   - 如果 T 没有 foo()，替换失败，SFINAE 生效
   - 返回类型为 void

3. **C++20 concepts**：
   - 更清晰的语法，更好的错误信息
   - `template<Integral T>` 替代冗长的 enable_if

**代码示例**:
```cpp
#include <iostream>
#include <type_traits>
#include <vector>

// C++11/14 SFINAE 方式
template<typename T>
std::enable_if_t<std::is_integral_v<T>, T> process(T t) {
    std::cout << "Integral: " << t << "\n";
    return t;
}

template<typename T>
std::enable_if_t<std::is_floating_point_v<T>, T> process(T t) {
    std::cout << "Floating: " << t << "\n";
    return t;
}

// 检测成员函数存在性
template<typename T, typename = void>
struct has_foo : std::false_type {};

template<typename T>
struct has_foo<T, std::void_t<decltype(std::declval<T>().foo())>> 
    : std::true_type {};

struct WithFoo { void foo() {} };
struct WithoutFoo {};

// 条件调用
template<typename T>
auto call_foo_if_exists(T& t) -> std::enable_if_t<has_foo<T>::value> {
    t.foo();
}

template<typename T>
auto call_foo_if_exists(T&) -> std::enable_if_t<!has_foo<T>::value> {
    std::cout << "No foo to call\n";
}

// C++20 concepts（概念说明）
// template<typename T>
// concept HasFoo = requires(T t) { t.foo(); };
// 
// template<HasFoo T>
// void call_foo(T& t) { t.foo(); }
```

**常见错误**:
- SFINAE 条件过于复杂导致编译错误难以理解
- 混淆编译期 if (if constexpr) 与 SFINAE
- 在函数参数中使用 SFINAE 导致重载决议歧义

**追问**:
- Q: void_t 是什么？
- A: C++17 引入，将任意类型映射为 void，用于检测表达式有效性
- Q: SFINAE 和重载决议的关系？
- A: SFINAE 发生在模板实参替换阶段，决定哪些模板进入重载集

---

### 题目 8: 模板特化优先级与偏特化

**难度**: 高级
**考察点**: 全特化、偏特化、优先级规则

**问题**:
```cpp
template<typename T>
struct Wrapper { static void print() { std::cout << "Primary\n"; } };

// 全特化
template<>
struct Wrapper<int> { static void print() { std::cout << "int\n"; } };

// 偏特化
template<typename T>
struct Wrapper<T*> { static void print() { std::cout << "pointer\n"; } };

template<typename T>
struct Wrapper<const T> { static void print() { std::cout << "const\n"; } };

// 问题：
// Wrapper<double>::print();      // ?
// Wrapper<int>::print();         // ?
// Wrapper<int*>::print();        // ?
// Wrapper<const int>::print();   // ?
// Wrapper<const int*>::print();  // ?（最复杂的情况）
```

**参考答案**:

**特化优先级**（从最匹配到最不匹配）：
1. **全特化**：完全匹配具体类型
2. **偏特化**：匹配模式（指针、引用、const 等）
3. **主模板**：通用版本

**分析**：
- `Wrapper<double>` → Primary（无匹配特化）
- `Wrapper<int>` → int 全特化
- `Wrapper<int*>` → pointer 偏特化（比主模板更匹配）
- `Wrapper<const int>` → const 偏特化
- `Wrapper<const int*>` → **歧义**！pointer 和 const 都匹配

**代码示例**:
```cpp
#include <iostream>

template<typename T>
struct Wrapper { 
    static void print() { std::cout << "Primary\n"; } 
};

// 全特化
template<>
struct Wrapper<int> { 
    static void print() { std::cout << "int specialization\n"; } 
};

// 偏特化：指针
template<typename T>
struct Wrapper<T*> { 
    static void print() { std::cout << "Pointer specialization\n"; } 
};

// 偏特化：const
template<typename T>
struct Wrapper<const T> { 
    static void print() { std::cout << "Const specialization\n"; } 
};

// 解决 const int* 歧义：更具体的偏特化
template<typename T>
struct Wrapper<const T*> { 
    static void print() { std::cout << "Const pointer specialization\n"; } 
};

void specialization_demo() {
    Wrapper<double>::print();       // Primary
    Wrapper<int>::print();          // int specialization
    Wrapper<int*>::print();         // Pointer specialization
    Wrapper<const int>::print();    // Const specialization
    Wrapper<const int*>::print();   // Const pointer specialization
}

// 实际应用：类型萃取
template<typename T>
struct is_pointer : std::false_type {};

template<typename T>
struct is_pointer<T*> : std::true_type {};

template<typename T>
struct remove_const { using type = T; };

template<typename T>
struct remove_const<const T> { using type = T; };
```

**常见错误**:
- 认为偏特化可以像函数重载一样自动选择最匹配
- 忽略全特化必须在命名空间作用域声明
- 模板函数不支持偏特化（只能用重载）

**追问**:
- Q: 为什么函数模板不能偏特化？
- A: 可以用重载实现类似功能，避免与类模板特化规则混淆
- Q: 全特化和偏特化的声明位置要求？
- A: 必须在主模板可见的作用域声明

---

### 题目 9: CRTP 应用与静态多态

**难度**: 高级
**考察点**: CRTP 模式、静态多态、编译期多态

**问题**:
```cpp
// CRTP: Curiously Recurring Template Pattern
template<typename Derived>
class Shape {
public:
    void draw() {
        static_cast<Derived*>(this)->drawImpl();
    }
    double area() const {
        return static_cast<const Derived*>(this)->areaImpl();
    }
};

class Circle : public Shape<Circle> {
public:
    void drawImpl() { /* ... */ }
    double areaImpl() const { return 3.14 * r * r; }
private:
    double r;
};

// 问题：
// 1. CRTP 相比虚函数的优势和劣势？
// 2. 如何防止错误继承（如 class Circle : public Shape<Square>）？
// 3. CRTP 在哪些标准库组件中使用？
```

**参考答案**:

1. **CRTP 优势**：
   - 零运行时开销（无 vptr/vtable）
   - 可内联，编译器优化更激进
   - 编译期确定调用，无间接跳转

2. **CRTP 劣势**：
   - 代码膨胀（每个实例化一份代码）
   - 无法运行时动态绑定
   - 类定义更复杂

3. **错误继承防护**：
   - 使用 static_assert 检查 Derived 继承自正确的基类

4. **标准库应用**：
   - `std::enable_shared_from_this`
   - `std::iterator`（C++17 前）
   - 比较运算符生成（C++20 <=> 之前）

**代码示例**:
```cpp
#include <iostream>
#include <type_traits>

// 安全的 CRTP 基类
template<typename Derived>
class Shape {
    // 编译期检查正确继承
    static_assert(std::is_base_of_v<Shape<Derived>, Derived>,
                  "Derived must inherit from Shape<Derived>");
public:
    void draw() {
        static_cast<Derived*>(this)->drawImpl();
    }
    double area() const {
        return static_cast<const Derived*>(this)->areaImpl();
    }
};

class Circle : public Shape<Circle> {
    double r = 1.0;
public:
    void drawImpl() { 
        std::cout << "Drawing circle\n"; 
    }
    double areaImpl() const { 
        return 3.14159 * r * r; 
    }
};

class Rectangle : public Shape<Rectangle> {
    double w = 2.0, h = 3.0;
public:
    void drawImpl() { 
        std::cout << "Drawing rectangle\n"; 
    }
    double areaImpl() const { 
        return w * h; 
    }
};

// CRTP 实现运算符自动生成
template<typename Derived>
class Comparable {
public:
    bool operator!=(const Derived& other) const {
        return !static_cast<const Derived*>(this)->operator==(other);
    }
    bool operator<=(const Derived& other) const {
        return !(static_cast<const Derived*>(this)->operator>(other));
    }
    // ... 其他运算符
};

class Point : public Comparable<Point> {
    int x, y;
public:
    Point(int x, int y) : x(x), y(y) {}
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
    bool operator<(const Point& other) const {
        return x < other.x || (x == other.x && y < other.y);
    }
    // != 和 <= 由 CRTP 基类自动生成
};

void crtp_demo() {
    Circle c;
    c.draw();
    std::cout << "Area: " << c.area() << "\n";
    
    Point p1(1, 2), p2(1, 3);
    std::cout << "p1 != p2: " << (p1 != p2) << "\n";
}
```

**常见错误**:
- 忘记在 CRTP 基类中使用 static_cast
- 在构造函数中调用虚函数式的方法（对象未完整构造）
- 混淆 CRTP 与 Mixin 模式

**追问**:
- Q: CRTP 和虚函数的性能差异？
- A: CRTP 无间接调用开销，可内联；虚函数有 vtable 查找开销
- Q: 什么时候选择 CRTP 而不是虚函数？
- A: 性能关键路径、类型在编译期确定、需要内联优化

---

### 题目 10: 变参模板与递归展开

**难度**: 专家
**考察点**: 参数包、包展开、折叠表达式

**问题**:
```cpp
// 变参模板基础
template<typename... Args>
void print(Args... args);

// 问题：
// 1. sizeof...(Args) 的值？
// 2. 如何实现递归打印每个参数？
// 3. C++17 折叠表达式如何简化？
// 4. 完美转发变参参数？

// 挑战：实现类型安全的 printf
// safe_printf("%s has %d apples\n", "Alice", 5);
```

**参考答案**:

1. **sizeof...(Args)**：返回参数包中参数的数量

2. **递归展开**：
   - 基础情况：空参数
   - 递归情况：处理第一个，递归处理剩余

3. **C++17 折叠表达式**：
   - `(std::cout << args << ...);` 一元右折叠
   - 更简洁，编译更快

4. **完美转发**：使用 `Args&&...` 和 `std::forward<Args>(args)...`

**代码示例**:
```cpp
#include <iostream>
#include <utility>
#include <string>

// C++11/14: 递归展开
template<typename T>
void print_impl(T&& t) {
    std::cout << std::forward<T>(t) << "\n";
}

template<typename T, typename... Rest>
void print_impl(T&& t, Rest&&... rest) {
    std::cout << std::forward<T>(t) << " ";
    print_impl(std::forward<Rest>(rest)...);
}

template<typename... Args>
void print(Args&&... args) {
    print_impl(std::forward<Args>(args)...);
}

// C++17: 折叠表达式
template<typename... Args>
void print_fold(Args&&... args) {
    (std::cout << ... << std::forward<Args>(args)) << "\n";
}

// 带分隔符的打印
template<typename... Args>
void print_sep(const char* sep, Args&&... args) {
    auto print_with_sep = [&](auto&& arg) {
        std::cout << sep << std::forward<decltype(arg)>(arg);
    };
    (print_with_sep(args), ...);
    std::cout << "\n";
}

// 类型安全的 printf（简化版）
void safe_printf(const char* fmt) {
    std::cout << fmt;
}

template<typename T, typename... Args>
void safe_printf(const char* fmt, T&& value, Args&&... args) {
    while (*fmt) {
        if (*fmt == '%' && *(fmt + 1) != '%') {
            std::cout << std::forward<T>(value);
            safe_printf(fmt + 2, std::forward<Args>(args)...);
            return;
        }
        std::cout << *fmt++;
    }
}

// 编译期计算参数数量
template<typename... Args>
constexpr std::size_t count_args() {
    return sizeof...(Args);
}

// 类型列表
template<typename... Types>
struct TypeList {
    static constexpr std::size_t size = sizeof...(Types);
    
    template<typename T>
    using Append = TypeList<Types..., T>;
};

void variadic_demo() {
    print("Hello", 42, 3.14, "World");
    print_fold("Hello", 42, 3.14);
    
    std::cout << "Count: " << count_args<int, double, char>() << "\n";
    
    safe_printf("%s has %d apples and %f oranges\n", "Alice", 5, 3.5);
}
```

**常见错误**:
- 参数包展开位置错误（必须在可展开上下文中）
- 递归终止条件缺失导致无限递归
- 混淆一元折叠和二元折叠

**追问**:
- Q: 参数包展开可以在哪些上下文？
- A: 函数参数、模板参数、初始化列表、基类列表等
- Q: 折叠表达式的求值顺序？
- A: 一元左折叠从左到右，一元右折叠从右到左

---

## 四、现代 C++ 特性

### 题目 11: 移动语义本质与右值引用

**难度**: 高级
**考察点**: 值类别、移动构造、std::move 本质

**问题**:
```cpp
std::string getString() {
    std::string s = "hello";
    return s;  // 发生什么？
}

void process(std::string s) {}

void test() {
    std::string a = "world";
    process(a);              // 发生什么？
    process(std::move(a));   // 发生什么？
    process(getString());    // 发生什么？
    
    std::string b = a;       // a 还能用吗？
    std::string c = std::move(a);  // 之后 a 的状态？
}

// 实现一个可移动但不可拷贝的类
class UniqueResource {
    int* data;
public:
    // 如何实现？
};
```

**参考答案**:

1. **返回值优化（RVO）**：
   - `return s` → 编译器可能直接构造在返回值位置
   - C++17 起为强制的 guaranteed copy elision

2. **参数传递**：
   - `process(a)`：拷贝构造
   - `process(std::move(a))`：移动构造（a 变为有效但未指定状态）
   - `process(getString())`：可能直接构造（省略移动）

3. **std::move 本质**：
   - 只是转换为右值引用，不执行移动
   - 实际移动发生在移动构造函数/赋值运算符中

4. **移动后状态**：
   - 对象处于有效但未指定状态
   - 可以销毁或重新赋值，但不应依赖其值

**代码示例**:
```cpp
#include <iostream>
#include <string>
#include <utility>

// 可移动但不可拷贝的类
class UniqueResource {
    int* data;
    std::size_t size;
public:
    explicit UniqueResource(std::size_t n) 
        : data(new int[n]), size(n) {
        std::cout << "Constructed\n";
    }
    
    // 禁用拷贝
    UniqueResource(const UniqueResource&) = delete;
    UniqueResource& operator=(const UniqueResource&) = delete;
    
    // 启用移动
    UniqueResource(UniqueResource&& other) noexcept
        : data(other.data), size(other.size) {
        other.data = nullptr;
        other.size = 0;
        std::cout << "Move constructed\n";
    }
    
    UniqueResource& operator=(UniqueResource&& other) noexcept {
        if (this != &other) {
            delete[] data;
            data = other.data;
            size = other.size;
            other.data = nullptr;
            other.size = 0;
        }
        std::cout << "Move assigned\n";
        return *this;
    }
    
    ~UniqueResource() {
        delete[] data;
        std::cout << "Destroyed\n";
    }
    
    bool isValid() const { return data != nullptr; }
};

UniqueResource createResource() {
    return UniqueResource(100);  // 移动或省略
}

void move_demo() {
    auto r1 = createResource();
    auto r2 = std::move(r1);  // 显式移动
    
    std::cout << "r1 valid: " << r1.isValid() << "\n";
    std::cout << "r2 valid: " << r2.isValid() << "\n";
    
    // r1 可以重新赋值
    r1 = createResource();
    std::cout << "r1 valid after assign: " << r1.isValid() << "\n";
}
```

**常见错误**:
- 认为 std::move 执行移动操作（只是类型转换）
- 移动后继续使用原对象
- 移动构造函数不标记 noexcept

**追问**:
- Q: 为什么移动构造函数要 noexcept？
- A: STL 容器在强异常安全保证下，移动可能抛异常时会用拷贝代替
- Q: 左值和右值的本质区别？
- A: 左值有身份（可寻址），右值可移动（通常是临时对象）

---

### 题目 12: 完美转发失败场景

**难度**: 专家
**考察点**: 万能引用、引用折叠、完美转发边界

**问题**:
```cpp
template<typename T>
void perfect_forward(T&& t) {
    foo(std::forward<T>(t));
}

// 以下调用会完美转发吗？
perfect_forward(42);           // 1
int x = 42;
perfect_forward(x);            // 2
perfect_forward(std::move(x)); // 3

// 重载决议问题
void bar(int& x) { std::cout << "lvalue\n"; }
void bar(int&& x) { std::cout << "rvalue\n"; }

template<typename T>
void wrapper(T&& t) {
    bar(t);                    // 4: 输出什么？
    bar(std::forward<T>(t));   // 5: 输出什么？
}

// 失败场景
std::vector<int> v;
perfect_forward(v[0]);         // 6: 能转发吗？
perfect_forward({1, 2, 3});    // 7: 能转发吗？
```

**参考答案**:

1. **万能引用条件**：`T&&` 在模板参数推导上下文中
   - `T` 是模板参数
   - 形式为 `T&&`

2. **调用分析**：
   - `perfect_forward(42)`：T = int，转发为 int&&
   - `perfect_forward(x)`：T = int&，转发为 int&
   - `perfect_forward(std::move(x))`：T = int，转发为 int&&

3. **wrapper 分析**：
   - `bar(t)`：总是输出 "lvalue"（t 有名字）
   - `bar(std::forward<T>(t))`：根据原始值类别转发

4. **失败场景**：
   - `v[0]`：返回引用，但 auto&& 可能不是万能引用
   - `{1,2,3}`：initializer_list，auto 推导为 initializer_list

**代码示例**:
```cpp
#include <iostream>
#include <vector>
#include <utility>

void bar(int& x) { std::cout << "lvalue bar\n"; }
void bar(int&& x) { std::cout << "rvalue bar\n"; }

// 正确的完美转发
template<typename T>
void wrapper(T&& t) {
    std::cout << "Calling bar with forward: ";
    bar(std::forward<T>(t));  // 完美转发
}

// 错误的写法
template<typename T>
void bad_wrapper(T&& t) {
    std::cout << "Calling bar without forward: ";
    bar(t);  // 总是 lvalue！
}

// 0 和 nullptr 转发问题
template<typename T>
void forward_call(T&& t) {
    process(std::forward<T>(t));
}

void process(int* p) { std::cout << "pointer\n"; }
void process(int i) { std::cout << "int\n"; }

void forwarding_demo() {
    int x = 42;
    
    wrapper(42);        // rvalue
    wrapper(x);         // lvalue
    wrapper(std::move(x));  // rvalue
    
    bad_wrapper(42);    // 错误：输出 lvalue bar
    
    // 0 转发问题
    forward_call(0);    // 调用 process(int)
    forward_call(nullptr);  // 调用 process(int*)
}

// 解决方案：显式指定类型或使用重载
template<typename T>
void better_wrapper(T&& t) {
    using ValueType = std::remove_reference_t<T>;
    if constexpr (std::is_integral_v<ValueType>) {
        // 整数类型的特殊处理
    }
    bar(std::forward<T>(t));
}
```

**常见错误**:
- 在万能引用上调用 std::move 而不是 std::forward
- 忽略引用折叠规则（&& + & = &）
- 在 lambda 中错误使用 auto&&（不是万能引用）

**追问**:
- Q: 引用折叠规则？
- A: & + & = &, & + && = &, && + & = &, && + && = &&
- Q: 什么时候 auto&& 不是万能引用？
- A: lambda 参数、函数参数（非模板）、已推导类型

---

### 题目 13: 智能指针线程安全

**难度**: 高级
**考察点**: shared_ptr 原子性、线程安全、循环引用

**问题**:
```cpp
// shared_ptr 的线程安全性
std::shared_ptr<int> global_ptr = std::make_shared<int>(42);

void thread_func() {
    auto local = global_ptr;  // 1: 线程安全吗？
    *local = 100;             // 2: 线程安全吗？
    global_ptr.reset();       // 3: 线程安全吗？
}

// 循环引用问题
struct Node {
    std::shared_ptr<Node> next;
    ~Node() { std::cout << "Node destroyed\n"; }
};

void circular_reference() {
    auto a = std::make_shared<Node>();
    auto b = std::make_shared<Node>();
    a->next = b;
    b->next = a;  // 会发生什么？
}

// 多线程下的 shared_ptr 性能问题
void performance_issue() {
    auto ptr = std::make_shared<int>(42);
    // 多线程频繁拷贝 ptr，有什么问题？
}
```

**参考答案**:

1. **shared_ptr 线程安全**：
   - 控制块（引用计数）操作是原子的
   - 指针本身的读写（拷贝、赋值）不是原子的
   - 所指向对象的操作不是线程安全的

2. **分析**：
   - `auto local = global_ptr`：非原子，需要同步
   - `*local = 100`：不线程安全，需要保护所指向对象
   - `global_ptr.reset()`：非原子，需要同步

3. **循环引用**：
   - a 和 b 互相引用，引用计数永不为 0
   - 内存泄漏！使用 weak_ptr 打破循环

4. **性能问题**：
   - 引用计数原子操作有开销
   - 多线程竞争同一计数器成为瓶颈

**代码示例**:
```cpp
#include <iostream>
#include <memory>
#include <thread>
#include <vector>
#include <atomic>

// 线程安全的 shared_ptr 访问
class ThreadSafePtr {
    std::shared_ptr<int> ptr;
    mutable std::mutex mtx;
public:
    void set(std::shared_ptr<int> newPtr) {
        std::lock_guard lock(mtx);
        ptr = std::move(newPtr);
    }
    
    std::shared_ptr<int> get() const {
        std::lock_guard lock(mtx);
        return ptr;  // 拷贝时引用计数增加
    }
};

// 使用 weak_ptr 打破循环
struct SafeNode {
    std::shared_ptr<SafeNode> next;
    std::weak_ptr<SafeNode> parent;  // 弱引用
    ~SafeNode() { std::cout << "SafeNode destroyed\n"; }
};

void safe_circular() {
    auto a = std::make_shared<SafeNode>();
    auto b = std::make_shared<SafeNode>();
    a->next = b;
    b->parent = a;  // OK：weak_ptr 不增加引用计数
}  // 正常析构

// make_shared vs 直接构造的性能
template<typename T, typename... Args>
void compare_construction(Args&&... args) {
    // 直接构造：两次分配（对象 + 控制块）
    std::shared_ptr<T> p1(new T(std::forward<Args>(args)...));
    
    // make_shared：一次分配（对象和控制块在一起）
    auto p2 = std::make_shared<T>(std::forward<Args>(args)...);
    // 更好的缓存局部性，更少的分配开销
}

// 原子 shared_ptr 操作（C++20）
// std::atomic<std::shared_ptr<int>> atomic_ptr;  // C++20

void shared_ptr_demo() {
    // 循环引用演示
    {
        auto a = std::make_shared<Node>();
        auto b = std::make_shared<Node>();
        a->next = b;
        b->next = a;
        std::cout << "Leaving scope...\n";
        // 没有析构输出！内存泄漏
    }
    
    std::cout << "---\n";
    
    // 安全版本
    safe_circular();
}
```

**常见错误**:
- 认为 shared_ptr 的所有操作都是线程安全的
- 在多线程中无保护地读写同一个 shared_ptr 对象
- 忘记 weak_ptr 需要 lock() 才能使用

**追问**:
- Q: unique_ptr 可以共享所有权吗？
- A: 不可以，unique_ptr 独占所有权，不可拷贝只可移动
- Q: shared_ptr 的引用计数存在哪里？
- A: 控制块（control block），与 make_shared 一起分配

---

### 题目 14: Lambda 捕获陷阱

**难度**: 高级
**考察点**: 捕获方式、生命周期、悬垂引用

**问题**:
```cpp
// 陷阱 1：悬垂引用
auto make_dangling_lambda() {
    int local = 42;
    return [&] { return local; };  // 危险！
}

// 陷阱 2：捕获 this
class MyClass {
    int value = 10;
public:
    auto get_lambda() {
        return [=] { return value; };  // 捕获了什么？
    }
    auto get_lambda_this() {
        return [this] { return value; };  // 显式捕获
    }
};

// 陷阱 3：mutable lambda
void mutable_trap() {
    int x = 0;
    auto f = [=]() mutable { return ++x; };
    std::cout << f() << " " << f() << " " << x;  // 输出？
}

// 陷阱 4：std::move 捕获（C++14）
void move_capture() {
    auto ptr = std::make_unique<int>(42);
    // auto f = [ptr] {};  // 错误！
    // 如何捕获 unique_ptr？
}
```

**参考答案**:

1. **悬垂引用**：
   - lambda 捕获局部变量的引用
   - 函数返回后局部变量销毁，lambda 内引用悬空

2. **捕获 this**：
   - `[=]` 隐式捕获 this 指针（不是 value 的拷贝）
   - 如果对象销毁，lambda 内访问 UB
   - C++17 起可用 `[*this]` 捕获 this 的拷贝

3. **mutable lambda**：
   - 允许修改捕获的副本
   - 不影响原始变量
   - 输出：`1 2 0`（x 的副本被修改，原始 x 不变）

4. **移动捕获**：
   - C++14 起支持初始化捕获：`[ptr = std::move(ptr)]`

**代码示例**:
```cpp
#include <iostream>
#include <memory>
#include <functional>

// 悬垂引用陷阱
dangerous_lambda() {
    int local = 42;
    return [&] { return local; };  // 不要这样做！
}

// 安全的做法
auto safe_lambda() {
    int local = 42;
    return [local] { return local; };  // 按值捕获
}

// this 捕获陷阱
class Dangerous {
    int value = 10;
public:
    std::function<int()> get_callback() {
        return [=] { return value; };  // 捕获 this，不是 value！
    }
};

class Safe {
    int value = 10;
public:
    std::function<int()> get_callback() {
        return [*this] { return value; };  // C++17：捕获 this 的拷贝
    }
};

// mutable lambda 演示
void mutable_demo() {
    int x = 0;
    auto f = [=]() mutable { 
        std::cout << "Inside lambda, x = " << ++x << "\n";
        return x; 
    };
    f();  // x = 1
    f();  // x = 2
    std::cout << "Outside lambda, x = " << x << "\n";  // x = 0
}

// C++14 初始化捕获
void init_capture_demo() {
    auto ptr = std::make_unique<int>(42);
    
    // 移动捕获
    auto f = [p = std::move(ptr)] { 
        return *p; 
    };
    
    std::cout << f() << "\n";  // 42
    // ptr 现在是 nullptr
}

// 泛型 lambda（C++14）
void generic_lambda() {
    auto print = [](const auto& x) {
        std::cout << x << "\n";
    };
    
    print(42);
    print("hello");
    print(3.14);
}

// 立即执行 lambda（IIFE）
void iife_demo() {
    const int value = [&] {
        int result = 0;
        for (int i = 0; i < 10; ++i) {
            result += i;
        }
        return result;
    }();  // 立即调用
    
    std::cout << "Value: " << value << "\n";
}
```

**常见错误**:
- 使用 `[&]` 捕获所有变量，导致悬垂引用
- 认为 `[=]` 会深拷贝对象成员
- 在异步回调中使用捕获 this 的 lambda

**追问**:
- Q: lambda 的类型是什么？
- A: 编译器生成的唯一闭包类型
- Q: lambda 可以递归吗？
- A: C++14 起可用 std::function 或 Y 组合子实现

---

## 五、内存管理

### 题目 15: RAII 与异常安全保证

**难度**: 高级
**考察点**: RAII 惯用法、异常安全等级、资源管理

**问题**:
```cpp
// 异常安全等级分析
class DatabaseConnection {
    Connection* conn;
    Transaction* trans;
public:
    void execute(const std::string& sql) {
        trans = begin_transaction();  // 1
        conn->execute(sql);           // 2 可能抛出
        trans->commit();              // 3
    }
};

// 如何改进为强异常安全？
// 如何实现不抛保证的 swap？
```

**参考答案**:

1. **异常安全等级**：
   - **无保证**：异常后对象可能损坏
   - **基本保证**：异常后对象有效但状态不确定
   - **强保证**：异常后对象状态不变（事务性）
   - **不抛保证**：承诺不抛出异常

2. **问题分析**：
   - 如果 2 抛出，事务未提交也未回滚
   - 连接可能处于不一致状态

3. **改进方案**：
   - 使用 RAII 管理事务（自动回滚）
   - copy-and-swap 实现强保证

**代码示例**:
```cpp
#include <iostream>
#include <memory>
#include <utility>
#include <vector>

// RAII 事务管理器
class TransactionGuard {
    Transaction* trans;
    bool committed = false;
public:
    explicit TransactionGuard(Transaction* t) : trans(t) {}
    
    void commit() {
        trans->commit();
        committed = true;
    }
    
    ~TransactionGuard() {
        if (!committed && trans) {
            trans->rollback();  // 自动回滚
        }
    }
    
    // 禁用拷贝，允许移动
    TransactionGuard(const TransactionGuard&) = delete;
    TransactionGuard& operator=(const TransactionGuard&) = delete;
    
    TransactionGuard(TransactionGuard&& other) noexcept
        : trans(other.trans), committed(other.committed) {
        other.trans = nullptr;
    }
};

// 强异常安全的类
class SafeVector {
    std::vector<int> data;
public:
    void insert_sorted(int value) {
        // copy-and-swap 惯用法
        auto temp = data;  // 拷贝
        auto it = std::lower_bound(temp.begin(), temp.end(), value);
        temp.insert(it, value);  // 可能抛出，但 data 未修改
        
        data.swap(temp);  // noexcept swap
    }
    
    // 不抛保证的 swap
    void swap(SafeVector& other) noexcept {
        using std::swap;
        swap(data, other.data);  // vector::swap 是 noexcept
    }
};

// 自定义资源管理类
template<typename T>
class UniqueArray {
    T* ptr;
    std::size_t size;
public:
    explicit UniqueArray(std::size_t n) 
        : ptr(new T[n]), size(n) {}
    
    ~UniqueArray() { delete[] ptr; }
    
    // 移动操作
    UniqueArray(UniqueArray&& other) noexcept
        : ptr(other.ptr), size(other.size) {
        other.ptr = nullptr;
        other.size = 0;
    }
    
    UniqueArray& operator=(UniqueArray&& other) noexcept {
        if (this != &other) {
            delete[] ptr;
            ptr = other.ptr;
            size = other.size;
            other.ptr = nullptr;
            other.size = 0;
        }
        return *this;
    }
    
    // 禁用拷贝
    UniqueArray(const UniqueArray&) = delete;
    UniqueArray& operator=(const UniqueArray&) = delete;
    
    T& operator[](std::size_t i) { return ptr[i]; }
    const T& operator[](std::size_t i) const { return ptr[i]; }
    std::size_t get_size() const { return size; }
};

void raii_demo() {
    // 使用 RAII 管理动态数组
    UniqueArray<int> arr(100);
    arr[0] = 42;
    
    // 自动释放，异常安全
    auto arr2 = std::move(arr);
    // arr 现在是空状态
}
```

**常见错误**:
- 手动管理资源，忘记异常路径的清理
- 在析构函数中抛出异常
- 认为基本保证足够，忽略强保证的需求

**追问**:
- Q: 如何实现强异常安全？
- A: copy-and-swap：先操作副本，成功后再交换
- Q: noexcept 移动对容器有什么影响？
- A: STL 容器优先使用 noexcept 移动，否则可能回退到拷贝

---

### 题目 16: 对象布局与 sizeof 陷阱

**难度**: 高级
**考察点**: 内存对齐、填充字节、虚函数影响

**问题**:
```cpp
class Empty {};
class EmptyVirtual { virtual void f() {} };

class A { char c; };
class B { int i; };
class C : public A, public B { char d; };

class VirtualA { virtual void f() {} char c; };
class VirtualB { virtual void g() {} int i; };
class VirtualC : public VirtualA, public VirtualB { char d; };

// 问题：
// sizeof(Empty) ?
// sizeof(EmptyVirtual) ?
// sizeof(C) ?
// sizeof(VirtualC) ?
// 为什么空类大小不为 0？
```

**参考答案**:

1. **空类大小**：
   - `sizeof(Empty)` = 1（不是 0！）
   - 原因：每个对象必须有唯一地址，0 大小会导致多个对象地址相同

2. **虚函数影响**：
   - `sizeof(EmptyVirtual)` = 8（64 位）或 4（32 位）
   - 包含 vptr 指针

3. **多重继承布局**：
   - `sizeof(C)` = 12（A: 1 + 3pad, B: 4, C::d: 1 + 3pad）
   - `sizeof(VirtualC)` = 32+（两个 vptr + 对齐）

4. **内存布局**：
   ```
   C:          VirtualC:
   ├─ A::c     ├─ VirtualA vptr
   │  padding  ├─ A::c + padding
   ├─ B::i     ├─ VirtualB vptr
   └─ C::d     ├─ B::i
      padding  ├─ C::d + padding
               └─ 可能的对齐填充
   ```

**代码示例**:
```cpp
#include <iostream>

class Empty {};
class EmptyVirtual { virtual void f() {} };

class A { char c; };
class B { int i; };
class C : public A, public B { char d; };

class VirtualA { virtual void f() {} char c; };
class VirtualB { virtual void g() {} int i; };
class VirtualC : public VirtualA, public VirtualB { char d; };

// 空基类优化（EBO）
template<typename T>
class Wrapper : private T {
    int value;
};

void size_demo() {
    std::cout << "sizeof(Empty): " << sizeof(Empty) << "\n";
    std::cout << "sizeof(EmptyVirtual): " << sizeof(EmptyVirtual) << "\n";
    std::cout << "sizeof(A): " << sizeof(A) << "\n";
    std::cout << "sizeof(B): " << sizeof(B) << "\n";
    std::cout << "sizeof(C): " << sizeof(C) << "\n";
    std::cout << "sizeof(VirtualA): " << sizeof(VirtualA) << "\n";
    std::cout << "sizeof(VirtualB): " << sizeof(VirtualB) << "\n";
    std::cout << "sizeof(VirtualC): " << sizeof(VirtualC) << "\n";
    
    // EBO 演示
    std::cout << "sizeof(Wrapper<Empty>): " << sizeof(Wrapper<Empty>) << "\n";
    std::cout << "sizeof(Wrapper<A>): " << sizeof(Wrapper<A>) << "\n";
}

// 手动对齐控制
struct alignas(64) CacheLine {
    int data[16];  // 64 字节对齐，避免伪共享
};

// 检查对齐
void alignment_demo() {
    alignas(32) char buffer[128];
    std::cout << "Alignment of buffer: " 
              << reinterpret_cast<uintptr_t>(buffer) % 32 << "\n";
}
```

**常见错误**:
- 假设类大小等于成员大小之和
- 忽略对齐填充的影响
- 在性能敏感场景忽略 EBO

**追问**:
- Q: 如何减少类的大小？
- A: 重新排序成员（从大到小），使用位域，继承空类利用 EBO
- Q: alignas 和 #pragma pack 的区别？
- A: alignas 增加对齐，pack 减小对齐（可能降低性能）

---

### 题目 17: Placement New 与显式析构

**难度**: 专家
**考察点**: 定位 new、显式析构、内存池实现

**问题**:
```cpp
// placement new 基础
char buffer[sizeof(int)];
int* p = new (buffer) int(42);

// 问题：
// 1. 如何正确销毁 placement new 创建的对象？
// 2. 与常规 new/delete 的区别？
// 3. 内存池实现中的应用？
// 4. 数组的 placement new？

// 实现一个简单的对象池
class ObjectPool {
    // 如何实现？
};
```

**参考答案**:

1. **显式析构**：
   - `p->~T()` 显式调用析构函数
   - 不释放内存，只执行析构逻辑

2. **与常规 new/delete 区别**：
   - placement new：在已分配内存上构造对象
   - 不分配内存，不返回新指针
   - 需要配对使用显式析构

3. **内存池应用**：
   - 预分配大块内存
   - 使用 placement new 在预分配内存上构造对象
   - 避免频繁的堆分配开销

**代码示例**:
```cpp
#include <iostream>
#include <memory>
#include <vector>

// placement new 基础用法
void placement_new_demo() {
    alignas(int) char buffer[sizeof(int) * 10];
    
    // 在 buffer 上构造 int
    int* p = new (buffer) int(42);
    std::cout << "Value: " << *p << "\n";
    
    // 显式析构
    p->~int();
    
    // 可以重复使用 buffer
    int* p2 = new (buffer) int(100);
    std::cout << "New value: " << *p2 << "\n";
    p2->~int();
}

// 简单对象池
template<typename T, std::size_t N>
class ObjectPool {
    alignas(T) char buffer_[sizeof(T) * N];
    bool used_[N] = {false};
    
public:
    template<typename... Args>
    T* acquire(Args&&... args) {
        for (std::size_t i = 0; i < N; ++i) {
            if (!used_[i]) {
                used_[i] = true;
                T* p = reinterpret_cast<T*>(buffer_ + sizeof(T) * i);
                new (p) T(std::forward<Args>(args)...);
                return p;
            }
        }
        return nullptr;  // 池已满
    }
    
    void release(T* p) {
        std::size_t index = (reinterpret_cast<char*>(p) - buffer_) / sizeof(T);
        if (index < N && used_[index]) {
            p->~T();
            used_[index] = false;
        }
    }
};

// 使用示例
class ExpensiveObject {
    int data[100];
public:
    ExpensiveObject() { std::cout << "Constructed\n"; }
    ~ExpensiveObject() { std::cout << "Destroyed\n"; }
};

void pool_demo() {
    ObjectPool<ExpensiveObject, 4> pool;
    
    auto obj1 = pool.acquire();
    auto obj2 = pool.acquire();
    
    pool.release(obj1);
    pool.release(obj2);
    
    // 可以重用释放的位置
    auto obj3 = pool.acquire();
}

// 不抛异常的 placement new
void nothrow_placement_new() {
    alignas(double) char buffer[sizeof(double)];
    double* p = new (buffer) double(3.14);
    // placement new 本身不抛异常（除非构造函数抛异常）
}
```

**常见错误**:
- 对 placement new 的对象使用 delete
- 忘记显式调用析构函数
- 内存对齐不当导致未定义行为

**追问**:
- Q: placement new 数组的语法？
- A: `new (buffer) T[n]`，但需要手动管理每个元素的析构
- Q: 为什么需要 alignas？
- A: 确保 buffer 满足 T 的对齐要求，否则 UB

---

## 六、STL

### 题目 18: 迭代器失效场景

**难度**: 高级
**考察点**: 容器迭代器失效规则、安全使用模式

**问题**:
```cpp
// vector 迭代器失效
std::vector<int> v = {1, 2, 3, 4, 5};
auto it = v.begin() + 2;
v.push_back(6);  // it 还有效吗？

// 删除元素时的迭代器失效
for (auto it = v.begin(); it != v.end(); ++it) {
    if (*it % 2 == 0) {
        v.erase(it);  // 安全吗？
    }
}

// list 和 vector 的区别
std::list<int> lst = {1, 2, 3};
auto lit = ++lst.begin();
lst.push_back(4);  // lit 还有效吗？

// map 的迭代器失效
std::map<int, std::string> m;
auto mit = m.insert({1, "one"}).first;
m[2] = "two";  // mit 还有效吗？
```

**参考答案**:

1. **vector 迭代器失效**：
   - `push_back`：如果重新分配，所有迭代器失效
   - `erase`：被删除元素及之后的迭代器失效
   - `insert`：如果重新分配，所有迭代器失效

2. **删除元素的正确方式**：
   - `it = v.erase(it)`：返回下一个有效迭代器
   - 或使用 remove-erase 惯用法

3. **list/forward_list**：
   - 插入不使任何迭代器失效
   - 仅被删除元素的迭代器失效

4. **map/set**：
   - 插入不使任何迭代器失效
   - 仅被删除元素的迭代器失效

**代码示例**:
```cpp
#include <iostream>
#include <vector>
#include <list>
#include <map>
#include <algorithm>

// 安全的 vector 删除
void safe_vector_erase(std::vector<int>& v) {
    // 方法 1：使用返回的迭代器
    for (auto it = v.begin(); it != v.end(); ) {
        if (*it % 2 == 0) {
            it = v.erase(it);  // erase 返回下一个迭代器
        } else {
            ++it;
        }
    }
}

// 方法 2：remove-erase 惯用法（更高效）
void remove_erase_idiom(std::vector<int>& v) {
    v.erase(
        std::remove_if(v.begin(), v.end(), 
            [](int x) { return x % 2 == 0; }),
        v.end()
    );
}

// 遍历并可能修改的正确方式
void safe_modification(std::vector<int>& v) {
    // 如果需要修改，先收集要修改的位置
    std::vector<std::size_t> to_modify;
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (v[i] > 10) {
            to_modify.push_back(i);
        }
    }
    
    // 然后修改（不会使索引失效）
    for (auto idx : to_modify) {
        v[idx] *= 2;
    }
}

// 预留空间避免重新分配
void avoid_reallocation() {
    std::vector<int> v;
    v.reserve(1000);  // 预分配
    
    auto it = v.begin();
    for (int i = 0; i < 1000; ++i) {
        v.push_back(i);  // 不会重新分配，it 保持有效
    }
}

// 迭代器失效演示
void invalidation_demo() {
    std::vector<int> v = {1, 2, 3, 4, 5};
    v.reserve(10);  // 预分配避免重新分配
    
    auto it = v.begin() + 2;  // 指向 3
    std::cout << "Before: *it = " << *it << "\n";
    
    v.push_back(6);  // 如果没有重新分配，it 可能仍有效
    // 但依赖这是未定义行为！
    
    // 安全做法：重新获取迭代器
    it = v.begin() + 2;
    std::cout << "After: *it = " << *it << "\n";
}
```

**常见错误**:
- 在循环中删除元素后不更新迭代器
- 假设 reserve 后迭代器永远不会失效
- 在修改操作后继续使用旧迭代器

**追问**:
- Q: deque 的迭代器失效规则？
- A: 两端插入可能使所有迭代器失效，中间插入/删除使该位置迭代器失效
- Q: 如何安全地在遍历时删除多个元素？
- A: 使用 remove-erase 惯用法，或从后向前遍历

---

### 题目 19: 容器选择策略

**难度**: 高级
**考察点**: 容器特性、时间复杂度、内存布局

**问题**:
```cpp
// 场景 1：需要频繁在头部插入
data_structure front_insert;

// 场景 2：需要频繁查找和插入
data_structure lookup_insert;

// 场景 3：需要保持元素有序，频繁插入删除
data_structure ordered_dynamic;

// 场景 4：大量数据，需要紧凑存储，偶尔插入
data_structure compact_storage;

// 场景 5：需要快速查找，遍历顺序不重要
data_structure fast_lookup;

// 问题：每个场景最适合什么容器？为什么？
```

**参考答案**:

| 场景 | 推荐容器 | 原因 |
|------|---------|------|
| 头部插入 | deque / list | vector 头部插入 O(n) |
| 查找+插入 | unordered_map | O(1) 平均查找 |
| 有序动态 | map / set | 自动排序，O(log n) |
| 紧凑存储 | vector | 缓存友好，内存连续 |
| 快速查找 | unordered_set | O(1) 查找，哈希实现 |

**详细分析**：

1. **vector vs deque**：
   - vector：连续内存，缓存友好，但插入可能重新分配
   - deque：分段连续，两端插入 O(1)，无重新分配

2. **map vs unordered_map**：
   - map：红黑树，O(log n)，有序，内存开销小
   - unordered_map：哈希表，O(1)，无序，可能有重新哈希开销

3. **list vs forward_list**：
   - list：双向链表，可以反向遍历
   - forward_list：单向链表，内存更紧凑

**代码示例**:
```cpp
#include <iostream>
#include <vector>
#include <deque>
#include <list>
#include <map>
#include <unordered_map>
#include <chrono>
#include <random>

// 场景 1：双端队列
template<typename T>
using FrontInsertContainer = std::deque<T>;

// 场景 2：哈希表
template<typename K, typename V>
using LookupContainer = std::unordered_map<K, V>;

// 场景 3：有序集合
template<typename T>
using OrderedContainer = std::set<T>;

// 场景 4：紧凑存储
template<typename T>
using CompactContainer = std::vector<T>;

// 性能对比
void benchmark_containers() {
    const int N = 100000;
    
    // vector 尾部插入
    {
        std::vector<int> v;
        v.reserve(N);
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < N; ++i) {
            v.push_back(i);
        }
        auto end = std::chrono::high_resolution_clock::now();
        std::cout << "vector push_back: " 
                  << std::chrono::duration_cast<std::chrono::microseconds>(end - start).count()
                  << " us\n";
    }
    
    // list 插入
    {
        std::list<int> lst;
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < N; ++i) {
            lst.push_back(i);
        }
        auto end = std::chrono::high_resolution_clock::now();
        std::cout << "list push_back: " 
                  << std::chrono::duration_cast<std::chrono::microseconds>(end - start).count()
                  << " us\n";
    }
    
    // 查找对比
    {
        std::vector<int> v(N);
        std::iota(v.begin(), v.end(), 0);
        std::unordered_set<int> s(v.begin(), v.end());
        
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, N * 2);
        
        // vector 线性查找
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < 1000; ++i) {
            std::find(v.begin(), v.end(), dis(gen));
        }
        auto end = std::chrono::high_resolution_clock::now();
        std::cout << "vector find: " 
                  << std::chrono::duration_cast<std::chrono::microseconds>(end - start).count()
                  << " us\n";
        
        // unordered_set 查找
        start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < 1000; ++i) {
            s.find(dis(gen));
        }
        end = std::chrono::high_resolution_clock::now();
        std::cout << "unordered_set find: " 
                  << std::chrono::duration_cast<std::chrono::microseconds>(end - start).count()
                  << " us\n";
    }
}
```

**常见错误**:
- 在需要频繁插入的场景使用 vector
- 在需要有序遍历时使用 unordered_map
- 忽略容器的内存布局对性能的影响

**追问**:
- Q: flat_map 是什么？什么时候用？
- A: 基于 vector 的有序 map，缓存友好，适合查找多修改少的场景
- Q: 自定义哈希函数要注意什么？
- A: 好的分布性、速度快、满足严格弱序

---

### 题目 20: sort 严格弱序与比较器

**难度**: 高级
**考察点**: 严格弱序、比较器要求、稳定性

**问题**:
```cpp
// 错误的比较器
auto bad_comp = [](int a, int b) {
    return a <= b;  // 有什么问题？
};

// 另一个错误
auto bad_comp2 = [](int a, int b) {
    return a < b + 1;  // 有什么问题？
};

// 正确的严格弱序
bool strict_weak_order(int a, int b) {
    return a < b;  // 满足所有要求
}

// 多字段排序
struct Person {
    std::string name;
    int age;
    double salary;
};

// 如何按 age 升序，然后 salary 降序排序？
```

**参考答案**:

1. **严格弱序要求**：
   - 反对称性：comp(a,b) → !comp(b,a)
   - 传递性：comp(a,b) && comp(b,c) → comp(a,c)
   - 非自反性：!comp(a,a)
   - 可比性：comp(a,b) || comp(b,a) || a 等价于 b

2. **错误分析**：
   - `a <= b`：违反非自反性（a==b 时 comp(a,a) 为 true）
   - `a < b + 1`：违反传递性（a=1,b=0,c=-2）

3. **多字段排序**：
   - 先比较主要字段
   - 相等时比较次要字段
   - 注意升序/降序的符号

**代码示例**:
```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <string>

struct Person {
    std::string name;
    int age;
    double salary;
};

// 正确的多字段比较器
bool person_compare(const Person& a, const Person& b) {
    if (a.age != b.age) {
        return a.age < b.age;  // age 升序
    }
    return a.salary > b.salary;  // salary 降序
}

// 使用 std::tie 简化
bool person_compare_tie(const Person& a, const Person& b) {
    return std::tie(a.age, b.salary) < std::tie(b.age, a.salary);
    // 注意：tie 比较是字典序，需要调整降序字段
}

// 更清晰的写法
bool person_compare_clear(const Person& a, const Person& b) {
    if (a.age != b.age) return a.age < b.age;
    if (a.salary != b.salary) return a.salary > b.salary;
    return a.name < b.name;
}

// 稳定排序
void stable_sort_demo() {
    std::vector<Person> people = {
        {"Alice", 30, 50000},
        {"Bob", 25, 60000},
        {"Charlie", 30, 70000},
        {"David", 25, 55000}
    };
    
    // 先按 salary 排序
    std::stable_sort(people.begin(), people.end(),
        [](const Person& a, const Person& b) {
            return a.salary > b.salary;
        });
    
    // 再按 age 稳定排序
    std::stable_sort(people.begin(), people.end(),
        [](const Person& a, const Person& b) {
            return a.age < b.age;
        });
    
    // 结果：按 age 分组，每组内保持 salary 顺序
}

// 自定义类型的比较器
struct CaseInsensitiveCompare {
    bool operator()(const std::string& a, const std::string& b) const {
        return std::lexicographical_compare(
            a.begin(), a.end(), b.begin(), b.end(),
            [](char ca, char cb) {
                return std::tolower(ca) < std::tolower(cb);
            }
        );
    }
};

void sort_demo() {
    std::vector<Person> people = {
        {"Alice", 30, 50000},
        {"Bob", 25, 60000},
        {"Charlie", 30, 70000}
    };
    
    std::sort(people.begin(), people.end(), person_compare_clear);
    
    for (const auto& p : people) {
        std::cout << p.name << ": " << p.age << ", " << p.salary << "\n";
    }
}
```

**常见错误**:
- 使用 `<=` 而不是 `<` 作为比较器
- 比较器不满足传递性
- 在需要稳定排序时使用 std::sort

**追问**:
- Q: sort 和 stable_sort 的性能差异？
- A: sort 平均 O(n log n)，stable_sort 需要额外内存，通常稍慢
- Q: 如何检测比较器是否满足严格弱序？
- A: 使用 _GLIBCXX_DEBUG 或自定义断言检查

---

## 七、并发编程

### 题目 21: Memory Order 选择与性能

**难度**: 专家
**考察点**: 内存序语义、happens-before、性能影响

**问题**:
```cpp
std::atomic<int> flag{0};
int data = 0;

// 线程 1
void producer() {
    data = 42;
    flag.store(1, std::memory_order_release);
}

// 线程 2
void consumer() {
    while (flag.load(std::memory_order_acquire) == 0) {}
    std::cout << data;  // 能保证看到 42 吗？
}

// 其他 memory_order 场景
std::atomic<int> counter{0};

void increment() {
    counter.fetch_add(1, std::memory_order_relaxed);  // 足够吗？
}

void spinlock() {
    while (flag.exchange(1, std::memory_order_acq_rel) == 1) {}
    // 临界区
    flag.store(0, std::memory_order_release);
}
```

**参考答案**:

1. **Release-Acquire 同步**：
   - `release` 保证之前的写入对 `acquire` 可见
   - 消费者保证看到 data = 42
   - 形成 happens-before 关系

2. **Memory Order 选择**：
   - `relaxed`：无同步，只保证原子性，性能最好
   - `acquire/release`：单向同步，适合生产者-消费者
   - `acq_rel`：双向同步，适合读-修改-写
   - `seq_cst`：最强顺序，默认，性能最差

3. **场景分析**：
   - 纯计数器：`relaxed` 足够
   - 标志位同步：`acquire/release`
   - 自旋锁：`acq_rel` 或 `seq_cst`

**代码示例**:
```cpp
#include <iostream>
#include <atomic>
#include <thread>
#include <vector>

// Release-Acquire 同步示例
std::atomic<int> ready{0};
int shared_data = 0;

void producer() {
    shared_data = 42;
    ready.store(1, std::memory_order_release);
}

void consumer() {
    while (ready.load(std::memory_order_acquire) == 0) {
        // 自旋等待
    }
    // 保证看到 shared_data = 42
    std::cout << "Data: " << shared_data << "\n";
}

// 不同 memory_order 的性能对比
void memory_order_benchmark() {
    const int N = 10000000;
    
    // seq_cst
    {
        std::atomic<int> counter{0};
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < N; ++i) {
            counter.fetch_add(1, std::memory_order_seq_cst);
        }
        auto end = std::chrono::high_resolution_clock::now();
        std::cout << "seq_cst: " 
                  << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
                  << " ms\n";
    }
    
    // relaxed
    {
        std::atomic<int> counter{0};
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < N; ++i) {
            counter.fetch_add(1, std::memory_order_relaxed);
        }
        auto end = std::chrono::high_resolution_clock::now();
        std::cout << "relaxed: " 
                  << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
                  << " ms\n";
    }
}

// 实现简单的信号量
template<typename T>
class AtomicQueue {
    std::vector<T> buffer;
    std::atomic<size_t> head{0};
    std::atomic<size_t> tail{0};
    
public:
    explicit AtomicQueue(size_t size) : buffer(size) {}
    
    bool push(const T& item) {
        size_t t = tail.load(std::memory_order_relaxed);
        size_t next = (t + 1) % buffer.size();
        
        if (next == head.load(std::memory_order_acquire)) {
            return false;  // 满
        }
        
        buffer[t] = item;
        tail.store(next, std::memory_order_release);
        return true;
    }
    
    bool pop(T& item) {
        size_t h = head.load(std::memory_order_relaxed);
        
        if (h == tail.load(std::memory_order_acquire)) {
            return false;  // 空
        }
        
        item = buffer[h];
        head.store((h + 1) % buffer.size(), std::memory_order_release);
        return true;
    }
};

void memory_order_demo() {
    std::thread t1(producer);
    std::thread t2(consumer);
    t1.join();
    t2.join();
}
```

**常见错误**:
- 在需要同步的场景使用 relaxed
- 混淆 acquire 和 release 的方向
- 过度使用 seq_cst 影响性能

**追问**:
- Q: happens-before 关系是什么？
- A: 定义操作间的可见性顺序，是内存模型的基础
- Q: 什么时候必须用 seq_cst？
- A: 需要全局顺序一致性的场景，如多个变量的同步

---

### 题目 22: 无锁编程与 ABA 问题

**难度**: 专家
**考察点**: CAS 操作、ABA 问题、 Hazard Pointer

**问题**:
```cpp
// 简单的无锁栈（有 ABA 问题）
template<typename T>
class LockFreeStack {
    struct Node {
        T data;
        Node* next;
    };
    std::atomic<Node*> head{nullptr};
    
public:
    void push(const T& value) {
        Node* new_node = new Node{value, head.load()};
        while (!head.compare_exchange_weak(new_node->next, new_node)) {}
    }
    
    bool pop(T& result) {
        Node* old_head = head.load();
        while (old_head && !head.compare_exchange_weak(
            old_head, old_head->next)) {}
        if (old_head) {
            result = old_head->data;
            delete old_head;  // ABA 问题！
            return true;
        }
        return false;
    }
};

// 问题：
// 1. ABA 问题是什么？
// 2. 如何解决 ABA 问题？
// 3. 内存泄漏问题如何解决？
```

**参考答案**:

1. **ABA 问题**：
   - 线程 1 读取 A
   - 线程 2 弹出 A，压入 B，再压入 A（回收的节点）
   - 线程 1 的 CAS 成功，但栈状态已改变
   - 可能导致节点丢失或重复

2. **解决方案**：
   - 带标签的指针（Tagged Pointer）
   - Hazard Pointer：延迟释放
   - 引用计数

3. **内存泄漏**：
   - 直接 delete 可能导致其他线程访问已释放内存
   - 需要延迟回收机制

**代码示例**:
```cpp
#include <iostream>
#include <atomic>
#include <memory>
#include <vector>
#include <thread>

// 带标签的指针（解决 ABA）
template<typename T>
class TaggedPointer {
    std::atomic<uintptr_t> ptr;
    static constexpr uintptr_t TAG_MASK = 0xFFFF;
    static constexpr uintptr_t PTR_MASK = ~TAG_MASK;
    
public:
    T* get_ptr() const {
        return reinterpret_cast<T*>(ptr.load() & PTR_MASK);
    }
    
    uint16_t get_tag() const {
        return static_cast<uint16_t>(ptr.load() & TAG_MASK);
    }
    
    bool compare_exchange(T*& expected_ptr, uint16_t& expected_tag,
                          T* desired_ptr, uint16_t desired_tag) {
        uintptr_t expected = reinterpret_cast<uintptr_t>(expected_ptr) 
                           | expected_tag;
        uintptr_t desired = reinterpret_cast<uintptr_t>(desired_ptr) 
                          | desired_tag;
        bool success = ptr.compare_exchange_strong(expected, desired);
        if (!success) {
            expected_ptr = reinterpret_cast<T*>(expected & PTR_MASK);
            expected_tag = static_cast<uint16_t>(expected & TAG_MASK);
        }
        return success;
    }
};

// Hazard Pointer 简化实现
class HazardPointer {
    static constexpr int MAX_THREADS = 64;
    static constexpr int MAX_HAZARD_POINTERS = 2;
    
    struct HPRecord {
        std::atomic<std::thread::id> thread_id;
        std::atomic<void*> hazard_ptr[MAX_HAZARD_POINTERS];
    };
    
    static HPRecord hp_records[MAX_THREADS];
    
public:
    static void* get(int index) {
        int tid = get_thread_index();
        return hp_records[tid].hazard_ptr[index].load();
    }
    
    static void set(int index, void* ptr) {
        int tid = get_thread_index();
        hp_records[tid].hazard_ptr[index].store(ptr);
    }
    
    static void retire(void* ptr);
    
private:
    static int get_thread_index();
};

// 更实用的方案：使用 std::shared_ptr（有开销但安全）
template<typename T>
class SafeStack {
    struct Node {
        T data;
        std::shared_ptr<Node> next;
    };
    
    std::shared_ptr<Node> head;
    
public:
    void push(const T& value) {
        auto new_node = std::make_shared<Node>();
        new_node->data = value;
        new_node->next = std::atomic_load(&head);
        while (!std::atomic_compare_exchange_weak(&head, &new_node->next, new_node)) {}
    }
    
    bool pop(T& result) {
        auto old_head = std::atomic_load(&head);
        while (old_head && !std::atomic_compare_exchange_weak(
            &head, &old_head, old_head->next)) {}
        if (old_head) {
            result = old_head->data;
            return true;
        }
        return false;
    }
};

// 工业级方案：使用成熟的库如 folly::AtomicLinkedList
void lockfree_demo() {
    SafeStack<int> stack;
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&stack, i]() {
            for (int j = 0; j < 1000; ++j) {
                stack.push(i * 1000 + j);
            }
        });
    }
    
    for (auto& t : threads) {
        t.join();
    }
}
```

**常见错误**:
- 忽略 ABA 问题导致数据丢失
- 直接 delete 节点导致 use-after-free
- 在 CAS 循环中忘记处理 spurious failure

**追问**:
- Q: compare_exchange_weak 和 strong 的区别？
- A: weak 可能伪失败（spurious failure），适合循环；strong 不会伪失败
- Q: 什么时候应该用有锁而不是无锁？
- A: 竞争不激烈、代码可维护性优先、无锁实现过于复杂时

---

### 题目 23: 线程安全单例模式

**难度**: 高级
**考察点**: 双重检查锁定、Meyers' Singleton、call_once

**问题**:
```cpp
// 双重检查锁定（C++11 之前有问题）
class Singleton {
    static Singleton* instance;
    static std::mutex mtx;
public:
    static Singleton* getInstance() {
        if (instance == nullptr) {          // 1
            std::lock_guard<std::mutex> lock(mtx);
            if (instance == nullptr) {      // 2
                instance = new Singleton(); // 3 可能重排序！
            }
        }
        return instance;
    }
};

// C++11 之后的正确实现
// 1. Meyers' Singleton
// 2. call_once
// 3. atomic + memory_order
```

**参考答案**:

1. **C++11 之前的 DCL 问题**：
   - `new Singleton()` 可能重排序：先赋值指针，再构造对象
   - 其他线程可能看到未构造完成的对象

2. **C++11 解决方案**：
   - Meyers' Singleton：静态局部变量线程安全初始化
   - `std::call_once`：确保只执行一次
   - `std::atomic` + memory_order：手动控制

3. **推荐方案**：
   - Meyers' Singleton：最简洁，C++11 起线程安全

**代码示例**:
```cpp
#include <iostream>
#include <mutex>
#include <atomic>
#include <memory>

// 方案 1：Meyers' Singleton（推荐）
class MeyersSingleton {
public:
    static MeyersSingleton& getInstance() {
        static MeyersSingleton instance;  // C++11 起线程安全
        return instance;
    }
    
    void doSomething() {
        std::cout << "MeyersSingleton working\n";
    }
    
private:
    MeyersSingleton() { std::cout << "Constructed\n"; }
    ~MeyersSingleton() = default;
    MeyersSingleton(const MeyersSingleton&) = delete;
    MeyersSingleton& operator=(const MeyersSingleton&) = delete;
};

// 方案 2：call_once
class CallOnceSingleton {
public:
    static CallOnceSingleton& getInstance() {
        std::call_once(init_flag, &CallOnceSingleton::init);
        return *instance;
    }
    
private:
    static std::once_flag init_flag;
    static std::unique_ptr<CallOnceSingleton> instance;
    
    static void init() {
        instance.reset(new CallOnceSingleton());
    }
    
    CallOnceSingleton() = default;
};

std::once_flag CallOnceSingleton::init_flag;
std::unique_ptr<CallOnceSingleton> CallOnceSingleton::instance;

// 方案 3：Atomic（了解即可）
class AtomicSingleton {
public:
    static AtomicSingleton* getInstance() {
        AtomicSingleton* tmp = instance.load(std::memory_order_acquire);
        if (tmp == nullptr) {
            std::lock_guard<std::mutex> lock(mtx);
            tmp = instance.load(std::memory_order_relaxed);
            if (tmp == nullptr) {
                tmp = new AtomicSingleton();
                instance.store(tmp, std::memory_order_release);
            }
        }
        return tmp;
    }
    
private:
    static std::atomic<AtomicSingleton*> instance;
    static std::mutex mtx;
};

std::atomic<AtomicSingleton*> AtomicSingleton::instance{nullptr};
std::mutex AtomicSingleton::mtx;

// 方案 4：CRTP 单例（支持继承）
template<typename T>
class SingletonBase {
public:
    static T& getInstance() {
        static T instance;
        return instance;
    }
    
protected:
    SingletonBase() = default;
    ~SingletonBase() = default;
    
private:
    SingletonBase(const SingletonBase&) = delete;
    SingletonBase& operator=(const SingletonBase&) = delete;
};

class MyService : public SingletonBase<MyService> {
    friend class SingletonBase<MyService>;
    MyService() = default;
public:
    void serve() { std::cout << "Serving\n"; }
};

void singleton_demo() {
    // Meyers' Singleton
    MeyersSingleton::getInstance().doSomething();
    MeyersSingleton::getInstance().doSomething();  // 只构造一次
    
    // CRTP Singleton
    MyService::getInstance().serve();
}
```

**常见错误**:
- C++11 之前使用无 memory_order 的 DCL
- 忘记禁用拷贝构造和赋值
- 在析构后访问单例

**追问**:
- Q: 静态局部变量初始化的线程安全保证？
- A: C++11 起，静态局部变量初始化是线程安全的，由编译器保证
- Q: 单例的析构顺序问题？
- A: 静态对象按构造逆序析构，注意循环依赖

---

## 八、性能优化

### 题目 24: 编译优化选项与调试

**难度**: 高级
**考察点**: 优化级别、调试信息、LTO

**问题**:
```cpp
// 编译选项对比
// -O0, -O1, -O2, -O3, -Os, -Ofast

// 链接时优化（LTO）
// -flto

// 调试信息
// -g, -g3, -ggdb

// 问题：
// 1. 各优化级别的区别？
// 2. 为什么 -O3 不一定比 -O2 快？
// 3. LTO 的优缺点？
// 4. 如何调试优化后的代码？
```

**参考答案**:

1. **优化级别**：
   - `-O0`：无优化，最快编译，适合调试
   - `-O1`：基本优化，平衡编译时间和性能
   - `-O2`：大部分优化，推荐用于发布
   - `-O3`：激进优化，可能代码膨胀，不一定更快
   - `-Os`：优化大小
   - `-Ofast`：不遵守严格标准，最快但可能有风险

2. **-O3 问题**：
   - 激进内联导致代码膨胀，缓存不友好
   - 向量化可能引入额外开销
   - 某些优化可能与代码假设冲突

3. **LTO**：
   - 跨模块优化，更好的内联和死代码消除
   - 编译时间增加，内存消耗大

**代码示例**:
```cpp
#include <iostream>
#include <vector>
#include <chrono>

// 可能被内联的函数
inline int add(int a, int b) {
    return a + b;
}

// 循环向量化示例
void vectorizable_loop(std::vector<float>& a, 
                       const std::vector<float>& b,
                       const std::vector<float>& c) {
    // 编译器可以自动向量化
    for (size_t i = 0; i < a.size(); ++i) {
        a[i] = b[i] + c[i];
    }
}

// 阻碍向量化的代码
void non_vectorizable(std::vector<float>& a, 
                      const std::vector<float>& b) {
    for (size_t i = 0; i < a.size(); ++i) {
        if (i > 0 && a[i-1] > 0) {  // 数据依赖
            a[i] = b[i] * 2;
        } else {
            a[i] = b[i];
        }
    }
}

// 帮助编译器优化
void optimized_version(std::vector<float>& a, 
                       const std::vector<float>& b) {
    // 使用 __restrict 提示无别名
    float* __restrict a_ptr = a.data();
    const float* __restrict b_ptr = b.data();
    
    // 使用 size_t 帮助向量化
    const size_t n = a.size();
    
    // 编译指示（pragma）
    #pragma GCC ivdep  // 忽略向量依赖
    for (size_t i = 0; i < n; ++i) {
        a_ptr[i] = b_ptr[i] * 2;
    }
}

// 检查编译器优化报告
// g++ -O3 -fopt-info-vec-all -c file.cpp

void optimization_demo() {
    const size_t N = 10000000;
    std::vector<float> a(N), b(N), c(N);
    
    auto start = std::chrono::high_resolution_clock::now();
    vectorizable_loop(a, b, c);
    auto end = std::chrono::high_resolution_clock::now();
    
    std::cout << "Time: " 
              << std::chrono::duration_cast<std::chrono::microseconds>(end - start).count()
              << " us\n";
}
```

**常见错误**:
- 发布版本使用 -O0
- 忽略编译器警告（可能提示优化问题）
- 过度依赖 -O3 解决性能问题

**追问**:
- Q: 如何查看编译器优化后的代码？
- A: 使用 `objdump -d` 或 Compiler Explorer (godbolt.org)
- Q: PGO（Profile Guided Optimization）是什么？
- A: 基于运行时分析的优化，编译器根据实际执行路径优化

---

### 题目 25: 缓存友好数据结构

**难度**: 高级
**考察点**: 缓存行、伪共享、数据布局

**问题**:
```cpp
// 结构 A：非缓存友好
struct NodeA {
    NodeA* next;
    NodeA* prev;
    int data;
    char padding[100];  // 分散存储
    double value;
};

// 结构 B：缓存友好？
struct NodeB {
    int data;
    double value;
    NodeB* next;
    NodeB* prev;
};

// 多线程计数器的伪共享
struct Counter {
    std::atomic<int> count;
};

Counter counters[4];  // 可能的问题？

// 问题：
// 1. 缓存行大小通常是多少？
// 2. 什么是伪共享（False Sharing）？
// 3. 如何设计缓存友好的数据结构？
```

**参考答案**:

1. **缓存行大小**：通常 64 字节（x86/x64）

2. **伪共享**：
   - 不同线程修改同一缓存行的不同变量
   - 导致缓存行在核心间来回"乒乓"
   - 严重性能下降

3. **缓存友好设计**：
   - 数据紧凑存储（SoA 优于 AoS）
   - 对齐到缓存行边界
   - 避免伪共享（padding 分离）

**代码示例**:
```cpp
#include <iostream>
#include <atomic>
#include <thread>
#include <vector>
#include <chrono>

// 有伪共享的计数器
struct BadCounter {
    std::atomic<int> value;
};

// 避免伪共享的计数器
struct GoodCounter {
    std::atomic<int> value;
    char padding[64 - sizeof(std::atomic<int>)];  // 填充到缓存行大小
};

// 测试伪共享影响
void false_sharing_demo() {
    const int N = 100000000;
    
    // 有伪共享
    {
        BadCounter counters[4];
        std::vector<std::thread> threads;
        
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&counters, i, N]() {
                for (int j = 0; j < N; ++j) {
                    counters[i].value++;
                }
            });
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        std::cout << "Bad (false sharing): " 
                  << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
                  << " ms\n";
    }
    
    // 无伪共享
    {
        GoodCounter counters[4];
        std::vector<std::thread> threads;
        
        auto start = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&counters, i, N]() {
                for (int j = 0; j < N; ++j) {
                    counters[i].value++;
                }
            });
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        std::cout << "Good (no false sharing): " 
                  << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
                  << " ms\n";
    }
}

// AoS vs SoA
// Array of Structs（非缓存友好）
struct ParticleAoS {
    float x, y, z;
    float vx, vy, vz;
    float mass;
};

// Struct of Arrays（缓存友好）
struct ParticleSoA {
    std::vector<float> x, y, z;
    std::vector<float> vx, vy, vz;
    std::vector<float> mass;
    
    void resize(size_t n) {
        x.resize(n); y.resize(n); z.resize(n);
        vx.resize(n); vy.resize(n); vz.resize(n);
        mass.resize(n);
    }
};

// SoA 的遍历更高效（缓存命中率高）
void update_particles_soa(ParticleSoA& p, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        p.x[i] += p.vx[i];
        p.y[i] += p.vy[i];
        p.z[i] += p.vz[i];
    }
}

// 对齐分配
void* aligned_alloc(size_t alignment, size_t size) {
    #ifdef _WIN32
    return _aligned_malloc(size, alignment);
    #else
    void* ptr = nullptr;
    posix_memalign(&ptr, alignment, size);
    return ptr;
    #endif
}

void cache_friendly_demo() {
    false_sharing_demo();
}
```

**常见错误**:
- 多线程中相邻的 atomic 变量导致伪共享
- 使用链表而非数组（缓存不友好）
- 忽略数据对齐

**追问**:
- Q: 如何检测伪共享？
- A: 使用 perf c2c（Linux）或 VTune 的 False Sharing 分析
- Q: prefetch 指令有用吗？
- A: 在遍历大数据集时有用，但需要谨慎使用

---

### 题目 26: Benchmark 方法论

**难度**: 高级
**考察点**: 微基准测试、统计方法、常见陷阱

**问题**:
```cpp
// 错误的 benchmark
void bad_benchmark() {
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < 1000; ++i) {
        function_to_test();
    }
    auto end = std::chrono::high_resolution_clock::now();
    std::cout << "Time: " << (end - start).count() / 1000 << "\n";
}

// 问题：
// 1. 上述 benchmark 有什么问题？
// 2. 如何消除编译器过度优化？
// 3. 如何处理测量噪声？
// 4. 什么是稳定的 benchmark 方法？
```

**参考答案**:

1. **常见陷阱**：
   - 编译器优化掉测试代码
   - 冷启动影响（缓存、分支预测）
   - 测量精度不足
   - 统计样本不足

2. **最佳实践**：
   - 使用 Google Benchmark 等成熟框架
   - 防止编译器优化（volatile 或 side effect）
   - 多次运行，取统计值
   - 考虑缓存预热

**代码示例**:
```cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <algorithm>
#include <numeric>
#include <cmath>

// 防止编译器优化
volatile int sink;

void escape(void* p) {
    asm volatile("" : : "g"(p) : "memory");
}

void clobber() {
    asm volatile("" ::: "memory");
}

// 简单的统计工具
struct Statistics {
    double mean;
    double stddev;
    double min;
    double max;
    double median;
};

Statistics analyze(const std::vector<double>& samples) {
    Statistics stats;
    stats.min = *std::min_element(samples.begin(), samples.end());
    stats.max = *std::max_element(samples.begin(), samples.end());
    
    double sum = std::accumulate(samples.begin(), samples.end(), 0.0);
    stats.mean = sum / samples.size();
    
    double sq_sum = 0.0;
    for (double s : samples) {
        sq_sum += (s - stats.mean) * (s - stats.mean);
    }
    stats.stddev = std::sqrt(sq_sum / samples.size());
    
    auto sorted = samples;
    std::sort(sorted.begin(), sorted.end());
    stats.median = sorted[sorted.size() / 2];
    
    return stats;
}

// 改进的 benchmark 模板
template<typename Func>
void benchmark(const char* name, Func&& f, int iterations = 1000) {
    std::vector<double> times;
    times.reserve(iterations);
    
    // 预热
    for (int i = 0; i < 10; ++i) {
        f();
    }
    
    // 实际测量
    for (int i = 0; i < iterations; ++i) {
        clobber();  // 清除缓存状态
        
        auto start = std::chrono::high_resolution_clock::now();
        f();
        auto end = std::chrono::high_resolution_clock::now();
        
        double elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
            end - start).count();
        times.push_back(elapsed);
    }
    
    auto stats = analyze(times);
    std::cout << name << ":\n";
    std::cout << "  Mean: " << stats.mean << " ns\n";
    std::cout << "  StdDev: " << stats.stddev << " ns\n";
    std::cout << "  Min: " << stats.min << " ns\n";
    std::cout << "  Max: " << stats.max << " ns\n";
    std::cout << "  Median: " << stats.median << " ns\n";
}

// 测试函数
int compute(int x) {
    int result = 0;
    for (int i = 0; i < x; ++i) {
        result += i * i;
    }
    return result;
}

void benchmark_demo() {
    int input = 1000;
    
    benchmark("compute", [&]() {
        sink = compute(input);
        escape(&sink);
    });
}

// 对比两种实现
void comparison_benchmark() {
    std::vector<int> data(10000);
    std::iota(data.begin(), data.end(), 0);
    
    benchmark("std::sort", [&]() {
        auto copy = data;
        std::sort(copy.begin(), copy.end(), std::greater<int>());
        escape(copy.data());
    }, 100);
    
    benchmark("std::stable_sort", [&]() {
        auto copy = data;
        std::stable_sort(copy.begin(), copy.end(), std::greater<int>());
        escape(copy.data());
    }, 100);
}
```

**常见错误**:
- 编译器优化掉测试代码
- 单次测量，忽略噪声
- 不考虑缓存和分支预测状态
- 在 debug 模式下 benchmark

**追问**:
- Q: 为什么需要 volatile sink？
- A: 防止编译器优化掉整个计算
- Q: 什么是 Amdahl 定律？
- A: 并行加速受限于串行部分比例

---

## 九、方案设计题

### 题目 27: 设计智能指针

**难度**: 专家
**考察点**: RAII、引用计数、线程安全、自定义删除器

**问题**:
```cpp
// 实现一个简化版的 shared_ptr
// 要求：
// 1. 支持拷贝构造、拷贝赋值
// 2. 支持移动构造、移动赋值
// 3. 线程安全的引用计数
// 4. 支持自定义删除器
// 5. 支持 weak_ptr（可选）

template<typename T>
class MySharedPtr {
    // 实现
};
```

**参考答案**:

**核心设计**：
1. **控制块**：存储引用计数和删除器
2. **原子计数**：使用 std::atomic 保证线程安全
3. **类型擦除**：支持自定义删除器
4. **别名构造函数**：支持共享所有权但指向子对象

**代码示例**:
```cpp
#include <iostream>
#include <atomic>
#include <functional>
#include <utility>

// 控制块基类（类型擦除）
class ControlBlockBase {
public:
    std::atomic<size_t> shared_count{1};
    std::atomic<size_t> weak_count{0};
    
    virtual ~ControlBlockBase() = default;
    virtual void destroy_object() = 0;
    virtual void destroy_control_block() = 0;
};

// 具体控制块
template<typename T, typename Deleter>
class ControlBlock : public ControlBlockBase {
    T* ptr;
    Deleter deleter;
public:
    ControlBlock(T* p, Deleter d) : ptr(p), deleter(std::move(d)) {}
    
    void destroy_object() override {
        if (ptr) {
            deleter(ptr);
            ptr = nullptr;
        }
    }
    
    void destroy_control_block() override {
        delete this;
    }
};

// 自定义 shared_ptr
template<typename T>
class MySharedPtr {
    T* ptr = nullptr;
    ControlBlockBase* control = nullptr;
    
    void release() {
        if (control) {
            if (--control->shared_count == 0) {
                control->destroy_object();
                if (control->weak_count == 0) {
                    control->destroy_control_block();
                }
            }
            control = nullptr;
            ptr = nullptr;
        }
    }
    
    void add_ref() {
        if (control) {
            ++control->shared_count;
        }
    }
    
public:
    // 构造
    MySharedPtr() = default;
    
    explicit MySharedPtr(T* p) : ptr(p) {
        if (p) {
            control = new ControlBlock<T, std::default_delete<T>>(
                p, std::default_delete<T>());
        }
    }
    
    template<typename Deleter>
    MySharedPtr(T* p, Deleter d) : ptr(p) {
        if (p) {
            control = new ControlBlock<T, Deleter>(p, std::move(d));
        }
    }
    
    // 拷贝
    MySharedPtr(const MySharedPtr& other) : ptr(other.ptr), control(other.control) {
        add_ref();
    }
    
    MySharedPtr& operator=(const MySharedPtr& other) {
        if (this != &other) {
            release();
            ptr = other.ptr;
            control = other.control;
            add_ref();
        }
        return *this;
    }
    
    // 移动
    MySharedPtr(MySharedPtr&& other) noexcept 
        : ptr(other.ptr), control(other.control) {
        other.ptr = nullptr;
        other.control = nullptr;
    }
    
    MySharedPtr& operator=(MySharedPtr&& other) noexcept {
        if (this != &other) {
            release();
            ptr = other.ptr;
            control = other.control;
            other.ptr = nullptr;
            other.control = nullptr;
        }
        return *this;
    }
    
    // 析构
    ~MySharedPtr() { release(); }
    
    // 解引用
    T& operator*() const { return *ptr; }
    T* operator->() const { return ptr; }
    T* get() const { return ptr; }
    
    // 检查
    explicit operator bool() const { return ptr != nullptr; }
    size_t use_count() const { return control ? control->shared_count.load() : 0; }
    
    // 重置
    void reset(T* p = nullptr) {
        release();
        if (p) {
            ptr = p;
            control = new ControlBlock<T, std::default_delete<T>>(
                p, std::default_delete<T>());
        }
    }
    
    void swap(MySharedPtr& other) noexcept {
        using std::swap;
        swap(ptr, other.ptr);
        swap(control, other.control);
    }
};

// 自定义删除器示例
struct FileDeleter {
    void operator()(FILE* f) const {
        if (f) {
            std::cout << "Closing file\n";
            fclose(f);
        }
    }
};

void shared_ptr_demo() {
    // 基本使用
    {
        MySharedPtr<int> p1(new int(42));
        std::cout << "Use count: " << p1.use_count() << "\n";
        
        auto p2 = p1;
        std::cout << "Use count after copy: " << p1.use_count() << "\n";
        
        std::cout << "Value: " << *p2 << "\n";
    }  // 自动释放
    
    // 自定义删除器
    {
        MySharedPtr<FILE> file(fopen("test.txt", "w"), FileDeleter());
        // 自动关闭文件
    }
}
```

**常见错误**:
- 引用计数更新非原子
- 忘记处理自赋值
- 异常安全（构造函数抛异常时）

**追问**:
- Q: 为什么需要 weak_ptr？
- A: 打破循环引用，观察对象而不影响生命周期
- Q: make_shared 的优势？
- A: 一次分配，更好的缓存局部性

---

### 题目 28: 设计线程池

**难度**: 专家
**考察点**: 任务队列、线程同步、优雅关闭、工作窃取

**问题**:
```cpp
// 设计一个线程池
// 要求：
// 1. 支持提交任意函数
// 2. 支持获取任务结果（future）
// 3. 优雅关闭（等待所有任务完成）
// 4. 支持动态调整线程数
// 5. 工作窃取优化（可选）

class ThreadPool {
    // 实现
};
```

**参考答案**:

**核心设计**：
1. **任务队列**：线程安全的任务存储
2. **工作线程**：循环从队列获取任务执行
3. **同步机制**：条件变量唤醒、原子标志控制
4. **结果返回**：使用 std::packaged_task 和 std::future

**代码示例**:
```cpp
#include <iostream>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <future>
#include <vector>
#include <atomic>

class ThreadPool {
public:
    explicit ThreadPool(size_t num_threads = std::thread::hardware_concurrency())
        : stop_flag(false) {
        for (size_t i = 0; i < num_threads; ++i) {
            workers.emplace_back([this] { worker_loop(); });
        }
    }
    
    ~ThreadPool() {
        shutdown();
    }
    
    // 提交任务
    template<typename F, typename... Args>
    auto submit(F&& f, Args&&... args) -> std::future<std::invoke_result_t<F, Args...>> {
        using return_type = std::invoke_result_t<F, Args...>;
        
        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );
        
        std::future<return_type> result = task->get_future();
        
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            if (stop_flag) {
                throw std::runtime_error("Cannot submit to stopped thread pool");
            }
            tasks.emplace([task]() { (*task)(); });
        }
        
        condition.notify_one();
        return result;
    }
    
    // 优雅关闭
    void shutdown() {
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            stop_flag = true;
        }
        
        condition.notify_all();
        
        for (std::thread& worker : workers) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }
    
    // 等待所有任务完成
    void wait_all() {
        std::unique_lock<std::mutex> lock(queue_mutex);
        done_condition.wait(lock, [this] { return tasks.empty() && active_tasks == 0; });
    }
    
    size_t get_task_count() {
        std::unique_lock<std::mutex> lock(queue_mutex);
        return tasks.size();
    }
    
private:
    void worker_loop() {
        while (true) {
            std::function<void()> task;
            
            {
                std::unique_lock<std::mutex> lock(queue_mutex);
                condition.wait(lock, [this] { return stop_flag || !tasks.empty(); });
                
                if (stop_flag && tasks.empty()) {
                    return;
                }
                
                task = std::move(tasks.front());
                tasks.pop();
                ++active_tasks;
            }
            
            task();
            
            {
                std::unique_lock<std::mutex> lock(queue_mutex);
                --active_tasks;
                if (tasks.empty() && active_tasks == 0) {
                    done_condition.notify_all();
                }
            }
        }
    }
    
    std::vector<std::thread> workers;
    std::queue<std::function<void()>> tasks;
    
    std::mutex queue_mutex;
    std::condition_variable condition;
    std::condition_variable done_condition;
    
    std::atomic<bool> stop_flag;
    std::atomic<size_t> active_tasks{0};
};

// 使用示例
void threadpool_demo() {
    ThreadPool pool(4);
    
    // 提交简单任务
    auto future1 = pool.submit([]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 42;
    });
    
    // 提交带参数的任务
    auto future2 = pool.submit([](int a, int b) {
        return a + b;
    }, 10, 20);
    
    // 批量提交
    std::vector<std::future<int>> futures;
    for (int i = 0; i < 10; ++i) {
        futures.push_back(pool.submit([i]() {
            return i * i;
        }));
    }
    
    // 获取结果
    std::cout << "Result 1: " << future1.get() << "\n";
    std::cout << "Result 2: " << future2.get() << "\n";
    
    for (size_t i = 0; i < futures.size(); ++i) {
        std::cout << "Future " << i << ": " << futures[i].get() << "\n";
    }
    
    // 优雅关闭
    pool.shutdown();
}
```

**常见错误**:
- 任务队列无界导致内存耗尽
- 忘记处理提交到已关闭线程池的情况
- 条件变量虚假唤醒处理不当

**追问**:
- Q: 如何实现工作窃取？
- A: 每个线程有自己的任务队列，空闲时从其他线程队列窃取
- Q: 线程池大小如何确定？
- A: CPU 密集型：核心数；IO 密集型：更多线程

---

### 题目 29: 设计内存池

**难度**: 专家
**考察点**: 内存分配策略、对齐、碎片管理、线程安全

**问题**:
```cpp
// 设计一个固定大小对象的内存池
// 要求：
// 1. 预分配大块内存
// 2. O(1) 分配和释放
// 3. 最小化内存碎片
// 4. 线程安全（可选）
// 5. 支持对齐要求

template<typename T>
class ObjectPool {
    // 实现
};
```

**参考答案**:

**核心设计**：
1. **自由列表**：使用链表管理空闲对象
2. **内存块**：预分配大块，从中切分对象
3. **对齐**：确保对象正确对齐
4. **placement new**：在预分配内存上构造对象

**代码示例**:
```cpp
#include <iostream>
#include <vector>
#include <memory>
#include <mutex>
#include <cassert>
#include <cstddef>

// 固定大小对象池
template<typename T>
class ObjectPool {
    struct FreeNode {
        FreeNode* next;
    };
    
    struct Block {
        alignas(alignof(T)) char data[sizeof(T) * BlockSize];
        Block* next;
    };
    
    static constexpr size_t BlockSize = 1024;
    
    FreeNode* free_list = nullptr;
    Block* blocks = nullptr;
    size_t num_allocated = 0;
    size_t num_available = 0;
    
    mutable std::mutex mtx;
    
    void allocate_block() {
        Block* new_block = new Block();
        new_block->next = blocks;
        blocks = new_block;
        
        // 将新块的所有对象加入自由列表
        char* start = new_block->data;
        char* end = start + sizeof(T) * BlockSize;
        
        for (char* p = start; p < end; p += sizeof(T)) {
            FreeNode* node = reinterpret_cast<FreeNode*>(p);
            node->next = free_list;
            free_list = node;
        }
        
        num_available += BlockSize;
    }
    
public:
    ObjectPool() = default;
    
    ~ObjectPool() {
        // 注意：不调用对象的析构函数，需要使用者确保所有对象已释放
        while (blocks) {
            Block* next = blocks->next;
            delete blocks;
            blocks = next;
        }
    }
    
    // 禁用拷贝
    ObjectPool(const ObjectPool&) = delete;
    ObjectPool& operator=(const ObjectPool&) = delete;
    
    // 分配对象
    template<typename... Args>
    T* acquire(Args&&... args) {
        std::lock_guard<std::mutex> lock(mtx);
        
        if (!free_list) {
            allocate_block();
        }
        
        assert(free_list && "Out of memory");
        
        FreeNode* node = free_list;
        free_list = free_list->next;
        
        T* obj = reinterpret_cast<T*>(node);
        new (obj) T(std::forward<Args>(args)...);  // placement new
        
        --num_available;
        ++num_allocated;
        
        return obj;
    }
    
    // 释放对象
    void release(T* obj) {
        if (!obj) return;
        
        std::lock_guard<std::mutex> lock(mtx);
        
        obj->~T();  // 显式析构
        
        FreeNode* node = reinterpret_cast<FreeNode*>(obj);
        node->next = free_list;
        free_list = node;
        
        --num_allocated;
        ++num_available;
    }
    
    size_t allocated() const {
        std::lock_guard<std::mutex> lock(mtx);
        return num_allocated;
    }
    
    size_t available() const {
        std::lock_guard<std::mutex> lock(mtx);
        return num_available;
    }
};

// 使用示例
class PooledObject {
    int value;
public:
    PooledObject() : value(0) { std::cout << "Default constructed\n"; }
    explicit PooledObject(int v) : value(v) { std::cout << "Constructed with " << v << "\n"; }
    ~PooledObject() { std::cout << "Destroyed\n"; }
    
    int get_value() const { return value; }
};

void object_pool_demo() {
    ObjectPool<PooledObject> pool;
    
    auto obj1 = pool.acquire(42);
    auto obj2 = pool.acquire(100);
    
    std::cout << "obj1: " << obj1->get_value() << "\n";
    std::cout << "obj2: " << obj2->get_value() << "\n";
    std::cout << "Allocated: " << pool.allocated() << "\n";
    
    pool.release(obj1);
    pool.release(obj2);
    
    // 重用释放的内存
    auto obj3 = pool.acquire(200);
    std::cout << "obj3: " << obj3->get_value() << "\n";
    std::cout << "Allocated: " << pool.allocated() << "\n";
    
    pool.release(obj3);
}

// 无锁内存池（简化版）
template<typename T>
class LockFreeObjectPool {
    struct alignas(64) PaddedPointer {  // 避免伪共享
        std::atomic<T*> ptr;
    };
    
    // 使用无锁栈管理空闲对象
    struct FreeNode {
        T* ptr;
        std::atomic<FreeNode*> next;
    };
    
    std::atomic<FreeNode*> free_list{nullptr};
    std::vector<std::unique_ptr<T[]>> blocks;
    
public:
    explicit LockFreeObjectPool(size_t num_objects) {
        auto block = std::make_unique<T[]>(num_objects);
        for (size_t i = 0; i < num_objects; ++i) {
            release(&block[i]);  // 初始化自由列表
        }
        blocks.push_back(std::move(block));
    }
    
    T* acquire() {
        FreeNode* node = free_list.load(std::memory_order_acquire);
        while (node && !free_list.compare_exchange_weak(
            node, node->next.load(std::memory_order_relaxed),
            std::memory_order_acquire, std::memory_order_relaxed)) {}
        
        return node ? node->ptr : nullptr;
    }
    
    void release(T* obj) {
        auto new_node = new FreeNode{obj, nullptr};
        new_node->next.store(free_list.load(std::memory_order_relaxed), 
                            std::memory_order_relaxed);
        while (!free_list.compare_exchange_weak(
            new_node->next, new_node,
            std::memory_order_release, std::memory_order_relaxed)) {}
    }
};

// 常见错误
// 1. 忘记调用 placement new 构造对象
// 2. 忘记显式调用析构函数
// 3. 内存对齐不当
// 4. 多线程竞争条件

// 追问
// Q: 内存池和分配器（allocator）的区别？
// A: 内存池管理对象生命周期，allocator 只负责内存分配
// Q: 如何处理不同大小的对象？
// A: 使用 size-class 分桶，或维护多个固定大小池

// 题目 30: 设计无锁队列
// 难度: 专家
// 考察点: CAS、ABA 问题、内存序、无锁数据结构

// 问题:
// 实现一个多生产者多消费者（MPMC）无锁队列
// 要求：
// 1. 基于数组的循环队列
// 2. 支持多个生产者和消费者
// 3. 正确处理 ABA 问题
// 4. 无锁的 push 和 pop

template<typename T>
class LockFreeQueue {
    // 实现
};

// 参考答案:

// 核心设计：
// 1. 循环数组：预分配固定大小缓冲区
// 2. 原子索引：head 和 tail 使用原子变量
// 3. 序列号：每个槽位有序列号检测 ABA
// 4. CAS 操作：更新 head/tail

// 代码示例:
#include <atomic>
#include <vector>
#include <new>
#include <optional>

template<typename T>
class LockFreeQueue {
    struct Cell {
        std::atomic<size_t> sequence;
        T data;
    };
    
    alignas(64) std::atomic<size_t> head{0};
    alignas(64) std::atomic<size_t> tail{0};
    
    std::vector<Cell> buffer;
    size_t mask;
    
public:
    explicit LockFreeQueue(size_t capacity) {
        size_t pow2 = 1;
        while (pow2 < capacity) pow2 <<= 1;
        buffer.resize(pow2);
        mask = pow2 - 1;
        
        for (size_t i = 0; i < pow2; ++i) {
            buffer[i].sequence.store(i, std::memory_order_relaxed);
        }
    }
    
    bool push(const T& value) {
        Cell* cell = nullptr;
        size_t seq = 0;
        size_t pos = 0;
        
        while (true) {
            pos = tail.load(std::memory_order_relaxed);
            cell = &buffer[pos & mask];
            seq = cell->sequence.load(std::memory_order_acquire);
            
            intptr_t diff = static_cast<intptr_t>(seq) - static_cast<intptr_t>(pos);
            
            if (diff == 0) {
                // 队列未满，尝试更新 tail
                if (tail.compare_exchange_weak(pos, pos + 1, 
                    std::memory_order_relaxed)) {
                    break;
                }
            } else if (diff < 0) {
                // 队列已满
                return false;
            }
            // 其他线程正在操作，重试
        }
        
        cell->data = value;
        cell->sequence.store(pos + 1, std::memory_order_release);
        return true;
    }
    
    std::optional<T> pop() {
        Cell* cell = nullptr;
        size_t seq = 0;
        size_t pos = 0;
        
        while (true) {
            pos = head.load(std::memory_order_relaxed);
            cell = &buffer[pos & mask];
            seq = cell->sequence.load(std::memory_order_acquire);
            
            intptr_t diff = static_cast<intptr_t>(seq) - static_cast<intptr_t>(pos + 1);
            
            if (diff == 0) {
                // 队列非空，尝试更新 head
                if (head.compare_exchange_weak(pos, pos + 1,
                    std::memory_order_relaxed)) {
                    break;
                }
            } else if (diff < 0) {
                // 队列已空
                return std::nullopt;
            }
            // 其他线程正在操作，重试
        }
        
        T result = std::move(cell->data);
        cell->sequence.store(pos + mask + 1, std::memory_order_release);
        return result;
    }
    
    bool empty() const {
        return head.load(std::memory_order_relaxed) == 
               tail.load(std::memory_order_relaxed);
    }
    
    size_t size() const {
        return tail.load(std::memory_order_relaxed) - 
               head.load(std::memory_order_relaxed);
    }
};

// 使用示例
void lockfree_queue_demo() {
    LockFreeQueue<int> queue(16);
    
    // 单线程测试
    for (int i = 0; i < 10; ++i) {
        queue.push(i);
    }
    
    while (auto val = queue.pop()) {
        std::cout << "Popped: " << *val << "\n";
    }
    
    // 多线程测试
    LockFreeQueue<int> mpmc_queue(1024);
    std::atomic<int> sum{0};
    
    std::vector<std::thread> producers;
    for (int t = 0; t < 4; ++t) {
        producers.emplace_back([&mpmc_queue, t]() {
            for (int i = 0; i < 100; ++i) {
                while (!mpmc_queue.push(t * 100 + i)) {
                    std::this_thread::yield();
                }
            }
        });
    }
    
    std::vector<std::thread> consumers;
    for (int t = 0; t < 4; ++t) {
        consumers.emplace_back([&mpmc_queue, &sum]() {
            int count = 0;
            while (count < 100) {
                if (auto val = mpmc_queue.pop()) {
                    sum += *val;
                    ++count;
                } else {
                    std::this_thread::yield();
                }
            }
        });
    }
    
    for (auto& t : producers) t.join();
    for (auto& t : consumers) t.join();
    
    std::cout << "Sum: " << sum.load() << "\n";
}

// 常见错误
// 1. 忽略 ABA 问题（使用序列号解决）
// 2. 错误的 memory_order 导致数据竞争
// 3. 忘记处理队列满/空的情况
// 4. 无限自旋不 yield

// 追问
// Q: 这个队列有什么限制？
// A: 固定大小，需要预分配；忙等待消耗 CPU
// Q: 如何实现阻塞等待？
// A: 结合条件变量或使用 semaphore（C++20）
// Q: 与有锁队列的性能对比？
// A: 高竞争时无锁更好，低竞争时有锁可能更快

// 总结
// 
// 本文档涵盖了 C++ 高级/专家级面试的核心主题：
// 
// 1. 类型系统与语言基础：auto 推导、类型转换、初始化陷阱
// 2. 面向对象与多态：虚函数表、菱形继承、析构函数异常安全
// 3. 模板与泛型编程：SFINAE、特化优先级、CRTP、变参模板
// 4. 现代 C++ 特性：移动语义、完美转发、智能指针线程安全、lambda 捕获
// 5. 内存管理：RAII、对象布局、placement new
// 6. STL：迭代器失效、容器选择、sort 比较器
// 7. 并发编程：memory_order、ABA 问题、线程安全单例
// 8. 性能优化：编译优化、缓存友好、benchmark 方法
// 9. 方案设计：智能指针、线程池、内存池、无锁队列
// 
// 面试建议：
// - 理解原理比记住答案更重要
// - 能够画出内存布局图
// - 了解 C++ 标准演进（C++11/14/17/20）
// - 有实际项目经验支撑
// - 关注 Undefined Behavior 和性能影响
// 
// ---
// 
// > 本文档持续更新，如有问题欢迎反馈。
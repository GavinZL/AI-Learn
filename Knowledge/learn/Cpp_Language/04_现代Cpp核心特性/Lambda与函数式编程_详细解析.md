# Lambda 与函数式编程详细解析

> **核心结论**：Lambda 是编译器生成的匿名函数对象，捕获列表决定其状态存储方式。理解闭包类型的实现机制是避免捕获悬空引用和性能陷阱的关键。

---

## 1. Why — 为什么需要 Lambda

### 1.1 传统函数对象的痛点

```cpp
// C++98/03：使用函数对象（繁琐）
class GreaterThan {
    int threshold_;
public:
    explicit GreaterThan(int threshold) : threshold_(threshold) {}
    bool operator()(int value) const {
        return value > threshold_;
    }
};

// 使用
std::vector<int> vec = {1, 5, 10, 15, 20};
auto it = std::find_if(vec.begin(), vec.end(), GreaterThan(10));

// 问题：
// 1. 需要定义单独的类（可能在远离使用处）
// 2. 代码冗余，意图不够清晰
// 3. 无法访问局部变量（除非通过构造函数传递）
```

### 1.2 Lambda 的优势

```cpp
// C++11：使用 Lambda（简洁直观）
int threshold = 10;
auto it = std::find_if(vec.begin(), vec.end(), 
    [threshold](int value) {  // 直接捕获局部变量
        return value > threshold;
    });

// 优势：
// 1. 内联定义，意图清晰
// 2. 自动捕获上下文变量
// 3. 编译器生成优化代码（通常优于手写函数对象）
```

---

## 2. What — Lambda 的本质

### 2.1 Lambda 是编译器生成的闭包类型

```cpp
// Lambda 表达式
auto lambda = [x, &y](int a, int b) -> int { return a + b + x + y; };

// 编译器生成的等价代码（概念上）
class __LambdaClosure {
    int x_;           // 值捕获：成员变量
    int& y_;          // 引用捕获：引用成员
public:
    __LambdaClosure(int x, int& y) : x_(x), y_(y) {}
    
    int operator()(int a, int b) const {  // 默认 const
        return a + b + x_ + y_;
    }
};

// 实际使用
int x = 1, y = 2;
auto lambda = __LambdaClosure(x, y);
```

### 2.2 Lambda 的类型特征

```cpp
// 每个 Lambda 都有唯一的闭包类型
auto lambda1 = []() {};
auto lambda2 = []() {};

// lambda1 和 lambda2 是不同的类型！
// static_assert(std::is_same_v<decltype(lambda1), decltype(lambda2)>);  // 编译错误

// 类型特征
static_assert(sizeof(lambda1) == 1);  // 空 Lambda 大小为 1（C++ 要求对象至少1字节）

// 有捕获的 Lambda
int x = 42;
auto lambda3 = [x]() {};
static_assert(sizeof(lambda3) == sizeof(int));  // 大小等于捕获变量之和
```

---

## 3. How — Lambda 语法详解

### 3.1 完整语法结构

```cpp
// [捕获列表](参数列表) 修饰符 -> 返回类型 { 函数体 }

// 各部分详解：
auto lambda = [
    capture-list      // [x, &y, z = expr, this, *this, ...]
](
    params            // (int a, double b) 或 (auto a, auto b) C++14
) 
mutable             // 可选：允许修改值捕获的变量
constexpr           // C++17：显式指定为 constexpr
consteval           // C++20：保证编译期求值
-> ReturnType       // 可选：显式返回类型
{
    // 函数体
    return result;
};
```

### 3.2 捕获列表详解

```cpp
#include <iostream>
#include <string>

void captureExamples() {
    int x = 10;
    int y = 20;
    std::string str = "hello";
    
    // 1. 空捕获 []
    auto lambda1 = []() { return 42; };
    
    // 2. 值捕获 [x]
    auto lambda2 = [x]() { return x * 2; };
    // x 被拷贝到闭包对象中
    
    // 3. 引用捕获 [&y]
    auto lambda3 = [&y]() { return ++y; };  // 修改原始 y
    
    // 4. 隐式值捕获 [=]
    auto lambda4 = [=]() { return x + y; };  // x 和 y 都被拷贝
    
    // 5. 隐式引用捕获 [&]
    auto lambda5 = [&]() { x++; y++; };  // 修改原始变量
    
    // 6. 混合捕获
    auto lambda6 = [=, &y]() {  // 默认值捕获，y 引用捕获
        // x 是拷贝，y 是引用
        return x + ++y;
    };
    
    auto lambda7 = [&, x]() {  // 默认引用捕获，x 值捕获
        // y 是引用，x 是拷贝
        return x + ++y;
    };
    
    // 7. C++14 初始化捕获（广义捕获）
    auto lambda8 = [z = x + y]() { return z; };  // z 是闭包内的变量
    auto lambda9 = [ptr = std::make_unique<int>(42)]() { return *ptr; };
    
    // 8. C++17 *this 捕获
    struct Widget {
        int value = 100;
        auto getLambda() {
            return [*this]() { return value; };  // 拷贝整个对象
        }
    };
    
    // 9. this 捕获
    struct Widget2 {
        int value = 100;
        auto getLambda() {
            return [this]() { return value; };  // 捕获 this 指针
        }
    };
}
```

### 3.3 mutable Lambda

```cpp
#include <iostream>

void mutableExample() {
    int x = 10;
    
    // 默认 Lambda 的 operator() 是 const
    auto lambda1 = [x]() {
        // x++;  // 错误：不能修改 const 成员
        return x;
    };
    
    // mutable 允许修改值捕获的变量
    auto lambda2 = [x]() mutable {
        x++;  // OK：修改闭包内的拷贝
        return x;
    };
    
    std::cout << lambda2() << std::endl;  // 11
    std::cout << lambda2() << std::endl;  // 12（每次调用都修改闭包内的 x）
    std::cout << "Original x: " << x << std::endl;  // 10（原变量未变）
}
```

### 3.4 C++14 Generic Lambda

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

void genericLambdaExample() {
    // C++14：使用 auto 参数的泛型 Lambda
    auto add = [](auto a, auto b) {
        return a + b;
    };
    
    std::cout << add(1, 2) << std::endl;        // int
    std::cout << add(1.5, 2.5) << std::endl;    // double
    std::cout << add(std::string("Hello"), std::string(" World")) << std::endl;
    
    // 编译器生成的等价代码（概念上）
    // struct __GenericLambda {
    //     template<typename T, typename U>
    //     auto operator()(T a, U b) const { return a + b; }
    // };
    
    // 泛型 Lambda 与 STL 算法
    std::vector<int> vec = {1, 2, 3, 4, 5};
    
    // 使用泛型 Lambda 处理多种类型
    std::for_each(vec.begin(), vec.end(), [](const auto& elem) {
        std::cout << elem << " ";
    });
}
```

### 3.5 C++17 constexpr Lambda

```cpp
#include <array>

// C++17：Lambda 可以隐式为 constexpr
constexpr auto square = [](int n) { return n * n; };

constexpr int result = square(5);  // 编译期计算

// 显式 constexpr
constexpr auto factorial = [](auto self, int n) -> int {
    return n <= 1 ? 1 : n * self(self, n - 1);
};

// C++23 支持显式 this 递归
// constexpr auto factorial2 = [](this auto self, int n) -> int {
//     return n <= 1 ? 1 : n * self(n - 1);
// };

void constexprLambdaExample() {
    // 编译期计算数组大小
    constexpr size_t size = square(4);
    std::array<int, size> arr;  // OK：size = 16
}
```

---

## 4. Lambda 与 std::function 的性能差异

### 4.1 类型擦除的开销

```cpp
#include <functional>
#include <iostream>
#include <chrono>

void performanceComparison() {
    int sum = 0;
    
    // Lambda 类型（具体类型，内联优化友好）
    auto lambda = [&sum](int x) { sum += x; };
    
    // std::function（类型擦除，有运行时开销）
    std::function<void(int)> func = [&sum](int x) { sum += x; };
    
    const int N = 10000000;
    
    // Lambda 性能测试
    auto start1 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; ++i) {
        lambda(i);
    }
    auto end1 = std::chrono::high_resolution_clock::now();
    
    // std::function 性能测试
    auto start2 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; ++i) {
        func(i);
    }
    auto end2 = std::chrono::high_resolution_clock::now();
    
    auto lambdaTime = std::chrono::duration_cast<std::chrono::microseconds>(end1 - start1).count();
    auto funcTime = std::chrono::duration_cast<std::chrono::microseconds>(end2 - start2).count();
    
    std::cout << "Lambda: " << lambdaTime << " us" << std::endl;
    std::cout << "std::function: " << funcTime << " us" << std::endl;
    std::cout << "Overhead: " << (double)funcTime / lambdaTime << "x" << std::endl;
    // 典型结果：std::function 比 Lambda 慢 2-5 倍
}
```

### 4.2 内存布局对比

```cpp
#include <functional>
#include <iostream>

void memoryComparison() {
    int x = 42;
    
    // Lambda：直接存储捕获变量
    auto lambda = [x]() { return x; };
    std::cout << "Lambda size: " << sizeof(lambda) << std::endl;  // 4（仅 int）
    
    // std::function：类型擦除容器
    std::function<int()> func = [x]() { return x; };
    std::cout << "std::function size: " << sizeof(func) << std::endl;  // 32+（实现相关）
    
    // std::function 内部结构（概念上）：
    // - 指向堆分配对象的指针（如果 Lambda 太大）
    // - 或本地存储缓冲区（小对象优化）
    // - 指向调用函数的指针（vtable）
    // - 指向删除/拷贝函数的指针
}
```

### 4.3 使用建议

```cpp
// 1. 优先使用具体 Lambda 类型（模板参数）
template<typename Func>
void process(Func&& func) {  // 完美转发 Lambda
    func();
}

// 2. 仅在需要类型擦除时使用 std::function
class EventHandler {
    std::vector<std::function<void()>> callbacks_;  // 需要存储异构类型
public:
    void addCallback(std::function<void()> cb) {
        callbacks_.push_back(std::move(cb));
    }
};

// 3. 避免在热点路径使用 std::function
void hotPath() {
    // 不好
    std::function<int(int)> op = [](int x) { return x * 2; };
    
    // 好
    auto op2 = [](int x) { return x * 2; };
}
```

---

## 5. 高阶函数模式

### 5.1 函数组合

```cpp
#include <iostream>
#include <functional>

// 函数组合：compose(f, g)(x) = f(g(x))
template<typename F, typename G>
auto compose(F&& f, G&& g) {
    return [f = std::forward<F>(f), g = std::forward<G>(g)](auto&&... args) {
        return f(g(std::forward<decltype(args)>(args)...));
    };
}

// 管道操作：x | f | g = g(f(x))
template<typename T, typename F>
auto operator|(T&& value, F&& func) {
    return func(std::forward<T>(value));
}

void higherOrderExample() {
    auto addOne = [](int x) { return x + 1; };
    auto doubleIt = [](int x) { return x * 2; };
    
    // 函数组合
    auto addThenDouble = compose(doubleIt, addOne);
    std::cout << addThenDouble(5) << std::endl;  // (5 + 1) * 2 = 12
    
    // 管道操作
    auto result = 5 | addOne | doubleIt;
    std::cout << result << std::endl;  // 12
}
```

### 5.2 柯里化（Currying）

```cpp
#include <iostream>
#include <functional>

// 简单柯里化实现
template<typename Func>
auto curry(Func func) {
    return [func](auto x) {
        return [func, x](auto y) {
            return func(x, y);
        };
    };
}

void curryingExample() {
    auto add = [](int a, int b) { return a + b; };
    auto curriedAdd = curry(add);
    
    auto addFive = curriedAdd(5);
    std::cout << addFive(3) << std::endl;   // 8
    std::cout << addFive(10) << std::endl;  // 15
}
```

### 5.3 惰性求值

```cpp
#include <iostream>
#include <functional>
#include <optional>

// 惰性求值包装器
template<typename Func>
class Lazy {
    mutable std::optional<std::invoke_result_t<Func>> value_;
    mutable Func func_;
    
public:
    explicit Lazy(Func func) : func_(std::move(func)) {}
    
    const auto& get() const {
        if (!value_) {
            value_ = func_();
        }
        return *value_;
    }
    
    auto operator()() const { return get(); }
};

template<typename Func>
auto makeLazy(Func&& func) {
    return Lazy<std::decay_t<Func>>(std::forward<Func>(func));
}

void lazyEvaluationExample() {
    // 昂贵的计算
    auto expensive = makeLazy([]() {
        std::cout << "Computing..." << std::endl;
        return 42;
    });
    
    std::cout << "Before access" << std::endl;
    std::cout << expensive() << std::endl;  // 此时才计算
    std::cout << expensive() << std::endl;  // 使用缓存值
}
```

---

## 6. Lambda 在 STL 算法中的应用

### 6.1 算法组合

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

void stlAlgorithmExample() {
    std::vector<int> vec = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    
    // 1. 过滤 + 转换 + 聚合
    auto result = std::accumulate(vec.begin(), vec.end(), 0,
        [](int sum, int x) {
            return x % 2 == 0 ? sum + x * x : sum;  // 偶数平方和
        });
    std::cout << "Sum of squares of even numbers: " << result << std::endl;
    
    // 2. 自定义比较
    std::sort(vec.begin(), vec.end(), 
        [](int a, int b) {
            return std::abs(a - 5) < std::abs(b - 5);  // 按距离5的远近排序
        });
    
    // 3. 查找满足条件的元素
    auto it = std::find_if(vec.begin(), vec.end(),
        [](int x) { return x > 5 && x % 3 == 0; });
    
    // 4. 分区
    auto mid = std::partition(vec.begin(), vec.end(),
        [](int x) { return x < 5; });
}
```

### 6.2 C++20 范围库（Ranges）

```cpp
// C++20 范围库提供更优雅的函数式风格
#include <ranges>
#include <vector>
#include <iostream>

void rangesExample() {
    std::vector<int> vec = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    
    // 管道操作：过滤偶数 -> 平方 -> 取前3个 -> 求和
    auto result = vec 
        | std::views::filter([](int x) { return x % 2 == 0; })
        | std::views::transform([](int x) { return x * x; })
        | std::views::take(3);
    
    for (int x : result) {
        std::cout << x << " ";  // 4 16 36
    }
}
```

---

## 7. 递归 Lambda

### 7.1 使用 std::function 实现递归

```cpp
#include <iostream>
#include <functional>

void recursiveLambdaWithFunction() {
    // 使用 std::function 实现递归（有开销）
    std::function<int(int)> factorial = [&](int n) -> int {
        return n <= 1 ? 1 : n * factorial(n - 1);
    };
    
    std::cout << factorial(5) << std::endl;  // 120
}
```

### 7.2 Y 组合子模式（无 std::function）

```cpp
#include <iostream>

// Y 组合子实现递归 Lambda
template<typename F>
struct Recursive {
    F f;
    template<typename... Args>
    decltype(auto) operator()(Args&&... args) const {
        return f(*this, std::forward<Args>(args)...);
    }
};

template<typename F>
Recursive<std::decay_t<F>> makeRecursive(F&& f) {
    return {std::forward<F>(f)};
}

void yCombinatorExample() {
    auto factorial = makeRecursive([](auto& self, int n) -> int {
        return n <= 1 ? 1 : n * self(self, n - 1);
    });
    
    std::cout << factorial(5) << std::endl;  // 120
    
    auto fibonacci = makeRecursive([](auto& self, int n) -> int {
        return n <= 1 ? n : self(self, n - 1) + self(self, n - 2);
    });
    
    std::cout << fibonacci(10) << std::endl;  // 55
}
```

### 7.3 C++23 显式 this 参数

```cpp
// C++23 支持显式 this 参数，简化递归 Lambda
// auto factorial = [](this auto self, int n) -> int {
//     return n <= 1 ? 1 : n * self(n - 1);
// };
```

---

## 8. 面试要点

### 8.1 高频面试题

#### Q1: Lambda 的捕获方式有哪些？值捕获和引用捕获的区别？

**答案**：
- **值捕获 `[x]`**：拷贝变量到闭包，修改不影响原变量，默认 const
- **引用捕获 `[&x]`**：存储引用，修改影响原变量
- **隐式值捕获 `[=]`**：默认所有变量值捕获
- **隐式引用捕获 `[&]`**：默认所有变量引用捕获
- **初始化捕获 `[x = expr]`**：C++14，可捕获移动语义类型
- **this 捕获 `[this]`**：捕获 this 指针；`[*this]`：C++17，拷贝整个对象

```cpp
int x = 10, y = 20;

[=] { return x + y; };      // x, y 都是值捕获
[&] { return x + y; };      // x, y 都是引用捕获
[=, &y] { return x + ++y; }; // x 值捕获，y 引用捕获
[&, x] { return x + ++y; };  // x 值捕获，y 引用捕获
```

#### Q2: Lambda 和 std::function 的性能差异？

**答案**：
- **Lambda**：编译器生成的具体闭包类型，内联友好，零开销抽象
- **std::function**：类型擦除容器，使用虚函数或函数指针间接调用
- **性能差异**：std::function 通常比 Lambda 慢 2-5 倍，有额外内存开销
- **使用建议**：优先使用模板参数传递 Lambda，仅在需要类型擦除时使用 std::function

```cpp
// 推荐：模板参数
void process(auto&& func) { func(); }

// 避免：热点路径使用 std::function
void hotPath(std::function<void()> func);  // 有开销
```

#### Q3: 如何捕获悬空引用？如何避免？

**答案**：
- **问题**：Lambda 的生命周期可能超过捕获的引用变量的生命周期
- **典型场景**：返回包含引用捕获的 Lambda，异步执行 Lambda

```cpp
// 错误：返回引用捕获的 Lambda
auto createBadLambda() {
    int x = 42;
    return [&x] { return x; };  // 返回后 x 已销毁！
}

// 正确：值捕获
auto createGoodLambda() {
    int x = 42;
    return [x] { return x; };  // 安全：拷贝 x
}

// 异步执行陷阱
void asyncTrap() {
    int x = 42;
    std::async([&x] {  // 危险：x 可能在 Lambda 执行前销毁
        std::cout << x;
    });
}  // x 在这里销毁
```

#### Q4: 泛型 Lambda 是如何实现的？

**答案**：
- C++14 引入 `auto` 参数，编译器生成带模板 `operator()` 的闭包类型
- 每次调用时根据实参类型实例化模板

```cpp
auto lambda = [](auto a, auto b) { return a + b; };

// 编译器生成（概念上）：
struct __GenericLambda {
    template<typename T, typename U>
    auto operator()(T a, U b) const { return a + b; }
};
```

#### Q5: 闭包类型的大小如何计算？

**答案**：
- 空 Lambda：大小为 1（C++ 要求对象至少 1 字节）
- 有捕获的 Lambda：大小等于所有捕获变量的总和（考虑对齐）
- 捕获 this 指针：大小为指针大小（8 字节）
- 引用捕获：存储指针，大小为指针大小

```cpp
auto empty = []{};
static_assert(sizeof(empty) == 1);

int x;
auto capture = [x]{};
static_assert(sizeof(capture) == sizeof(int));

auto refCapture = [&x]{};
static_assert(sizeof(refCapture) == sizeof(void*));
```

---

## 9. 最佳实践

### 9.1 捕获建议

```cpp
// 1. 优先使用显式捕获，避免隐式捕获
// 不好
[=] { /* 不知道捕获了什么 */ };
[&] { /* 不知道捕获了什么 */ };

// 好
[x, &y] { /* 明确知道捕获了什么 */ };

// 2. 需要修改捕获变量时使用 mutable
int counter = 0;
auto increment = [counter]() mutable {
    return ++counter;  // 修改闭包内的拷贝
};

// 3. 移动语义类型使用初始化捕获
auto ptr = std::make_unique<int>(42);
auto lambda = [p = std::move(ptr)]() { return *p; };

// 4. 类成员 Lambda 注意 this 捕获
class Widget {
    int value_;
public:
    auto getLambda() {
        return [*this] { return value_; };  // C++17：拷贝对象
    }
};
```

### 9.2 性能优化

```cpp
// 1. 避免 std::function 的过度使用
template<typename Callback>
void process(Callback&& cb) {  // 模板参数，零开销
    std::forward<Callback>(cb)();
}

// 2. 使用 constexpr Lambda 进行编译期计算
constexpr auto square = [](int n) { return n * n; };
std::array<int, square(4)> arr;  // 编译期确定大小

// 3. 注意 Lambda 拷贝开销
BigObject obj;
// 不好：多次拷贝
auto lambda1 = [obj] {};
auto lambda2 = lambda1;

// 好：使用引用或移动
auto lambda3 = [&obj] {};  // 引用捕获
auto lambda4 = [obj = std::move(obj)] {};  // 移动捕获
```

---

## 10. 常见陷阱

### 10.1 悬空引用陷阱

```cpp
// 陷阱 1：返回引用捕获的 Lambda
auto createLambda() {
    int local = 42;
    return [&local] { return local; };  // UB！
}

// 陷阱 2：异步 Lambda
void asyncCallback() {
    std::string data = "important";
    std::thread([&data] {  // data 可能在 thread 执行前销毁
        process(data);
    }).detach();
}  // data 销毁

// 陷阱 3：循环中捕获
std::vector<std::function<void()>> callbacks;
for (int i = 0; i < 10; ++i) {
    callbacks.push_back([&i] {  // 所有 Lambda 引用同一个 i
        std::cout << i;
    });
}
// 所有回调输出 10（或 UB）

// 正确做法
for (int i = 0; i < 10; ++i) {
    callbacks.push_back([i] {  // 值捕获
        std::cout << i;
    });
}
```

### 10.2 mutable 陷阱

```cpp
// 陷阱：mutable Lambda 的拷贝行为
auto lambda = [x = 0]() mutable { return ++x; };

auto lambda2 = lambda;  // 拷贝闭包，包括 x 的值

std::cout << lambda() << std::endl;   // 1
std::cout << lambda() << std::endl;   // 2
std::cout << lambda2() << std::endl;  // 1（独立的 x）
std::cout << lambda2() << std::endl;  // 2
```

### 10.3 递归陷阱

```cpp
// 陷阱：Lambda 内部无法直接引用自身
auto factorial = [](int n) {  // 编译错误：factorial 未定义
    return n <= 1 ? 1 : n * factorial(n - 1);
};

// 解决方案 1：使用 std::function
std::function<int(int)> factorial = [&](int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
};

// 解决方案 2：Y 组合子（见上文）
```

---

## 11. 总结

### 核心要点回顾

1. **Lambda 本质**：编译器生成的匿名闭包类型，包含 `operator()`
2. **捕获机制**：值捕获创建拷贝，引用捕获存储指针
3. **性能考量**：Lambda 零开销，std::function 有类型擦除开销
4. **生命周期**：特别注意引用捕获的悬空引用问题
5. **泛型支持**：C++14 auto 参数，C++17 constexpr，C++23 显式 this

### 学习路径

```
基本语法 → 捕获机制 → 闭包类型 → 性能特性 → 高阶函数 → 最佳实践
```

Lambda 是现代 C++ 函数式编程的基石，掌握其内部机制对编写高效、安全的代码至关重要。

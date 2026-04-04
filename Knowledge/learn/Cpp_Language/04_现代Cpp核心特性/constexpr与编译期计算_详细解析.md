# constexpr 与编译期计算详细解析

> **核心结论**：`constexpr` 是 C++ 编译期编程的基石，C++11 引入、C++14 放宽限制、C++17 引入 `if constexpr` 实现编译期分支。理解编译期与运行期的边界是高效使用 constexpr 的关键。

---

## 1. Why — 为什么需要编译期计算

### 1.1 运行期计算的代价

```cpp
// 运行期计算的局限性
#include <array>
#include <cmath>

// 问题 1：数组大小必须是编译期常量
int n = 10;
// int arr[n];  // 错误：VLA（GCC 扩展）

// 问题 2：查找表在运行期初始化
const double sinTable[360] = {
    std::sin(0 * 3.14159 / 180),    // 运行期计算
    std::sin(1 * 3.14159 / 180),
    // ... 360 次函数调用
};

// 问题 3：模板元编程的复杂性
template<int N>
struct Factorial {
    static const int value = N * Factorial<N - 1>::value;
};

template<>
struct Factorial<0> {
    static const int value = 1;
};
// 语法复杂，调试困难
```

### 1.2 编译期计算的价值

```cpp
// 编译期计算的优势
constexpr int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

constexpr int result = factorial(5);  // 编译期计算，结果为 120

// 应用：编译期数组大小
std::array<int, factorial(5)> arr;  // 数组大小为 120

// 应用：编译期查找表
constexpr auto makeSinTable() {
    std::array<double, 360> table{};
    for (int i = 0; i < 360; ++i) {
        table[i] = std::sin(i * 3.14159265359 / 180);
    }
    return table;
}
constexpr auto sinTable = makeSinTable();  // 编译期生成
```

---

## 2. What — constexpr 的本质

### 2.1 constexpr 变量

```cpp
// constexpr 变量必须是编译期可计算的
constexpr int maxSize = 100;           // OK：字面量
constexpr int doubleSize = maxSize * 2; // OK：编译期表达式

const int runtimeValue = getValue();    // 运行期值
// constexpr int bad = runtimeValue;    // 错误：不是编译期常量

// constexpr vs const 的区别
const int c1 = 10;           // 编译期常量（可能）
const int c2 = getValue();   // 运行期常量

constexpr int ce1 = 10;      // 必须是编译期常量
// constexpr int ce2 = getValue();  // 错误

// constexpr 变量隐含 const
// constexpr int x = 10;
// x = 20;  // 错误：x 是 const
```

### 2.2 constexpr 函数演进

```cpp
// C++11：严格限制
constexpr int add_cpp11(int a, int b) {
    return a + b;  // 只能有一条 return 语句
}

// C++14：放宽限制
constexpr int factorial_cpp14(int n) {
    int result = 1;      // 可以声明变量
    for (int i = 2; i <= n; ++i) {  // 可以使用循环
        result *= i;
    }
    return result;
}

// C++17：进一步放宽
constexpr int complex_cpp17(int n) {
    if (n <= 0) return 0;  // 可以使用 if（C++14 也可以）
    
    int sum = 0;
    for (int i = 0; i < n; ++i) {
        sum += i;
    }
    return sum;
}

// C++20：constexpr 虚函数、try-catch、new/delete
// constexpr int cpp20_features() {
//     int* p = new int(42);  // C++20 允许
//     int result = *p;
//     delete p;
//     return result;
// }
```

---

## 3. How — constexpr 使用详解

### 3.1 constexpr 函数规则

```cpp
// constexpr 函数的基本规则

// 1. 隐式 const（C++14 前）
struct Point {
    int x, y;
    
    // C++11：constexpr 成员函数隐式 const
    constexpr int sum() const {  // 必须标记 const
        return x + y;
    }
    
    // C++17：非 const constexpr 成员函数
    constexpr void setX(int val) {  // C++17 起允许
        x = val;
    }
};

// 2. 编译期 vs 运行期调用
constexpr int compute(int n) {
    return n * n;
}

void usage() {
    constexpr int a = compute(5);  // 编译期计算
    
    int x = 5;
    int b = compute(x);  // 运行期计算（x 不是编译期常量）
    
    // 强制编译期计算（C++23）
    // int c = consteval_call(compute(5));
}

// 3. constexpr 函数可以调用非 constexpr 函数吗？
// 答案：可以，但此时调用不是编译期计算
constexpr int maybeCompileTime(int n) {
    if (std::is_constant_evaluated()) {  // C++20
        return n * n;  // 编译期路径
    } else {
        std::cout << "Runtime" << std::endl;  // 运行期路径
        return n;
    }
}
```

### 3.2 constexpr 与字面量类型

```cpp
// 字面量类型（Literal Type）：可以在编译期构造和使用的类型

// 1. 标量类型是字面量类型
// int, double, bool, 指针, 引用, 枚举

// 2. 自定义字面量类型
class LiteralType {
    int value_;
    
public:
    // constexpr 构造函数
    constexpr LiteralType(int v) : value_(v) {}
    
    // constexpr 成员函数
    constexpr int get() const { return value_; }
    constexpr void set(int v) { value_ = v; }  // C++17
    
    // 析构函数必须是平凡的（trivial）
    ~LiteralType() = default;
};

// 使用
constexpr LiteralType lt(42);
constexpr int val = lt.get();

// 3. 非字面量类型
class NonLiteral {
    std::string str_;  // string 不是字面量类型
public:
    // 不是 constexpr 构造函数
    NonLiteral(const char* s) : str_(s) {}
};

// NonLiteral nl("hello");  // 运行期对象
```

### 3.3 C++17 if constexpr

```cpp
// if constexpr：编译期分支

// 传统 SFINAE 方式（复杂）
template<typename T>
std::enable_if_t<std::is_integral_v<T>, T>
process(T value) {
    return value * 2;
}

template<typename T>
std::enable_if_t<!std::is_integral_v<T>, T>
process(T value) {
    return value;
}

// C++17 if constexpr（简洁）
template<typename T>
auto process_cpp17(T value) {
    if constexpr (std::is_integral_v<T>) {
        return value * 2;  // 只有 T 是整数类型时编译
    } else {
        return value;      // 否则编译这部分
    }
}

// 实际应用：类型安全的访问
template<typename T, typename U>
constexpr auto add(T t, U u) {
    if constexpr (std::is_same_v<T, U>) {
        return t + u;
    } else {
        // 类型转换
        using Common = std::common_type_t<T, U>;
        return static_cast<Common>(t) + static_cast<Common>(u);
    }
}

// 编译期类型选择
template<typename T>
using add_const_if_pointer = std::conditional_t<
    std::is_pointer_v<T>,
    std::add_const_t<T>,
    T
>;

// 结合 if constexpr 和类型特征
template<typename Container>
auto getFirst(Container& c) {
    if constexpr (std::is_array_v<Container>) {
        return c[0];  // 数组
    } else {
        return *c.begin();  // 容器
    }
}
```

---

## 4. 编译期计算的实际应用

### 4.1 编译期查找表

```cpp
#include <array>
#include <cmath>

// 编译期生成正弦查找表
constexpr auto generateSinTable() {
    std::array<double, 360> table{};
    for (int i = 0; i < 360; ++i) {
        table[i] = std::sin(i * 3.14159265358979323846 / 180.0);
    }
    return table;
}

constexpr auto sinTable = generateSinTable();

// 使用
double fastSin(int degrees) {
    return sinTable[degrees % 360];
}

// 编译期字符串哈希
constexpr uint32_t hashString(const char* str, int h = 0) {
    return !str[h] ? 5381 : (hashString(str, h + 1) * 33) ^ static_cast<unsigned char>(str[h]);
}

constexpr uint32_t operator"" _hash(const char* str, size_t) {
    return hashString(str);
}

// 使用
switch (hashString(command)) {
    case "start"_hash: /* ... */ break;
    case "stop"_hash:  /* ... */ break;
}
```

### 4.2 编译期元编程

```cpp
// 编译期计算斐波那契数列
constexpr int fibonacci(int n) {
    if (n <= 1) return n;
    int a = 0, b = 1;
    for (int i = 2; i <= n; ++i) {
        int temp = a + b;
        a = b;
        b = temp;
    }
    return b;
}

constexpr auto fib10 = fibonacci(10);  // 55

// 编译期类型列表操作
template<typename... Types>
struct TypeList {
    static constexpr size_t size = sizeof...(Types);
};

// 编译期获取类型列表大小
template<typename List>
struct Size;

template<typename... Types>
struct Size<TypeList<Types...>> {
    static constexpr size_t value = sizeof...(Types);
};

// if constexpr 简化元编程
template<typename T>
constexpr auto typeName() {
    if constexpr (std::is_integral_v<T>) {
        return "integral";
    } else if constexpr (std::is_floating_point_v<T>) {
        return "floating point";
    } else if constexpr (std::is_pointer_v<T>) {
        return "pointer";
    } else {
        return "other";
    }
}
```

### 4.3 编译期正则表达式（C++17）

```cpp
#include <regex>

// C++17 支持 constexpr 正则表达式
constexpr bool matchPattern(const char* str, const char* pattern) {
    // 简化实现
    if (*pattern == '\0') return *str == '\0';
    if (*pattern == '*') {
        return matchPattern(str, pattern + 1) || 
               (*str && matchPattern(str + 1, pattern));
    }
    if (*pattern == *str) {
        return matchPattern(str + 1, pattern + 1);
    }
    return false;
}

// 编译期验证
static_assert(matchPattern("hello", "h*o"));
static_assert(!matchPattern("hello", "h*x"));
```

---

## 5. constexpr vs 模板元编程

### 5.1 对比分析

```cpp
// 模板元编程（TMP）方式：计算阶乘
template<int N>
struct FactorialTMP {
    static constexpr int value = N * FactorialTMP<N - 1>::value;
};

template<>
struct FactorialTMP<0> {
    static constexpr int value = 1;
};

constexpr int fact_tmp = FactorialTMP<5>::value;

// constexpr 方式：更简洁
constexpr int factorialConstexpr(int n) {
    int result = 1;
    for (int i = 2; i <= n; ++i) {
        result *= i;
    }
    return result;
}

constexpr int fact_ce = factorialConstexpr(5);

// 对比
// | 特性 | TMP | constexpr |
// |------|-----|-----------|
// | 语法 | 复杂 | 普通 C++ |
// | 调试 | 困难 | 容易 |
// | 编译时间 | 长 | 短 |
// | 表达能力 | 强 | 逐渐增强 |
// | 可读性 | 差 | 好 |
```

### 5.2 何时使用模板元编程

```cpp
// 1. 类型操作（constexpr 无法处理）
template<typename T>
struct RemovePointer {
    using type = T;
};

template<typename T>
struct RemovePointer<T*> {
    using type = T;
};

// 2. 编译期多态
template<typename T>
void process(const T& value) {
    if constexpr (std::is_integral_v<T>) {
        processInt(value);
    } else {
        processOther(value);
    }
}

// 3. 复杂的类型特征
template<typename T>
struct is_container {
    static constexpr bool value = requires(T t) {
        t.begin();
        t.end();
    };
};
```

---

## 6. 编译期容器操作（C++20）

### 6.1 constexpr 容器

```cpp
// C++20 起，更多容器操作支持 constexpr
#include <array>
#include <vector>  // C++20 部分支持
#include <string>  // C++20 部分支持

// constexpr 数组操作
constexpr auto processArray() {
    std::array<int, 5> arr = {1, 2, 3, 4, 5};
    
    // 编译期排序
    for (size_t i = 0; i < arr.size(); ++i) {
        for (size_t j = i + 1; j < arr.size(); ++j) {
            if (arr[i] > arr[j]) {
                int temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
        }
    }
    
    return arr;
}

constexpr auto sorted = processArray();
```

### 6.2 constexpr 算法

```cpp
#include <algorithm>
#include <array>

// C++20 标准算法支持 constexpr
constexpr auto findValue() {
    std::array<int, 5> arr = {3, 1, 4, 1, 5};
    
    // constexpr std::find
    auto it = std::find(arr.begin(), arr.end(), 4);
    
    // constexpr std::sort
    std::sort(arr.begin(), arr.end());
    
    return arr;
}

constexpr auto result = findValue();
```

---

## 7. 面试要点

### 7.1 高频面试题

#### Q1: constexpr 和 const 的区别？

**答案**：
- **const**：只读，可以是编译期或运行期常量
- **constexpr**：必须是编译期可计算的常量/函数
- constexpr 变量隐含 const

```cpp
const int c1 = 10;           // 编译期常量
const int c2 = getValue();   // 运行期常量
constexpr int ce = 10;       // 必须是编译期常量
// constexpr int bad = getValue();  // 错误
```

#### Q2: if constexpr 和 SFINAE 的区别？

**答案**：
- **SFINAE**：通过模板替换失败实现分支，语法复杂
- **if constexpr**：编译期 if 语句，失败的分支不编译
- **优势**：if constexpr 更易读、调试更方便

```cpp
// SFINAE
template<typename T>
std::enable_if_t<std::is_integral_v<T>> f(T);

// if constexpr
template<typename T>
void f(T) {
    if constexpr (std::is_integral_v<T>) {
        // ...
    }
}
```

#### Q3: constexpr 函数的编译期和运行期调用区别？

**答案**：
- 如果所有参数是编译期常量，则在编译期计算
- 如果有运行期参数，则在运行期计算
- C++20 `is_constant_evaluated()` 可以检测当前是否在编译期求值

```cpp
constexpr int compute(int n) {
    if (std::is_constant_evaluated()) {
        // 编译期路径
    } else {
        // 运行期路径
    }
    return n;
}

constexpr int a = compute(5);  // 编译期
int x = 5;
int b = compute(x);  // 运行期
```

#### Q4: C++11/14/17/20 中 constexpr 的限制变化？

**答案**：
- **C++11**：只能有一条 return 语句，不能声明变量
- **C++14**：允许多条语句、局部变量、循环
- **C++17**：允许 if/switch、非 const 成员函数
- **C++20**：允许虚函数、try-catch、new/delete、动态内存分配

#### Q5: 编译期 vs 运行期的边界是什么？

**答案**：
- **编译期**：模板实例化、constexpr 计算、类型推导
- **运行期**：I/O 操作、动态内存分配（C++20 前）、虚函数调用（C++20 前）
- **边界**：`constexpr` 标记决定代码是否可以在编译期执行

---

## 8. 最佳实践

### 8.1 constexpr 使用规范

```cpp
// 1. 尽可能使用 constexpr
constexpr int maxSize = 100;  // 编译期常量

// 2. 函数标记 constexpr 即使当前只在运行期使用
constexpr int compute(int n) {
    // 将来可能在编译期使用
    return n * n;
}

// 3. 使用 if constexpr 替代 SFINAE
template<typename T>
void process(T value) {
    if constexpr (std::is_integral_v<T>) {
        processInt(value);
    } else {
        processOther(value);
    }
}

// 4. 编译期查找表替代运行期计算
constexpr auto lookupTable = generateTable();
double fastLookup(int index) {
    return lookupTable[index];  // O(1) 运行期
}
```

### 8.2 性能优化

```cpp
// 1. 编译期计算减少运行期开销
constexpr int arraySize = computeSize();  // 编译期计算
std::array<int, arraySize> data;  // 无运行期开销

// 2. 编译期类型选择减少虚函数开销
template<typename T>
void process(T value) {
    if constexpr (std::is_integral_v<T>) {
        // 编译期确定分支，无运行期判断
        processInt(value);
    }
}

// 3. 编译期字符串处理
constexpr uint32_t hash = "hello"_hash;
switch (inputHash) {
    case "start"_hash: break;  // 编译期计算哈希
}
```

---

## 9. 常见陷阱

### 9.1 编译期与运行期混淆

```cpp
// 陷阱：假设 constexpr 函数总是在编译期执行
constexpr int compute(int n) {
    return n * n;
}

int x = 5;
int result = compute(x);  // 运行期执行！

// 正确做法：使用 constexpr 变量强制编译期计算
constexpr int result2 = compute(5);  // 编译期
```

### 9.2 非字面量类型

```cpp
// 陷阱：尝试在 constexpr 中使用非字面量类型
struct Bad {
    std::string s;  // string 不是字面量类型
};

// constexpr Bad b{"hello"};  // 错误

// 正确做法：使用字面量类型
struct Good {
    const char* s;
    constexpr Good(const char* p) : s(p) {}
};

constexpr Good g{"hello"};  // OK
```

### 9.3 未定义行为

```cpp
// 陷阱：constexpr 中的 UB 是编译错误
constexpr int bad() {
    int* p = nullptr;
    return *p;  // 编译错误：解引用空指针是 UB
}

constexpr int overflow() {
    int x = INT_MAX;
    return x + 1;  // 有符号溢出是 UB，编译错误
}
```

---

## 10. 总结

### 核心要点回顾

1. **constexpr 变量**：必须是编译期可计算的常量
2. **constexpr 函数**：C++11 严格 → C++14 放宽 → C++17 进一步放宽 → C++20 接近完整 C++
3. **if constexpr**：编译期分支，替代复杂的 SFINAE
4. **编译期计算**：查找表生成、类型计算、数组大小确定
5. **与 TMP 的关系**：constexpr 简化大多数编译期计算，TMP 仍用于复杂类型操作

### 演进时间线

```
C++11：constexpr 引入，严格限制
   ↓
C++14：放宽限制，允许局部变量和循环
   ↓
C++17：if constexpr，非 const 成员函数
   ↓
C++20：虚函数、try-catch、new/delete
   ↓
C++23：更多 constexpr 标准库支持
```

constexpr 是现代 C++ 编译期编程的核心，掌握它可以显著提升代码性能和编译期表达能力。

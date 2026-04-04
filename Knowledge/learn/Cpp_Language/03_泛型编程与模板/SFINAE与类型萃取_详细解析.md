# SFINAE与类型萃取详细解析

> **核心结论**：SFINAE（替换失败不是错误）是C++模板元编程的核心机制。C++17的`if constexpr`和C++20的Concepts正在逐步替代复杂的SFINAE技巧，但理解SFINAE仍是掌握现代C++模板编程的基础。

---

## 1. Why — 为什么需要SFINAE

**结论先行**：SFINAE让我们能够在编译期根据类型特征选择不同的代码路径，实现"编译期多态"。

### 1.1 编译期类型选择的必要性

```cpp
// 问题：如何为不同类型选择不同实现？
// 方案1：运行时if（有开销，且可能编译失败）
template<typename T>
void process(T val) {
    if (std::is_pointer<T>::value) {
        // 对指针和非指针都编译！
        // *val;  // 非指针类型编译错误！
    }
}

// 方案2：SFINAE（编译期选择，零开销）
template<typename T>
std::enable_if_t<std::is_pointer_v<T>> process(T val) {
    // 只有T是指针时才参与重载解析
    std::cout << *val << std::endl;
}

template<typename T>
std::enable_if_t<!std::is_pointer_v<T>> process(T val) {
    // 只有T不是指针时才参与重载解析
    std::cout << val << std::endl;
}
```

### 1.2 SFINAE的应用场景

| 场景 | 说明 | 示例 |
|-----|------|------|
| **函数重载选择** | 根据类型特征选择重载 | 指针/非指针处理 |
| **类型约束** | 限制模板参数类型 | 只接受整数类型 |
| **特征检测** | 检测类型是否有某成员 | 是否有`begin()` |
| **条件模板** | 条件启用模板特化 | 迭代器类型特化 |

---

## 2. What — SFINAE核心概念

### 2.1 SFINAE基本原理

```cpp
// C++11/14/17/20/23 通用
#include <iostream>
#include <type_traits>

// SFINAE：Substitution Failure Is Not An Error
// 替换失败不是错误，只是从重载集中移除该候选

// 通用版本
template<typename T>
void foo(T val) {
    std::cout << "通用版本: " << val << std::endl;
}

// SFINAE版本：只有当T是指针时才有效
template<typename T>
void foo(T* val) {
    std::cout << "指针版本: " << *val << std::endl;
}

int main() {
    int x = 42;
    
    foo(x);    // 调用通用版本（T=int）
    foo(&x);   // 调用指针版本（T=int）
    
    // 当调用foo(42)时：
    // 1. 尝试匹配foo<int>(int*)：替换失败（int不能转换为int*）
    // 2. 但这不是编译错误！只是从重载集移除该候选
    // 3. 匹配通用版本foo<int>(int)
    
    return 0;
}
```

### 2.2 std::enable_if 详解

```cpp
// C++11/14/17/20/23 通用
#include <iostream>
#include <type_traits>

// std::enable_if 基本实现原理
template<bool B, typename T = void>
struct enable_if {};

template<typename T>
struct enable_if<true, T> {
    using type = T;
};

// C++14起有enable_if_t别名
template<bool B, typename T = void>
using enable_if_t = typename enable_if<B, T>::type;

// 使用enable_if控制函数重载

// 版本1：只接受整数类型
template<typename T>
std::enable_if_t<std::is_integral_v<T>, T>  // 返回类型位置
add(T a, T b) {
    std::cout << "整数版本" << std::endl;
    return a + b;
}

// 版本2：只接受浮点类型
template<typename T>
std::enable_if_t<std::is_floating_point_v<T>, T>
add(T a, T b) {
    std::cout << "浮点版本" << std::endl;
    return a + b;
}

// 使用默认模板参数（更常见的写法）
template<typename T, 
         std::enable_if_t<std::is_integral_v<T>, int> = 0>
T multiply(T a, T b) {
    return a * b;
}

template<typename T, 
         std::enable_if_t<std::is_floating_point_v<T>, int> = 0>
T multiply(T a, T b) {
    return a * b;
}

// C++17起可以用constexpr if替代简单场景
template<typename T>
auto add_cpp17(T a, T b) {
    if constexpr (std::is_integral_v<T>) {
        std::cout << "编译期选择：整数" << std::endl;
    } else if constexpr (std::is_floating_point_v<T>) {
        std::cout << "编译期选择：浮点" << std::endl;
    }
    return a + b;
}

int main() {
    std::cout << add(1, 2) << std::endl;           // 整数版本
    std::cout << add(1.5, 2.5) << std::endl;       // 浮点版本
    // add("a", "b");  // 错误：没有匹配的重载
    
    std::cout << multiply(3, 4) << std::endl;      // 整数
    std::cout << multiply(3.0, 4.0) << std::endl;  // 浮点
    
    add_cpp17(1, 2);
    add_cpp17(1.5, 2.5);
    
    return 0;
}
```

### 2.3 type_traits 完整分类

```cpp
// C++11/14/17/20/23 通用
#include <iostream>
#include <type_traits>

// ============== 主类型类别（Primary Type Categories）=============
void test_primary_categories() {
    // 检查具体类型
    static_assert(std::is_void_v<void>);
    static_assert(std::is_null_pointer_v<decltype(nullptr)>);
    static_assert(std::is_integral_v<int>);
    static_assert(std::is_floating_point_v<double>);
    static_assert(std::is_array_v<int[5]>);
    static_assert(std::is_pointer_v<int*>);
    static_assert(std::is_lvalue_reference_v<int&>);
    static_assert(std::is_rvalue_reference_v<int&&>);
    static_assert(std::is_member_object_pointer_v<int Class::*>);
    static_assert(std::is_member_function_pointer_v<int (Class::*)()>);
    static_assert(std::is_enum_v<EnumType>);
    static_assert(std::is_union_v<UnionType>);
    static_assert(std::is_class_v<ClassType>);
    static_assert(std::is_function_v<void()>);
}

// ============== 复合类型类别（Composite Type Categories）=============
void test_composite_categories() {
    static_assert(std::is_reference_v<int&>);        // 左值或右值引用
    static_assert(std::is_arithmetic_v<int>);        // 整数或浮点
    static_assert(std::is_fundamental_v<int>);       // void/null/整数/浮点
    static_assert(std::is_object_v<int>);            // 非void/非引用/非函数
    static_assert(std::is_scalar_v<int>);            // 算术/枚举/指针/成员指针/null
    static_assert(std::is_compound_v<int*>);         // 非基本类型
    static_assert(std::is_member_pointer_v<int Class::*>);
}

// ============== 类型属性（Type Properties）=============
void test_type_properties() {
    // const/volatile属性
    static_assert(std::is_const_v<const int>);
    static_assert(std::is_volatile_v<volatile int>);
    static_assert(std::is_trivial_v<int>);
    static_assert(std::is_trivially_copyable_v<int>);
    static_assert(std::is_standard_layout_v<int>);
    static_assert(std::is_pod_v<int>);  // C++20 deprecated
    static_assert(std::is_empty_v<EmptyClass>);
    static_assert(std::is_polymorphic_v<PolymorphicClass>);
    static_assert(std::is_abstract_v<AbstractClass>);
    static_assert(std::is_final_v<FinalClass>);
    static_assert(std::is_aggregate_v<AggregateClass>);
    static_assert(std::is_signed_v<int>);
    static_assert(std::is_unsigned_v<unsigned int>);
}

// ============== 支持的运算（Supported Operations）=============
struct Constructible {
    Constructible() = default;
    Constructible(const Constructible&) = default;
    Constructible(Constructible&&) = default;
    Constructible& operator=(const Constructible&) = default;
    Constructible& operator=(Constructible&&) = default;
    ~Constructible() = default;
};

void test_supported_operations() {
    static_assert(std::is_constructible_v<Constructible>);
    static_assert(std::is_default_constructible_v<Constructible>);
    static_assert(std::is_copy_constructible_v<Constructible>);
    static_assert(std::is_move_constructible_v<Constructible>);
    static_assert(std::is_assignable_v<Constructible&, const Constructible&>);
    static_assert(std::is_copy_assignable_v<Constructible>);
    static_assert(std::is_move_assignable_v<Constructible>);
    static_assert(std::is_destructible_v<Constructible>);
    static_assert(std::is_trivially_constructible_v<int>);
    static_assert(std::is_trivially_default_constructible_v<int>);
    static_assert(std::is_trivially_copyable_v<int>);
    static_assert(std::is_trivially_copy_constructible_v<int>);
    static_assert(std::is_trivially_move_constructible_v<int>);
    static_assert(std::is_trivially_assignable_v<int&, int>);
    static_assert(std::is_trivially_copy_assignable_v<int>);
    static_assert(std::is_trivially_move_assignable_v<int>);
    static_assert(std::is_trivially_destructible_v<int>);
    static_assert(std::is_nothrow_constructible_v<int>);
    static_assert(std::is_nothrow_default_constructible_v<int>);
    static_assert(std::is_nothrow_copy_constructible_v<int>);
    static_assert(std::is_nothrow_move_constructible_v<int>);
    static_assert(std::is_nothrow_assignable_v<int&, int>);
    static_assert(std::is_nothrow_copy_assignable_v<int>);
    static_assert(std::is_nothrow_move_assignable_v<int>);
    static_assert(std::is_nothrow_destructible_v<int>);
    static_assert(std::has_virtual_destructor_v<PolymorphicClass>);
}

// ============== 类型关系（Type Relationships）=============
class Base {};
class Derived : public Base {};

void test_type_relationships() {
    static_assert(std::is_same_v<int, int>);
    static_assert(std::is_base_of_v<Base, Derived>);
    static_assert(std::is_convertible_v<Derived*, Base*>);
    static_assert(std::is_nothrow_convertible_v<int, double>);  // C++20
}

// ============== 类型修改（Type Modifications）=============
void test_type_modifications() {
    // cv修饰符
    using T1 = std::remove_cv_t<const volatile int>;  // int
    using T2 = std::remove_const_t<const int>;        // int
    using T3 = std::remove_volatile_t<volatile int>;  // int
    using T4 = std::add_cv_t<int>;                    // const volatile int
    using T5 = std::add_const_t<int>;                 // const int
    using T6 = std::add_volatile_t<int>;              // volatile int
    
    // 引用修饰符
    using T7 = std::remove_reference_t<int&>;         // int
    using T8 = std::remove_reference_t<int&&>;        // int
    using T9 = std::add_lvalue_reference_t<int>;      // int&
    using T10 = std::add_rvalue_reference_t<int>;     // int&&
    
    // 指针修饰符
    using T11 = std::remove_pointer_t<int*>;          // int
    using T12 = std::add_pointer_t<int>;              // int*
    
    // 符号修饰符
    using T13 = std::make_signed_t<unsigned int>;     // int
    using T14 = std::make_unsigned_t<int>;            // unsigned int
    
    // 数组修饰符
    using T15 = std::remove_extent_t<int[5]>;         // int
    using T16 = std::remove_all_extents_t<int[5][3]>; // int
}

// ============== 其他类型操作（Miscellaneous Transformations）=============
template<typename... Args>
void test_other_transformations() {
    using T1 = std::aligned_storage_t<64, alignof(double)>;  // 对齐存储
    using T2 = std::aligned_union_t<64, int, double, char>;  // 对齐联合
    using T3 = std::decay_t<int&>;                           // int（去引用、去cv、数组转指针、函数转指针）
    using T4 = std::remove_cvref_t<const int&>;              // C++20，移除cv和引用
    using T5 = std::enable_if_t<true, int>;                  // int
    using T6 = std::conditional_t<true, int, double>;        // int
    using T7 = std::common_type_t<int, short, char>;         // int（公共类型）
    using T8 = std::underlying_type_t<EnumType>;             // 枚举底层类型
    using T9 = std::result_of_t<void(int)>;                  // C++17前，函数结果类型
    using T10 = std::invoke_result_t<void(*)(int), int>;     // C++17起，替代result_of
}

// 辅助类型定义
struct ClassType {};
enum class EnumType { A, B };
union UnionType { int i; float f; };
struct EmptyClass {};
struct PolymorphicClass { virtual ~PolymorphicClass() = default; };
struct AbstractClass { virtual void foo() = 0; };
struct FinalClass final {};
struct AggregateClass { int x; int y; };

int main() {
    std::cout << "type_traits 测试完成" << std::endl;
    return 0;
}
```

### 2.4 自定义 type traits

```cpp
// C++11/14/17/20/23 通用
#include <iostream>
#include <type_traits>

// ============== 自定义 is_same ==============
template<typename T, typename U>
struct is_same : std::false_type {};

template<typename T>
struct is_same<T, T> : std::true_type {};

template<typename T, typename U>
inline constexpr bool is_same_v = is_same<T, U>::value;

// ============== 自定义 is_base_of ==============
template<typename Base, typename Derived>
struct is_base_of_helper {
private:
    static std::true_type test(const Base*);
    static std::false_type test(...);
public:
    using type = decltype(test(static_cast<Derived*>(nullptr)));
};

template<typename Base, typename Derived>
struct is_base_of : is_base_of_helper<Base, Derived>::type {};

// 更完整的实现（考虑cv限定符）
template<typename Base, typename Derived>
struct is_base_of_v2 
    : std::conditional_t<
        std::is_class_v<Base> && std::is_class_v<Derived>,
        is_base_of_helper<std::remove_cv_t<Base>, std::remove_cv_t<Derived>>,
        std::false_type
      >::type {};

// ============== 自定义 is_void ==============
template<typename T>
struct is_void : std::false_type {};

template<>
struct is_void<void> : std::true_type {};

template<>
struct is_void<const void> : std::true_type {};

template<>
struct is_void<volatile void> : std::true_type {};

template<>
struct is_void<const volatile void> : std::true_type {};

// ============== 自定义 is_pointer ==============
template<typename T>
struct is_pointer : std::false_type {};

template<typename T>
struct is_pointer<T*> : std::true_type {};

template<typename T>
struct is_pointer<T* const> : std::true_type {};

template<typename T>
struct is_pointer<T* volatile> : std::true_type {};

template<typename T>
struct is_pointer<T* const volatile> : std::true_type {};

// ============== 自定义 remove_reference ==============
template<typename T>
struct remove_reference { using type = T; };

template<typename T>
struct remove_reference<T&> { using type = T; };

template<typename T>
struct remove_reference<T&&> { using type = T; };

template<typename T>
using remove_reference_t = typename remove_reference<T>::type;

// ============== 自定义 add_lvalue_reference ==============
template<typename T>
struct add_lvalue_reference { using type = T&; };

template<>
struct add_lvalue_reference<void> { using type = void; };

template<>
struct add_lvalue_reference<const void> { using type = const void; };

template<>
struct add_lvalue_reference<volatile void> { using type = volatile void; };

template<>
struct add_lvalue_reference<const volatile void> { using type = const volatile void; };

// ============== 测试 ==============
class Base {};
class Derived : public Base {};
class Unrelated {};

int main() {
    // 测试 is_same
    static_assert(is_same_v<int, int>);
    static_assert(!is_same_v<int, double>);
    
    // 测试 is_base_of
    static_assert(is_base_of<Base, Derived>::value);
    static_assert(!is_base_of<Derived, Base>::value);
    static_assert(!is_base_of<Base, Unrelated>::value);
    static_assert(is_base_of<Base, Base>::value);  // 类是自身的基类
    
    // 测试 is_void
    static_assert(is_void<void>::value);
    static_assert(is_void<const void>::value);
    static_assert(!is_void<int>::value);
    
    // 测试 is_pointer
    static_assert(is_pointer<int*>::value);
    static_assert(is_pointer<int* const>::value);
    static_assert(!is_pointer<int>::value);
    static_assert(!is_pointer<int&>::value);
    
    // 测试 remove_reference
    static_assert(is_same_v<remove_reference_t<int>, int>);
    static_assert(is_same_v<remove_reference_t<int&>, int>);
    static_assert(is_same_v<remove_reference_t<int&&>, int>);
    
    std::cout << "所有自定义type_traits测试通过！" << std::endl;
    
    return 0;
}
```

### 2.5 void_t 技巧

```cpp
// C++11/14/17/20/23 通用
#include <iostream>
#include <type_traits>
#include <vector>
#include <list>

// ============== void_t 定义 ==============
// C++17起在std中提供，C++11/14需要自定义
template<typename... Ts>
struct make_void { using type = void; };

template<typename... Ts>
using void_t = typename make_void<Ts...>::type;

// C++17可以直接用 std::void_t

// ============== 检测成员类型是否存在 ==============
template<typename, typename = void_t<>>
struct has_value_type : std::false_type {};

template<typename T>
struct has_value_type<T, void_t<typename T::value_type>> : std::true_type {};

template<typename T>
inline constexpr bool has_value_type_v = has_value_type<T>::value;

// ============== 检测成员函数是否存在 ==============
template<typename, typename = void_t<>>
struct has_begin : std::false_type {};

template<typename T>
struct has_begin<T, void_t<decltype(std::declval<T>().begin())>> : std::true_type {};

// ============== 检测成员变量是否存在 ==============
template<typename, typename = void_t<>>
struct has_size_member : std::false_type {};

template<typename T>
struct has_size_member<T, void_t<decltype(std::declval<T>().size)>> : std::true_type {};

// ============== 检测类型是否可以默认构造 ==============
template<typename, typename = void_t<>>
struct is_default_constructible_v2 : std::false_type {};

template<typename T>
struct is_default_constructible_v2<T, void_t<decltype(T())>> : std::true_type {};

// ============== 更通用的检测宏（C++11） ==============
#define DEFINE_HAS_MEMBER(member_name)                              \
    template<typename, typename = void>                             \
    struct has_##member_name : std::false_type {};                  \
                                                                    \
    template<typename T>                                            \
    struct has_##member_name<T, void_t<decltype(std::declval<T>().member_name)>> : std::true_type {};

DEFINE_HAS_MEMBER(foo)
DEFINE_HAS_MEMBER(bar)
DEFINE_HAS_MEMBER(push_back)

// ============== 应用：根据类型特征选择算法 ==============
// 检测是否有随机访问迭代器
template<typename T, typename = void_t<>>
struct has_random_access_iterator : std::false_type {};

template<typename T>
struct has_random_access_iterator<T, 
    void_t<typename T::iterator_category,
           std::enable_if_t<std::is_same_v<typename T::iterator_category, 
                                           std::random_access_iterator_tag>>>
> : std::true_type {};

// 简化的距离计算
template<typename Container>
std::enable_if_t<has_random_access_iterator<Container>::value, size_t>
fast_distance(const Container& c) {
    std::cout << "使用O(1)距离计算" << std::endl;
    return c.end() - c.begin();
}

template<typename Container>
std::enable_if_t<!has_random_access_iterator<Container>::value, size_t>
fast_distance(const Container& c) {
    std::cout << "使用O(n)距离计算" << std::endl;
    return std::distance(c.begin(), c.end());
}

// ============== 测试 ==============
struct WithFoo { void foo() {} };
struct WithBar { int bar; };
struct Empty {};

int main() {
    // 测试成员类型检测
    static_assert(has_value_type_v<std::vector<int>>);
    static_assert(!has_value_type_v<int>);
    
    // 测试成员函数检测
    static_assert(has_begin<std::vector<int>>::value);
    static_assert(!has_begin<int>::value);
    
    // 测试宏定义的检测
    static_assert(has_foo<WithFoo>::value);
    static_assert(!has_foo<WithBar>::value);
    static_assert(has_bar<WithBar>::value);
    static_assert(has_push_back<std::vector<int>>::value);
    static_assert(!has_push_back<std::list<int>>::value);  // list有push_back，但检测方式不同
    
    // 测试算法选择
    std::vector<int> vec{1, 2, 3, 4, 5};
    std::list<int> lst{1, 2, 3, 4, 5};
    
    std::cout << "vector: ";
    fast_distance(vec);
    
    std::cout << "list: ";
    fast_distance(lst);
    
    return 0;
}
```

### 2.6 Detection Idiom（C++17）

```cpp
// C++17 完整示例
#include <iostream>
#include <type_traits>
#include <utility>

// ============== 标准 detection idiom（C++17）=============
template<typename Default, typename AlwaysVoid, 
         template<typename...> class Op, typename... Args>
struct detector {
    using value_t = std::false_type;
    using type = Default;
};

template<typename Default, template<typename...> class Op, typename... Args>
struct detector<Default, std::void_t<Op<Args...>>, Op, Args...> {
    using value_t = std::true_type;
    using type = Op<Args...>;
};

// 别名模板
struct nonesuch {
    nonesuch() = delete;
    ~nonesuch() = delete;
    nonesuch(nonesuch const&) = delete;
    void operator=(nonesuch const&) = delete;
};

template<template<typename...> class Op, typename... Args>
using is_detected = typename detector<nonesuch, void, Op, Args...>::value_t;

template<template<typename...> class Op, typename... Args>
using detected_t = typename detector<nonesuch, void, Op, Args...>::type;

template<typename Default, template<typename...> class Op, typename... Args>
using detected_or = detector<Default, void, Op, Args...>;

template<typename Default, template<typename...> class Op, typename... Args>
using detected_or_t = typename detected_or<Default, Op, Args...>::type;

// ============== 使用 detection idiom ==============

// 检测是否有value_type
template<typename T>
using value_type_t = typename T::value_type;

template<typename T>
using has_value_type = is_detected<value_type_t, T>;

// 检测是否有size()成员函数
template<typename T>
using size_member_t = decltype(std::declval<T>().size());

template<typename T>
using has_size_member = is_detected<size_member_t, T>;

// 检测是否有嵌套类型iterator
template<typename T>
using iterator_t = typename T::iterator;

template<typename T>
using has_iterator = is_detected<iterator_t, T>;

// 检测是否可以调用
template<typename T>
using call_operator_t = decltype(&T::operator());

template<typename T>
using has_call_operator = is_detected<call_operator_t, T>;

// ============== 检测表达式是否合法 ==============
template<typename T, typename U>
using equality_comparable_t = decltype(std::declval<T>() == std::declval<U>());

template<typename T, typename U = T>
using is_equality_comparable = is_detected<equality_comparable_t, T, U>;

template<typename T, typename U>
using less_than_comparable_t = decltype(std::declval<T>() < std::declval<U>());

template<typename T, typename U = T>
using is_less_than_comparable = is_detected<less_than_comparable_t, T, U>;

// ============== 应用：通用打印函数 ==============
// 检测是否有ostream的operator<<
template<typename T>
using ostream_insertable_t = decltype(std::declval<std::ostream&>() << std::declval<T>());

template<typename T>
using is_ostream_insertable = is_detected<ostream_insertable_t, T>;

// 为可插入ostream的类型提供打印
template<typename T>
std::enable_if_t<is_ostream_insertable<T>::value>
print(const T& val) {
    std::cout << val << std::endl;
}

// 为容器类型提供打印
template<typename T>
std::enable_if_t<!is_ostream_insertable<T>::value && has_iterator<T>::value>
print(const T& container) {
    std::cout << "[";
    bool first = true;
    for (const auto& elem : container) {
        if (!first) std::cout << ", ";
        first = false;
        print(elem);  // 递归打印
    }
    std::cout << "]" << std::endl;
}

// ============== 测试 ==============
struct HasValueType {
    using value_type = int;
};

struct NoValueType {};

struct Callable {
    void operator()() {}
};

struct NotCallable {};

struct Comparable {
    bool operator==(const Comparable&) const { return true; }
    bool operator<(const Comparable&) const { return true; }
};

int main() {
    // 测试 value_type 检测
    std::cout << "has_value_type<HasValueType>: " 
              << has_value_type<HasValueType>::value << std::endl;
    std::cout << "has_value_type<NoValueType>: " 
              << has_value_type<NoValueType>::value << std::endl;
    
    // 测试 callable 检测
    std::cout << "has_call_operator<Callable>: " 
              << has_call_operator<Callable>::value << std::endl;
    std::cout << "has_call_operator<NotCallable>: " 
              << has_call_operator<NotCallable>::value << std::endl;
    
    // 测试比较操作符检测
    std::cout << "is_equality_comparable<Comparable>: " 
              << is_equality_comparable<Comparable>::value << std::endl;
    std::cout << "is_equality_comparable<int>: " 
              << is_equality_comparable<int>::value << std::endl;
    
    // 测试打印
    print(42);
    print("Hello");
    print(std::vector<int>{1, 2, 3});
    
    return 0;
}
```

### 2.7 std::is_invocable 家族

```cpp
// C++17 完整示例
#include <iostream>
#include <type_traits>
#include <functional>

// ============== std::is_invocable ==============
// 检查类型是否可以用给定参数调用

void free_function(int, double) {}

struct Functor {
    void operator()(int) {}
    int operator()(int, int) { return 0; }
};

struct MemberFunc {
    void member(int) {}
    int data = 42;
};

int main() {
    // 检查自由函数
    static_assert(std::is_invocable_v<decltype(free_function), int, double>);
    static_assert(!std::is_invocable_v<decltype(free_function), int>);  // 参数不够
    
    // 检查lambda
    auto lambda = [](int x, double y) { return x + y; };
    static_assert(std::is_invocable_v<decltype(lambda), int, double>);
    static_assert(std::is_invocable_r_v<double, decltype(lambda), int, double>);
    
    // 检查函数对象
    static_assert(std::is_invocable_v<Functor, int>);
    static_assert(std::is_invocable_v<Functor, int, int>);
    
    // 检查成员函数（需要对象指针或引用）
    static_assert(std::is_invocable_v<void(MemberFunc::*)(int), MemberFunc*, int>);
    static_assert(std::is_invocable_v<void(MemberFunc::*)(int), MemberFunc&, int>);
    
    // 检查成员数据
    static_assert(std::is_invocable_v<int MemberFunc::*, MemberFunc*>);
    static_assert(std::is_invocable_v<int MemberFunc::*, MemberFunc&>);
    
    // 检查返回类型
    static_assert(std::is_invocable_r_v<void, decltype(free_function), int, double>);
    static_assert(std::is_invocable_r_v<int, Functor, int, int>);
    
    // 检查是否nothrow
    auto noexcept_lambda = [](int x) noexcept { return x * 2; };
    static_assert(std::is_nothrow_invocable_v<decltype(noexcept_lambda), int>);
    
    // std::invoke_result 替代 result_of (C++17)
    static_assert(std::is_same_v<
        std::invoke_result_t<decltype(lambda), int, double>,
        double
    >);
    
    static_assert(std::is_same_v<
        std::invoke_result_t<Functor, int, int>,
        int
    >);
    
    std::cout << "所有is_invocable测试通过！" << std::endl;
    
    return 0;
}
```

### 2.8 C++17 std::conjunction/disjunction/negation

```cpp
// C++17 完整示例
#include <iostream>
#include <type_traits>

// ============== std::conjunction（逻辑与）=============
// 所有类型都为true时才为true，短路求值

template<typename... Ts>
struct all_integral : std::conjunction<std::is_integral<Ts>...> {};

template<typename... Ts>
inline constexpr bool all_integral_v = all_integral<Ts...>::value;

// ============== std::disjunction（逻辑或）=============
// 任一类型为true时就为true，短路求值

template<typename... Ts>
struct any_pointer : std::disjunction<std::is_pointer<Ts>...> {};

template<typename... Ts>
inline constexpr bool any_pointer_v = any_pointer<Ts...>::value;

// ============== std::negation（逻辑非）=============
template<typename T>
struct is_not_void : std::negation<std::is_void<T>> {};

// ============== 应用：复杂类型约束 ==============

// 约束：所有参数都是算术类型
template<typename... Args,
         std::enable_if_t<std::conjunction_v<std::is_arithmetic<Args>...>, int> = 0>
auto sum(Args... args) {
    return (args + ...);  // 折叠表达式
}

// 约束：至少有一个参数是指针
template<typename... Args,
         std::enable_if_t<std::disjunction_v<std::is_pointer<Args>...>, int> = 0>
void process_pointers(Args... args) {
    std::cout << "处理包含指针的参数包" << std::endl;
}

// 约束：类型不是void
template<typename T,
         std::enable_if_t<std::negation_v<std::is_void<T>>, int> = 0>
T create() {
    return T{};
}

// ============== 自定义组合traits ==============

// 检查是否是整数或枚举
template<typename T>
struct is_integral_or_enum 
    : std::disjunction<std::is_integral<T>, std::is_enum<T>> {};

// 检查是否是类且不是联合体
template<typename T>
struct is_class_not_union
    : std::conjunction<std::is_class<T>, std::negation<std::is_union<T>>> {};

// 检查是否不是指针、引用或数组
template<typename T>
struct is_scalar_like
    : std::negation<std::disjunction<
        std::is_pointer<T>,
        std::is_reference<T>,
        std::is_array<T>
      >> {};

// ============== 测试 ==============
int main() {
    // 测试 conjunction
    static_assert(all_integral_v<int, short, char>);
    static_assert(!all_integral_v<int, double>);
    
    // 测试 disjunction
    static_assert(any_pointer_v<int*, double>);
    static_assert(any_pointer_v<int, double*>);
    static_assert(!any_pointer_v<int, double>);
    
    // 测试 negation
    static_assert(is_not_void<int>::value);
    static_assert(!is_not_void<void>::value);
    
    // 测试组合traits
    static_assert(is_integral_or_enum<int>::value);
    static_assert(is_integral_or_enum<enum class E { A }>::value);
    static_assert(!is_integral_or_enum<double>::value);
    
    // 测试约束函数
    std::cout << "sum(1, 2, 3, 4) = " << sum(1, 2, 3, 4) << std::endl;
    std::cout << "sum(1.5, 2.5) = " << sum(1.5, 2.5) << std::endl;
    // sum("a", "b");  // 编译错误：不是算术类型
    
    int x = 42;
    process_pointers(&x);  // OK
    process_pointers(1, &x);  // OK
    // process_pointers(1, 2);  // 编译错误：没有指针
    
    auto val = create<int>();
    std::cout << "create<int>() = " << val << std::endl;
    // create<void>();  // 编译错误
    
    return 0;
}
```

### 2.9 SFINAE vs if constexpr

```cpp
// C++17 完整示例
#include <iostream>
#include <type_traits>
#include <vector>
#include <string>

// ============== 方案1：SFINAE（C++11/14风格）=============

// 优点：可以控制重载解析
// 缺点：语法复杂，错误信息难读

template<typename T>
std::enable_if_t<std::is_integral_v<T>, T>
add_sfinae(T a, T b) {
    std::cout << "SFINAE整数版本" << std::endl;
    return a + b;
}

template<typename T>
std::enable_if_t<std::is_floating_point_v<T>, T>
add_sfinae(T a, T b) {
    std::cout << "SFINAE浮点版本" << std::endl;
    return a + b;
}

// ============== 方案2：if constexpr（C++17风格）=============

// 优点：语法简洁，错误信息清晰
// 缺点：所有分支都必须是合法代码（只是不实例化）

template<typename T>
T add_constexpr(T a, T b) {
    if constexpr (std::is_integral_v<T>) {
        std::cout << "constexpr整数版本" << std::endl;
        return a + b;
    } else if constexpr (std::is_floating_point_v<T>) {
        std::cout << "constexpr浮点版本" << std::endl;
        return a + b;
    } else {
        // 这个分支在T不是算术类型时也会被编译
        // 所以必须保证代码合法
        static_assert(std::is_arithmetic_v<T>, "T必须是算术类型");
        return a;  // 永远不会执行，但必须存在
    }
}

// ============== 关键区别示例 ==============

// SFINAE可以排除函数参与重载解析
template<typename T>
std::enable_if_t<std::is_pointer_v<T>>
process_sfinae(T ptr) {
    std::cout << "处理指针: " << *ptr << std::endl;
}

// 非指针版本
template<typename T>
std::enable_if_t<!std::is_pointer_v<T>>
process_sfinae(T val) {
    std::cout << "处理值: " << val << std::endl;
}

// if constexpr无法排除函数参与重载解析
// 以下代码会导致编译错误！
template<typename T>
void process_constexpr_bad(T val) {
    if constexpr (std::is_pointer_v<T>) {
        std::cout << "处理指针: " << *val << std::endl;  // 非指针类型编译错误！
    } else {
        std::cout << "处理值: " << val << std::endl;     // 指针类型编译错误！
    }
}

// 修正：使用通用代码
template<typename T>
void process_constexpr_good(T val) {
    if constexpr (std::is_pointer_v<T>) {
        std::cout << "处理指针: " << *val << std::endl;
    } else {
        std::cout << "处理值: " << val << std::endl;
    }
}

// ============== 选择建议 ==============

// 需要重载解析时：用SFINAE
template<typename Container>
std::enable_if_t<std::is_same_v<typename Container::iterator_category, 
                                std::random_access_iterator_tag>,
                 typename Container::value_type&>
get_element(Container& c, size_t index) {
    return c[index];  // O(1)
}

template<typename Container>
std::enable_if_t<!std::is_same_v<typename Container::iterator_category,
                                 std::random_access_iterator_tag>,
                 typename Container::value_type&>
get_element(Container& c, size_t index) {
    auto it = c.begin();
    std::advance(it, index);
    return *it;  // O(n)
}

// 不需要重载解析时：用if constexpr
template<typename T>
auto serialize(const T& val) {
    if constexpr (std::is_arithmetic_v<T>) {
        return std::to_string(val);
    } else if constexpr (std::is_same_v<T, std::string>) {
        return val;
    } else {
        return std::string("unknown");
    }
}

// ============== 测试 ==============
int main() {
    // SFINAE
    std::cout << add_sfinae(1, 2) << std::endl;
    std::cout << add_sfinae(1.5, 2.5) << std::endl;
    
    // if constexpr
    std::cout << add_constexpr(1, 2) << std::endl;
    std::cout << add_constexpr(1.5, 2.5) << std::endl;
    
    // 重载解析
    int x = 42;
    process_sfinae(x);
    process_sfinae(&x);
    
    // if constexpr通用版本
    process_constexpr_good(x);
    process_constexpr_good(&x);
    
    // 序列化
    std::cout << serialize(42) << std::endl;
    std::cout << serialize(std::string("hello")) << std::endl;
    std::cout << serialize(std::vector<int>{}) << std::endl;
    
    return 0;
}
```

---

## 3. How — 实战代码示例

### 3.1 完整示例：类型安全的通用序列化器

```cpp
// C++17 完整示例
#include <iostream>
#include <string>
#include <sstream>
#include <type_traits>
#include <vector>
#include <map>
#include <utility>

// ============== 类型特征检测 ==============

// 检测是否有to_string成员
template<typename T>
using has_to_string_t = decltype(std::declval<T>().to_string());

template<typename T>
inline constexpr bool has_to_string_v = std::is_detected_v<has_to_string_t, T>;

// 检测是否是容器（有begin/end）
template<typename T>
using has_begin_end_t = std::void_t<
    decltype(std::begin(std::declval<T>())),
    decltype(std::end(std::declval<T>()))
>;

template<typename T>
inline constexpr bool is_container_v = std::is_detected_v<has_begin_end_t, T>;

// 检测是否是pair
template<typename T>
struct is_pair : std::false_type {};

template<typename T, typename U>
struct is_pair<std::pair<T, U>> : std::true_type {};

template<typename T>
inline constexpr bool is_pair_v = is_pair<T>::value;

// 检测是否是map
template<typename T>
struct is_map : std::false_type {};

template<typename K, typename V, typename... Args>
struct is_map<std::map<K, V, Args...>> : std::true_type {};

template<typename T>
inline constexpr bool is_map_v = is_map<T>::value;

// ============== 序列化实现 ==============

class Serializer {
public:
    // 算术类型
    template<typename T>
    static std::enable_if_t<std::is_arithmetic_v<T>, std::string>
    serialize(const T& val) {
        if constexpr (std::is_same_v<T, bool>) {
            return val ? "true" : "false";
        } else if constexpr (std::is_same_v<T, char>) {
            return std::string("'") + val + "'";
        } else {
            return std::to_string(val);
        }
    }
    
    // 字符串类型
    static std::string serialize(const std::string& val) {
        return "\"" + val + "\"";
    }
    
    static std::string serialize(const char* val) {
        return std::string("\"") + val + "\"";
    }
    
    // 有to_string方法的类型
    template<typename T>
    static std::enable_if_t<has_to_string_v<T> && !std::is_arithmetic_v<T>, std::string>
    serialize(const T& val) {
        return val.to_string();
    }
    
    // pair类型
    template<typename T>
    static std::enable_if_t<is_pair_v<T>, std::string>
    serialize(const T& val) {
        return "[" + serialize(val.first) + ", " + serialize(val.second) + "]";
    }
    
    // map类型
    template<typename T>
    static std::enable_if_t<is_map_v<T>, std::string>
    serialize(const T& val) {
        std::ostringstream oss;
        oss << "{";
        bool first = true;
        for (const auto& [k, v] : val) {
            if (!first) oss << ", ";
            first = false;
            oss << serialize(k) << ": " << serialize(v);
        }
        oss << "}";
        return oss.str();
    }
    
    // 其他容器类型
    template<typename T>
    static std::enable_if_t<is_container_v<T> && !is_map_v<T> && !std::is_same_v<T, std::string>, std::string>
    serialize(const T& val) {
        std::ostringstream oss;
        oss << "[";
        bool first = true;
        for (const auto& elem : val) {
            if (!first) oss << ", ";
            first = false;
            oss << serialize(elem);
        }
        oss << "]";
        return oss.str();
    }
};

// ============== 测试类型 ==============
struct Point {
    int x, y;
    std::string to_string() const {
        return "Point(" + std::to_string(x) + ", " + std::to_string(y) + ")";
    }
};

// ============== 测试 ==============
int main() {
    // 算术类型
    std::cout << Serializer::serialize(42) << std::endl;
    std::cout << Serializer::serialize(3.14) << std::endl;
    std::cout << Serializer::serialize(true) << std::endl;
    std::cout << Serializer::serialize('A') << std::endl;
    
    // 字符串
    std::cout << Serializer::serialize(std::string("hello")) << std::endl;
    std::cout << Serializer::serialize("world") << std::endl;
    
    // 自定义类型
    Point p{10, 20};
    std::cout << Serializer::serialize(p) << std::endl;
    
    // 容器
    std::vector<int> vec{1, 2, 3};
    std::cout << Serializer::serialize(vec) << std::endl;
    
    // pair
    std::pair<int, std::string> pr{1, "one"};
    std::cout << Serializer::serialize(pr) << std::endl;
    
    // map
    std::map<int, std::string> mp{{1, "one"}, {2, "two"}};
    std::cout << Serializer::serialize(mp) << std::endl;
    
    // 嵌套容器
    std::vector<std::vector<int>> nested{{1, 2}, {3, 4}};
    std::cout << Serializer::serialize(nested) << std::endl;
    
    return 0;
}
```

---

## 4. 面试要点

### 4.1 高频面试题

#### Q1: 手写实现 is_same 和 is_base_of

**标准答案**：

```cpp
// is_same：利用特化
template<typename T, typename U>
struct is_same : std::false_type {};

template<typename T>
struct is_same<T, T> : std::true_type {};

// is_base_of：利用SFINAE和指针转换
template<typename Base, typename Derived>
struct is_base_of {
private:
    static std::true_type test(const Base*);
    static std::false_type test(...);
public:
    static constexpr bool value = decltype(test(static_cast<Derived*>(nullptr)))::value;
};
```

#### Q2: SFINAE 和 if constexpr 如何选择？

**标准答案**：

| 场景 | 推荐方案 | 原因 |
|-----|---------|------|
| 需要重载解析 | SFINAE | 可以排除函数参与重载 |
| 简单条件分支 | if constexpr | 语法简洁，错误信息清晰 |
| 复杂类型约束 | SFINAE + Concepts | 精确控制重载集 |
| 编译期计算 | if constexpr | 代码可读性更好 |

**关键区别**：`if constexpr`的所有分支都必须是合法代码，只是不实例化；SFINAE可以完全排除不匹配的函数。

#### Q3: 什么是 Detection Idiom？如何实现？

**标准答案**：

```cpp
// Detection Idiom 用于检测某个表达式是否合法

template<typename Default, typename Void, 
         template<typename...> class Op, typename... Args>
struct detector {
    using value_t = std::false_type;
    using type = Default;
};

template<typename Default, template<typename...> class Op, typename... Args>
struct detector<Default, std::void_t<Op<Args...>>, Op, Args...> {
    using value_t = std::true_type;
    using type = Op<Args...>;
};

// 使用：检测是否有foo成员
template<typename T>
using foo_t = decltype(std::declval<T>().foo());

template<typename T>
using has_foo = detector<void, void, foo_t, T>;
```

#### Q4: 如何用SFINAE实现函数重载选择？

**标准答案**：

```cpp
// 方案1：返回类型位置
template<typename T>
std::enable_if_t<std::is_integral_v<T>> process(T val);

// 方案2：默认模板参数（推荐）
template<typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
void process(T val);

// 方案3：参数类型位置（不常用）
template<typename T>
void process(T val, std::enable_if_t<std::is_integral_v<T>, int> = 0);
```

#### Q5: void_t 技巧的原理是什么？

**标准答案**：

```cpp
// void_t 将任意类型列表转换为void
template<typename... Ts>
using void_t = void;

// 原理：利用SFINAE
// 当Op<Args...>不合法时，偏特化版本匹配失败
// 回退到通用版本（返回false_type）

template<typename, typename = void>
struct has_type : std::false_type {};

template<typename T>
struct has_type<T, void_t<typename T::type>> : std::true_type {};
```

---

## 5. 最佳实践

### 5.1 SFINAE使用建议

```cpp
// 1. C++17起优先使用if constexpr（如果不需要重载解析）
template<typename T>
auto process(T val) {
    if constexpr (std::is_pointer_v<T>) {
        return *val;
    } else {
        return val;
    }
}

// 2. 需要重载解析时用enable_if
template<typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
void handle(T val) { /* 整数处理 */ }

template<typename T, std::enable_if_t<std::is_floating_point_v<T>, int> = 0>
void handle(T val) { /* 浮点处理 */ }

// 3. C++20起使用Concepts（最推荐）
template<typename T>
concept Integral = std::is_integral_v<T>;

template<Integral T>
void modern_handle(T val) { }

// 4. 复杂约束用requires子句
template<typename T>
    requires std::is_integral_v<T> && (sizeof(T) >= 4)
void constrained_handle(T val) { }
```

### 5.2 type_traits使用建议

```cpp
// 1. 使用C++17的_v变量模板
static_assert(std::is_integral_v<int>);      // C++17
static_assert(std::is_integral<int>::value); // C++11/14

// 2. 使用C++14的_t类型别名
using T1 = std::remove_reference_t<int&>;       // C++14
using T2 = typename std::remove_reference<int&>::type; // C++11

// 3. 组合使用traits
template<typename T>
using decayed = std::remove_cv_t<std::remove_reference_t<T>>;

// 4. 自定义traits继承标准traits
template<typename T>
struct is_smart_pointer 
    : std::disjunction<
        std::is_same<T, std::shared_ptr<typename T::element_type>>,
        std::is_same<T, std::unique_ptr<typename T::element_type>>
      > {};
```

---

## 6. 常见陷阱与UB

### 6.1 SFINAE陷阱

```cpp
// 陷阱1：硬错误 vs 软错误
template<typename T>
struct AlwaysFails {
    using type = typename T::does_not_exist;  // 硬错误！
};

template<typename T, typename = void>
struct SafeCheck : std::false_type {};

template<typename T>
struct SafeCheck<T, std::void_t<typename T::does_not_exist>> 
    : std::true_type {};  // 如果T::does_not_exist不存在，只是SFINAE失败

// 陷阱2：decltype中的副作用
template<typename T>
auto bad_func(T val) -> std::enable_if_t<(++global_var, true)>;  // UB！

// 陷阱3：不完全类型的检测
struct Incomplete;
static_assert(!std::is_constructible_v<Incomplete>);  // 可能UB！
```

### 6.2 type_traits陷阱

```cpp
// 陷阱1：引用类型的cv限定符
static_assert(!std::is_const_v<int&>);  // int&不是const！
static_assert(std::is_const_v<const int&>);  // 引用指向const int

// 陷阱2：数组类型的decay
static_assert(std::is_same_v<std::decay_t<int[5]>, int*>);

// 陷阱3：函数类型的decay
static_assert(std::is_same_v<std::decay_t<void(int)>, void(*)(int)>);

// 陷阱4：is_base_of对非类类型
static_assert(!std::is_base_of_v<int, int>);  // OK，返回false
// static_assert(std::is_base_of_v<Incomplete, Derived>);  // 可能UB！
```

---

## 7. 性能数据

### 7.1 编译期计算能力

| 技术 | 编译期计算能力 | 代码复杂度 | 编译时间影响 |
|-----|--------------|-----------|-------------|
| SFINAE | 强 | 高 | 中等 |
| if constexpr | 中 | 低 | 低 |
| Concepts | 强 | 低 | 低 |
| 模板递归 | 强 | 高 | 高（深度限制） |

### 7.2 运行时性能

所有type_traits和SFINAE技巧都是**编译期**的，**零运行时开销**。

```cpp
// 以下代码运行时完全相同：
template<typename T>
std::enable_if_t<std::is_integral_v<T>, T> add1(T a, T b) { return a + b; }

template<typename T>
T add2(T a, T b) {
    if constexpr (std::is_integral_v<T>) {
        return a + b;
    }
}

T add3(T a, T b) { return a + b; }  // 非模板
```

---

## 8. 总结

```
SFINAE与类型萃取核心要点
│
├── SFINAE原理
│   ├── 替换失败不是错误
│   ├── 从重载集中移除候选
│   └── 实现编译期多态
│
├── std::enable_if
│   ├── 返回类型位置
│   ├── 默认模板参数位置（推荐）
│   └── 函数参数位置
│
├── type_traits分类
│   ├── 主类型类别（is_void, is_integral等）
│   ├── 复合类型类别（is_arithmetic, is_scalar等）
│   ├── 类型属性（is_const, is_trivial等）
│   ├── 类型关系（is_same, is_base_of等）
│   └── 类型修改（remove_cv, add_reference等）
│
├── 自定义traits
│   ├── 继承std::true_type/false_type
│   ├── 使用偏特化实现条件判断
│   └── 组合标准traits
│
├── void_t技巧
│   ├── 检测成员类型/函数/变量
│   └── detection idiom（C++17）
│
├── SFINAE vs if constexpr
│   ├── 需要重载解析：SFINAE
│   ├── 简单条件分支：if constexpr
│   └── C++20：Concepts
│
└── 最佳实践
    ├── 优先使用_v和_t后缀版本
    ├── 复杂约束用conjunction/disjunction
    └── C++20用Concepts替代复杂SFINAE
```

**核心原则**：
1. SFINAE是编译期条件选择的核心机制
2. C++17起优先使用`if constexpr`，需要重载解析时用SFINAE
3. C++20 Concepts是最现代的解决方案
4. 所有type_traits操作都是编译期，零运行时开销

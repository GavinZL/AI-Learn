
# iOS ARC 引用计数存储原理与 SideTable 协作机制深度解析

## 一、isa 指针的位域布局：内联引用计数存储

### 1.1 Non-pointer isa 的位域设计

在 64 位架构（ARM64/x86_64）下，Objective-C 利用地址空间的冗余位，将 isa 指针改造为**多用途位域容器**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1  │ 1  │ 1  │ 33        │ 6     │ 1      │ 1    │ 19            │ 1    │
│ idx│has │has │ shiftcls  │ magic │ weakly │deallo│ extra_rc      │ has  │
│    │assoc│cxx│ (类指针)   │(调试) │ref'd   │cating│ (内联引用计数) │sidet │
│    │    │dtor│           │       │        │      │               │able  │
└─────────────────────────────────────────────────────────────────────────┘
 63   62   61   60-28      27-22   21       20     19-1            0
```

### 1.2 关键位域解析

| 位域 | 范围 | 含义 |
|------|------|------|
| `extra_rc` | 0-18 (19位) | **内联引用计数**，存储对象的引用计数减1 |
| `has_sidetable_rc` | 19 (1位) | 标记是否有溢出到 SideTable 的引用计数 |
| `weakly_referenced` | 21 (1位) | 标记对象是否被弱引用指向 |
| `deallocating` | 20 (1位) | 标记对象是否正在释放 |
| `shiftcls` | 28-60 (33位) | 实际的类指针（右移3位后存储） |

### 1.3 引用计数的存储策略

```cpp
// 伪代码：引用计数操作逻辑
inline uintptr_t getRetainCount() {
    uintptr_t extra_rc = (isa >> 1) & 0x7FFFF;  // 提取19位extra_rc
    if (isa & (1 << 19)) {  // has_sidetable_rc 为真
        return extra_rc + sideTable->refcnts[this] + 1;
    }
    return extra_rc + 1;  // +1 是因为 extra_rc 存储的是"额外引用数"
}
```

**核心设计思想**：
- **空间换时间**：将高频访问的引用计数直接嵌入 isa，避免额外内存访问
- **延迟分配**：只有当 `extra_rc` 溢出时才分配 SideTable
- **位运算优化**：所有操作通过位掩码完成，速度极快

---

## 二、SideTable 的触发条件与存储结构

### 2.1 何时使用 SideTable

SideTable 在以下两种情况下被使用：

| 场景 | 触发条件 | 说明 |
|------|----------|------|
| **引用计数溢出** | `extra_rc` 超过 2^19-1 (约52万) | 对象的引用计数非常大 |
| **存在弱引用** | 对象被 `__weak` 修饰的指针指向 | 需要记录所有弱引用地址 |

### 2.2 SideTable 全局结构

SideTable 并非每个对象一个，而是**全局哈希表**结构：

```cpp
// 简化版源码结构（objc4-818.2）
struct SideTable {
    spinlock_t slock;              // 自旋锁，保证线程安全
    RefcountMap refcnts;           // 引用计数哈希表: obj -> refcount
    weak_table_t weak_table;       // 弱引用哈希表: obj -> weak_entries
};

// 全局 SideTable 数组（减少锁竞争）
static const int SideTableHashBits = 8;
static const int SideTableSize = 1 << SideTableHashBits;  // 256个表
static SideTable SideTables[SideTableSize];

// 根据对象地址计算使用哪个 SideTable
static SideTable& tableForPointer(id obj) {
    uintptr_t hash = (uintptr_t)obj >> 4;  // 对齐后地址
    return SideTables[hash & (SideTableSize - 1)];
}
```

### 2.3 引用计数在 SideTable 中的存储

```cpp
// RefcountMap 实际上是 DenseMap 的封装
typedef objc::DenseMap<id, size_t> RefcountMap;

// 存储格式（简化）：
// key:   对象指针 (id)
// value: 引用计数的高 bits (uintptr_t)
//        低1位标记是否为 deallocating 状态
```

**存储规则**：
- `isa.extra_rc` 存储引用计数的低 19 位（减1后的值）
- `SideTable.refcnts` 存储引用计数的高位部分
- 两者相加得到完整的引用计数

---

## 三、弱引用表（weak_table_t）的详细结构

### 3.1 weak_table_t 结构定义

```cpp
// 弱引用表结构（源自 objc4 源码）
struct weak_table_t {
    weak_entry_t *weak_entries;     // 弱引用条目数组（哈希表）
    size_t num_entries;             // 当前条目数
    uintptr_t mask;                 // 哈希表大小-1
    uintptr_t max_hash_displacement; // 最大探测距离
};

// 单个弱引用条目
struct weak_entry_t {
    // 联合体：根据引用数量选择不同存储方式
    union {
        struct {
            // 当弱引用数量 <= 4 时，使用内联数组存储
            __weak id *inline_referrers[4];
        };
        struct {
            // 当弱引用数量 > 4 时，使用动态数组
            __weak id **referrers;      // 弱引用指针数组
            uintptr_t num_refs;          // 引用数量
            uintptr_t mask;              // 数组容量-1
            uintptr_t max_hash_displacement;
        };
    };
    id referent;  // 被引用的对象（key）
};
```

### 3.2 弱引用存储的两种模式

**模式一：内联存储（≤4个弱引用）**

```
┌─────────────────────────────────────────┐
│ weak_entry_t                            │
├─────────────────────────────────────────┤
│ referent: 0x12345678 (被引用对象地址)    │
├─────────────────────────────────────────┤
│ inline_referrers[0]: 0xABCDEF00 ──┐    │
│ inline_referrers[1]: 0xABCDEF04 ──┼──┐ │
│ inline_referrers[2]: nil          │  │ │
│ inline_referrers[3]: nil          │  │ │
└─────────────────────────────────────────┘
                                    │  │
                                    ▼  ▼
                              ┌─────────────┐
                              │ __weak id * │
                              │ 指向弱引用变量 │
                              └─────────────┘
```

**模式二：动态数组（>4个弱引用）**

```
┌─────────────────────────────────────────┐
│ weak_entry_t                            │
├─────────────────────────────────────────┤
│ referent: 0x12345678                    │
├─────────────────────────────────────────┤
│ referers ──────┐                        │
│ num_refs: 10   │                        │
│ mask: 15       │                        │
└────────────────┼────────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ __weak id* 数组  │
        ├─────────────────┤
        │ [0] 0xABCDEF00  │
        │ [1] 0xABCDEF04  │
        │ [2] 0xABCDEF08  │
        │ ...             │
        │ [9] 0xABCDEF24  │
        └─────────────────┘
```

### 3.3 弱引用的注册流程

```cpp
// 伪代码：注册弱引用
void weak_register_no_lock(weak_table_t *weak_table, 
                           id referent,           // 被引用对象
                           __weak id *referrer) {  // 弱引用变量地址
    // 1. 查找是否已有该对象的 entry
    weak_entry_t *entry = weak_table_find(weak_table, referent);
    
    if (!entry) {
        // 2. 创建新 entry，使用内联存储
        entry = weak_table_add(weak_table, referent);
        entry->inline_referrers[0] = referrer;
    } else {
        // 3. 已有 entry，添加新的弱引用
        if (entry->num_refs < 4) {
            // 使用内联数组
            entry->inline_referrers[entry->num_refs] = referrer;
        } else if (entry->num_refs == 4) {
            // 从内联切换到动态数组
            weak_entry_grow(entry);
            append_to_dynamic_array(entry, referrer);
        } else {
            // 使用动态数组
            append_to_dynamic_array(entry, referrer);
        }
    }
    
    // 4. 标记对象的 isa.weakly_referenced = true
    referent->isa.weakly_referenced = true;
}
```

---

## 四、对象销毁时的弱引用清理机制

### 4.1 完整的销毁调用链

```
┌─────────────────────────────────────────────────────────────────┐
│                        对象销毁流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [对象 release，引用计数归零]                                      │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │   dealloc       │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                    │
│  │objc_destructInstance    │     │ 标记 isa.deallocating = true │                    │
│  │                 │────▶│ 调用 C++ 析构函数 │                    │
│  └────────┬────────┘     │ 移除关联对象       │                    │
│           │              └─────────────────┘                    │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │weak_clear_no_lock│  ◀── 核心：清理所有弱引用                   │
│  └────────┬────────┘                                            │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │ 遍历 weak_table  │                                            │
│  │ 找到所有指向此    │                                            │
│  │ 对象的弱引用      │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                    │
│  │atomic_store()   │────▶│ 将每个 __weak   │                    │
│  │(内存屏障)        │     │ 指针置为 nil    │                    │
│  └─────────────────┘     └─────────────────┘                    │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │ 从 SideTable    │                                            │
│  │ 删除 weak_entry │                                            │
│  └─────────────────┘                                            │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │  free(对象内存)  │                                            │
│  └─────────────────┘                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 weak_clear_no_lock 的详细实现

```cpp
// 伪代码：清理弱引用（objc-weak.mm）
void weak_clear_no_lock(weak_table_t *weak_table, id referent) {
    // 1. 查找该对象的弱引用条目
    weak_entry_t *entry = weak_table_find(weak_table, referent);
    if (!entry) return;
    
    // 2. 遍历所有弱引用指针
    for (uintptr_t i = 0; i < entry->num_refs; i++) {
        __weak id *referrer = entry->referrers[i];
        
        if (referrer) {
            // 3. 原子性置零：将弱引用变量设为 nil
            // 使用内存屏障确保多线程安全
            atomic_store((uintptr_t*)referrer, (uintptr_t)nil);
            
            // 4. 清空条目
            entry->referrers[i] = nil;
        }
    }
    
    // 5. 从弱引用表中移除该 entry
    weak_table_remove(weak_table, referent);
    
    // 6. 注意：此时不释放 entry 内存，留给后续复用
}
```

### 4.3 零化弱引用的线程安全保证

```cpp
// 原子置零的关键代码
static inline void weak_store_zero(id *referrer) {
    // 使用顺序一致性内存序，确保：
    // 1. 之前的内存操作都已完成
    // 2. 其他线程立即可见 nil 值
    atomic_store_explicit((atomic_uintptr_t *)referrer, 
                          (uintptr_t)nil, 
                          memory_order_seq_cst);
}
```

**线程安全机制**：
1. **自旋锁保护**：SideTable 操作使用 `spinlock_t` 保护
2. **原子操作**：弱引用置零使用 `atomic_store`，保证多线程可见性
3. **内存屏障**：顺序一致性语义确保 happens-before 关系

---

## 五、isa 与 SideTable 协作的完整流程

### 5.1 retain 操作的数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                        retain 流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  objc_retain(obj)                                               │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                            │
│  │ 检查 isa.extra_rc│                                            │
│  │ 是否达到最大值   │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│     ┌─────┴─────┐                                               │
│     ▼           ▼                                               │
│  未溢出      已溢出                                              │
│     │           │                                               │
│     ▼           ▼                                               │
│  ┌────────┐  ┌─────────────────┐                                │
│  │extra_rc│  │ 检查 isa.has_   │                                │
│  │  +1    │  │ sidetable_rc    │                                │
│  │        │  └────────┬────────┘                                │
│  │ 完成   │           │                                         │
│  └────────┘     ┌─────┴─────┐                                   │
│                 ▼           ▼                                   │
│              未设置        已设置                                │
│                 │           │                                   │
│                 ▼           ▼                                   │
│           ┌────────┐   ┌─────────────────┐                      │
│           │创建    │   │ SideTable.refcnts│                      │
│           │SideTable│   │ [obj] += 1       │                      │
│           │.refcnts│   │                  │                      │
│           │ = 1    │   │ 完成             │                      │
│           │        │   └─────────────────┘                      │
│           │设置    │                                            │
│           │has_    │                                            │
│           │sidetable│                                            │
│           │_rc = 1 │                                            │
│           └────────┘                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 release 操作的数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                       release 流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  objc_release(obj)                                              │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                            │
│  │ 检查 isa.extra_rc│                                            │
│  │ > 0 ?           │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│     ┌─────┴─────┐                                               │
│     ▼           ▼                                               │
│   > 0          = 0                                               │
│     │           │                                               │
│     ▼           ▼                                               │
│  ┌────────┐  ┌─────────────────┐                                │
│  │extra_rc│  │ 检查 has_       │                                │
│  │  -1    │  │ sidetable_rc    │                                │
│  │        │  └────────┬────────┘                                │
│  │ 完成   │           │                                         │
│  └────────┘     ┌─────┴─────┐                                   │
│                 ▼           ▼                                   │
│              未设置        已设置                                │
│                 │           │                                   │
│                 ▼           ▼                                   │
│           ┌────────┐   ┌─────────────────┐                      │
│           │ 调用   │   │ SideTable.refcnts│                      │
│           │dealloc │   │ [obj] -= 1       │                      │
│           │        │   │                  │                      │
│           │清理弱   │   │ > 0 ? ─────┐     │                      │
│           │引用等   │   │            │     │                      │
│           └────────┘   └────────────┼─────┘                      │
│                                     │                           │
│                               ┌─────┴─────┐                     │
│                               ▼           ▼                     │
│                             > 0          = 0                     │
│                               │           │                     │
│                               ▼           ▼                     │
│                          ┌────────┐   ┌────────┐                │
│                          │ 完成   │   │ 调用   │                │
│                          │        │   │dealloc │                │
│                          └────────┘   └────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、总结：设计思想与性能权衡

### 6.1 核心设计思想

| 设计决策 | 原理 | 收益 |
|----------|------|------|
| **isa 内联引用计数** | 利用 64 位地址冗余位 | 90% 对象无需 SideTable，节省内存 |
| **延迟分配 SideTable** | 只在溢出或有弱引用时创建 | 减少内存碎片，提高缓存命中率 |
| **弱引用哈希表** | 对象 → 弱引用列表的映射 | O(1) 查找，快速清理 |
| **内联/动态数组切换** | 小对象用内联，大对象用动态 | 空间效率与扩展性平衡 |
| **原子置零** | 多线程安全地置 nil | 避免野指针，保证 ARC 安全 |

### 6.2 性能数据参考

| 操作 | 时间复杂度 | 典型耗时 |
|------|-----------|----------|
| isa 内联 retain | O(1) | ~3ns |
| isa 内联 release | O(1) | ~3ns |
| SideTable retain | O(1) + 锁竞争 | ~15ns |
| 弱引用创建 | O(1) + 哈希计算 | ~20ns |
| 弱引用清理 (dealloc) | O(n), n=弱引用数 | ~50ns × n |

### 6.3 关键源码文件（objc4）

- `objc-object.h`：`objc_object` 结构定义
- `objc-runtime-new.mm`：SideTable 管理
- `objc-weak.mm`：弱引用实现
- `objc-references.mm`：关联对象（使用类似机制）

这种设计体现了 Apple 对移动设备内存管理的深刻理解：**在有限内存下，通过精细的位域设计和分层存储策略，实现了高性能与低内存占用的完美平衡**。
# SwiftUI 基础使用与典型场景详细解析

> **文档版本**: iOS 15+ / Swift 5.7+  
> **核心定位**: 面向从 UIKit 转型或初学 SwiftUI 的开发者，以实践为导向的使用指南  
> **前置阅读**: [SwiftUI 架构与渲染机制](SwiftUI架构与渲染机制_详细解析.md)  
> **进阶阅读**: [SwiftUI 高级实践与性能优化](SwiftUI高级实践与性能优化_详细解析.md)

---

## 核心结论 TL;DR

| 维度 | 核心结论 |
|------|----------|
| **核心语法** | `@main` + `App` 协议定义入口，`View` 协议的 `body` 属性描述 UI，`some View` 保证类型安全 |
| **布局三板斧** | `HStack`/`VStack`/`ZStack` 三轴布局覆盖 90% 场景，配合 `Spacer`/`GeometryReader` 精细调整 |
| **修饰符核心规则** | 修饰符**顺序决定行为**——每个修饰符包裹前一个视图，产生新视图；先 `.padding` 后 `.background` 常为正确顺序 |
| **数据流选择** | 简单值 → `@State`；父子通信 → `@Binding`；跨层共享 → `@Environment`；复杂对象 → `@Observable` (iOS 17+) |
| **最佳起点版本** | iOS 16+ 为理想起点（`NavigationStack`/`Charts`），iOS 17+ 为最佳体验（`@Observable`/`SwiftData`） |
| **典型场景覆盖** | 设置页/列表页/详情页/登录页/TabBar 架构/弹窗交互/网络加载/下拉刷新 8 大场景可直接复用 |
| **迁移策略** | 通过 `UIHostingController` 渐进式嵌入，逐页面替换而非一次性重写 |

---

## 一、SwiftUI 核心语法与基础概念

### 1.1 App 入口与 Scene 管理

**SwiftUI 应用的入口由 `@main` 标记的 `App` 协议类型定义，取代了 UIKit 时代的 `AppDelegate` + `SceneDelegate` 模式。**

```
┌─────────────────────────────────────────────────┐
│                 SwiftUI App 结构                  │
├─────────────────────────────────────────────────┤
│                                                   │
│   @main App                                       │
│   ├── Scene (WindowGroup / DocumentGroup)         │
│   │   ├── View                                    │
│   │   │   ├── SubView                             │
│   │   │   └── SubView                             │
│   │   └── View                                    │
│   └── Scene                                       │
│       └── View                                    │
│                                                   │
│   App 持有 Scene → Scene 持有 View 层级           │
│   一个 App 可以有多个 Scene（多窗口）              │
└─────────────────────────────────────────────────┘
```

**完整 App 入口示例：**

```swift
// iOS 14+ 标准入口
import SwiftUI

@main
struct MyApp: App {
    // App 级别的状态（整个应用生命周期）
    @StateObject private var appState = AppState()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
    }
}

// iOS 17+ 使用 @Observable 替代 @StateObject
@main
struct MyModernApp: App {
    @State private var appState = AppState() // @Observable 类型
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
        }
    }
}
```

**关键概念说明：**

| 概念 | 说明 |
|------|------|
| `@main` | 标记应用入口点，取代 `UIApplicationMain` |
| `App` 协议 | 定义应用顶层结构，`body` 返回 `some Scene` |
| `WindowGroup` | 最常用 Scene，管理一组共享相同结构的窗口 |
| `DocumentGroup` | 文档型应用的 Scene（如文本编辑器） |
| Scene 生命周期 | `scenePhase` 环境值：`.active` / `.inactive` / `.background` |

```swift
// 监听 Scene 生命周期
@main
struct MyApp: App {
    @Environment(\.scenePhase) private var scenePhase
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .onChange(of: scenePhase) { _, newPhase in
            switch newPhase {
            case .active:    print("应用活跃")
            case .inactive:  print("即将进入后台")
            case .background: print("已进入后台")
            @unknown default: break
            }
        }
    }
}
```

### 1.2 View 协议基础

**`View` 协议是 SwiftUI 的核心抽象——任何遵循该协议并实现 `body` 属性的类型都是一个视图。**

```swift
// View 协议定义（简化版）
public protocol View {
    associatedtype Body: View
    @ViewBuilder var body: Self.Body { get }
}
```

**关键要素解析：**

- **`some View`（不透明返回类型）**：编译器知道具体类型但对外隐藏，避免暴露复杂的泛型嵌套类型
- **`@ViewBuilder`**：结果构建器，允许在 `body` 中使用 `if/else`、`switch`、多行表达式等声明式语法
- **View 是值类型**：SwiftUI View 是轻量级 `struct`，不是 UIKit 的重量级 `class`

```swift
// ✅ 正确的自定义 View 写法
struct ProfileCard: View {
    let name: String
    let subtitle: String
    var isHighlighted: Bool = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(name)
                .font(.headline)
                .foregroundStyle(isHighlighted ? .blue : .primary)
            
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
    }
}

// ✅ 使用 @ViewBuilder 构建条件内容
struct ConditionalContent: View {
    let showDetail: Bool
    
    var body: some View {
        VStack {
            headerSection
            if showDetail {
                detailSection
            }
        }
    }
    
    // 提取子视图为计算属性
    private var headerSection: some View {
        Text("Header").font(.title)
    }
    
    @ViewBuilder
    private var detailSection: some View {
        Text("Detail Line 1")
        Text("Detail Line 2")
    }
}
```

> **⚠️ 常见错误**：在 View 的 `init` 中执行耗时操作或副作用。View 是值类型，可能被频繁创建，body 也可能被多次求值。详见 [架构篇：View 的生命周期](SwiftUI架构与渲染机制_详细解析.md)。

### 1.3 基础布局系统

**SwiftUI 使用 HStack/VStack/ZStack 三轴布局容器覆盖绝大多数排列需求，配合 Spacer 和 GeometryReader 实现精细控制。**

#### 三轴布局容器

```swift
// VStack: 垂直排列（Y轴）
VStack(alignment: .leading, spacing: 12) {
    Text("Title").font(.title)
    Text("Subtitle").font(.subheadline)
}

// HStack: 水平排列（X轴）
HStack(alignment: .center, spacing: 16) {
    Image(systemName: "star.fill")
    Text("Favorited")
    Spacer() // 推到两端
    Text("★ 4.8")
}

// ZStack: 层叠排列（Z轴）
ZStack(alignment: .bottomTrailing) {
    Image("cover").resizable().aspectRatio(contentMode: .fill)
    Text("Badge")
        .padding(6)
        .background(.red)
        .clipShape(Capsule())
}
```

#### 辅助组件与尺寸获取

```swift
// Spacer: 弹性空间
HStack {
    Text("Left")
    Spacer()           // 填充所有可用空间
    Text("Right")
}

// Spacer 带最小间距
HStack {
    Text("A")
    Spacer(minLength: 20) // 至少 20pt 间距
    Text("B")
}

// Divider: 分隔线
VStack {
    Text("Section 1")
    Divider()           // 水平分隔线（在 VStack 中）
    Text("Section 2")
}

// GeometryReader: 获取父容器尺寸
GeometryReader { proxy in
    HStack(spacing: 0) {
        Color.red
            .frame(width: proxy.size.width * 0.3) // 30% 宽度
        Color.blue
            .frame(width: proxy.size.width * 0.7) // 70% 宽度
    }
}
```

#### 修饰符链与布局优先级

```swift
// .frame / .padding / .background 修饰符链
Text("Hello")
    .padding(.horizontal, 16)       // 1. 添加水平内边距
    .padding(.vertical, 8)          // 2. 添加垂直内边距
    .background(.blue)              // 3. 蓝色背景（包含 padding 区域）
    .clipShape(RoundedRectangle(cornerRadius: 8))
    .frame(maxWidth: .infinity)     // 4. 扩展到最大宽度

// layoutPriority: 控制空间不足时的压缩优先级
HStack {
    Text("重要内容，不应被截断")
        .layoutPriority(1)           // 高优先级，优先获得空间
    Text("次要内容，可以被压缩...")
        .layoutPriority(0)           // 默认优先级
}
```

### 1.4 常用内置组件速查表

#### 基础显示与输入组件

| 组件 | 用途 | 关键参数/用法 | 最低版本 |
|------|------|---------------|----------|
| `Text` | 文本显示 | `.font()` `.foregroundStyle()` `.lineLimit()` | iOS 13 |
| `Image` | 图片显示 | `systemName:` SF Symbols / `.resizable()` `.aspectRatio()` | iOS 13 |
| `AsyncImage` | 异步网络图片 | `url:` `content:` `placeholder:` 三阶段回调 | iOS 15 |
| `Button` | 按钮 | `action:` 闭包 + `label:` 视图 / `.buttonStyle()` | iOS 13 |
| `Toggle` | 开关 | `isOn: $binding` / `.toggleStyle()` | iOS 13 |
| `Slider` | 滑块 | `value: $binding` `in: range` `step:` | iOS 13 |
| `Picker` | 选择器 | `selection: $binding` + `ForEach` / `.pickerStyle()` | iOS 13 |
| `TextField` | 单行输入 | `text: $binding` / `prompt:` 占位文字 (iOS 15+) | iOS 13 |
| `TextEditor` | 多行输入 | `text: $binding` / `.scrollContentBackground(.hidden)` (iOS 16+) | iOS 14 |
| `SecureField` | 密码输入 | `text: $binding` / 自动隐藏输入内容 | iOS 13 |

#### 容器与导航组件

| 组件 | 用途 | 关键参数/用法 | 最低版本 |
|------|------|---------------|----------|
| `List` | 列表 | 静态行 / `ForEach` 动态行 / `.listStyle()` | iOS 13 |
| `Form` | 表单 | 自动分组样式 / 包裹 `Section` 使用 | iOS 13 |
| `Section` | 分组 | `header:` `footer:` / 在 List/Form 中使用 | iOS 13 |
| `ScrollView` | 滚动容器 | `.horizontal` / `.vertical` / 嵌套 LazyVStack | iOS 13 |
| `TabView` | 标签页 | `selection: $binding` + `.tag()` / `.tabItem()` | iOS 13 |
| `NavigationStack` | 导航容器 | `path: $binding` + `NavigationLink` + `.navigationDestination()` | iOS 16 |
| `NavigationLink` | 导航链接 | `value:` 类型安全导航 (iOS 16+) / 旧版 `destination:` | iOS 13 |
| `Sheet` | 半屏弹窗 | `.sheet(isPresented:)` / `.sheet(item:)` | iOS 13 |
| `Alert` | 弹窗 | `.alert(_:isPresented:actions:message:)` | iOS 15 |
| `FullScreenCover` | 全屏弹窗 | `.fullScreenCover(isPresented:)` | iOS 14 |

---

## 二、修饰符（Modifier）系统

### 2.1 修饰符链的执行顺序

**修饰符的顺序至关重要——每个修饰符会包裹前一个视图生成一个新的视图类型，因此顺序直接决定最终渲染效果。**

```
修饰符链的包裹原理：

Text("Hello")                        → Text
    .padding()                       → _PaddedView<Text>
    .background(.blue)               → _BackgroundView<_PaddedView<Text>>
    .clipShape(RoundedRectangle(...))→ _ClipShapeView<...>

实际上每个修饰符创建了一个新的包裹视图：
┌─────────────────────────────────┐
│  clipShape                       │
│  ┌───────────────────────────┐  │
│  │  background(.blue)         │  │
│  │  ┌───────────────────┐    │  │
│  │  │  padding()         │    │  │
│  │  │  ┌─────────────┐  │    │  │
│  │  │  │  Text("Hello")│  │    │  │
│  │  │  └─────────────┘  │    │  │
│  │  └───────────────────┘    │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### 2.2 修饰符顺序陷阱：.background 与 .padding 的顺序

**`.background` 在 `.padding` 前后会产生截然不同的视觉效果——这是 SwiftUI 初学者最常踩的坑。**

```
⚠️ 顺序对比：

写法 A（✅ 正确 — 背景包含 padding 区域）:       写法 B（❌ 错误 — 背景仅覆盖文字区域）:

Text("Hello")                                    Text("Hello")
    .padding(16)                                     .background(.blue)
    .background(.blue)                               .padding(16)

渲染效果：                                         渲染效果：
┌──────────────────────┐                          ┌──────────────────────┐
│  ████████████████████│                          │                      │
│  ████ Hello █████████│                          │    ████████████      │
│  ████████████████████│                          │    █ Hello ███      │
└──────────────────────┘                          │    ████████████      │
蓝色填满整个含 padding 的区域                      │                      │
                                                  └──────────────────────┘
                                                  蓝色仅覆盖文字，padding 透明
```

### 2.3 常用修饰符分类表

#### 布局类修饰符

| 修饰符 | 作用 | 典型用法 |
|--------|------|----------|
| `.frame(width:height:alignment:)` | 设置固定或范围尺寸 | `.frame(maxWidth: .infinity)` 铺满 |
| `.padding(_:_:)` | 添加内边距 | `.padding(.horizontal, 16)` |
| `.offset(x:y:)` | 偏移（不影响布局） | `.offset(y: -10)` 向上偏移 |
| `.position(x:y:)` | 绝对定位（影响布局） | 在 ZStack/overlay 中使用 |
| `.ignoresSafeArea()` | 忽略安全区域 | `.ignoresSafeArea(.all, edges: .bottom)` |

#### 样式类修饰符

| 修饰符 | 作用 | 典型用法 |
|--------|------|----------|
| `.foregroundStyle()` | 前景色/渐变 | `.foregroundStyle(.blue)` / `.foregroundStyle(.linearGradient(...))` |
| `.font()` | 字体 | `.font(.system(size: 16, weight: .bold))` |
| `.background()` | 背景 | `.background(.ultraThinMaterial)` 毛玻璃 |
| `.overlay()` | 覆盖层 | `.overlay(alignment: .topTrailing) { badge }` |
| `.clipShape()` | 裁剪形状 | `.clipShape(Circle())` |
| `.shadow()` | 阴影 | `.shadow(color: .black.opacity(0.1), radius: 8, y: 4)` |
| `.opacity()` | 透明度 | `.opacity(isEnabled ? 1.0 : 0.5)` |

#### 交互类修饰符

| 修饰符 | 作用 | 典型用法 |
|--------|------|----------|
| `.onTapGesture()` | 点击手势 | `.onTapGesture { action() }` |
| `.onLongPressGesture()` | 长按手势 | `.onLongPressGesture(minimumDuration: 0.5) { ... }` |
| `.gesture()` | 自定义手势 | `.gesture(DragGesture().onChanged { ... })` |
| `.disabled()` | 禁用交互 | `.disabled(!isFormValid)` |
| `.allowsHitTesting()` | 控制点击穿透 | `.allowsHitTesting(false)` |

#### 状态弹窗类修饰符

| 修饰符 | 作用 | 典型用法 |
|--------|------|----------|
| `.sheet(isPresented:)` | 半屏弹窗 | `.sheet(isPresented: $showSheet) { SheetView() }` |
| `.fullScreenCover()` | 全屏覆盖 | `.fullScreenCover(isPresented: $showFull) { ... }` |
| `.alert()` | 系统弹窗 | `.alert("Title", isPresented: $showAlert) { Button("OK") {} }` |
| `.confirmationDialog()` | 操作菜单 | `.confirmationDialog("", isPresented: $show) { ... }` |
| `.popover()` | 气泡弹窗 | `.popover(isPresented: $show) { content }` (iPad) |

#### 动画类修饰符

| 修饰符 | 作用 | 典型用法 |
|--------|------|----------|
| `.animation(_:value:)` | 隐式动画 | `.animation(.spring, value: isExpanded)` |
| `.transition()` | 视图插入/移除过渡 | `.transition(.slide.combined(with: .opacity))` |
| `.matchedGeometryEffect()` | 跨视图几何动画 | 配合 `@Namespace` 实现 Hero 动画 |
| `.withAnimation {}` | 显式动画（全局函数） | `withAnimation(.easeInOut) { state.toggle() }` |

### 2.4 自定义 ViewModifier

**当多个视图复用相同的修饰符组合时，应提取为自定义 `ViewModifier`，提高代码复用性和一致性。**

```swift
// 定义自定义修饰符
struct CardStyle: ViewModifier {
    var isElevated: Bool = true
    
    func body(content: Content) -> some View {
        content
            .padding(16)
            .background(.background)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .shadow(
                color: isElevated ? .black.opacity(0.1) : .clear,
                radius: isElevated ? 8 : 0,
                y: isElevated ? 4 : 0
            )
    }
}

// 扩展 View 提供便捷方法
extension View {
    func cardStyle(elevated: Bool = true) -> some View {
        modifier(CardStyle(isElevated: elevated))
    }
}

// 使用
VStack {
    Text("Card Content")
    Text("More Content")
}
.cardStyle()                // 带阴影
.cardStyle(elevated: false) // 不带阴影
```

---

## 三、数据流基础

### 3.1 数据流核心概念

**SwiftUI 的数据流遵循单向数据流原则：状态（Source of Truth）驱动视图，用户交互修改状态，触发视图更新。**

```mermaid
graph TB
    A[Source of Truth<br/>状态源] --> B[Derived Value<br/>派生值]
    B --> C[View Body<br/>视图渲染]
    C --> D[User Action<br/>用户交互]
    D --> A
    
    A -.->|@State / @Observable| C
    A -.->|@Binding| E[Child View<br/>子视图]
    A -.->|@Environment| F[Deep Child View<br/>深层子视图]
```

### 3.2 @State：本地值状态

**`@State` 用于视图私有的简单值状态（Bool、Int、String 等），SwiftUI 管理其存储生命周期。**

```swift
struct CounterView: View {
    @State private var count = 0       // ✅ 私有、简单值
    @State private var name = ""       // ✅ 本地输入状态
    @State private var isOn = false    // ✅ 开关状态
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Count: \(count)")
            
            HStack {
                Button("−") { count -= 1 }
                Button("+") { count += 1 }
            }
            
            TextField("Name", text: $name)   // $ 前缀获取 Binding
            Toggle("Enable", isOn: $isOn)
        }
        .padding()
    }
}
```

**注意事项：**
- `@State` 应始终标记为 `private`，属于视图内部实现细节
- 不要在 `body` 中读取/写入同一个 `@State`（会导致无限循环）
- `@State` 的初始值在视图首次创建时设定，后续视图重建**不会**重置

### 3.3 @Binding：双向绑定

**`@Binding` 用于子视图读写父视图拥有的状态，实现双向数据传递而不持有存储。**

```swift
// 父视图持有状态
struct ParentView: View {
    @State private var volume: Double = 50
    @State private var isMuted = false
    
    var body: some View {
        VStack {
            Text("Volume: \(Int(volume))%")
            VolumeControl(volume: $volume, isMuted: $isMuted) // 传递 Binding
        }
    }
}

// 子视图通过 @Binding 读写父视图状态
struct VolumeControl: View {
    @Binding var volume: Double    // 不持有存储，引用父视图的 @State
    @Binding var isMuted: Bool
    
    var body: some View {
        VStack {
            Slider(value: $volume, in: 0...100)
                .disabled(isMuted)
            Toggle("Mute", isOn: $isMuted)
        }
    }
}

// Preview 中使用 .constant 创建静态 Binding
#Preview {
    VolumeControl(volume: .constant(50), isMuted: .constant(false))
}
```

### 3.4 @Environment：环境值注入

**`@Environment` 从视图层级的环境中读取系统或自定义值，适合跨多层传递配置信息。**

```swift
struct ThemeAwareView: View {
    @Environment(\.colorScheme) private var colorScheme         // 深色/浅色模式
    @Environment(\.dynamicTypeSize) private var typeSize         // 字体大小
    @Environment(\.horizontalSizeClass) private var sizeClass   // 尺寸类别
    @Environment(\.dismiss) private var dismiss                  // 关闭当前视图
    
    var body: some View {
        VStack {
            Text("Current Mode: \(colorScheme == .dark ? "Dark" : "Light")")
            
            if sizeClass == .regular {
                Text("iPad / 大屏布局")
            } else {
                Text("iPhone 布局")
            }
            
            Button("Close") { dismiss() }
        }
    }
}
```

**常用系统环境值：**

| 环境值 | 类型 | 说明 |
|--------|------|------|
| `\.colorScheme` | `ColorScheme` | `.light` / `.dark` |
| `\.dynamicTypeSize` | `DynamicTypeSize` | 用户字体大小偏好 |
| `\.horizontalSizeClass` | `UserInterfaceSizeClass?` | `.compact` / `.regular` |
| `\.locale` | `Locale` | 用户语言区域 |
| `\.dismiss` | `DismissAction` | 关闭当前 sheet/navigation |
| `\.openURL` | `OpenURLAction` | 打开 URL |
| `\.isSearching` | `Bool` | 是否正在搜索 (iOS 15+) |
| `\.editMode` | `Binding<EditMode>?` | List 编辑模式 |

### 3.5 @Observable (iOS 17+)：现代对象状态管理

**iOS 17 引入 `@Observable` 宏，取代 `ObservableObject` + `@Published`，实现自动细粒度依赖追踪。**

```swift
import Observation

// iOS 17+ 推荐方式
@Observable
class UserProfile {
    var name: String = ""
    var email: String = ""
    var avatar: URL?
    var loginCount: Int = 0    // 即使此属性变化，只有使用它的视图才会更新
}

struct ProfileView: View {
    // 直接使用，无需 @ObservedObject
    var profile: UserProfile
    
    var body: some View {
        VStack {
            Text(profile.name)     // 仅追踪 name
            Text(profile.email)    // 仅追踪 email
            // loginCount 变化时此视图不会更新（未在 body 中读取）
        }
    }
}

// 对比：iOS 16 及以下的旧方式
class OldUserProfile: ObservableObject {
    @Published var name: String = ""    // 需要逐个标记 @Published
    @Published var email: String = ""
    @Published var loginCount: Int = 0  // 任何 @Published 变化都通知所有观察者
}

struct OldProfileView: View {
    @ObservedObject var profile: OldUserProfile  // 需要属性包装器
    var body: some View {
        Text(profile.name) // loginCount 变化时此视图也会更新 ❌
    }
}
```

### 3.6 数据流选择决策树

```mermaid
graph TD
    A[需要管理状态] --> B{数据归属?}
    B -->|视图私有| C{数据类型?}
    B -->|父视图传入| D[@Binding<br/>双向绑定]
    B -->|跨多层共享| E{iOS 版本?}
    
    C -->|简单值类型<br/>Bool/Int/String| F[@State]
    C -->|复杂对象| G{iOS 版本?}
    
    G -->|iOS 17+| H[@State + @Observable]
    G -->|iOS 16-| I[@StateObject + ObservableObject]
    
    E -->|iOS 17+| J[@Environment + @Observable]
    E -->|iOS 16-| K[@EnvironmentObject + ObservableObject]
    
    style F fill:#e8f5e9
    style D fill:#e3f2fd
    style H fill:#f3e5f5
    style J fill:#fff3e0
```

---

## 四、典型使用场景与最佳实践

### 4.1 设置/表单页面

**场景描述：** 应用设置页面，使用 `Form` + `Section` 组织选项，配合 `Toggle`/`Picker`/`Slider` 交互。

```swift
// iOS 16+
struct SettingsView: View {
    @AppStorage("username") private var username = ""
    @AppStorage("notifications") private var notificationsEnabled = true
    @State private var downloadQuality = Quality.high
    @State private var maxCacheSize: Double = 500
    @State private var showClearAlert = false
    
    enum Quality: String, CaseIterable, Identifiable {
        case low = "低"
        case medium = "中"
        case high = "高"
        var id: Self { self }
    }
    
    var body: some View {
        NavigationStack {
            Form {
                Section("账户") {
                    TextField("用户名", text: $username)
                    NavigationLink("编辑个人资料") {
                        Text("Profile Editor")
                    }
                }
                
                Section("偏好设置") {
                    Toggle("启用通知", isOn: $notificationsEnabled)
                    
                    Picker("下载质量", selection: $downloadQuality) {
                        ForEach(Quality.allCases) { quality in
                            Text(quality.rawValue).tag(quality)
                        }
                    }
                    
                    VStack(alignment: .leading) {
                        Text("缓存上限: \(Int(maxCacheSize)) MB")
                        Slider(value: $maxCacheSize, in: 100...2000, step: 100)
                    }
                }
                
                Section {
                    Button("清除缓存", role: .destructive) {
                        showClearAlert = true
                    }
                } footer: {
                    Text("当前缓存占用 234 MB")
                }
            }
            .navigationTitle("设置")
            .alert("确认清除？", isPresented: $showClearAlert) {
                Button("取消", role: .cancel) {}
                Button("清除", role: .destructive) { /* clear cache */ }
            } message: {
                Text("此操作不可恢复")
            }
        }
    }
}
```

**关键要点：**
- `Form` 自动提供平台原生表单样式（iOS 为 grouped 样式）
- `@AppStorage` 直接读写 `UserDefaults`，适合简单偏好设置
- `Picker` 在 `Form` 中自动以导航行样式呈现

### 4.2 列表展示页面

**场景描述：** 可搜索的列表页面，支持导航到详情、删除、搜索过滤。

```swift
// iOS 16+
struct ContactListView: View {
    @State private var contacts = Contact.sampleData
    @State private var searchText = ""
    @State private var path = NavigationPath()
    
    var filteredContacts: [Contact] {
        if searchText.isEmpty { return contacts }
        return contacts.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
    }
    
    var body: some View {
        NavigationStack(path: $path) {
            List {
                ForEach(filteredContacts) { contact in
                    NavigationLink(value: contact) {
                        ContactRow(contact: contact)
                    }
                }
                .onDelete(perform: deleteContacts)
            }
            .navigationTitle("通讯录")
            .searchable(text: $searchText, prompt: "搜索联系人")
            .navigationDestination(for: Contact.self) { contact in
                ContactDetailView(contact: contact)
            }
            .toolbar {
                EditButton()
            }
            .overlay {
                if filteredContacts.isEmpty {
                    ContentUnavailableView.search(text: searchText)
                }
            }
        }
    }
    
    private func deleteContacts(at offsets: IndexSet) {
        contacts.remove(atOffsets: offsets)
    }
}

struct ContactRow: View {
    let contact: Contact
    
    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(.blue.opacity(0.2))
                .frame(width: 44, height: 44)
                .overlay {
                    Text(String(contact.name.prefix(1)))
                        .font(.headline)
                        .foregroundStyle(.blue)
                }
            
            VStack(alignment: .leading) {
                Text(contact.name).font(.body)
                Text(contact.phone)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
```

### 4.3 详情页面

**场景描述：** 滚动详情页面，展示网络图片、文字描述和操作按钮。

```swift
// iOS 15+
struct ArticleDetailView: View {
    let article: Article
    @State private var isBookmarked = false
    
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                // 顶部大图
                AsyncImage(url: article.imageURL) { phase in
                    switch phase {
                    case .empty:
                        Rectangle()
                            .fill(.gray.opacity(0.2))
                            .overlay { ProgressView() }
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(16/9, contentMode: .fill)
                    case .failure:
                        Rectangle()
                            .fill(.gray.opacity(0.2))
                            .overlay {
                                Image(systemName: "photo")
                                    .foregroundStyle(.secondary)
                            }
                    @unknown default:
                        EmptyView()
                    }
                }
                .frame(height: 220)
                .clipped()
                
                // 内容区域
                VStack(alignment: .leading, spacing: 12) {
                    Text(article.title)
                        .font(.title2.bold())
                    
                    HStack {
                        Label(article.author, systemImage: "person")
                        Spacer()
                        Label(article.date.formatted(.dateTime.month().day()),
                              systemImage: "calendar")
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    
                    Divider()
                    
                    Text(article.content)
                        .font(.body)
                        .lineSpacing(6)
                }
                .padding(.horizontal)
            }
        }
        .navigationTitle(article.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            Button {
                isBookmarked.toggle()
            } label: {
                Image(systemName: isBookmarked ? "bookmark.fill" : "bookmark")
            }
        }
    }
}
```

### 4.4 登录/注册页面

**场景描述：** 登录页面包含输入校验、按钮禁用逻辑和加载状态。

```swift
// iOS 15+
struct LoginView: View {
    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    @FocusState private var focusedField: Field?
    
    enum Field { case email, password }
    
    private var isFormValid: Bool {
        !email.isEmpty && email.contains("@") && password.count >= 6
    }
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()
                
                // Logo 区域
                Image(systemName: "lock.shield")
                    .font(.system(size: 60))
                    .foregroundStyle(.blue)
                
                Text("Welcome Back")
                    .font(.title.bold())
                
                // 输入区域
                VStack(spacing: 16) {
                    TextField("邮箱", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                        .focused($focusedField, equals: .email)
                        .submitLabel(.next)
                        .onSubmit { focusedField = .password }
                    
                    SecureField("密码（至少6位）", text: $password)
                        .textContentType(.password)
                        .focused($focusedField, equals: .password)
                        .submitLabel(.done)
                        .onSubmit { login() }
                }
                .textFieldStyle(.roundedBorder)
                .padding(.horizontal)
                
                // 错误提示
                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .transition(.opacity)
                }
                
                // 登录按钮
                Button {
                    login()
                } label: {
                    Group {
                        if isLoading {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("登录")
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!isFormValid || isLoading)
                .padding(.horizontal)
                
                Spacer()
                
                // 底部注册入口
                HStack {
                    Text("还没有账号？")
                    NavigationLink("立即注册") {
                        Text("Registration View")
                    }
                }
                .font(.footnote)
            }
            .animation(.easeInOut, value: errorMessage)
        }
    }
    
    private func login() {
        focusedField = nil
        isLoading = true
        errorMessage = nil
        
        Task {
            try? await Task.sleep(for: .seconds(2)) // 模拟网络请求
            isLoading = false
            errorMessage = "邮箱或密码错误" // 模拟错误
        }
    }
}
```

### 4.5 TabBar 应用架构

**场景描述：** 多 Tab 应用的标准架构组织。

```swift
// iOS 16+
struct MainTabView: View {
    @State private var selectedTab = Tab.home
    
    enum Tab: String, CaseIterable {
        case home = "首页"
        case explore = "发现"
        case messages = "消息"
        case profile = "我的"
        
        var icon: String {
            switch self {
            case .home:     return "house"
            case .explore:  return "safari"
            case .messages: return "message"
            case .profile:  return "person"
            }
        }
    }
    
    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem { Label(Tab.home.rawValue, systemImage: Tab.home.icon) }
                .tag(Tab.home)
            
            ExploreView()
                .tabItem { Label(Tab.explore.rawValue, systemImage: Tab.explore.icon) }
                .tag(Tab.explore)
            
            MessagesView()
                .tabItem { Label(Tab.messages.rawValue, systemImage: Tab.messages.icon) }
                .tag(Tab.messages)
                .badge(3) // 未读消息数
            
            ProfileView()
                .tabItem { Label(Tab.profile.rawValue, systemImage: Tab.profile.icon) }
                .tag(Tab.profile)
        }
    }
}

// 每个 Tab 页面独立持有 NavigationStack
struct HomeView: View {
    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack {
                    ForEach(0..<20) { i in
                        NavigationLink("Item \(i)") {
                            Text("Detail \(i)")
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("首页")
        }
    }
}
```

**关键要点：**
- 每个 Tab 内部独立管理自己的 `NavigationStack`
- 使用枚举管理 Tab 类型，便于扩展和程序化切换
- `.badge()` 支持数字或字符串角标

### 4.6 Sheet/弹窗交互与数据传递

**场景描述：** 弹出 Sheet 并向 Sheet 传递数据，Sheet 内编辑后回传。

```swift
// iOS 16+
struct ItemListView: View {
    @State private var items = ["Apple", "Banana", "Cherry"]
    @State private var selectedItem: String?
    @State private var showAddSheet = false
    
    var body: some View {
        NavigationStack {
            List {
                ForEach(items, id: \.self) { item in
                    Button(item) {
                        selectedItem = item  // 触发 item sheet
                    }
                }
            }
            .navigationTitle("Items")
            .toolbar {
                Button { showAddSheet = true } label: {
                    Image(systemName: "plus")
                }
            }
            // Sheet 方式 1：基于 Bool
            .sheet(isPresented: $showAddSheet) {
                AddItemSheet { newItem in
                    items.append(newItem)
                }
            }
            // Sheet 方式 2：基于 Optional Item（自动 unwrap）
            .sheet(item: $selectedItem) { item in
                // 这里 item 是非可选的 String
                Text("Selected: \(item)")
                    .presentationDetents([.medium, .large]) // iOS 16+ 半屏高度
            }
        }
    }
}

// Sheet 内容视图，通过闭包回传数据
struct AddItemSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var newItemName = ""
    var onAdd: (String) -> Void
    
    var body: some View {
        NavigationStack {
            Form {
                TextField("名称", text: $newItemName)
            }
            .navigationTitle("添加项目")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("添加") {
                        onAdd(newItemName)
                        dismiss()
                    }
                    .disabled(newItemName.isEmpty)
                }
            }
        }
    }
}
```

> 使 `String` 符合 `Identifiable` 以配合 `.sheet(item:)` 使用：  
> `extension String: @retroactive Identifiable { public var id: Self { self } }`

### 4.7 网络数据加载

**场景描述：** 使用 `.task` + `async/await` 加载网络数据，展示加载/成功/失败三种状态。

```swift
// iOS 15+
struct PostListView: View {
    @State private var posts: [Post] = []
    @State private var loadingState = LoadingState.idle
    
    enum LoadingState: Equatable {
        case idle
        case loading
        case loaded
        case error(String)
    }
    
    var body: some View {
        NavigationStack {
            Group {
                switch loadingState {
                case .idle, .loading:
                    ProgressView("加载中...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    
                case .loaded:
                    List(posts) { post in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(post.title).font(.headline)
                            Text(post.body)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(2)
                        }
                    }
                    
                case .error(let message):
                    ContentUnavailableView {
                        Label("加载失败", systemImage: "wifi.exclamationmark")
                    } description: {
                        Text(message)
                    } actions: {
                        Button("重试") { Task { await loadPosts() } }
                    }
                }
            }
            .navigationTitle("Posts")
            .task {
                // .task 在视图出现时自动执行，视图消失时自动取消
                await loadPosts()
            }
        }
    }
    
    private func loadPosts() async {
        loadingState = .loading
        do {
            let url = URL(string: "https://jsonplaceholder.typicode.com/posts")!
            let (data, _) = try await URLSession.shared.data(from: url)
            posts = try JSONDecoder().decode([Post].self, from: data)
            loadingState = .loaded
        } catch {
            loadingState = .error(error.localizedDescription)
        }
    }
}

struct Post: Codable, Identifiable {
    let id: Int
    let title: String
    let body: String
}
```

**关键要点：**
- `.task` 修饰符是 SwiftUI 中执行异步操作的标准方式（iOS 15+）
- `.task` 自动绑定视图生命周期：出现时执行，消失时取消
- 使用枚举管理加载状态，确保 UI 状态的完备性

### 4.8 下拉刷新与分页加载

**场景描述：** 列表支持下拉刷新和滚动到底部自动加载更多。

```swift
// iOS 15+
struct PaginatedListView: View {
    @State private var items: [String] = []
    @State private var page = 1
    @State private var isLoadingMore = false
    @State private var hasMoreData = true
    
    var body: some View {
        NavigationStack {
            List {
                ForEach(items, id: \.self) { item in
                    Text(item)
                }
                
                // 底部加载更多指示器
                if hasMoreData {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .listRowSeparator(.hidden)
                        .onAppear {
                            // 出现在屏幕上时触发加载
                            Task { await loadMore() }
                        }
                }
            }
            .navigationTitle("分页列表")
            .refreshable {
                // 下拉刷新：重置并重新加载
                page = 1
                hasMoreData = true
                items = []
                await loadMore()
            }
            .task {
                // 首次加载
                if items.isEmpty {
                    await loadMore()
                }
            }
        }
    }
    
    private func loadMore() async {
        guard !isLoadingMore, hasMoreData else { return }
        isLoadingMore = true
        defer { isLoadingMore = false }
        
        // 模拟网络请求
        try? await Task.sleep(for: .seconds(1))
        
        let newItems = (1...20).map { "Item \((page - 1) * 20 + $0)" }
        items.append(contentsOf: newItems)
        
        hasMoreData = page < 5  // 假设共 5 页
        page += 1
    }
}
```

**关键要点：**
- `.refreshable` 自动提供下拉刷新 UI（iOS 15+），闭包结束后自动停止刷新动画
- 利用 `ProgressView` 的 `.onAppear` 实现触底加载——当加载指示器滚入可见区域时触发
- `defer` 确保 `isLoadingMore` 状态正确重置

---

## 五、iOS 版本兼容性与适配策略

### 5.1 版本特性对照表

| 版本 | 关键新增 API | 重要性 |
|------|-------------|--------|
| **iOS 13** | SwiftUI 首发、`@State`/`@Binding`/`@ObservedObject`/`@EnvironmentObject`、`NavigationView`、基础组件 | 基础版 |
| **iOS 14** | `@StateObject`、`@main` App 入口、`LazyVStack`/`LazyHStack`、`@SceneStorage`、`.fullScreenCover`、`ProgressView`、`Map` | 补全核心缺失 |
| **iOS 15** | `.task`、`.refreshable`、`.searchable`、`AsyncImage`、`FocusState`、`Material`（毛玻璃）、`.confirmationDialog`、`TimelineView`、Markdown Text | 实用性飞跃 |
| **iOS 16** | `NavigationStack`/`NavigationSplitView`、`Charts`、`.presentationDetents`、`AnyLayout`、`Grid`/`GridRow`、`Transferable`、`.scrollDismissesKeyboard` | **推荐起点** |
| **iOS 17** | `@Observable` 宏、SwiftData、`#Preview` 宏、`.contentTransition`、`.sensoryFeedback`、`ScrollView` 增强（`.scrollPosition`）、`TipKit` | **最佳体验** |
| **iOS 18** | `@Entry` 宏简化 EnvironmentKey、`MeshGradient`、`CustomContainerView`、Tab 增强、Zoom transition | 持续增强 |

### 5.2 最低版本选择建议

| 目标版本 | 适用场景 | 理由 |
|----------|----------|------|
| **iOS 15+** | 推荐起点 | `.task`/`.refreshable`/`.searchable` 可用，覆盖常见交互模式 |
| **iOS 16+** | **理想起点** | `NavigationStack` 解决导航痛点，`Charts`/`Grid` 大幅提升表达力 |
| **iOS 17+** | 最佳体验 | `@Observable` 简化数据流，SwiftData 替代 Core Data，`#Preview` 提升开发效率 |
| iOS 13/14 | 不推荐新项目 | 缺失大量关键 API，开发体验差，维护成本高 |

### 5.3 版本兼容代码模式

```swift
struct CompatibleNavigationView: View {
    var body: some View {
        if #available(iOS 16, *) {
            NavigationStack {
                contentView
                    .navigationDestination(for: String.self) { value in
                        Text("Detail: \(value)")
                    }
            }
        } else {
            NavigationView {
                contentView
            }
            .navigationViewStyle(.stack)
        }
    }
    
    @ViewBuilder
    private var contentView: some View {
        List {
            if #available(iOS 16, *) {
                NavigationLink("Go to Detail", value: "hello")
            } else {
                NavigationLink("Go to Detail") {
                    Text("Detail: hello")
                }
            }
        }
        .navigationTitle("Home")
    }
}
```

### 5.4 API 替代方案表

| 高版本 API | 最低版本 | 低版本替代方案 |
|-----------|----------|---------------|
| `NavigationStack` | iOS 16 | `NavigationView` + `.navigationViewStyle(.stack)` |
| `@Observable` | iOS 17 | `ObservableObject` + `@Published` + `@ObservedObject`/`@StateObject` |
| `.searchable` | iOS 15 | 手动 `TextField` + 过滤逻辑 |
| `.refreshable` | iOS 15 | `UIViewRepresentable` 包裹 `UIRefreshControl` |
| `.task` | iOS 15 | `.onAppear` + `Task { }` (需手动管理取消) |
| `AsyncImage` | iOS 15 | 自定义 `AsyncImageView` 或使用 SDWebImage/Kingfisher |
| `Charts` | iOS 16 | 第三方库（swift-charts-backport / SwiftUICharts） |
| `.presentationDetents` | iOS 16 | 自定义半屏 Sheet 或使用第三方库 |
| `ContentUnavailableView` | iOS 17 | 自定义空状态占位视图 |
| `#Preview` 宏 | iOS 17 | `struct _Previews: PreviewProvider { ... }` |
| `SwiftData` | iOS 17 | Core Data + `@FetchRequest` |
| `.sensoryFeedback` | iOS 17 | `UIImpactFeedbackGenerator` / `UINotificationFeedbackGenerator` |

---

## 六、从 UIKit 迁移实践指南

### 6.1 UIKit 概念到 SwiftUI 的映射表

| UIKit 概念 | SwiftUI 对应 | 关键差异 |
|-----------|-------------|----------|
| `UIViewController` | `View` (struct) | 值类型，无生命周期回调 |
| `UIView` | `View` (struct) | 每次状态变化重新求值 body |
| `UINavigationController` | `NavigationStack` (iOS 16+) | 声明式导航，数据驱动 |
| `UITabBarController` | `TabView` | 使用 `.tabItem` + `.tag` 配置 |
| `UITableView` | `List` | 自动 diff，无需手动 reload |
| `UICollectionView` | `LazyVGrid` / `LazyHGrid` | 内置懒加载 |
| `UIScrollView` | `ScrollView` | 有限的滚动控制（iOS 17+ 增强） |
| `UIStackView` | `HStack` / `VStack` / `ZStack` | 布局原语，性能更好 |
| `UIAlertController` | `.alert()` / `.confirmationDialog()` | 修饰符形式绑定状态 |
| `UIActivityIndicatorView` | `ProgressView` | 支持确定/不确定进度 |
| `UIImageView` + SDWebImage | `AsyncImage` (iOS 15+) | 内置异步加载，可自定义阶段 |
| `prepareForReuse` | 自动处理 | SwiftUI List 自动管理复用 |
| `delegate` / `dataSource` | 闭包 / `@Binding` | 声明式数据流取代委托 |
| `UIHostingController` | — | SwiftUI → UIKit 桥接 |
| `UIViewRepresentable` | — | UIKit → SwiftUI 桥接 |
| Storyboard / XIB | 代码声明 + Preview | 无 IB，实时预览替代 |
| Auto Layout | 布局容器 + 修饰符 | 无约束系统，父容器提议尺寸 |
| `viewDidLoad` / `viewWillAppear` | `.onAppear` / `.task` | 声明式生命周期 |
| `UIGestureRecognizer` | `.gesture()` / `.onTapGesture()` | 组合式手势 |

### 6.2 渐进式迁移策略

**从 UIKit 迁移到 SwiftUI 应采用渐进式策略：先在 UIKit 中嵌入 SwiftUI 视图，逐步替换页面。**

```swift
// 策略 1：UIKit 中嵌入 SwiftUI（UIHostingController）
class ExistingViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        
        // 将 SwiftUI 视图嵌入 UIKit
        let swiftUIView = NewFeatureView()
        let hostingController = UIHostingController(rootView: swiftUIView)
        
        addChild(hostingController)
        view.addSubview(hostingController.view)
        hostingController.view.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            hostingController.view.topAnchor.constraint(equalTo: view.topAnchor),
            hostingController.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            hostingController.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            hostingController.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
        hostingController.didMove(toParent: self)
    }
}

// 策略 2：SwiftUI 中使用 UIKit 组件（UIViewRepresentable）
struct MapViewWrapper: UIViewRepresentable {
    @Binding var region: MKCoordinateRegion
    
    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator
        return mapView
    }
    
    func updateUIView(_ mapView: MKMapView, context: Context) {
        mapView.setRegion(region, animated: true)
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, MKMapViewDelegate {
        var parent: MapViewWrapper
        init(_ parent: MapViewWrapper) { self.parent = parent }
    }
}
```

### 6.3 常见迁移陷阱与解决方案

| 陷阱 | 原因 | 解决方案 |
|------|------|----------|
| NavigationView 行为不一致 | iOS 13-15 的 NavigationView 在 iPad 上默认 SplitView | 使用 `.navigationViewStyle(.stack)` 或迁移到 `NavigationStack` (iOS 16+) |
| List 性能不如 UITableView | 未使用懒加载或数据模型未优化 | 使用 `LazyVStack` + `ScrollView` 替代复杂 List；确保 `Identifiable` 实现高效 |
| 键盘遮挡输入框 | SwiftUI 无内置键盘避让 (iOS 14 前) | iOS 15+ 使用 `@FocusState`；低版本手动调整 `.offset` |
| Sheet 内无法访问父视图状态 | Sheet 创建新的视图上下文 | 通过闭包回调、`@Binding` 或 `@Environment` 传递数据 |
| 自定义返回手势失效 | NavigationStack 替换了 UINavigationController 的行为 | 使用 `.toolbar` 自定义返回按钮或桥接 UIKit 导航控制器 |
| 布局循环 / 无限更新 | 在 body 中修改触发更新的状态 | 将副作用放到 `.onAppear` / `.task` / `.onChange` 中 |

---

## 七、开发工作流与工具链

### 7.1 Xcode Preview 高效使用技巧

**Xcode Preview 是 SwiftUI 开发的核心加速器——善用 Preview 可以将 UI 开发效率提升 3-5 倍。**

```swift
// iOS 17+ 使用 #Preview 宏（推荐）
#Preview("Light Mode") {
    ProfileCard(name: "Alice", subtitle: "iOS Developer")
}

#Preview("Dark Mode") {
    ProfileCard(name: "Alice", subtitle: "iOS Developer")
        .preferredColorScheme(.dark)
}

#Preview("Large Text") {
    ProfileCard(name: "Alice", subtitle: "iOS Developer")
        .environment(\.dynamicTypeSize, .xxxLarge)
}

// iOS 16 及以下使用 PreviewProvider
struct ProfileCard_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            ProfileCard(name: "Alice", subtitle: "iOS Developer")
                .previewDisplayName("Default")
            
            ProfileCard(name: "Alice", subtitle: "iOS Developer")
                .preferredColorScheme(.dark)
                .previewDisplayName("Dark Mode")
        }
        .previewLayout(.sizeThatFits)
        .padding()
    }
}
```

**Preview 实用技巧：**
- **多设备预览**：`.previewDevice(PreviewDevice(rawValue: "iPhone SE (3rd generation)"))` 指定设备
- **尺寸模式**：`.previewLayout(.sizeThatFits)` 仅显示组件实际尺寸（适合组件级预览）
- **快捷键**：`⌥⌘P` 刷新 Preview / `⌥⌘Enter` 打开/关闭 Canvas
- **Pin Preview**：固定某个文件的 Preview，在修改其他文件时保持可见

### 7.2 调试工具

```swift
// 1. Self._printChanges() — 打印导致视图更新的原因
struct DebugView: View {
    @State private var count = 0
    
    var body: some View {
        let _ = Self._printChanges() // 在控制台输出更新原因
        // 输出示例：DebugView: @self, @identity, _count changed.
        
        Button("Count: \(count)") {
            count += 1
        }
    }
}

// 2. 在 Debug 模式下可视化布局
extension View {
    func debugBorder(_ color: Color = .red) -> some View {
        #if DEBUG
        self.border(color)
        #else
        self
        #endif
    }
}

// 使用：
VStack {
    Text("Hello").debugBorder()
    Text("World").debugBorder(.blue)
}
```

**其他调试手段：**

| 工具 | 用途 | 使用方式 |
|------|------|----------|
| `Self._printChanges()` | 查看视图更新原因 | 在 `body` 开头添加 `let _ = Self._printChanges()` |
| View Hierarchy Debugger | 查看视图层级结构 | Xcode → Debug → View Debugging → Capture View Hierarchy |
| Instruments → SwiftUI | 分析视图更新频率 | Product → Profile → SwiftUI instrument |
| `.id()` 调试 | 验证视图标识是否正确 | 添加 `.id(UUID())` 观察视图是否重建 |
| `print()` 在 body 中 | 验证 body 是否被调用 | `let _ = print("body evaluated")` |

### 7.3 SwiftUI 项目结构组织建议

```
MyApp/
├── MyApp.swift                      // @main 入口
├── ContentView.swift                // 根视图
│
├── Features/                        // 按功能模块组织
│   ├── Home/
│   │   ├── HomeView.swift
│   │   ├── HomeViewModel.swift      // 或 @Observable 类
│   │   └── Components/
│   │       ├── FeaturedCard.swift
│   │       └── CategoryRow.swift
│   │
│   ├── Profile/
│   │   ├── ProfileView.swift
│   │   └── EditProfileView.swift
│   │
│   └── Settings/
│       └── SettingsView.swift
│
├── Shared/                          // 共享组件
│   ├── Components/                  // 可复用 UI 组件
│   │   ├── LoadingView.swift
│   │   ├── ErrorView.swift
│   │   └── AvatarView.swift
│   ├── Modifiers/                   // 自定义修饰符
│   │   ├── CardModifier.swift
│   │   └── ShimmerModifier.swift
│   └── Extensions/                  // View 扩展
│       └── View+Extensions.swift
│
├── Models/                          // 数据模型
│   ├── User.swift
│   └── Post.swift
│
├── Services/                        // 网络/数据服务
│   ├── APIClient.swift
│   └── UserService.swift
│
└── Resources/                       // 资源文件
    ├── Assets.xcassets
    └── Localizable.xcstrings
```

**组织原则：**
- **按功能模块（Feature）组织**而非按文件类型（所有 View 放一起）
- 每个 Feature 目录包含 View + ViewModel（或 @Observable 模型）+ 专属子组件
- 共享组件提取到 `Shared/` 目录
- 遵循就近原则：只在一处使用的子视图放在对应 Feature 内部

---

## 参考与延伸阅读

| 资源 | 说明 |
|------|------|
| [SwiftUI 架构与渲染机制](SwiftUI架构与渲染机制_详细解析.md) | 理解 AttributeGraph、视图标识、渲染流水线等底层原理 |
| [SwiftUI 高级实践与性能优化](SwiftUI高级实践与性能优化_详细解析.md) | 性能调优、自定义布局、复杂动画、架构模式 |
| [UIKit 架构与事件机制](../03_UIKit深度解析/UIKit架构与事件机制_详细解析.md) | UIKit 底层原理，理解 SwiftUI 与 UIKit 的关系 |
| [Apple SwiftUI 官方文档](https://developer.apple.com/documentation/swiftui) | 官方 API 参考 |
| [Apple SwiftUI Tutorials](https://developer.apple.com/tutorials/swiftui) | 官方入门教程 |

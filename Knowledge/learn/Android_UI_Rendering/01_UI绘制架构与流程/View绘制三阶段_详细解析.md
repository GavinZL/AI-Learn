# View绘制三阶段详细解析

> 深入剖析Android View树的构建过程与Measure、Layout、Draw三阶段的实现原理

---

## 核心结论（TL;DR）

**View绘制的本质是：将View树中每个节点的描述信息（LayoutParams、属性、内容），转换为屏幕上的像素信息。这个过程分为三个严格有序的阶段：**

1. **Measure（测量）**：确定每个View应该占据多大的空间（宽度和高度）
2. **Layout（布局）**：确定每个View应该放在什么位置（四个坐标：left, top, right, bottom）
3. **Draw（绘制）**：将View的内容实际绘制到屏幕上

**关键洞察**：
- 三个阶段**必须按序执行**：没有尺寸就无法确定位置，没有位置就无法绑定
- 每个阶段都是**自顶向下的递归遍历**：父View先处理，再递归处理子View
- 测量结果会被缓存，避免重复计算：通过标志位（PFLAG）控制是否需要重新测量/布局/绘制

---

## 第一部分：View树的构建过程

### 1.1 从XML到View对象树

当我们在Activity中调用`setContentView(R.layout.activity_main)`时，系统会完成一系列复杂的操作，将XML布局文件转换为内存中的View对象树。

**整体流程**：

```
setContentView(R.layout.xxx)
        │
        ▼
┌─────────────────────────────┐
│     PhoneWindow             │
│   .setContentView()         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 1. 初始化DecorView          │
│    (如果尚未创建)            │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 2. 获取ContentParent        │
│    (id=android.R.id.content)│
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 3. LayoutInflater.inflate() │
│    解析XML，创建View树       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 4. ContentParent.addView()  │
│    将View树添加到DecorView   │
└─────────────────────────────┘
```

### 1.2 LayoutInflater的工作原理

LayoutInflater是XML布局解析的核心引擎。它的主要职责是将XML布局文件转换为对应的View对象。

**核心解析流程**：

```java
// LayoutInflater.inflate() 简化流程
public View inflate(int resource, ViewGroup root, boolean attachToRoot) {
    // 1. 获取XML解析器
    XmlResourceParser parser = getContext().getResources().getLayout(resource);
    
    // 2. 解析XML，创建View树
    return inflate(parser, root, attachToRoot);
}

private View inflate(XmlPullParser parser, ViewGroup root, boolean attachToRoot) {
    // 3. 读取根节点
    final String name = parser.getName();
    
    // 4. 创建根View
    View temp = createViewFromTag(root, name, inflaterContext, attrs);
    
    // 5. 递归解析子节点
    rInflateChildren(parser, temp, attrs, true);
    
    // 6. 根据attachToRoot决定是否添加到root
    if (root != null && attachToRoot) {
        root.addView(temp, params);
    }
    
    return temp;
}
```

**View创建的三种方式**：

LayoutInflater创建View时，会依次尝试以下方式：

| 优先级 | 方式 | 说明 |
|--------|------|------|
| 1 | Factory2.onCreateView() | 自定义Factory可以拦截View创建 |
| 2 | Factory.onCreateView() | 旧版Factory接口 |
| 3 | mPrivateFactory.onCreateView() | 系统内部使用（如Fragment） |
| 4 | 反射创建 | 默认方式，通过反射调用View构造函数 |

**反射创建View的核心代码**：

```java
// LayoutInflater.createView() 简化版
public final View createView(String name, String prefix, AttributeSet attrs) {
    // 1. 从缓存获取构造函数
    Constructor<? extends View> constructor = sConstructorMap.get(name);
    
    if (constructor == null) {
        // 2. 加载Class
        Class<? extends View> clazz = mContext.getClassLoader()
                .loadClass(prefix != null ? (prefix + name) : name);
        
        // 3. 获取两参数构造函数 View(Context, AttributeSet)
        constructor = clazz.getConstructor(mConstructorSignature);
        
        // 4. 缓存构造函数
        sConstructorMap.put(name, constructor);
    }
    
    // 5. 反射创建View实例
    return constructor.newInstance(mConstructorArgs);
}
```

### 1.3 Factory/Factory2拦截机制

Factory机制允许开发者拦截View的创建过程，常用于：
- 全局替换系统控件（如将TextView替换为自定义的CustomTextView）
- 实现换肤框架
- 兼容性处理（如AppCompat将Button替换为AppCompatButton）

**使用示例**：

```java
LayoutInflater inflater = LayoutInflater.from(context);
inflater.setFactory2(new LayoutInflater.Factory2() {
    @Override
    public View onCreateView(View parent, String name, Context context, AttributeSet attrs) {
        // 拦截TextView的创建
        if ("TextView".equals(name)) {
            return new CustomTextView(context, attrs);
        }
        // 返回null表示不拦截，交给后续流程处理
        return null;
    }
    
    @Override
    public View onCreateView(String name, Context context, AttributeSet attrs) {
        return onCreateView(null, name, context, attrs);
    }
});
```

**AppCompatActivity的Factory2实现**：

AppCompat库通过Factory2将系统控件替换为兼容版本：

| 原控件 | 替换为 |
|--------|--------|
| TextView | AppCompatTextView |
| Button | AppCompatButton |
| ImageView | AppCompatImageView |
| EditText | AppCompatEditText |
| CheckBox | AppCompatCheckBox |
| ... | ... |

### 1.4 DecorView的初始化链路

DecorView是整个窗口的根View，它的创建和初始化涉及多个组件的协作。

**PhoneWindow.setContentView()流程**：

```java
// PhoneWindow.setContentView() 简化版
@Override
public void setContentView(int layoutResID) {
    // 1. 确保DecorView已创建
    if (mContentParent == null) {
        installDecor();
    }
    
    // 2. 清空原有内容（如果有）
    mContentParent.removeAllViews();
    
    // 3. 解析布局并添加到ContentParent
    mLayoutInflater.inflate(layoutResID, mContentParent);
}

private void installDecor() {
    if (mDecor == null) {
        // 创建DecorView
        mDecor = generateDecor(-1);
    }
    
    if (mContentParent == null) {
        // 根据窗口特性选择布局，并获取ContentParent
        mContentParent = generateLayout(mDecor);
    }
}
```

**DecorView的层次结构**：

```
DecorView (FrameLayout)
    │
    ├── LinearLayout (系统布局，包含状态栏、ActionBar等)
    │       │
    │       ├── ViewStub (ActionBar占位)
    │       │
    │       └── FrameLayout (id = android.R.id.content)
    │               │
    │               └── 用户的布局内容
    │
    └── 其他系统装饰View (导航栏等)
```

### 1.5 Activity/Fragment的View挂载时机

**Activity的View挂载**：

```
Activity.onCreate()
    │
    └── setContentView()  ← 此时View树已创建，但尚未挂载到Window
            │
Activity.onResume()
    │
    └── WindowManager.addView(decorView)  ← 触发ViewRootImpl创建
            │
            └── ViewRootImpl.setView()
                    │
                    └── requestLayout()  ← 首次绘制请求
```

**关键时机点**：

| 时机 | 事件 | View状态 |
|------|------|---------|
| onCreate | setContentView | View树已创建，未attach |
| onStart | Activity可见 | View树准备好显示 |
| onResume | WindowManager.addView | ViewRootImpl创建，首次requestLayout |
| 首次绘制 | performTraversals | Measure/Layout/Draw执行 |

---

## 第二部分：ViewRootImpl——UI绘制的核心调度器

### 2.1 ViewRootImpl的创建时机

ViewRootImpl是View系统与WindowManager之间的桥梁，它的创建发生在Activity变为可见时。

**创建链路**：

```
ActivityThread.handleResumeActivity()
    │
    └── WindowManagerImpl.addView(decorView, params)
            │
            └── WindowManagerGlobal.addView()
                    │
                    └── new ViewRootImpl(context, display)
                            │
                            └── root.setView(decorView, params, ...)
```

**WindowManagerGlobal.addView()核心代码**：

```java
public void addView(View view, ViewGroup.LayoutParams params, ...) {
    // 1. 创建ViewRootImpl
    ViewRootImpl root = new ViewRootImpl(view.getContext(), display);
    
    // 2. 保存到列表中
    mViews.add(view);           // DecorView列表
    mRoots.add(root);           // ViewRootImpl列表
    mParams.add(wparams);       // WindowParams列表
    
    // 3. 将DecorView与ViewRootImpl关联
    root.setView(view, wparams, panelParentView);
}
```

### 2.2 ViewRootImpl与Window、DecorView的关系

三者的关系可以理解为：

```
┌────────────────────────────────────────────────────────────┐
│                        Window (PhoneWindow)                 │
│                                                            │
│   ┌──────────────────────────────────────────────────┐    │
│   │                   DecorView                       │    │
│   │                                                  │    │
│   │   ┌──────────────────────────────────────────┐  │    │
│   │   │           用户View树                      │  │    │
│   │   │                                          │  │    │
│   │   └──────────────────────────────────────────┘  │    │
│   │                                                  │    │
│   └──────────────────────────────────────────────────┘    │
│                            ▲                               │
│                            │ mView                         │
│                    ┌───────┴────────┐                      │
│                    │  ViewRootImpl  │                      │
│                    └───────┬────────┘                      │
│                            │                               │
└────────────────────────────┼───────────────────────────────┘
                             │
                             ▼
                    WindowManagerService
                     (系统服务进程)
```

**关键字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| mView | View | 指向DecorView |
| mAttachInfo | View.AttachInfo | View的附加信息，包含Handler、Surface等 |
| mSurface | Surface | 绑定缓冲区的画布 |
| mChoreographer | Choreographer | 编舞者，协调绘制时机 |
| mTraversalRunnable | Runnable | 执行performTraversals的任务 |

### 2.3 scheduleTraversals()方法

`scheduleTraversals()`是请求绘制的入口方法，当View需要重绘或重新布局时，最终都会调用此方法。

**源码分析**：

```java
void scheduleTraversals() {
    if (!mTraversalScheduled) {
        // 1. 标记已调度，避免重复调度
        mTraversalScheduled = true;
        
        // 2. 设置同步屏障，阻止同步消息执行
        //    确保绘制消息优先处理
        mTraversalBarrier = mHandler.getLooper().getQueue()
                .postSyncBarrier();
        
        // 3. 向Choreographer注册回调，等待VSYNC
        mChoreographer.postCallback(
            Choreographer.CALLBACK_TRAVERSAL,
            mTraversalRunnable,  // 回调任务
            null
        );
        
        // 4. 通知输入系统
        notifyRendererOfFramePending();
        pokeDrawLockIfNeeded();
    }
}
```

**同步屏障（Sync Barrier）的作用**：

Handler消息队列中的消息分为同步消息和异步消息。同步屏障会阻止同步消息的执行，但异步消息不受影响。Choreographer发送的绘制回调是异步消息，因此可以优先执行。

```
消息队列：[同步1] [同步2] [异步-绘制] [同步3]
                            │
设置同步屏障后 ─────────────→│
                            ▼
                      优先执行绘制消息
```

### 2.4 performTraversals()方法

`performTraversals()`是整个绘制流程的入口，它协调了Measure、Layout、Draw三个阶段的执行。

**方法结构**（简化版）：

```java
private void performTraversals() {
    // ========== 准备阶段 ==========
    final View host = mView;  // DecorView
    
    // 计算窗口大小
    WindowManager.LayoutParams lp = mWindowAttributes;
    int desiredWindowWidth = ...;
    int desiredWindowHeight = ...;
    
    // ========== Measure阶段 ==========
    if (mFirst || windowShouldResize || ...) {
        // 第一次或窗口大小变化时，需要重新测量
        performMeasure(childWidthMeasureSpec, childHeightMeasureSpec);
    }
    
    // ========== Layout阶段 ==========
    if (didLayout) {
        performLayout(lp, desiredWindowWidth, desiredWindowHeight);
    }
    
    // ========== Draw阶段 ==========
    if (!cancelDraw) {
        performDraw();
    }
    
    // ========== 清理阶段 ==========
    mIsInTraversal = false;
}
```

**performTraversals的触发条件**：

| 触发来源 | 典型场景 |
|---------|---------|
| requestLayout() | View尺寸或位置需要改变 |
| invalidate() | View内容需要重绘 |
| 首次显示 | Activity可见时 |
| 窗口大小变化 | 屏幕旋转、窗口模式切换 |
| 焦点变化 | 获得/失去焦点 |

### 2.5 TraversalRunnable的执行时机

TraversalRunnable是一个简单的Runnable，它在Choreographer的VSYNC回调中被执行：

```java
final class TraversalRunnable implements Runnable {
    @Override
    public void run() {
        doTraversal();
    }
}

void doTraversal() {
    if (mTraversalScheduled) {
        mTraversalScheduled = false;
        
        // 1. 移除同步屏障
        mHandler.getLooper().getQueue()
                .removeSyncBarrier(mTraversalBarrier);
        
        // 2. 执行实际的遍历
        performTraversals();
    }
}
```

**完整的时序**：

```
                     App Process
                         │
requestLayout()          │
        │               │
        ▼               │
scheduleTraversals()     │
        │               │
        ▼               │
postCallback to         │
Choreographer           │
        │               │
        │    ┌──────────┘
        │    │
        ▼    ▼
    等待VSYNC信号
        │
        │     VSYNC到达
        │        │
        ▼        ▼
    Choreographer回调
        │
        ▼
    doTraversal()
        │
        ▼
    performTraversals()
        │
    ┌───┼───┐
    ▼   ▼   ▼
Measure Layout Draw
```

---

## 第三部分：Measure阶段详解

### 3.1 MeasureSpec的三种模式

MeasureSpec是父View对子View的测量约束，它是一个32位的int值，高2位表示模式（mode），低30位表示大小（size）。

**三种测量模式**：

| 模式 | 值 | 含义 | 对应LayoutParams |
|------|---|------|-----------------|
| **EXACTLY** | 01 | 精确值，子View应该是这个大小 | match_parent 或具体dp值 |
| **AT_MOST** | 10 | 最大值，子View最多是这个大小 | wrap_content |
| **UNSPECIFIED** | 00 | 无限制，子View想多大就多大 | 很少使用，ScrollView等 |

**MeasureSpec的编码方式**：

```java
// MeasureSpec类的关键方法
public static class MeasureSpec {
    private static final int MODE_SHIFT = 30;
    private static final int MODE_MASK  = 0x3 << MODE_SHIFT;  // 0xC0000000
    
    // 打包：将mode和size合并为一个int
    public static int makeMeasureSpec(int size, int mode) {
        return (size & ~MODE_MASK) | (mode & MODE_MASK);
    }
    
    // 获取模式
    public static int getMode(int measureSpec) {
        return (measureSpec & MODE_MASK);
    }
    
    // 获取大小
    public static int getSize(int measureSpec) {
        return (measureSpec & ~MODE_MASK);
    }
}
```

**示意图**：

```
MeasureSpec (32位int)
┌──┬──────────────────────────────────────────────────────────┐
│MM│              SIZE (30位)                                  │
└──┴──────────────────────────────────────────────────────────┘
  │
  └── Mode: 00=UNSPECIFIED, 01=EXACTLY, 10=AT_MOST
```

### 3.2 getChildMeasureSpec方法详解

`ViewGroup.getChildMeasureSpec()`是计算子View MeasureSpec的核心方法。它根据父View的MeasureSpec和子View的LayoutParams，计算出子View应该遵循的MeasureSpec。

**源码分析**：

```java
public static int getChildMeasureSpec(int spec, int padding, int childDimension) {
    int specMode = MeasureSpec.getMode(spec);
    int specSize = MeasureSpec.getSize(spec);
    
    // 父View可用空间 = 父View大小 - padding
    int size = Math.max(0, specSize - padding);
    
    int resultSize = 0;
    int resultMode = 0;
    
    switch (specMode) {
        case MeasureSpec.EXACTLY:
            // 父View是精确大小
            if (childDimension >= 0) {
                // 子View指定了具体大小
                resultSize = childDimension;
                resultMode = MeasureSpec.EXACTLY;
            } else if (childDimension == LayoutParams.MATCH_PARENT) {
                // 子View想填满父View
                resultSize = size;
                resultMode = MeasureSpec.EXACTLY;
            } else if (childDimension == LayoutParams.WRAP_CONTENT) {
                // 子View想自己决定大小，但不能超过父View
                resultSize = size;
                resultMode = MeasureSpec.AT_MOST;
            }
            break;
            
        case MeasureSpec.AT_MOST:
            // 父View有最大限制
            if (childDimension >= 0) {
                resultSize = childDimension;
                resultMode = MeasureSpec.EXACTLY;
            } else if (childDimension == LayoutParams.MATCH_PARENT) {
                // 子View想填满，但父View自己也不确定，给个最大值
                resultSize = size;
                resultMode = MeasureSpec.AT_MOST;
            } else if (childDimension == LayoutParams.WRAP_CONTENT) {
                resultSize = size;
                resultMode = MeasureSpec.AT_MOST;
            }
            break;
            
        case MeasureSpec.UNSPECIFIED:
            // 父View无限制（如ScrollView）
            if (childDimension >= 0) {
                resultSize = childDimension;
                resultMode = MeasureSpec.EXACTLY;
            } else if (childDimension == LayoutParams.MATCH_PARENT) {
                resultSize = size;
                resultMode = MeasureSpec.UNSPECIFIED;
            } else if (childDimension == LayoutParams.WRAP_CONTENT) {
                resultSize = size;
                resultMode = MeasureSpec.UNSPECIFIED;
            }
            break;
    }
    
    return MeasureSpec.makeMeasureSpec(resultSize, resultMode);
}
```

**规则总结表**：

| 父View模式 | 子View LayoutParams | 子View MeasureSpec |
|-----------|---------------------|-------------------|
| EXACTLY | 具体值(如100dp) | EXACTLY, 100dp |
| EXACTLY | MATCH_PARENT | EXACTLY, 父View大小 |
| EXACTLY | WRAP_CONTENT | AT_MOST, 父View大小 |
| AT_MOST | 具体值(如100dp) | EXACTLY, 100dp |
| AT_MOST | MATCH_PARENT | AT_MOST, 父View大小 |
| AT_MOST | WRAP_CONTENT | AT_MOST, 父View大小 |
| UNSPECIFIED | 具体值(如100dp) | EXACTLY, 100dp |
| UNSPECIFIED | MATCH_PARENT | UNSPECIFIED, 0 |
| UNSPECIFIED | WRAP_CONTENT | UNSPECIFIED, 0 |

### 3.3 View.measure()与onMeasure()

**measure()方法**（View.java）：

```java
public final void measure(int widthMeasureSpec, int heightMeasureSpec) {
    // 1. 检查是否需要重新测量
    boolean forceLayout = (mPrivateFlags & PFLAG_FORCE_LAYOUT) == PFLAG_FORCE_LAYOUT;
    boolean specChanged = widthMeasureSpec != mOldWidthMeasureSpec
            || heightMeasureSpec != mOldHeightMeasureSpec;
    boolean isSpecExactly = MeasureSpec.getMode(widthMeasureSpec) == MeasureSpec.EXACTLY
            && MeasureSpec.getMode(heightMeasureSpec) == MeasureSpec.EXACTLY;
    boolean matchesSpecSize = getMeasuredWidth() == MeasureSpec.getSize(widthMeasureSpec)
            && getMeasuredHeight() == MeasureSpec.getSize(heightMeasureSpec);
    
    boolean needsLayout = specChanged && (!isSpecExactly || !matchesSpecSize);
    
    if (forceLayout || needsLayout) {
        // 2. 清除测量缓存标记
        mPrivateFlags &= ~PFLAG_MEASURED_DIMENSION_SET;
        
        // 3. 调用onMeasure进行实际测量
        onMeasure(widthMeasureSpec, heightMeasureSpec);
        
        // 4. 检查是否正确设置了测量结果
        if ((mPrivateFlags & PFLAG_MEASURED_DIMENSION_SET) 
                != PFLAG_MEASURED_DIMENSION_SET) {
            throw new IllegalStateException("onMeasure() did not call "
                    + "setMeasuredDimension()");
        }
        
        // 5. 标记需要Layout
        mPrivateFlags |= PFLAG_LAYOUT_REQUIRED;
    }
    
    // 6. 保存MeasureSpec用于下次比较
    mOldWidthMeasureSpec = widthMeasureSpec;
    mOldHeightMeasureSpec = heightMeasureSpec;
}
```

**onMeasure()方法**（View.java默认实现）：

```java
protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
    // 默认实现：使用建议的最小尺寸或MeasureSpec约束的尺寸
    setMeasuredDimension(
        getDefaultSize(getSuggestedMinimumWidth(), widthMeasureSpec),
        getDefaultSize(getSuggestedMinimumHeight(), heightMeasureSpec)
    );
}

public static int getDefaultSize(int size, int measureSpec) {
    int result = size;
    int specMode = MeasureSpec.getMode(measureSpec);
    int specSize = MeasureSpec.getSize(measureSpec);
    
    switch (specMode) {
        case MeasureSpec.UNSPECIFIED:
            result = size;  // 使用建议的最小尺寸
            break;
        case MeasureSpec.AT_MOST:
        case MeasureSpec.EXACTLY:
            result = specSize;  // 使用MeasureSpec指定的尺寸
            break;
    }
    return result;
}
```

**重要提醒**：
- `onMeasure()`中**必须**调用`setMeasuredDimension()`，否则会抛出异常
- 自定义View如果支持`wrap_content`，需要重写`onMeasure()`并正确处理`AT_MOST`模式

### 3.4 ViewGroup测量子View的遍历过程

ViewGroup需要测量所有子View，才能确定自己的大小。以`measureChildren()`为例：

```java
protected void measureChildren(int widthMeasureSpec, int heightMeasureSpec) {
    final int size = mChildrenCount;
    final View[] children = mChildren;
    
    for (int i = 0; i < size; ++i) {
        final View child = children[i];
        // 跳过GONE的子View
        if ((child.mViewFlags & VISIBILITY_MASK) != GONE) {
            measureChild(child, widthMeasureSpec, heightMeasureSpec);
        }
    }
}

protected void measureChild(View child, int parentWidthMeasureSpec,
        int parentHeightMeasureSpec) {
    final LayoutParams lp = child.getLayoutParams();
    
    // 计算子View的MeasureSpec
    final int childWidthMeasureSpec = getChildMeasureSpec(parentWidthMeasureSpec,
            mPaddingLeft + mPaddingRight, lp.width);
    final int childHeightMeasureSpec = getChildMeasureSpec(parentHeightMeasureSpec,
            mPaddingTop + mPaddingBottom, lp.height);
    
    // 测量子View
    child.measure(childWidthMeasureSpec, childHeightMeasureSpec);
}
```

### 3.5 常见ViewGroup的测量策略差异

不同ViewGroup有不同的测量策略，这直接影响布局的性能。

**LinearLayout的测量策略**：

LinearLayout可能需要**两次测量**：

```java
// LinearLayout.measureVertical() 简化版
void measureVertical(int widthMeasureSpec, int heightMeasureSpec) {
    // 第一次测量：计算总高度和weight总和
    for (int i = 0; i < count; ++i) {
        measureChildBeforeLayout(child, ...);
        totalLength += childHeight + margin;
        totalWeight += lp.weight;
    }
    
    // 如果有weight，需要第二次测量
    if (totalWeight > 0) {
        // 计算剩余空间
        int remainingExcess = heightSize - totalLength;
        
        // 第二次测量：根据weight分配剩余空间
        for (int i = 0; i < count; ++i) {
            if (lp.weight > 0) {
                int share = (int) (remainingExcess * lp.weight / totalWeight);
                // 重新测量
                child.measure(childWidthMeasureSpec,
                        MeasureSpec.makeMeasureSpec(childHeight + share, EXACTLY));
            }
        }
    }
}
```

**RelativeLayout的测量策略**：

RelativeLayout需要**两次测量**来处理相对定位：

1. 第一次：水平方向排序和测量
2. 第二次：垂直方向排序和测量

**ConstraintLayout的测量策略**：

ConstraintLayout使用**约束求解器**，通过数学算法一次性计算所有View的位置和大小，通常只需要一次测量。

**性能对比**：

| ViewGroup | 测量复杂度 | 适用场景 |
|-----------|-----------|---------|
| FrameLayout | O(n) | 简单堆叠布局 |
| LinearLayout（无weight） | O(n) | 简单线性布局 |
| LinearLayout（有weight） | O(2n) | 需要比例分配 |
| RelativeLayout | O(2n) | 相对定位布局 |
| ConstraintLayout | O(n) | 复杂扁平布局 |

### 3.6 Measure的缓存优化

View通过标志位和缓存来避免重复测量：

**关键标志位**：

| 标志位 | 作用 |
|--------|------|
| PFLAG_FORCE_LAYOUT | 强制重新Layout（会触发重新Measure） |
| PFLAG_MEASURED_DIMENSION_SET | onMeasure中已调用setMeasuredDimension |
| PFLAG_LAYOUT_REQUIRED | Measure后标记，表示需要Layout |

**测量结果缓存**：

```java
// View中的测量结果缓存
private int mMeasuredWidth;   // 测量宽度
private int mMeasuredHeight;  // 测量高度

// 设置测量结果
protected final void setMeasuredDimension(int measuredWidth, int measuredHeight) {
    mMeasuredWidth = measuredWidth;
    mMeasuredHeight = measuredHeight;
    mPrivateFlags |= PFLAG_MEASURED_DIMENSION_SET;
}

// 获取测量结果
public final int getMeasuredWidth() {
    return mMeasuredWidth & MEASURED_SIZE_MASK;
}
```

---

## 第四部分：Layout阶段详解

### 4.1 View.layout()与onLayout()

**layout()方法**（View.java）：

```java
public void layout(int l, int t, int r, int b) {
    // 1. 检查是否需要重新Layout
    if ((mPrivateFlags3 & PFLAG3_MEASURE_NEEDED_BEFORE_LAYOUT) != 0) {
        onMeasure(mOldWidthMeasureSpec, mOldHeightMeasureSpec);
        mPrivateFlags3 &= ~PFLAG3_MEASURE_NEEDED_BEFORE_LAYOUT;
    }
    
    // 2. 保存旧的位置
    int oldL = mLeft;
    int oldT = mTop;
    int oldB = mBottom;
    int oldR = mRight;
    
    // 3. 设置新的位置
    boolean changed = setFrame(l, t, r, b);
    
    // 4. 如果位置变化或需要Layout，调用onLayout
    if (changed || (mPrivateFlags & PFLAG_LAYOUT_REQUIRED) == PFLAG_LAYOUT_REQUIRED) {
        onLayout(changed, l, t, r, b);
        
        // 5. 清除Layout标记
        mPrivateFlags &= ~PFLAG_LAYOUT_REQUIRED;
        
        // 6. 通知布局变化监听器
        ListenerInfo li = mListenerInfo;
        if (li != null && li.mOnLayoutChangeListeners != null) {
            for (OnLayoutChangeListener listener : li.mOnLayoutChangeListeners) {
                listener.onLayoutChange(this, l, t, r, b, oldL, oldT, oldR, oldB);
            }
        }
    }
}
```

**setFrame()方法**：

```java
protected boolean setFrame(int left, int top, int right, int bottom) {
    boolean changed = false;
    
    if (mLeft != left || mRight != right || mTop != top || mBottom != bottom) {
        changed = true;
        
        // 保存新的坐标
        mLeft = left;
        mTop = top;
        mRight = right;
        mBottom = bottom;
        
        // 标记需要重绘
        invalidate(sizeChanged);
    }
    return changed;
}
```

### 4.2 Layout阶段确定View的四个坐标

Layout阶段的核心目标是确定View的四个坐标：

```
┌────────────────────────────────────────┐
│              Parent View               │
│                                        │
│    (mLeft, mTop)                       │
│         ┌─────────────────┐            │
│         │                 │            │
│         │    Child View   │            │
│         │                 │            │
│         └─────────────────┘            │
│                     (mRight, mBottom)  │
│                                        │
└────────────────────────────────────────┘

View的位置由四个值确定：
- mLeft: View左边缘相对于父View左边缘的距离
- mTop: View上边缘相对于父View上边缘的距离
- mRight: View右边缘相对于父View左边缘的距离
- mBottom: View下边缘相对于父View上边缘的距离

计算关系：
- View宽度 = mRight - mLeft = getWidth()
- View高度 = mBottom - mTop = getHeight()
```

**重要区分**：

| 方法 | 时机 | 含义 |
|------|------|------|
| getMeasuredWidth() | Measure后 | 测量宽度（View期望的宽度） |
| getWidth() | Layout后 | 实际宽度（mRight - mLeft） |
| getMeasuredHeight() | Measure后 | 测量高度 |
| getHeight() | Layout后 | 实际高度 |

通常两者相等，但父View可以在Layout时给子View分配不同于测量值的大小。

### 4.3 ViewGroup.onLayout()的实现要求

ViewGroup的`onLayout()`是抽象方法，子类必须实现：

```java
// ViewGroup.java
@Override
protected abstract void onLayout(boolean changed, int l, int t, int r, int b);
```

**实现要求**：
- 必须遍历所有子View，调用`child.layout()`
- 需要考虑padding和margin
- 需要处理Gravity等对齐属性

### 4.4 LinearLayout的Layout实现逻辑

以垂直方向的LinearLayout为例：

```java
// LinearLayout.layoutVertical() 简化版
void layoutVertical(int left, int top, int right, int bottom) {
    final int paddingLeft = mPaddingLeft;
    int childTop;
    int childLeft;
    
    // 1. 根据Gravity计算起始位置
    switch (majorGravity) {
        case Gravity.BOTTOM:
            childTop = bottom - top - mTotalLength + mPaddingTop;
            break;
        case Gravity.CENTER_VERTICAL:
            childTop = (bottom - top - mTotalLength) / 2 + mPaddingTop;
            break;
        default:  // Gravity.TOP
            childTop = mPaddingTop;
            break;
    }
    
    // 2. 遍历子View进行Layout
    for (int i = 0; i < count; i++) {
        final View child = getVirtualChildAt(i);
        if (child == null || child.getVisibility() == GONE) {
            continue;
        }
        
        final int childWidth = child.getMeasuredWidth();
        final int childHeight = child.getMeasuredHeight();
        final LinearLayout.LayoutParams lp = (LinearLayout.LayoutParams) child.getLayoutParams();
        
        // 3. 根据layout_gravity计算水平位置
        int gravity = lp.gravity;
        switch (gravity & Gravity.HORIZONTAL_GRAVITY_MASK) {
            case Gravity.CENTER_HORIZONTAL:
                childLeft = paddingLeft + (childSpace - childWidth) / 2 + lp.leftMargin - lp.rightMargin;
                break;
            case Gravity.RIGHT:
                childLeft = childRight - childWidth - lp.rightMargin;
                break;
            default:  // Gravity.LEFT
                childLeft = paddingLeft + lp.leftMargin;
                break;
        }
        
        // 4. 考虑topMargin
        childTop += lp.topMargin;
        
        // 5. 调用child.layout()
        setChildFrame(child, childLeft, childTop, childWidth, childHeight);
        
        // 6. 更新childTop，加上高度和bottomMargin
        childTop += childHeight + lp.bottomMargin;
    }
}

private void setChildFrame(View child, int left, int top, int width, int height) {
    child.layout(left, top, left + width, top + height);
}
```

### 4.5 Layout阶段的性能注意事项

**避免在onLayout中触发requestLayout**：

如果在`onLayout()`中修改了会触发`requestLayout()`的属性，可能导致无限循环。

```java
// 错误示例
@Override
protected void onLayout(boolean changed, int l, int t, int r, int b) {
    // 这会触发requestLayout，导致再次Layout
    child.setLayoutParams(newParams);  // 危险！
}
```

**减少Layout次数**：

- 避免频繁调用`requestLayout()`
- 使用`View.offsetLeftAndRight()`和`View.offsetTopAndBottom()`进行简单位移
- 动画尽量使用`translationX/Y`而非修改`LayoutParams`

---

## 第五部分：Draw阶段详解

### 5.1 View.draw()方法的六个步骤

Draw阶段是整个绑定流程的最后一步，将View的内容实际绘制到屏幕上。`View.draw()`方法定义了标准的绘制顺序：

```java
// View.draw() 源码分析
public void draw(Canvas canvas) {
    final int privateFlags = mPrivateFlags;
    final boolean dirtyOpaque = (privateFlags & PFLAG_DIRTY_MASK) == PFLAG_DIRTY_OPAQUE;
    mPrivateFlags = (privateFlags & ~PFLAG_DIRTY_MASK) | PFLAG_DRAWN;
    
    /*
     * Draw traversal performs several drawing steps which must be executed
     * in the appropriate order:
     *
     *      1. Draw the background
     *      2. If necessary, save the canvas' layers to prepare for fading
     *      3. Draw view's content
     *      4. Draw children
     *      5. If necessary, draw the fading edges and restore layers
     *      6. Draw decorations (scrollbars for instance)
     *      7. If necessary, draw the default focus highlight
     */
    
    // Step 1: 绘制背景
    int saveCount;
    if (!dirtyOpaque) {
        drawBackground(canvas);
    }
    
    // 判断是否需要绘制渐变边缘
    final int viewFlags = mViewFlags;
    boolean horizontalEdges = (viewFlags & FADING_EDGE_HORIZONTAL) != 0;
    boolean verticalEdges = (viewFlags & FADING_EDGE_VERTICAL) != 0;
    
    // 如果不需要渐变边缘，走快速路径
    if (!verticalEdges && !horizontalEdges) {
        // Step 3: 绘制内容
        if (!dirtyOpaque) onDraw(canvas);
        
        // Step 4: 绘制子View
        dispatchDraw(canvas);
        
        // Step 6: 绘制前景、滚动条等装饰
        onDrawForeground(canvas);
        
        // Step 7: 绘制默认焦点高亮
        drawDefaultFocusHighlight(canvas);
        
        return;
    }
    
    // 需要渐变边缘时的完整路径（省略）
    // Step 2: 保存Canvas层
    // Step 5: 绘制渐变边缘并恢复层
    ...
}
```

**六个步骤详解**：

| 步骤 | 方法 | 作用 |
|------|------|------|
| 1 | drawBackground(canvas) | 绘制View的背景Drawable |
| 2 | canvas.saveLayer() | 保存Canvas层，为渐变边缘做准备（可选） |
| 3 | onDraw(canvas) | 绘制View自身的内容 |
| 4 | dispatchDraw(canvas) | 绘制子View（ViewGroup重写） |
| 5 | 绘制渐变边缘 | 如ListView的上下渐变（可选） |
| 6 | onDrawForeground(canvas) | 绘制前景、滚动条等装饰 |
| 7 | drawDefaultFocusHighlight(canvas) | 绘制默认焦点高亮 |

### 5.2 drawBackground()

```java
private void drawBackground(Canvas canvas) {
    final Drawable background = mBackground;
    if (background == null) {
        return;
    }
    
    // 设置背景的边界
    setBackgroundBounds();
    
    // 硬件加速路径
    if (canvas.isHardwareAccelerated() && mAttachInfo != null
            && mAttachInfo.mThreadedRenderer != null) {
        mBackgroundRenderNode = getDrawableRenderNode(background, mBackgroundRenderNode);
        // ...
    }
    
    // 软件渲染路径
    final int scrollX = mScrollX;
    final int scrollY = mScrollY;
    if ((scrollX | scrollY) == 0) {
        background.draw(canvas);
    } else {
        canvas.translate(scrollX, scrollY);
        background.draw(canvas);
        canvas.translate(-scrollX, -scrollY);
    }
}
```

### 5.3 onDraw() - 绘制自身内容

`onDraw()`是自定义View的核心方法，在这里绑定View的实际内容。

```java
// View.java 默认实现为空
protected void onDraw(Canvas canvas) {
}

// TextView.onDraw() 简化示例
@Override
protected void onDraw(Canvas canvas) {
    // 绑定文本
    canvas.drawText(mText, x, y, mTextPaint);
    
    // 绘制光标、选择高亮等
    // ...
}
```

**自定义View的onDraw()最佳实践**：

```java
@Override
protected void onDraw(Canvas canvas) {
    // 1. 不要在onDraw中创建对象（避免GC）
    // 错误：Paint paint = new Paint();
    // 正确：在构造函数或init方法中创建，保存为成员变量
    
    // 2. 使用clipRect减少绘制区域
    canvas.clipRect(dirtyRect);
    
    // 3. 考虑padding
    int paddingLeft = getPaddingLeft();
    int paddingTop = getPaddingTop();
    int width = getWidth() - paddingLeft - getPaddingRight();
    int height = getHeight() - paddingTop - getPaddingBottom();
    
    // 4. 执行绑制
    canvas.drawCircle(centerX, centerY, radius, mPaint);
}
```

### 5.4 dispatchDraw() - 绘制子View

`dispatchDraw()`在ViewGroup中实现，负责绘制所有子View：

```java
// ViewGroup.dispatchDraw() 简化版
@Override
protected void dispatchDraw(Canvas canvas) {
    final int childrenCount = mChildrenCount;
    final View[] children = mChildren;
    int flags = mGroupFlags;
    
    // 遍历并绘制子View
    for (int i = 0; i < childrenCount; i++) {
        final int childIndex = getAndVerifyPreorderedIndex(childrenCount, i, customOrder);
        final View child = getAndVerifyPreorderedView(preorderedList, children, childIndex);
        
        if ((child.mViewFlags & VISIBILITY_MASK) == VISIBLE 
                || child.getAnimation() != null) {
            more |= drawChild(canvas, child, drawingTime);
        }
    }
}

protected boolean drawChild(Canvas canvas, View child, long drawingTime) {
    return child.draw(canvas, this, drawingTime);
}
```

### 5.5 软件渲染 vs 硬件加速

**软件渲染路径**：

```
performDraw()
    │
    └── draw(fullRedrawNeeded)
            │
            └── drawSoftware(surface, ...)
                    │
                    ├── surface.lockCanvas(dirty)  // 锁定画布
                    │
                    ├── mView.draw(canvas)         // 执行绘制
                    │
                    └── surface.unlockCanvasAndPost(canvas)  // 解锁并提交
```

**硬件加速路径**：

```
performDraw()
    │
    └── draw(fullRedrawNeeded)
            │
            └── mAttachInfo.mThreadedRenderer.draw(mView, ...)
                    │
                    ├── updateRootDisplayList(view)  // 更新DisplayList
                    │       │
                    │       └── view.updateDisplayListIfDirty()
                    │               │
                    │               └── 录制绘制命令到RenderNode
                    │
                    └── syncAndDrawFrame()  // 同步到RenderThread执行
```

### 5.6 DisplayList录制与回放机制

**什么是DisplayList**：

DisplayList是绘制命令的序列化记录，类似于一个"绘制脚本"。它记录了所有Canvas操作（drawText、drawBitmap等），但不立即执行。

**录制过程**（主线程）：

```java
// View.updateDisplayListIfDirty() 简化版
public RenderNode updateDisplayListIfDirty() {
    final RenderNode renderNode = mRenderNode;
    
    if ((mPrivateFlags & PFLAG_DRAWING_CACHE_VALID) == 0
            || !renderNode.hasDisplayList()) {
        
        // 开始录制
        final RecordingCanvas canvas = renderNode.beginRecording(width, height);
        
        try {
            // 执行draw方法，但不是真正绘制，而是录制命令
            draw(canvas);
        } finally {
            // 结束录制
            renderNode.endRecording();
        }
    }
    
    return renderNode;
}
```

**回放过程**（RenderThread）：

```
RenderThread
    │
    └── DrawFrameTask.run()
            │
            ├── syncFrameState()      // 同步主线程的DisplayList
            │
            └── drawFrame()           // 执行GPU绘制
                    │
                    ├── prepareTree()    // 准备渲染树
                    │
                    └── draw()           // 遍历RenderNode，执行绘制命令
```

**DisplayList的优势**：

| 优势 | 说明 |
|------|------|
| 主线程解放 | 实际GPU绘制在RenderThread执行 |
| 增量更新 | 只更新变化的RenderNode |
| 属性动画优化 | 透明度、位移等属性变化无需重建DisplayList |
| 硬件加速 | 直接转换为GPU指令 |

### 5.7 RenderThread的作用

RenderThread是Android 5.0引入的独立渲染线程：

```
┌─────────────────────────────────────────────────────────────┐
│                        主线程 (UI Thread)                    │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  处理输入事件                                         │  │
│   │  执行动画计算                                         │  │
│   │  Measure / Layout                                    │  │
│   │  录制DisplayList                                     │  │
│   └─────────────────────────────────────────────────────┘  │
│                            │                                │
│                            │ 同步DisplayList                │
│                            ▼                                │
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                            ▼               RenderThread     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  接收DisplayList                                     │  │
│   │  执行GPU绘制                                         │  │
│   │  EGL/OpenGL ES操作                                   │  │
│   │  SwapBuffers                                         │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**RenderThread的优势**：

1. **主线程卡顿不影响渲染**：动画可以继续流畅执行
2. **并行处理**：主线程处理下一帧时，RenderThread可以绘制当前帧
3. **GPU利用率提升**：专门的线程管理GPU资源

---

## 第六部分：invalidate与requestLayout

### 6.1 invalidate()的触发链路

`invalidate()`用于请求View重绘，只触发Draw阶段，不触发Measure和Layout。

**调用链路**：

```
view.invalidate()
    │
    └── invalidateInternal(l, t, r, b, true, true)
            │
            ├── 标记dirty区域: mPrivateFlags |= PFLAG_DIRTY
            │
            └── parent.invalidateChild(this, damage)
                    │
                    └── 循环向上传播
                            │
                            └── ViewRootImpl.invalidateChildInParent(...)
                                    │
                                    └── scheduleTraversals()
```

**invalidateInternal()源码**：

```java
void invalidateInternal(int l, int t, int r, int b, boolean invalidateCache,
        boolean fullInvalidate) {
    
    // 1. 检查是否需要重绘
    if (skipInvalidate()) {
        return;
    }
    
    // 2. 标记dirty
    if (fullInvalidate) {
        mPrivateFlags |= PFLAG_DIRTY;
    }
    
    // 3. 向父View传播
    final ViewParent p = mParent;
    if (p != null && mAttachInfo != null) {
        final Rect damage = mAttachInfo.mTmpInvalRect;
        damage.set(l, t, r, b);
        p.invalidateChild(this, damage);
    }
}
```

**ViewGroup.invalidateChild()**：

```java
public final void invalidateChild(View child, final Rect dirty) {
    final AttachInfo attachInfo = mAttachInfo;
    
    if (attachInfo != null && attachInfo.mHardwareAccelerated) {
        // 硬件加速路径：直接通知ViewRootImpl
        onDescendantInvalidated(child, child);
        return;
    }
    
    // 软件渲染路径：逐层传播dirty区域
    ViewParent parent = this;
    do {
        // 调整dirty区域坐标
        // ...
        parent = parent.invalidateChildInParent(location, dirty);
    } while (parent != null);
}
```

### 6.2 requestLayout()的触发链路

`requestLayout()`用于请求重新布局，会触发Measure、Layout和Draw全部三个阶段。

**调用链路**：

```
view.requestLayout()
    │
    ├── 标记: mPrivateFlags |= PFLAG_FORCE_LAYOUT | PFLAG_INVALIDATED
    │
    └── mParent.requestLayout()
            │
            └── 循环向上传播
                    │
                    └── ViewRootImpl.requestLayout()
                            │
                            └── scheduleTraversals()
```

**View.requestLayout()源码**：

```java
public void requestLayout() {
    // 1. 清除测量缓存
    if (mMeasureCache != null) mMeasureCache.clear();
    
    // 2. 检查是否在Layout过程中
    if (mAttachInfo != null && mAttachInfo.mViewRequestingLayout == null) {
        // 正常情况
        ViewRootImpl viewRoot = getViewRootImpl();
        if (viewRoot != null && viewRoot.isInLayout()) {
            // 在Layout过程中调用requestLayout，延迟处理
            if (!viewRoot.requestLayoutDuringLayout(this)) {
                return;
            }
        }
        mAttachInfo.mViewRequestingLayout = this;
    }
    
    // 3. 标记需要强制Layout
    mPrivateFlags |= PFLAG_FORCE_LAYOUT;
    mPrivateFlags |= PFLAG_INVALIDATED;
    
    // 4. 向父View传播
    if (mParent != null && !mParent.isLayoutRequested()) {
        mParent.requestLayout();
    }
    
    if (mAttachInfo != null && mAttachInfo.mViewRequestingLayout == this) {
        mAttachInfo.mViewRequestingLayout = null;
    }
}
```

### 6.3 invalidate与requestLayout的区别

| 特性 | invalidate() | requestLayout() |
|------|--------------|-----------------|
| **触发Measure** | 否 | 是 |
| **触发Layout** | 否 | 是 |
| **触发Draw** | 是 | 是 |
| **传播方向** | 向上传播dirty区域 | 向上传播Layout请求 |
| **使用场景** | 内容变化，大小不变 | 大小或位置需要改变 |
| **典型例子** | 修改背景颜色、文字内容 | 修改LayoutParams、setText导致宽度变化 |

**选择原则**：

```java
// 只需要重绘时，用invalidate
void setBackgroundColor(int color) {
    mBackgroundColor = color;
    invalidate();  // 大小不变，只需重绘
}

// 大小可能变化时，用requestLayout
void setText(String text) {
    mText = text;
    requestLayout();  // 文字长度变化可能影响View大小
}
```

### 6.4 postInvalidateOnAnimation

`postInvalidateOnAnimation()`是动画友好的重绘方法，它会在下一个VSYNC时执行：

```java
public void postInvalidateOnAnimation() {
    final AttachInfo attachInfo = mAttachInfo;
    if (attachInfo != null) {
        attachInfo.mViewRootImpl.dispatchInvalidateOnAnimation(this);
    }
}

// ViewRootImpl中
void dispatchInvalidateOnAnimation(View view) {
    mInvalidateOnAnimationRunnable.addView(view);
}

// 在Choreographer的CALLBACK_ANIMATION回调中执行
final class InvalidateOnAnimationRunnable implements Runnable {
    @Override
    public void run() {
        for (View view : mViews) {
            view.invalidate();
        }
    }
}
```

**优势**：
- 与VSYNC同步，避免过度绘制
- 多次调用会合并，避免重复工作
- 动画更流畅

---

## 总结

### 绘制流程全景图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           绘制流程全景                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  setContentView()                                                       │
│        │                                                                │
│        ▼                                                                │
│  ┌─────────────┐                                                       │
│  │ View树构建   │  LayoutInflater → 反射创建View → 构建树形结构           │
│  └─────┬───────┘                                                       │
│        │                                                                │
│        ▼ (Activity.onResume后，WindowManager.addView)                   │
│  ┌─────────────┐                                                       │
│  │ViewRootImpl │  管理Window、协调绘制、处理输入                          │
│  │   创建      │                                                        │
│  └─────┬───────┘                                                       │
│        │                                                                │
│        ▼                                                                │
│  ┌─────────────┐                                                       │
│  │schedule     │  设置同步屏障、注册Choreographer回调                     │
│  │Traversals() │                                                        │
│  └─────┬───────┘                                                       │
│        │                                                                │
│        │ 等待VSYNC                                                      │
│        ▼                                                                │
│  ┌─────────────┐                                                       │
│  │perform      │  绘制流程入口                                           │
│  │Traversals() │                                                        │
│  └─────┬───────┘                                                       │
│        │                                                                │
│   ┌────┼────┬────────────────┐                                         │
│   ▼    ▼    ▼                ▼                                         │
│ ┌────┐ ┌────┐ ┌────┐  ┌─────────────┐                                 │
│ │ M  │ │ L  │ │ D  │  │ Render      │                                 │
│ │ e  │ │ a  │ │ r  │  │ Thread      │                                 │
│ │ a  │ │ y  │ │ a  │  │ GPU绑制     │                                 │
│ │ s  │ │ o  │ │ w  │  └─────────────┘                                 │
│ │ u  │ │ u  │ │    │                                                   │
│ │ r  │ │ t  │ │    │                                                   │
│ │ e  │ │    │ │    │                                                   │
│ └────┘ └────┘ └────┘                                                   │
│   │      │      │                                                      │
│   │      │      └──→ DisplayList录制 → RenderThread回放                 │
│   │      │                                                              │
│   │      └──→ 确定位置(mLeft/mTop/mRight/mBottom)                       │
│   │                                                                     │
│   └──→ 确定大小(mMeasuredWidth/mMeasuredHeight)                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 关键知识点回顾

1. **View树构建**：LayoutInflater通过反射创建View，Factory可以拦截
2. **ViewRootImpl**：UI绘制的核心调度器，连接View树与Window
3. **MeasureSpec**：父View对子View的测量约束，包含mode和size
4. **三阶段顺序**：Measure → Layout → Draw，严格有序
5. **硬件加速**：DisplayList录制+RenderThread回放，主线程卸载
6. **invalidate vs requestLayout**：重绘用前者，改大小用后者

---

## 参考资源

1. AOSP源码 - View.java, ViewGroup.java, ViewRootImpl.java
2. Android Developers - UI Performance
3. 《深入理解Android内核设计思想》
4. Google I/O - "For Butter or Worse: Smoothing Out Performance in Android UIs"

---

> 本文从源码角度深入分析了View绘制的完整流程。理解这些原理，对于优化UI性能、解决绘制问题至关重要。

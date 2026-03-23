# Surface与BufferQueue详细解析

## 概述

在Android图形系统中，Surface和BufferQueue是连接应用层渲染与底层合成显示的关键桥梁。理解这两个核心组件的工作原理，对于深入掌握Android UI渲染机制、进行性能调优以及解决图形相关问题至关重要。本章将从AOSP源码角度深入剖析Surface的本质、普通View的渲染路径、SurfaceView与TextureView的独特机制，以及整体Window-Surface架构设计。

---

## 1. Surface的本质

### 1.1 Surface在Android图形系统中的定位

Surface是Android图形系统中最核心的抽象之一，它代表了一个可以被渲染的画布（Canvas），同时也是图形数据流转的关键节点。从架构角度来看，Surface承担着以下重要角色：

**生产者-消费者模型的生产端入口**：Surface封装了BufferQueue的Producer端，应用程序通过Surface向BufferQueue提交渲染完成的图形缓冲区（GraphicBuffer）。

**跨进程图形数据传递的载体**：Surface对象可以通过Binder IPC跨进程传递，使得应用进程能够向SurfaceFlinger进程提交图形数据。

**Native层图形接口的统一抽象**：Surface实现了ANativeWindow接口，为EGL、OpenGL ES、Vulkan等图形API提供了统一的本地窗口抽象。

在AOSP源码中，Surface的Java层定义位于`frameworks/base/core/java/android/view/Surface.java`，而Native层实现位于`frameworks/native/libs/gui/Surface.cpp`。

```java
// frameworks/base/core/java/android/view/Surface.java
public class Surface implements Parcelable {
    // Native层Surface对象的指针
    long mNativeObject;
    
    // Surface持有的Canvas，用于软件渲染
    private final Canvas mCanvas = new CompatibleCanvas();
    
    // 关联的SurfaceControl，用于管理Surface属性
    private SurfaceControl mSurfaceControl;
}
```

### 1.2 Surface = BufferQueue的Producer端封装

从本质上理解，**Surface就是BufferQueue的Producer端的高级封装**。这一设计使得应用程序无需直接与复杂的BufferQueue交互，而是通过Surface提供的简洁API进行图形渲染。

BufferQueue是一个经典的生产者-消费者队列，它管理着一组GraphicBuffer：

```
+------------------+     +------------------+     +------------------+
|    Producer      |     |   BufferQueue    |     |    Consumer      |
|    (Surface)     |     |                  |     | (SurfaceFlinger) |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         | dequeueBuffer()        |                        |
         |----------------------->|                        |
         |<-----------------------|                        |
         | (获取空闲Buffer)        |                        |
         |                        |                        |
         | [渲染到Buffer]          |                        |
         |                        |                        |
         | queueBuffer()          |                        |
         |----------------------->|                        |
         |                        | acquireBuffer()        |
         |                        |----------------------->|
         |                        |<-----------------------|
         |                        |                        |
         |                        | releaseBuffer()        |
         |                        |<-----------------------|
```

Native层Surface与BufferQueue的关联在构造函数中建立：

```cpp
// frameworks/native/libs/gui/Surface.cpp
Surface::Surface(const sp<IGraphicBufferProducer>& bufferProducer, 
                 bool controlledByApp)
    : mGraphicBufferProducer(bufferProducer),  // 持有Producer接口
      mGenerationNumber(0),
      mSharedBufferMode(false),
      mAutoRefresh(false) {
    // 初始化ANativeWindow回调函数
    ANativeWindow::setSwapInterval  = hook_setSwapInterval;
    ANativeWindow::dequeueBuffer    = hook_dequeueBuffer;
    ANativeWindow::queueBuffer      = hook_queueBuffer;
    ANativeWindow::cancelBuffer     = hook_cancelBuffer;
    ANativeWindow::query            = hook_query;
    ANativeWindow::perform          = hook_perform;
    // ...
}
```

### 1.3 Surface的创建过程

Surface的创建是一个涉及多个系统组件协作的复杂过程。以Activity窗口的Surface为例，其创建流程如下：

#### 阶段一：ViewRootImpl发起窗口布局请求

当Activity启动或窗口属性变化时，ViewRootImpl会调用`relayoutWindow()`方法向WindowManagerService请求布局：

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
private int relayoutWindow(WindowManager.LayoutParams params, 
                           int viewVisibility,
                           boolean insetsPending) {
    // mSurfaceControl是用于接收WMS创建的Surface控制句柄
    // mSurface是实际用于渲染的Surface对象
    int relayoutResult = mWindowSession.relayout(
            mWindow, mSeq, params,
            (int) (mView.getMeasuredWidth() * appScale + 0.5f),
            (int) (mView.getMeasuredHeight() * appScale + 0.5f),
            viewVisibility, insetsPending ? RELAYOUT_INSETS_PENDING : 0,
            mWinFrame, mPendingOverscanInsets, mPendingContentInsets,
            mPendingVisibleInsets, mPendingStableInsets,
            mPendingOutsets, mPendingBackDropFrame,
            mPendingDisplayCutout, mPendingMergedConfiguration,
            mSurfaceControl,  // 输出参数：SurfaceControl
            mTempInsets);
    
    if (mSurfaceControl.isValid()) {
        // 通过SurfaceControl创建本地Surface
        mSurface.copyFrom(mSurfaceControl);
    }
}
```

#### 阶段二：WMS通过SurfaceControl创建SurfaceFlinger中的Layer

WindowManagerService收到relayout请求后，会为窗口创建对应的SurfaceControl，并最终在SurfaceFlinger中创建Layer：

```java
// frameworks/base/services/core/java/com/android/server/wm/WindowStateAnimator.java
SurfaceControl createSurfaceLocked(int windowType, int ownerUid) {
    // 构建SurfaceControl.Builder
    final SurfaceControl.Builder b = mService.makeSurfaceBuilder(mSession)
            .setName(attrs.getTitle().toString())
            .setBufferSize(mTmpSize.x, mTmpSize.y)
            .setFormat(attrs.format)
            .setFlags(flags)
            .setMetadata(windowType, ownerUid);
    
    // 创建SurfaceControl，这会触发SurfaceFlinger创建对应的Layer
    mSurfaceControl = b.build();
    return mSurfaceControl;
}
```

SurfaceControl的创建最终通过Binder调用到达SurfaceFlinger：

```cpp
// frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
status_t SurfaceFlinger::createLayer(const String8& name, 
                                     const sp<Client>& client,
                                     uint32_t w, uint32_t h, 
                                     PixelFormat format,
                                     uint32_t flags,
                                     sp<IBinder>* handle,
                                     sp<IGraphicBufferProducer>* gbp) {
    sp<Layer> layer;
    
    switch (flags & ISurfaceComposerClient::eFXSurfaceMask) {
        case ISurfaceComposerClient::eFXSurfaceBufferQueue:
            // 创建BufferQueueLayer（最常见的类型）
            result = createBufferQueueLayer(client, name, w, h, 
                                           flags, format, handle, gbp, &layer);
            break;
        case ISurfaceComposerClient::eFXSurfaceBufferState:
            // 创建BufferStateLayer
            result = createBufferStateLayer(client, name, w, h, 
                                           flags, handle, &layer);
            break;
    }
    
    // 将Layer添加到当前显示状态
    mCurrentState.layersSortedByZ.add(layer);
    return result;
}
```

#### 阶段三：Surface对象跨进程传递给应用端

SurfaceControl创建完成后，通过Binder序列化机制将相关信息传递回应用进程。应用端的ViewRootImpl通过`mSurface.copyFrom(mSurfaceControl)`获取可用于渲染的Surface对象：

```java
// frameworks/base/core/java/android/view/Surface.java
public void copyFrom(SurfaceControl other) {
    if (other == null) {
        throw new IllegalArgumentException("other must not be null");
    }
    
    long surfaceControlPtr = other.mNativeObject;
    long newNativeObject = nativeGetFromSurfaceControl(surfaceControlPtr);
    
    synchronized (mLock) {
        // 释放旧的Native Surface
        if (mNativeObject != 0) {
            nativeRelease(mNativeObject);
        }
        // 设置新的Native Surface
        setNativeObjectLocked(newNativeObject);
    }
}
```

### 1.4 Surface与Window的一一对应关系

在Android图形系统中，**每个Window都拥有且仅拥有一个主Surface**。这种一一对应关系体现在以下层面：

**应用层**：每个Activity对应一个PhoneWindow，PhoneWindow持有DecorView，DecorView的渲染通过ViewRootImpl关联的Surface进行。

**系统服务层**：WindowManagerService为每个WindowState维护一个WindowStateAnimator，后者持有对应的SurfaceControl。

**合成层**：SurfaceFlinger为每个Surface创建一个Layer，参与最终的屏幕合成。

```
┌─────────────────────────────────────────────────────────────────┐
│                         Application Process                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Activity   │    │ PhoneWindow │    │  DecorView  │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         │                  │                  │                │
│         │                  │           ┌──────┴──────┐         │
│         │                  │           │ ViewRootImpl│         │
│         │                  │           └──────┬──────┘         │
│         │                  │                  │                │
│         │                  │           ┌──────┴──────┐         │
│         │                  │           │   Surface   │◄────────┼──┐
│         │                  │           └─────────────┘         │  │
└─────────┼──────────────────┼──────────────────┼────────────────┘  │
          │                  │                  │                   │
          ▼                  ▼                  ▼                   │
┌─────────────────────────────────────────────────────────────────┐│
│                    WindowManagerService                         ││
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐    ││
│  │ WindowState │────│WindowState  │────│  SurfaceControl  │────┼┘
│  │             │    │  Animator   │    │                  │    │
│  └─────────────┘    └─────────────┘    └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SurfaceFlinger                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Layer     │    │ BufferQueue │    │GraphicBuffer│         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.5 ANativeWindow接口：Surface作为Native层图形接口的统一抽象

ANativeWindow是Android定义的Native层窗口抽象接口，它使得OpenGL ES、EGL、Vulkan等图形API能够以统一的方式与Android窗口系统交互。Surface类继承自ANativeWindow，实现了其定义的所有接口：

```cpp
// frameworks/native/libs/nativewindow/include/system/window.h
struct ANativeWindow {
    // 查询窗口属性
    int (*query)(const struct ANativeWindow* window, int what, int* value);
    
    // 执行窗口操作
    int (*perform)(struct ANativeWindow* window, int operation, ...);
    
    // 获取一个空闲的缓冲区用于渲染
    int (*dequeueBuffer)(struct ANativeWindow* window, 
                         struct ANativeWindowBuffer** buffer, int* fenceFd);
    
    // 将渲染完成的缓冲区提交回队列
    int (*queueBuffer)(struct ANativeWindow* window, 
                       struct ANativeWindowBuffer* buffer, int fenceFd);
    
    // 取消已获取但未使用的缓冲区
    int (*cancelBuffer)(struct ANativeWindow* window, 
                        struct ANativeWindowBuffer* buffer, int fenceFd);
};
```

Surface通过hook函数实现ANativeWindow接口：

```cpp
// frameworks/native/libs/gui/Surface.cpp
int Surface::hook_dequeueBuffer(ANativeWindow* window,
                                ANativeWindowBuffer** buffer, 
                                int* fenceFd) {
    Surface* c = getSelf(window);
    return c->dequeueBuffer(buffer, fenceFd);
}

int Surface::dequeueBuffer(android_native_buffer_t** buffer, int* fenceFd) {
    // 通过IGraphicBufferProducer接口从BufferQueue获取缓冲区
    status_t result = mGraphicBufferProducer->dequeueBuffer(
            &buf, &fence, reqWidth, reqHeight, reqFormat, reqUsage,
            &mBufferAge, enableFrameTimestamps ? &mFrameEventHistory : nullptr);
    
    // 将BufferSlot中的GraphicBuffer映射到本地
    sp<GraphicBuffer>& gbuf(mSlots[buf].buffer);
    *buffer = gbuf.get();
    
    if (fence != nullptr && fence->isValid()) {
        *fenceFd = fence->dup();
    } else {
        *fenceFd = -1;
    }
    
    return OK;
}
```

这种设计使得EGL可以通过标准接口使用Surface作为渲染目标：

```cpp
// 创建EGLSurface时，传入Surface（ANativeWindow）
EGLSurface eglSurface = eglCreateWindowSurface(
    eglDisplay, 
    eglConfig, 
    (EGLNativeWindowType)surface,  // Surface as ANativeWindow
    nullptr
);
```

---

## 2. 普通View的渲染路径

### 2.1 完整数据流解析

普通View的渲染是Android UI系统最核心的渲染路径。当一个View需要重绘时，会经历以下完整的数据流转过程：

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              应用进程                                     │
│                                                                          │
│  View.draw()                                                             │
│      │                                                                   │
│      ▼                                                                   │
│  Canvas.drawXxx()  ──────────────────┐                                   │
│      │                               │                                   │
│      ▼                               ▼                                   │
│  RecordingCanvas              DisplayListCanvas                          │
│      │                               │                                   │
│      ▼                               ▼                                   │
│  DisplayList / RenderNode (绘制命令录制)                                  │
│      │                                                                   │
│      │ syncFrameState()                                                  │
│      ▼                                                                   │
│  RenderThread (独立渲染线程)                                              │
│      │                                                                   │
│      ▼                                                                   │
│  CanvasContext::draw()                                                   │
│      │                                                                   │
│      ▼                                                                   │
│  OpenGL ES / Vulkan / SkiaGL / SkiaVulkan                                │
│      │                                                                   │
│      ▼                                                                   │
│  GPU渲染到GraphicBuffer                                                  │
│      │                                                                   │
│      ▼                                                                   │
│  Surface.queueBuffer() ─────────────────────────────────────────────────┼──┐
│                                                                          │  │
└──────────────────────────────────────────────────────────────────────────┘  │
                                                                              │
┌──────────────────────────────────────────────────────────────────────────┐  │
│                           SurfaceFlinger进程                             │  │
│                                                                          │  │
│  BufferQueue.acquireBuffer() ◄─────────────────────────────────────────────┘
│      │                                                                   │
│      ▼                                                                   │
│  Layer合成准备                                                           │
│      │                                                                   │
│      ▼                                                                   │
│  HWC (Hardware Composer) 合成                                            │
│      │                                                                   │
│      ├──► HWC硬件合成路径 ──────────────────┐                            │
│      │                                      │                            │
│      └──► GPU合成路径（Fallback）──────────┐│                            │
│                                           ││                            │
│                                           ▼▼                            │
│                                      Display输出                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

让我们详细分析每个阶段：

#### 阶段一：View.draw() 触发绘制

当View需要重绘时（调用invalidate()或requestLayout()），ViewRootImpl会在下一个Vsync信号到来时开始绘制流程：

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
void doTraversal() {
    // ...
    performTraversals();
}

private void performTraversals() {
    // 1. Measure阶段
    performMeasure(childWidthMeasureSpec, childHeightMeasureSpec);
    
    // 2. Layout阶段  
    performLayout(lp, mWidth, mHeight);
    
    // 3. Draw阶段
    performDraw();
}

private void performDraw() {
    // 获取ThreadedRenderer（硬件加速渲染器）
    final boolean fullRedrawNeeded = mFullRedrawNeeded;
    
    if (mAttachInfo.mThreadedRenderer != null && mAttachInfo.mThreadedRenderer.isEnabled()) {
        // 硬件加速路径
        mAttachInfo.mThreadedRenderer.draw(mView, mAttachInfo, this);
    } else {
        // 软件渲染路径
        drawSoftware(surface, mAttachInfo, ...);
    }
}
```

#### 阶段二：Canvas录制绘制命令到DisplayList

在硬件加速开启的情况下，View的绘制命令不会直接执行，而是被录制到DisplayList（RenderNode）中：

```java
// frameworks/base/core/java/android/view/View.java
public void draw(Canvas canvas) {
    // 1. 绘制背景
    drawBackground(canvas);
    
    // 2. 绘制内容
    onDraw(canvas);
    
    // 3. 绘制子View
    dispatchDraw(canvas);
    
    // 4. 绘制前景和滚动条
    onDrawForeground(canvas);
}

// frameworks/base/graphics/java/android/graphics/RenderNode.java
public class RenderNode {
    // 获取用于录制DisplayList的Canvas
    public RecordingCanvas beginRecording(int width, int height) {
        // 返回RecordingCanvas，所有绑制操作会被录制
        return RecordingCanvas.obtain(this, width, height);
    }
    
    // 结束录制
    public void endRecording() {
        // DisplayList录制完成，可以提交给RenderThread
    }
}
```

#### 阶段三：RenderThread执行GPU渲染

ThreadedRenderer将录制好的DisplayList同步给RenderThread，由RenderThread负责实际的GPU渲染：

```cpp
// frameworks/base/libs/hwui/renderthread/RenderThread.cpp
void RenderThread::threadLoop() {
    while (true) {
        // 等待并处理任务
        mQueue.waitForWork();
        
        while (auto work = mQueue.pop()) {
            work->run();  // 执行渲染任务
        }
    }
}

// frameworks/base/libs/hwui/renderthread/CanvasContext.cpp
void CanvasContext::draw() {
    // 1. 从Surface获取GraphicBuffer
    Frame frame = mRenderPipeline->getFrame();
    
    // 2. 执行DisplayList中的绘制命令
    bool drew = mRenderPipeline->draw(frame, ...
    
    // 3. 将渲染结果提交到BufferQueue
    mRenderPipeline->swapBuffers(frame, drew, ...
}
```

#### 阶段四：BufferQueue数据流转

渲染完成的GraphicBuffer通过BufferQueue传递给SurfaceFlinger：

```cpp
// frameworks/native/libs/gui/BufferQueueProducer.cpp
status_t BufferQueueProducer::queueBuffer(int slot,
                                          const QueueBufferInput& input,
                                          QueueBufferOutput* output) {
    // 将Buffer标记为QUEUED状态
    mSlots[slot].mBufferState.queue();
    
    // 更新Buffer的元数据（时间戳、裁剪区域等）
    mSlots[slot].mTimestamp = timestamp;
    mSlots[slot].mCrop = crop;
    mSlots[slot].mTransform = transform;
    
    // 通知Consumer有新Buffer可用
    frameAvailableListener->onFrameAvailable(item);
    
    return NO_ERROR;
}
```

### 2.2 整个Window共享同一个Surface

一个非常重要的设计原则是：**整个Window（即整个View树）共享同一个Surface**。这意味着：

- DecorView及其所有子View的绘制内容都会渲染到同一个GraphicBuffer上
- 不同View之间没有独立的缓冲区，它们共享同一个画布
- 这种设计简化了合成流程，但也意味着单个View的更新会导致整个Surface的重绘（通过脏区域优化可以减少实际绘制量）

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
public final class ViewRootImpl implements ViewParent {
    // 整个View树共享的Surface
    final Surface mSurface = new Surface();
    
    // DecorView是整个View树的根
    View mView;  // DecorView
    
    // 硬件加速渲染器，使用mSurface进行渲染
    ThreadedRenderer mThreadedRenderer;
}
```

### 2.3 所有普通View都绘制到同一个GraphicBuffer上

当View树进行遍历绘制时，所有普通View的绘制命令最终都会作用于同一个GraphicBuffer：

```java
// 简化的绘制流程
class ViewRootImpl {
    void performDraw() {
        // 从Surface获取Canvas（对应一个GraphicBuffer）
        Canvas canvas = mSurface.lockHardwareCanvas();
        
        // 整个View树绘制到这个Canvas上
        mView.draw(canvas);  // DecorView.draw()
                             //   └─ child1.draw(canvas)
                             //   └─ child2.draw(canvas)
                             //   └─ ...所有子View
        
        // 提交到BufferQueue
        mSurface.unlockCanvasAndPost(canvas);
    }
}
```

### 2.4 ViewRootImpl如何管理Surface的生命周期

ViewRootImpl负责管理Surface的完整生命周期，包括创建、更新和销毁：

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java

// Surface创建/更新
private int relayoutWindow(...) {
    int relayoutResult = mWindowSession.relayout(..., mSurfaceControl, ...);
    
    if (mSurfaceControl.isValid()) {
        // Surface有效，复制到mSurface
        mSurface.copyFrom(mSurfaceControl);
        
        if (mAttachInfo.mThreadedRenderer != null) {
            // 通知渲染器Surface已更新
            mAttachInfo.mThreadedRenderer.updateSurface(mSurface);
        }
    }
    return relayoutResult;
}

// Surface销毁
void destroySurface() {
    if (mSurfaceControl != null) {
        mSurface.release();
        mSurfaceControl.release();
        mSurfaceControl = null;
    }
}

// Activity暂停/停止时
void windowFocusChanged(boolean hasFocus, boolean inTouchMode) {
    if (!hasFocus) {
        // 可能触发Surface的回收
    }
}
```

---

## 3. SurfaceView的独立Surface机制

### 3.1 SurfaceView的设计动机

SurfaceView是Android提供的一个特殊View，它的设计初衷是解决普通View渲染的以下限制：

**主线程渲染瓶颈**：普通View的绘制发生在UI线程，复杂的渲染逻辑会阻塞UI响应。

**帧率同步限制**：普通View的绘制与Vsync同步，无法实现超过屏幕刷新率的渲染。

**灵活性不足**：普通View必须通过Android的Canvas API绑制，无法直接使用OpenGL ES等高性能图形API。

SurfaceView通过拥有独立的Surface来解决这些问题，使得复杂的图形渲染（如视频播放、相机预览、游戏）可以在独立的线程中进行，不受主线程和View系统的限制。

### 3.2 SurfaceView拥有独立的Surface和BufferQueue

与普通View共享Window的Surface不同，SurfaceView创建并管理自己独立的Surface：

```java
// frameworks/base/core/java/android/view/SurfaceView.java
public class SurfaceView extends View {
    // SurfaceView自己的Surface，独立于主窗口Surface
    final Surface mSurface = new Surface();
    
    // Surface控制器
    SurfaceControl mSurfaceControl;
    SurfaceControl mBackgroundControl;
    
    // Surface回调接口
    SurfaceHolder.Callback mSurfaceHolderCallback;
    
    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        // 请求创建独立Surface
        getViewRootImpl().addSurfaceView(this);
    }
    
    // 创建独立Surface的核心逻辑
    protected void updateSurface() {
        if (mSurfaceControl == null) {
            // 创建SurfaceControl
            mSurfaceControl = new SurfaceControl.Builder(mSession)
                    .setName(getClass().getName())
                    .setBufferSize(mSurfaceWidth, mSurfaceHeight)
                    .setFormat(mRequestedFormat)
                    .setParent(viewRoot.getSurfaceControl())  // 设置父Surface
                    .build();
        }
        
        // 从SurfaceControl获取Surface
        mSurface.copyFrom(mSurfaceControl);
    }
}
```

独立的BufferQueue架构示意：

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用进程                                  │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                    Window/DecorView                       │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │  │
│   │  │  Button  │  │ TextView │  │     SurfaceView      │   │  │
│   │  └──────────┘  └──────────┘  │  ┌────────────────┐  │   │  │
│   │       │             │        │  │ 独立Surface    │  │   │  │
│   │       │             │        │  │ 独立BufferQueue│  │   │  │
│   │       ▼             ▼        │  └───────┬────────┘  │   │  │
│   │  ┌─────────────────────┐    └───────────┼───────────┘   │  │
│   │  │   主窗口Surface     │                │               │  │
│   │  │   主窗口BufferQueue │                │               │  │
│   │  └──────────┬──────────┘                │               │  │
│   └─────────────┼───────────────────────────┼───────────────┘  │
│                 │                           │                   │
└─────────────────┼───────────────────────────┼───────────────────┘
                  │                           │
                  ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SurfaceFlinger                              │
│   ┌────────────────────┐    ┌────────────────────┐              │
│   │   主窗口 Layer     │    │  SurfaceView Layer  │              │
│   └────────────────────┘    └────────────────────┘              │
│                  │                           │                   │
│                  └───────────┬───────────────┘                   │
│                              ▼                                   │
│                      HWC合成输出                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 SurfaceView的Z-ordering

SurfaceView的独立Surface需要与主窗口Surface进行Z轴排序。默认情况下，SurfaceView的Surface位于主窗口Surface之下，通过"挖洞"（punch-through）机制显示：

```java
// frameworks/base/core/java/android/view/SurfaceView.java

// 默认情况：SurfaceView在主窗口之下
public SurfaceView(Context context) {
    super(context);
    // 默认Z-order在窗口之下
    mSubLayer = APPLICATION_MEDIA_SUBLAYER;
}

// 设置Z-order在窗口之上
public void setZOrderOnTop(boolean onTop) {
    if (onTop) {
        mSubLayer = APPLICATION_MEDIA_OVERLAY_SUBLAYER;
    } else {
        mSubLayer = APPLICATION_MEDIA_SUBLAYER;
    }
    mLayout.onTop = onTop;
}

// 设置Z-order在媒体层之上
public void setZOrderMediaOverlay(boolean isMediaOverlay) {
    mSubLayer = isMediaOverlay 
            ? APPLICATION_MEDIA_OVERLAY_SUBLAYER 
            : APPLICATION_MEDIA_SUBLAYER;
}
```

挖洞机制的工作原理：

```
┌─────────────────────────────────────────────────────┐
│              主窗口Surface（上层）                   │
│   ┌─────────────┐                                   │
│   │   Button    │                                   │
│   └─────────────┘                                   │
│                    ┌─────────────────────┐          │
│                    │ 透明区域（挖洞）    │          │
│                    │                     │          │
│                    └─────────────────────┘          │
│   ┌─────────────┐                                   │
│   │   TextView  │                                   │
│   └─────────────┘                                   │
└─────────────────────────────────────────────────────┘
                     │
                     │ 透明区域可见下层
                     ▼
┌─────────────────────────────────────────────────────┐
│          SurfaceView Surface（下层）                │
│                    ┌─────────────────────┐          │
│                    │   视频内容显示      │          │
│                    │                     │          │
│                    └─────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

### 3.4 SurfaceHolder接口

SurfaceHolder是应用访问SurfaceView的Surface的标准接口：

```java
// frameworks/base/core/java/android/view/SurfaceHolder.java
public interface SurfaceHolder {
    // 获取Surface对象
    Surface getSurface();
    
    // 软件渲染接口
    Canvas lockCanvas();
    Canvas lockCanvas(Rect dirty);
    void unlockCanvasAndPost(Canvas canvas);
    
    // 硬件渲染接口（获取Surface后使用EGL）
    Canvas lockHardwareCanvas();
    
    // 设置Surface参数
    void setType(int type);
    void setFixedSize(int width, int height);
    void setFormat(int format);
    
    // 生命周期回调
    void addCallback(Callback callback);
    void removeCallback(Callback callback);
    
    interface Callback {
        void surfaceCreated(SurfaceHolder holder);
        void surfaceChanged(SurfaceHolder holder, int format, int width, int height);
        void surfaceDestroyed(SurfaceHolder holder);
    }
}
```

软件渲染使用示例：

```java
public class MySurfaceView extends SurfaceView implements SurfaceHolder.Callback {
    private Thread renderThread;
    private boolean running;
    
    public MySurfaceView(Context context) {
        super(context);
        getHolder().addCallback(this);
    }
    
    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        running = true;
        renderThread = new Thread(() -> {
            while (running) {
                // 获取Canvas
                Canvas canvas = holder.lockCanvas();
                if (canvas != null) {
                    try {
                        // 绑制内容
                        canvas.drawColor(Color.BLACK);
                        canvas.drawCircle(100, 100, 50, paint);
                    } finally {
                        // 提交
                        holder.unlockCanvasAndPost(canvas);
                    }
                }
            }
        });
        renderThread.start();
    }
    
    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        running = false;
        // 等待渲染线程结束
    }
}
```

硬件渲染（OpenGL ES）使用示例：

```java
public class GLSurfaceViewRenderer implements SurfaceHolder.Callback {
    private EGLDisplay eglDisplay;
    private EGLSurface eglSurface;
    private EGLContext eglContext;
    
    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        // 初始化EGL
        eglDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
        EGL14.eglInitialize(eglDisplay, null, 0, null, 0);
        
        // 选择配置
        int[] configAttribs = { /* ... */ };
        EGLConfig[] configs = new EGLConfig[1];
        EGL14.eglChooseConfig(eglDisplay, configAttribs, 0, configs, 0, 1, null, 0);
        
        // 创建EGLSurface，使用SurfaceHolder的Surface
        eglSurface = EGL14.eglCreateWindowSurface(
            eglDisplay, configs[0], 
            holder.getSurface(),  // 使用SurfaceView的Surface
            null, 0
        );
        
        // 创建EGLContext
        int[] contextAttribs = { EGL14.EGL_CONTEXT_CLIENT_VERSION, 3, EGL14.EGL_NONE };
        eglContext = EGL14.eglCreateContext(eglDisplay, configs[0], 
                                            EGL14.EGL_NO_CONTEXT, contextAttribs, 0);
        
        // 绑定上下文
        EGL14.eglMakeCurrent(eglDisplay, eglSurface, eglSurface, eglContext);
        
        // 现在可以使用OpenGL ES进行渲染
    }
    
    public void render() {
        // OpenGL ES渲染
        GLES30.glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT);
        
        // 绘制内容...
        
        // 交换缓冲区
        EGL14.eglSwapBuffers(eglDisplay, eglSurface);
    }
}
```

### 3.5 SurfaceView的双Surface架构

SurfaceView内部维护了双Surface架构，用于处理Surface的平滑过渡：

```java
// frameworks/base/core/java/android/view/SurfaceView.java
public class SurfaceView extends View {
    // 当前使用的Surface
    final Surface mSurface = new Surface();
    
    // 过渡期间使用的新Surface
    private SurfaceControl mSurfaceControl;
    private SurfaceControl mBackgroundControl;
    
    // 旧的SurfaceControl，用于过渡动画
    SurfaceControl mDeferredDestroySurfaceControl;
    
    protected void updateSurface() {
        // 当需要重新创建Surface时
        if (creating) {
            // 保存旧的SurfaceControl
            mDeferredDestroySurfaceControl = mSurfaceControl;
            
            // 创建新的SurfaceControl
            mSurfaceControl = new SurfaceControl.Builder(...)
                    .build();
            
            // 新Surface准备好后，销毁旧Surface
            // 这样可以避免闪烁
        }
    }
}
```

### 3.6 SurfaceView vs 普通View的渲染路径对比

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         普通View渲染路径                                 │
│                                                                          │
│  ┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ UI线程  │───>│  View.draw  │───>│ DisplayList │───>│RenderThread │  │
│  └─────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘  │
│       │                                                       │         │
│       │ 阻塞等待Vsync                                         │ GPU渲染  │
│       ▼                                                       ▼         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              主窗口Surface（与所有普通View共享）                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       SurfaceView渲染路径                                │
│                                                                          │
│  ┌─────────────┐                           ┌─────────────────────────┐  │
│  │  独立线程   │──────────────────────────>│  SurfaceView独立Surface │  │
│  │ （可以是任  │    Canvas.lockCanvas()    │  （独立BufferQueue）     │  │
│  │  意线程）   │    或 EGL/OpenGL ES       │                          │  │
│  └─────────────┘                           └─────────────────────────┘  │
│       │                                                                  │
│       │ 不受Vsync限制                                                    │
│       │ 不阻塞UI线程                                                     │
│                                                                          │
│  ┌─────────┐    ┌─────────────┐                                         │
│  │ UI线程  │───>│占位View绘制 │───> 透明区域（挖洞）                    │
│  └─────────┘    └─────────────┘                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.7 SurfaceView的典型使用场景

**视频播放**：MediaPlayer/ExoPlayer将解码后的视频帧直接渲染到SurfaceView的Surface，避免了YUV到RGB转换和View系统的开销。

```java
MediaPlayer player = new MediaPlayer();
player.setSurface(surfaceView.getHolder().getSurface());
player.setDataSource(videoUrl);
player.prepare();
player.start();
```

**相机预览**：Camera2 API可以将预览帧直接输出到SurfaceView，实现高效的实时预览。

```java
CaptureRequest.Builder builder = cameraDevice.createCaptureRequest(
    CameraDevice.TEMPLATE_PREVIEW);
builder.addTarget(surfaceView.getHolder().getSurface());
cameraCaptureSession.setRepeatingRequest(builder.build(), null, null);
```

**游戏渲染**：游戏引擎可以在独立线程中以任意帧率进行渲染，不受系统UI刷新率限制。

### 3.8 SurfaceView的生命周期回调

SurfaceView通过SurfaceHolder.Callback通知应用Surface的状态变化：

```java
public interface SurfaceHolder.Callback {
    /**
     * Surface首次创建时调用
     * 此时可以开始渲染
     */
    void surfaceCreated(SurfaceHolder holder);
    
    /**
     * Surface尺寸或格式改变时调用
     * 需要调整渲染参数
     */
    void surfaceChanged(SurfaceHolder holder, int format, int width, int height);
    
    /**
     * Surface即将销毁时调用
     * 必须在此方法返回前停止所有渲染操作
     * 返回后Surface将不再有效
     */
    void surfaceDestroyed(SurfaceHolder holder);
}
```

---

## 4. TextureView的工作原理

### 4.1 TextureView的设计目标

TextureView是Android 4.0引入的另一种高性能渲染View，它的设计目标是在保持View层级特性的同时支持独立内容源的渲染。与SurfaceView不同，TextureView是一个真正的View，可以像普通View一样进行变换操作。

```java
// frameworks/base/core/java/android/view/TextureView.java
public class TextureView extends View {
    // 内部持有的SurfaceTexture
    private SurfaceTexture mSurface;
    
    // 关联的纹理ID
    private int mNativeTextureId;
    
    // 是否已附加到窗口
    private boolean mOpaque = true;
}
```

### 4.2 SurfaceTexture的角色

SurfaceTexture是TextureView的核心组件，它将BufferQueue中的GraphicBuffer转换为OpenGL ES纹理：

```java
// frameworks/base/graphics/java/android/graphics/SurfaceTexture.java
public class SurfaceTexture {
    // 关联的OpenGL ES纹理ID
    private int mTexName;
    
    // BufferQueue的Producer端
    private long mProducer;  // IGraphicBufferProducer
    
    // BufferQueue的Consumer端
    private long mConsumer;  // IGraphicBufferConsumer
    
    /**
     * 构造函数，创建关联指定纹理的SurfaceTexture
     * @param texName OpenGL ES纹理ID（必须是GL_TEXTURE_EXTERNAL_OES类型）
     */
    public SurfaceTexture(int texName) {
        mTexName = texName;
        nativeInit(false, texName, singleBufferMode, new WeakReference<>(this));
    }
    
    /**
     * 将最新的Buffer内容更新到关联的纹理
     */
    public void updateTexImage() {
        nativeUpdateTexImage();
    }
}
```

SurfaceTexture的内部架构：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SurfaceTexture                                 │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                      BufferQueue                                 │   │
│   │  ┌─────────────┐    ┌──────────────────┐    ┌──────────────┐   │   │
│   │  │  Producer   │───>│  Buffer Slots    │───>│   Consumer   │   │   │
│   │  │ (Surface)   │    │  [0][1][2]...    │    │(Texture更新) │   │   │
│   │  └─────────────┘    └──────────────────┘    └──────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    │ updateTexImage()                    │
│                                    ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │              OpenGL ES External Texture                          │   │
│   │                   (GL_TEXTURE_EXTERNAL_OES)                      │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 TextureView的渲染流程

TextureView的完整渲染流程涉及外部Producer、BufferQueue、SurfaceTexture和View绑制系统：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  外部Producer（Camera/MediaPlayer/自定义渲染）                          │
│                           │                                              │
│                           │ queueBuffer()                                │
│                           ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BufferQueue                                   │   │
│  │              (由SurfaceTexture管理)                              │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│                              │ onFrameAvailable回调                     │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  SurfaceTexture                                  │   │
│  │                                                                   │   │
│  │   updateTexImage() ─────────────────────────────────────────┐    │   │
│  │         │                                                    │    │   │
│  │         │ 将Buffer内容更新到纹理                              │    │   │
│  │         ▼                                                    │    │   │
│  │   GL_TEXTURE_EXTERNAL_OES纹理 ◄──────────────────────────────┘    │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│                              │ TextureView.draw()                       │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     TextureView                                  │   │
│  │                                                                   │   │
│  │   draw() {                                                        │   │
│  │       // 将纹理绘制到View的Canvas上                              │   │
│  │       canvas.drawTexture(mNativeTextureId);                      │   │
│  │   }                                                               │   │
│  │                           │                                       │   │
│  └───────────────────────────┼───────────────────────────────────────┘   │
│                              │                                          │
│                              │ 作为View树的一部分参与正常绘制            │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              主窗口Surface/RenderThread                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

TextureView的绘制实现：

```java
// frameworks/base/core/java/android/view/TextureView.java
@Override
public final void draw(Canvas canvas) {
    // 必须启用硬件加速
    if (!canvas.isHardwareAccelerated()) {
        Log.w(LOG_TAG, "A TextureView or a subclass can only be "
                + "used with hardware acceleration enabled.");
        return;
    }
    
    // 将SurfaceTexture的内容更新到纹理
    mSurface.updateTexImage();
    
    // 获取纹理变换矩阵
    mSurface.getTransformMatrix(mTransformMatrix);
    
    // 使用HardwareLayer绑制纹理内容
    HardwareLayer layer = getHardwareLayer();
    if (layer != null) {
        applyTransformMatrix();
        // 将纹理作为View内容绘制
        canvas.drawTextureLayer(layer);
    }
}
```

### 4.4 TextureView vs SurfaceView的优劣对比

| 特性 | TextureView | SurfaceView |
|------|-------------|-------------|
| **View变换支持** | 完全支持（旋转、缩放、透明度、位移） | 有限支持（Android 7.0+支持同步移动） |
| **动画支持** | 完全支持属性动画 | 不支持（位于独立Layer） |
| **渲染线程** | 依赖主窗口的RenderThread | 可以完全独立的线程 |
| **合成方式** | GPU合成（占用主窗口资源） | 可使用HWC硬件合成 |
| **性能** | 较低（额外的纹理采样和合成） | 较高（独立合成路径） |
| **帧率控制** | 受View刷新限制 | 完全独立 |
| **内存占用** | 额外的纹理内存 | 只有Buffer内存 |
| **硬件加速要求** | 必须开启 | 不强制 |
| **Z-ordering** | 跟随View层级 | 默认在窗口下方 |
| **适用场景** | 需要View变换的视频播放 | 高性能渲染（游戏、相机） |

### 4.5 TextureView需要硬件加速的原因

TextureView必须在硬件加速环境下工作，原因如下：

**SurfaceTexture依赖OpenGL ES**：SurfaceTexture将Buffer转换为OpenGL ES纹理，这需要GPU支持。

**纹理绘制需要GPU**：TextureView的内容是通过绘制OpenGL纹理实现的，软件渲染无法处理。

**性能要求**：将外部Buffer转换为纹理并绘制是GPU密集操作，软件渲染无法满足实时性要求。

```java
// TextureView在draw时检查硬件加速
@Override
public final void draw(Canvas canvas) {
    if (!canvas.isHardwareAccelerated()) {
        // 警告并跳过绘制
        Log.w(LOG_TAG, "A TextureView can only be used with hardware acceleration enabled.");
        return;
    }
    // ...
}
```

---

## 5. Window-Surface架构设计

### 5.1 每个Window对应一个Surface的设计原则

Android图形系统遵循"一个Window一个Surface"的核心设计原则。这种设计带来以下优势：

**清晰的所有权**：每个Window独立管理自己的渲染资源，避免资源竞争。

**简化合成**：SurfaceFlinger可以将每个Surface作为独立的合成单元处理。

**隔离性**：一个Window的渲染问题不会影响其他Window。

**安全性**：Window级别的Surface隔离提供了基本的图形安全边界。

### 5.2 Activity的Window层级

一个典型Activity的Window-Surface层级结构如下：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Activity                                    │
│                                  │                                       │
│                                  │ getWindow()                           │
│                                  ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                          PhoneWindow                               │  │
│  │                                │                                   │  │
│  │                                │ getDecorView()                    │  │
│  │                                ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │                        DecorView                             │  │  │
│  │  │  ┌─────────────────────────────────────────────────────┐    │  │  │
│  │  │  │                    StatusBarStub                     │    │  │  │
│  │  │  └─────────────────────────────────────────────────────┘    │  │  │
│  │  │  ┌─────────────────────────────────────────────────────┐    │  │  │
│  │  │  │                   ContentFrameLayout                 │    │  │  │
│  │  │  │  ┌───────────────────────────────────────────────┐  │    │  │  │
│  │  │  │  │              用户的ContentView                 │  │    │  │  │
│  │  │  │  │           (setContentView设置)                │  │    │  │  │
│  │  │  │  └───────────────────────────────────────────────┘  │    │  │  │
│  │  │  └─────────────────────────────────────────────────────┘    │  │  │
│  │  │  ┌─────────────────────────────────────────────────────┐    │  │  │
│  │  │  │                 NavigationBarStub                    │    │  │  │
│  │  │  └─────────────────────────────────────────────────────┘    │  │  │
│  │  └───────────────────────────────┬─────────────────────────────┘  │  │
│  │                                  │                                 │  │
│  └──────────────────────────────────┼─────────────────────────────────┘  │
│                                     │                                    │
│                                     │ ViewRootImpl管理                   │
│                                     ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         ViewRootImpl                               │  │
│  │                              │                                     │  │
│  │                              │ 关联Surface                         │  │
│  │                              ▼                                     │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │                         Surface                              │  │  │
│  │  │               (Activity的主渲染Surface)                      │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Dialog、PopupWindow、Toast等的Surface关系

不同的窗口类型有不同的Surface管理方式：

**Dialog**：
- 拥有独立的Window（PhoneWindow）
- 通过WindowManager添加，拥有独立的Surface
- 在SurfaceFlinger中是独立的Layer

```java
// Dialog创建Window
Dialog dialog = new Dialog(context);
// 内部创建独立的PhoneWindow和Surface
dialog.show();
```

**PopupWindow**：
- 内部创建PopupDecorView
- 通过WindowManager.addView添加
- 拥有独立的Surface

```java
// PopupWindow添加View
PopupWindow popup = new PopupWindow(contentView, width, height);
popup.showAtLocation(anchor, gravity, x, y);
// 内部调用 mWindowManager.addView(decorView, ...);
```

**Toast**：
- 系统Toast服务管理
- 拥有独立的Surface（由SystemUI进程管理）

### 5.4 多窗口模式下的Surface管理

在分屏或自由窗口模式下，每个Activity仍然保持独立的Surface：

```
┌───────────────────────────────────────────────────────────────────────┐
│                           多窗口模式                                   │
│                                                                        │
│   ┌─────────────────────────┐    ┌─────────────────────────┐         │
│   │      Activity A         │    │      Activity B         │         │
│   │    ┌───────────────┐    │    │    ┌───────────────┐    │         │
│   │    │   Surface A   │    │    │    │   Surface B   │    │         │
│   │    │   Layer A     │    │    │    │   Layer B     │    │         │
│   │    └───────────────┘    │    │    └───────────────┘    │         │
│   └─────────────────────────┘    └─────────────────────────┘         │
│                                                                        │
│   SurfaceFlinger 独立合成每个Surface                                   │
└───────────────────────────────────────────────────────────────────────┘
```

### 5.5 WindowManager的addView/removeView对Surface生命周期的影响

WindowManager的addView和removeView直接影响Surface的创建和销毁：

```java
// WindowManager添加View（创建Surface）
WindowManager wm = (WindowManager) getSystemService(WINDOW_SERVICE);
View view = new View(this);
WindowManager.LayoutParams params = new WindowManager.LayoutParams(
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE);

// 添加View -> 创建ViewRootImpl -> 创建Surface
wm.addView(view, params);

// 移除View -> 销毁Surface -> 释放资源
wm.removeView(view);
```

内部流程：

```java
// WindowManagerGlobal.addView()
public void addView(View view, ViewGroup.LayoutParams params, ...) {
    ViewRootImpl root = new ViewRootImpl(view.getContext(), display);
    
    // ViewRootImpl构造函数中初始化Surface相关对象
    // mSurface = new Surface()
    // mSurfaceControl 等待relayoutWindow时创建
    
    root.setView(view, wparams, panelParentView);
    // setView -> requestLayout -> scheduleTraversals -> relayoutWindow
    // relayoutWindow 中 WMS 创建 SurfaceControl
}

// WindowManagerGlobal.removeView()
public void removeView(View view, boolean immediate) {
    ViewRootImpl root = findViewRootImpl(view);
    root.die(immediate);
    // die -> destroySurface -> mSurface.release()
}
```

### 5.6 SurfaceControl：WMS管理Surface属性的远程句柄

SurfaceControl是WindowManagerService用来管理SurfaceFlinger中Layer属性的远程句柄：

```java
// frameworks/base/core/java/android/view/SurfaceControl.java
public final class SurfaceControl implements Parcelable {
    // Native层SurfaceControl的指针
    private long mNativeObject;
    
    // 构建器模式创建SurfaceControl
    public static class Builder {
        public Builder setName(String name) { ... }
        public Builder setBufferSize(int width, int height) { ... }
        public Builder setFormat(@PixelFormat.Format int format) { ... }
        public Builder setParent(@Nullable SurfaceControl parent) { ... }
        public Builder setFlags(@Flags int flags) { ... }
        
        public SurfaceControl build() {
            // 通过Binder调用SurfaceFlinger创建Layer
            return new SurfaceControl(...);
        }
    }
    
    // Transaction用于批量更新属性
    public static class Transaction {
        public Transaction setLayer(SurfaceControl sc, int z) { ... }
        public Transaction setPosition(SurfaceControl sc, float x, float y) { ... }
        public Transaction setAlpha(SurfaceControl sc, float alpha) { ... }
        public Transaction setMatrix(SurfaceControl sc, float dsdx, float dtdx, 
                                     float dtdy, float dsdy) { ... }
        public Transaction show(SurfaceControl sc) { ... }
        public Transaction hide(SurfaceControl sc) { ... }
        
        public void apply() {
            // 将所有属性变更提交到SurfaceFlinger
            nativeApplyTransaction(mNativeObject, false);
        }
    }
}
```

WMS使用SurfaceControl.Transaction批量更新窗口属性：

```java
// WindowManagerService中的典型使用
SurfaceControl.Transaction t = new SurfaceControl.Transaction();
t.setPosition(surfaceControl, x, y);
t.setLayer(surfaceControl, zOrder);
t.setAlpha(surfaceControl, alpha);
t.show(surfaceControl);
t.apply();  // 提交到SurfaceFlinger
```

---

## 6. 架构总结

### 6.1 整体图形数据流总览

从应用层到显示输出的完整图形数据流：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            应用层                                        │
│                                                                          │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────────┐  │
│   │ 普通View    │   │ SurfaceView │   │      TextureView            │  │
│   │             │   │             │   │                             │  │
│   │ View.draw() │   │ 独立线程    │   │ SurfaceTexture.updateTexImage│  │
│   │      │      │   │ 渲染        │   │            │                │  │
│   │      ▼      │   │      │      │   │            ▼                │  │
│   │ DisplayList │   │      │      │   │     GL纹理绘制              │  │
│   │      │      │   │      │      │   │            │                │  │
│   │      ▼      │   │      │      │   │            │                │  │
│   │RenderThread │   │      │      │   │            │                │  │
│   │      │      │   │      │      │   │            │                │  │
│   └──────┼──────┘   └──────┼──────┘   └────────────┼────────────────┘  │
│          │                 │                       │                    │
│          ▼                 ▼                       ▼                    │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    Surface / BufferQueue                         │  │
│   │   dequeueBuffer() → GPU渲染 → queueBuffer()                      │  │
│   └──────────────────────────────┬──────────────────────────────────┘  │
│                                  │                                      │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │ Binder IPC
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          SurfaceFlinger                                  │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    BufferQueue Consumer                          │  │
│   │                acquireBuffer() 获取Buffer                        │  │
│   └──────────────────────────────┬──────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                        Layer管理                                 │  │
│   │            计算每个Layer的显示区域、Z-order等                    │  │
│   └──────────────────────────────┬──────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │               Hardware Composer (HWC)                            │  │
│   │                                                                   │  │
│   │   ┌─────────────────────┐     ┌─────────────────────┐           │  │
│   │   │   HWC硬件合成路径   │     │   GPU合成路径       │           │  │
│   │   │   （性能最优）      │     │   （Fallback）      │           │  │
│   │   └──────────┬──────────┘     └──────────┬──────────┘           │  │
│   │              │                           │                       │  │
│   │              └─────────────┬─────────────┘                       │  │
│   │                            │                                     │  │
│   └────────────────────────────┼─────────────────────────────────────┘  │
│                                │                                        │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Display                                       │
│                       屏幕显示最终画面                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 不同渲染路径的对比表格

| 特性 | 普通View | SurfaceView | TextureView |
|------|----------|-------------|-------------|
| **Surface所有权** | 共享Window的Surface | 独立Surface | 共享Window的Surface（纹理） |
| **渲染线程** | RenderThread | 任意线程 | RenderThread |
| **BufferQueue** | 共享 | 独立 | 独立（SurfaceTexture管理） |
| **Vsync同步** | 是 | 可选 | 是 |
| **View变换** | 完全支持 | 有限支持 | 完全支持 |
| **属性动画** | 支持 | 不支持 | 支持 |
| **合成方式** | GPU合成 | 可HWC合成 | GPU合成 |
| **性能开销** | 中 | 低 | 高 |
| **硬件加速** | 可选 | 不要求 | 必须 |
| **典型用途** | UI控件 | 视频/相机/游戏 | 需变换的视频 |

### 6.3 选择建议

**使用普通View**：适用于大部分UI场景，简单的绘制需求。

**使用SurfaceView**：
- 高帧率、低延迟渲染需求（如游戏、相机预览）
- 需要独立线程渲染
- 不需要View变换效果

**使用TextureView**：
- 需要对视频内容进行旋转、缩放、淡入淡出等动画
- 视频内容需要与其他View混合绘制
- 可以接受一定的性能损失

理解Surface与BufferQueue的工作机制，是深入掌握Android图形系统、进行性能优化和解决显示问题的基础。通过本章的学习，开发者应能够根据具体场景选择合适的渲染方案，并理解各种方案的底层实现原理。

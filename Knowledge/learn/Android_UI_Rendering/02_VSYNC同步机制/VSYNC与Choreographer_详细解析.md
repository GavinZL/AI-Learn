# VSYNC与Choreographer详细解析

## 概述

VSYNC（Vertical Synchronization，垂直同步）是Android图形系统实现流畅渲染的核心机制。Choreographer作为应用层接收VSYNC信号的"编舞者"，协调着输入处理、动画更新和View绘制的节奏。本文将从AOSP源码角度深入剖析VSYNC信号的产生、分发机制，以及Choreographer的完整工作流程。

---

## 一、VSYNC信号的本质与产生

### 1.1 什么是VSYNC：从CRT到LCD的演变

**VSYNC（Vertical Synchronization）** 的概念起源于CRT（阴极射线管）显示器时代。

#### CRT时代的VSYNC

CRT显示器通过电子束从左到右、从上到下逐行扫描荧光屏来显示图像。当电子束扫描完一帧的最后一行后，需要回到屏幕左上角开始下一帧的扫描，这个过程称为**垂直回扫（Vertical Retrace）**。在垂直回扫期间，显示器会产生一个电信号——这就是VSYNC信号。

```
CRT扫描过程示意：

    ┌──────────────────┐
    │→→→→→→→→→→→→→→→→│  第1行
    │→→→→→→→→→→→→→→→→│  第2行
    │→→→→→→→→→→→→→→→→│  第3行
    │      ...         │
    │→→→→→→→→→→→→→→→→│  第N行（最后一行）
    └──────────────────┘
           ↓
    垂直回扫期间产生VSYNC信号
           ↓
    ┌──────────────────┐
    │→ 开始下一帧扫描   │
```

在CRT时代，如果在扫描过程中更新帧缓冲区的内容，会导致屏幕上半部分显示旧帧、下半部分显示新帧，产生**屏幕撕裂（Tearing）**。因此，VSYNC信号的核心作用是：**通知系统当前帧扫描已完成，可以安全地切换到下一帧的缓冲区**。

#### LCD时代的VSYNC

现代LCD/OLED显示器不再使用电子束扫描，而是通过逐行刷新像素矩阵的方式显示图像。虽然物理原理不同，但显示控制器仍然保留了VSYNC信号的概念，用于：

1. **标记一帧刷新周期的边界**
2. **同步GPU输出与Display读取**
3. **为软件提供稳定的时间基准**

对于60Hz刷新率的显示器，VSYNC信号每16.67ms（1000ms/60）产生一次；90Hz为11.11ms；120Hz为8.33ms。

```
VSYNC信号时序（60Hz）：

    VSYNC信号：  │      │      │      │      │
                ↓      ↓      ↓      ↓      ↓
    时间轴：    0ms   16.6ms  33.3ms 50ms   66.6ms
                ├──────┼──────┼──────┼──────┤
                 Frame1 Frame2 Frame3 Frame4
```

### 1.2 硬件VSYNC：HWComposer产生硬件中断

在Android系统中，**硬件VSYNC信号由Hardware Composer HAL（HWC）产生**。HWC是Android定义的硬件抽象层接口，由各硬件厂商实现，直接与显示控制器硬件交互。

#### HWComposer的VSYNC产生流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Display Hardware                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Display Controller (CRTC)                   │   │
│  │                      │                                │   │
│  │           产生硬件VSYNC中断                            │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │ 硬件中断
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Linux Kernel                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Display Driver (DRM/KMS)                 │   │
│  │                      │                                │   │
│  │       通过eventfd/uevent通知用户空间                    │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │ 
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Hardware Composer HAL                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              HWC2::ComposerCallback                   │   │
│  │                      │                                │   │
│  │    onVsync(display, timestamp, vsyncPeriodNanos)      │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │ Binder调用
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    SurfaceFlinger                            │
│                 HWComposer::vsyncCallback()                  │
└─────────────────────────────────────────────────────────────┘
```

#### AOSP源码分析

在`frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp`中，HWComposer注册了VSYNC回调：

```cpp
// HWComposer注册VSYNC回调
void HWComposer::registerCallback(HWC2::ComposerCallback* callback,
                                   int32_t sequenceId) {
    mCallback = callback;
    // 向HAL注册回调，当硬件VSYNC到达时会调用onVsync
    mComposer->registerCallback(callback);
}

// VSYNC回调处理
void HWComposer::onVsync(hal::HWDisplayId hwcDisplayId, int64_t timestamp) {
    // 通知SurfaceFlinger的Scheduler组件
    mCallback->onVsyncReceived(sequenceId, hwcDisplayId, timestamp, 
                               vsyncPeriodNanos);
}
```

硬件VSYNC的特点是**精确但消耗资源**——每次VSYNC都会触发硬件中断，唤醒CPU处理。因此，Android并不会一直监听硬件VSYNC，而是采用软件模型来预测。

### 1.3 软件VSYNC模拟：DispSync模型

为了减少对硬件VSYNC的依赖，Android引入了**DispSync**组件（Android 10+升级为**VSyncPredictor**），它基于历史硬件VSYNC时间戳，使用**相位锁定环（PLL，Phase-Locked Loop）** 算法预测未来的VSYNC时间点。

#### DispSync的核心思想

```
软件VSYNC预测模型：

历史硬件VSYNC样本：
    HW_VSYNC[0] = T0
    HW_VSYNC[1] = T0 + 16.6ms
    HW_VSYNC[2] = T0 + 33.3ms
    ...
    HW_VSYNC[N] = T0 + N × 16.6ms

基于线性回归计算：
    - 周期（Period）：VSYNC间隔的平均值
    - 相位（Phase）：VSYNC信号的时间偏移
    
预测公式：
    VSYNC_predicted(n) = reference_time + n × period + phase
```

#### VSyncPredictor源码分析

在`frameworks/native/services/surfaceflinger/Scheduler/VSyncPredictor.cpp`中：

```cpp
nsecs_t VSyncPredictor::nextAnticipatedVSyncTimeFrom(nsecs_t timePoint) const {
    std::lock_guard lock(mMutex);
    
    // 使用线性回归模型预测
    auto const [slope, intercept] = getVSyncPredictionModel(lock);
    
    // 计算下一个VSYNC时间点
    auto const [numPeriods, error] = 
        divideAndGetRemainder(timePoint - intercept, slope);
    
    return intercept + (numPeriods + 1) * slope;
}

// 线性回归模型
std::pair<nsecs_t, nsecs_t> VSyncPredictor::getVSyncPredictionModel() const {
    // 使用最小二乘法拟合历史样本
    // slope = 周期，intercept = 相位
    ...
}
```

#### 硬件VSYNC与软件VSYNC的协作

DispSync/VSyncPredictor会定期校准：

1. **开启硬件VSYNC监听**：当预测误差超过阈值时
2. **收集若干样本**：通常6-8个硬件VSYNC时间戳
3. **更新预测模型**：重新计算周期和相位
4. **关闭硬件VSYNC监听**：继续使用软件预测

```
硬件/软件VSYNC协作时序：

状态：    ┃ 校准期 ┃────── 预测期 ──────┃ 校准期 ┃
         ┃        ┃                    ┃        ┃
硬件VSYNC：│ │ │ │ │                    │ │ │ │ │
          ↓ ↓ ↓ ↓ ↓                    ↓ ↓ ↓ ↓ ↓
软件预测：  [收集样本]  ─→预测→预测→预测→  [误差过大,重新校准]
```

### 1.4 VSYNC Offset的概念

**VSYNC Offset（相位偏移）** 是Android图形系统的一个关键优化。它指的是：**软件VSYNC事件相对于硬件VSYNC的时间偏移**。

#### 为什么需要VSYNC Offset？

在一个完整的帧渲染流水线中，存在三个主要阶段：

1. **应用绘制（App）**：CPU执行measure/layout/draw
2. **合成（SurfaceFlinger）**：将多个Surface合成为最终画面
3. **显示（Display）**：将合成后的Buffer送达屏幕

如果三个阶段都使用同一个VSYNC信号触发，会导致不必要的延迟：

```
无Offset情况（延迟为3帧）：

VSYNC:    │       │       │       │       │
          ↓       ↓       ↓       ↓       ↓
App:      [绘制F1]       [绘制F2]       [绘制F3]
SF:               [合成F1]       [合成F2]       
Display:                  [显示F1]       [显示F2]

Frame1从开始绘制到显示：需要等待3个VSYNC周期
```

通过引入VSYNC Offset，可以让各阶段错峰执行，减少整体延迟：

```
有Offset情况（延迟优化）：

VSYNC-hw:     │           │           │           │
              ↓           ↓           ↓           ↓
VSYNC-app:  ↓ (offset=1ms)
VSYNC-sf:       ↓ (offset=6ms)

App:        [──绘制F1──]   [──绘制F2──]
SF:              [──合成F1──]   [──合成F2──]
Display:                  [显示F1]    [显示F2]

优化后：Frame1从开始绘制到显示仅需约1.5个VSYNC周期
```

在AOSP中，这些offset值定义在设备的配置文件中（如`device.mk`），典型值为：
- `vsync_event_phase_offset_ns`：VSYNC-app的偏移（通常1-4ms）
- `sf_vsync_event_phase_offset_ns`：VSYNC-sf的偏移（通常4-6ms）

---

## 二、VSYNC信号的分发机制

### 2.1 DispSync组件的角色

DispSync（Android 10+为VSyncDispatch）是VSYNC信号的**分发中枢**，负责将硬件/预测的VSYNC信号转化为多路软件VSYNC事件，分发给不同的消费者。

```
VSYNC分发架构：

                    ┌─────────────────────┐
                    │   HWComposer        │
                    │  (硬件VSYNC源)       │
                    └──────────┬──────────┘
                               │
                               ↓
                    ┌─────────────────────┐
                    │     DispSync /      │
                    │   VSyncPredictor    │
                    │   (预测 + 分发)      │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ↓                ↓                ↓
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   VSYNC-app     │ │   VSYNC-sf      │ │  VSYNC-appSf    │
    │  (offset=1ms)   │ │  (offset=6ms)   │ │    (备用)       │
    └────────┬────────┘ └────────┬────────┘ └─────────────────┘
             │                   │
             ↓                   ↓
    ┌─────────────────┐ ┌─────────────────┐
    │  EventThread    │ │  EventThread    │
    │   (for App)     │ │   (for SF)      │
    └────────┬────────┘ └────────┬────────┘
             │                   │
             ↓                   ↓
    ┌─────────────────┐ ┌─────────────────┐
    │  Choreographer  │ │ SurfaceFlinger  │
    │    (应用进程)    │ │   (系统服务)     │
    └─────────────────┘ └─────────────────┘
```

### 2.2 VSYNC-app与VSYNC-sf

Android图形系统定义了两路主要的VSYNC信号：

#### VSYNC-app

- **用途**：触发应用层的UI绘制
- **消费者**：Choreographer（通过EventThread分发）
- **时机**：相对硬件VSYNC偏移较小（通常1-4ms）
- **作用**：通知应用"现在可以开始准备下一帧了"

#### VSYNC-sf

- **用途**：触发SurfaceFlinger的合成操作
- **消费者**：SurfaceFlinger主线程
- **时机**：相对硬件VSYNC偏移较大（通常4-6ms）
- **作用**：通知SF"现在可以开始合成了"

#### 两路VSYNC的时序关系

```
一帧的完整时序（60Hz，16.6ms周期）：

时间轴：0ms                           16.6ms                         33.3ms
        │                             │                              │
HW-VSYNC│                             │                              │
        ↓                             ↓                              ↓
VSYNC-app:                            
        ↓(offset=1ms)                 ↓(offset=1ms)
        ├────CPU绘制(~8ms)────┤
                              │
VSYNC-sf:                     ↓(offset=6ms)                ↓(offset=6ms)
                              ├────SF合成(~4ms)────┤
                                                   │
Display:                                           ↓ 显示Frame N
                                                   ├────扫描输出────┤
```

设计意图：
1. **VSYNC-app先到达**：给应用足够时间完成绘制
2. **VSYNC-sf后到达**：确保在合成时应用的Buffer已准备好
3. **流水线化**：App绘制Frame N+1时，SF正在合成Frame N

### 2.3 EventThread的工作原理

EventThread是VSYNC事件分发的核心组件，它负责**等待VSYNC事件并通过BitTube分发给注册的监听者**。

#### EventThread架构

```cpp
// frameworks/native/services/surfaceflinger/Scheduler/EventThread.cpp

class EventThread : public android::EventThread {
    // VSYNC事件源（来自DispSync/VSyncDispatch）
    VSyncSource* mVSyncSource;
    
    // 注册的连接列表
    std::vector<sp<Connection>> mConnections;
    
    // 线程主循环
    std::thread mThread;
    
    // 等待VSYNC的条件变量
    std::condition_variable mCondition;
};
```

#### EventThread工作流程

```
EventThread工作流程：

┌────────────────────────────────────────────────────────────────┐
│                     EventThread主循环                           │
│                                                                │
│   while (true) {                                               │
│       1. 等待下一个VSYNC事件                                     │
│          mCondition.wait() / VSyncSource.await()               │
│                          │                                     │
│                          ↓                                     │
│       2. 收到VSYNC事件                                          │
│          timestamp, vsyncId, deadline                          │
│                          │                                     │
│                          ↓                                     │
│       3. 遍历所有Connection                                     │
│          for (conn : mConnections) {                           │
│              if (conn.waitingForVsync) {                       │
│                  4. 通过BitTube发送事件                          │
│                     conn->postEvent(vsyncEvent);               │
│              }                                                 │
│          }                                                     │
│   }                                                            │
└────────────────────────────────────────────────────────────────┘
```

#### BitTube：跨进程事件传递

BitTube是Android定义的一种轻量级IPC机制，基于**socketpair**实现，用于高效传递小型事件：

```cpp
// frameworks/native/libs/gui/BitTube.cpp

class BitTube {
    // 底层使用socketpair
    int mSendFd;    // 发送端文件描述符
    int mReceiveFd; // 接收端文件描述符
    
    // 发送事件（EventThread端）
    ssize_t sendObjects(void const* events, size_t count, size_t objSize);
    
    // 接收事件（Choreographer端）
    ssize_t recvObjects(void* events, size_t count, size_t objSize);
};
```

应用进程的Choreographer通过持有BitTube的接收端fd，使用`epoll`监听VSYNC事件的到达。

---

## 三、Choreographer完整工作流程

### 3.1 Choreographer的创建和初始化

Choreographer（编舞者）是应用层接收VSYNC信号的核心组件，采用**ThreadLocal单例模式**，确保每个Looper线程拥有独立的Choreographer实例。

#### 单例获取

```java
// frameworks/base/core/java/android/view/Choreographer.java

public final class Choreographer {
    // ThreadLocal存储，每个线程独立实例
    private static final ThreadLocal<Choreographer> sThreadInstance =
            new ThreadLocal<Choreographer>() {
                @Override
                protected Choreographer initialValue() {
                    Looper looper = Looper.myLooper();
                    if (looper == null) {
                        throw new IllegalStateException(
                            "The current thread must have a looper!");
                    }
                    return new Choreographer(looper, VSYNC_SOURCE_APP);
                }
            };
    
    public static Choreographer getInstance() {
        return sThreadInstance.get();
    }
}
```

#### 构造函数初始化

```java
private Choreographer(Looper looper, int vsyncSource) {
    mLooper = looper;
    
    // 1. 创建Handler用于处理消息
    mHandler = new FrameHandler(looper);
    
    // 2. 创建VSYNC事件接收器
    mDisplayEventReceiver = USE_VSYNC 
            ? new FrameDisplayEventReceiver(looper, vsyncSource)
            : null;
    
    // 3. 记录上一帧时间
    mLastFrameTimeNanos = Long.MIN_VALUE;
    
    // 4. 计算帧间隔
    mFrameIntervalNanos = (long)(1000000000 / getRefreshRate());
    
    // 5. 初始化回调队列（4种类型）
    mCallbackQueues = new CallbackQueue[CALLBACK_LAST + 1];
    for (int i = 0; i <= CALLBACK_LAST; i++) {
        mCallbackQueues[i] = new CallbackQueue();
    }
}
```

### 3.2 FrameDisplayEventReceiver：接收VSYNC事件

FrameDisplayEventReceiver是Choreographer接收VSYNC信号的入口，它继承自DisplayEventReceiver：

```java
private final class FrameDisplayEventReceiver extends DisplayEventReceiver
        implements Runnable {
    
    private boolean mHavePendingVsync;
    private long mTimestampNanos;
    private int mFrame;
    private VsyncEventData mLastVsyncEventData = new VsyncEventData();

    @Override
    public void onVsync(long timestampNanos, long physicalDisplayId,
                        int frame, VsyncEventData vsyncEventData) {
        // VSYNC事件到达！
        
        // 1. 记录时间戳
        mTimestampNanos = timestampNanos;
        mFrame = frame;
        mLastVsyncEventData = vsyncEventData;
        
        // 2. 标记有待处理的VSYNC
        mHavePendingVsync = true;
        
        // 3. 发送异步消息，触发doFrame
        Message msg = Message.obtain(mHandler, this);
        msg.setAsynchronous(true);  // 关键：设置为异步消息
        mHandler.sendMessageAtTime(msg, timestampNanos / TimeUtils.NANOS_PER_MS);
    }

    @Override
    public void run() {
        mHavePendingVsync = false;
        // 执行帧处理
        doFrame(mTimestampNanos, mFrame, mLastVsyncEventData);
    }
}
```

#### Native层的VSYNC接收

DisplayEventReceiver的底层通过JNI与SurfaceFlinger的EventThread建立连接：

```cpp
// frameworks/base/core/jni/android_view_DisplayEventReceiver.cpp

class NativeDisplayEventReceiver : public DisplayEventDispatcher {
    // 通过BitTube接收VSYNC事件
    sp<Looper> mMessageQueue;
    
    void dispatchVsync(nsecs_t timestamp, PhysicalDisplayId displayId,
                       uint32_t count, VsyncEventData vsyncEventData) {
        // 回调Java层的onVsync方法
        JNIEnv* env = ...;
        env->CallVoidMethod(mReceiverObj, gDisplayEventReceiverClassInfo.onVsync,
                           timestamp, displayId, count, vsyncEventData);
    }
};
```

### 3.3 Choreographer管理的四种Callback类型

Choreographer维护四个独立的回调队列，按优先级从高到低：

```java
// 回调类型常量
public static final int CALLBACK_INPUT = 0;           // 输入事件
public static final int CALLBACK_ANIMATION = 1;       // 动画
public static final int CALLBACK_INSETS_ANIMATION = 2; // 窗口Insets动画
public static final int CALLBACK_TRAVERSAL = 3;       // View遍历（measure/layout/draw）
private static final int CALLBACK_LAST = CALLBACK_TRAVERSAL;
```

#### 各回调类型的用途

| 类型 | 优先级 | 用途 | 典型调用者 |
|------|--------|------|-----------|
| CALLBACK_INPUT | 最高(0) | 处理输入事件 | InputEventConsistencyVerifier |
| CALLBACK_ANIMATION | 高(1) | ValueAnimator/ObjectAnimator | AnimationHandler |
| CALLBACK_INSETS_ANIMATION | 中(2) | 系统窗口动画（状态栏、导航栏） | InsetsController |
| CALLBACK_TRAVERSAL | 低(3) | View的measure/layout/draw | ViewRootImpl |

#### 为什么这样设计优先级？

1. **输入优先**：用户操作的响应必须最快，否则会感到卡顿
2. **动画次之**：动画需要流畅，但可以稍微延后于输入
3. **Insets动画**：系统UI动画，优先级介于用户动画和绘制之间
4. **绘制最后**：只有在输入处理和动画更新完成后，才能确定最终的绘制内容

### 3.4 请求VSYNC的流程

当应用需要绘制新帧时，需要先请求VSYNC信号：

```java
// Choreographer.java
private void scheduleFrameLocked(long now) {
    if (!mFrameScheduled) {
        mFrameScheduled = true;
        
        if (USE_VSYNC) {
            // 使用VSYNC模式
            if (isRunningOnLooperThreadLocked()) {
                // 当前在Looper线程，直接请求
                scheduleVsyncLocked();
            } else {
                // 不在Looper线程，发消息切换
                Message msg = mHandler.obtainMessage(MSG_DO_SCHEDULE_VSYNC);
                msg.setAsynchronous(true);
                mHandler.sendMessageAtFrontOfQueue(msg);
            }
        } else {
            // 不使用VSYNC，直接发延时消息
            final long nextFrameTime = Math.max(
                    mLastFrameTimeNanos / TimeUtils.NANOS_PER_MS + sFrameDelay, now);
            Message msg = mHandler.obtainMessage(MSG_DO_FRAME);
            msg.setAsynchronous(true);
            mHandler.sendMessageAtTime(msg, nextFrameTime);
        }
    }
}

private void scheduleVsyncLocked() {
    // 调用Native方法请求VSYNC
    mDisplayEventReceiver.scheduleVsync();
}
```

Native层的请求流程：

```cpp
// android_view_DisplayEventReceiver.cpp
void NativeDisplayEventReceiver::scheduleVsync() {
    // 通过EventThread请求下一个VSYNC事件
    status_t status = mReceiver.requestNextVsync();
}
```

```
VSYNC请求流程：

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  应用/Framework  │    │   Choreographer  │    │  DisplayEvent   │
│                 │    │                  │    │    Receiver     │
└────────┬────────┘    └────────┬─────────┘    └────────┬────────┘
         │                      │                       │
         │ postCallback()       │                       │
         │─────────────────────→│                       │
         │                      │                       │
         │                      │ scheduleVsyncLocked() │
         │                      │──────────────────────→│
         │                      │                       │
         │                      │                       │ nativeScheduleVsync()
         │                      │                       │────────────────┐
         │                      │                       │                │
         │                      │                       │←───────────────┘
         │                      │                       │
         │                      │                       │ [等待VSYNC到达]
         │                      │                       │
         │                      │     onVsync()        │
         │                      │←──────────────────────│
         │                      │                       │
         │                      │ doFrame()            │
         │                      │──────────┐           │
         │                      │          │           │
         │    callback.run()    │←─────────┘           │
         │←─────────────────────│                       │
```

### 3.5 doFrame()方法的完整执行过程

doFrame()是Choreographer处理每一帧的核心方法：

```java
void doFrame(long frameTimeNanos, int frame, 
             DisplayEventData displayEventData) {
    final long startNanos;
    final long frameIntervalNanos = mFrameIntervalNanos;
    
    synchronized (mLock) {
        if (!mFrameScheduled) {
            return; // 没有调度帧，直接返回
        }
        
        // 1. 记录预期帧时间
        long intendedFrameTimeNanos = frameTimeNanos;
        startNanos = System.nanoTime();
        
        // 2. 计算掉帧情况
        final long jitterNanos = startNanos - frameTimeNanos;
        if (jitterNanos >= frameIntervalNanos) {
            // 掉帧了！计算掉了多少帧
            final long skippedFrames = jitterNanos / frameIntervalNanos;
            if (skippedFrames >= SKIPPED_FRAME_WARNING_LIMIT) {
                // 掉帧超过30帧，打印警告日志
                Log.i(TAG, "Skipped " + skippedFrames + " frames! " +
                        "The application may be doing too much work on its main thread.");
            }
            // 调整帧时间到最近的VSYNC边界
            final long lastFrameOffset = jitterNanos % frameIntervalNanos;
            frameTimeNanos = startNanos - lastFrameOffset;
        }
        
        // 3. 防止时间回退
        if (frameTimeNanos < mLastFrameTimeNanos) {
            scheduleVsyncLocked();
            return;
        }
        
        // 4. 更新帧信息
        mFrameInfo.setVsync(intendedFrameTimeNanos, frameTimeNanos,
                           displayEventData.preferredFrameTimelineIndex,
                           ...);
        mFrameScheduled = false;
        mLastFrameTimeNanos = frameTimeNanos;
    }
    
    // 5. 记录动画开始
    AnimationUtils.lockAnimationClock(frameTimeNanos / TimeUtils.NANOS_PER_MS);
    
    // 6. 记录Trace
    mFrameInfo.markInputHandlingStart();
    
    // 7. 按优先级执行四类回调
    doCallbacks(Choreographer.CALLBACK_INPUT, frameTimeNanos, frameIntervalNanos);
    
    mFrameInfo.markAnimationsStart();
    doCallbacks(Choreographer.CALLBACK_ANIMATION, frameTimeNanos, frameIntervalNanos);
    doCallbacks(Choreographer.CALLBACK_INSETS_ANIMATION, frameTimeNanos, frameIntervalNanos);
    
    mFrameInfo.markPerformTraversalsStart();
    doCallbacks(Choreographer.CALLBACK_TRAVERSAL, frameTimeNanos, frameIntervalNanos);
    
    // 8. 执行提交回调（用于诊断）
    doCallbacks(Choreographer.CALLBACK_COMMIT, frameTimeNanos, frameIntervalNanos);
    
    // 9. 解锁动画时钟
    AnimationUtils.unlockAnimationClock();
}
```

#### doCallbacks()的执行逻辑

```java
void doCallbacks(int callbackType, long frameTimeNanos, long frameIntervalNanos) {
    CallbackRecord callbacks;
    
    synchronized (mLock) {
        final long now = System.nanoTime();
        // 从队列中提取到期的回调
        callbacks = mCallbackQueues[callbackType].extractDueCallbacksLocked(
                now / TimeUtils.NANOS_PER_MS);
        if (callbacks == null) {
            return;
        }
        mCallbacksRunning = true;
    }
    
    try {
        // 遍历执行所有回调
        for (CallbackRecord c = callbacks; c != null; c = c.next) {
            c.run(frameTimeNanos);
        }
    } finally {
        synchronized (mLock) {
            mCallbacksRunning = false;
            // 回收CallbackRecord到对象池
            recycleCallbacksLocked(callbacks);
        }
    }
}
```

### 3.6 postFrameCallback的使用场景

Choreographer提供了公开API供开发者使用：

```java
// 在下一个VSYNC时执行回调
public void postFrameCallback(FrameCallback callback) {
    postFrameCallbackDelayed(callback, 0);
}

// 在指定延迟后的VSYNC时执行回调
public void postFrameCallbackDelayed(FrameCallback callback, long delayMillis) {
    postCallbackDelayedInternal(CALLBACK_ANIMATION,
            callback, FRAME_CALLBACK_TOKEN, delayMillis);
}
```

**典型使用场景**：

1. **帧率监控**：统计实际帧率
```java
Choreographer.getInstance().postFrameCallback(new FrameCallback() {
    private long lastFrameTimeNanos = 0;
    
    @Override
    public void doFrame(long frameTimeNanos) {
        if (lastFrameTimeNanos != 0) {
            long frameDurationMs = (frameTimeNanos - lastFrameTimeNanos) / 1_000_000;
            Log.d("FPS", "Frame duration: " + frameDurationMs + "ms");
        }
        lastFrameTimeNanos = frameTimeNanos;
        // 继续监听下一帧
        Choreographer.getInstance().postFrameCallback(this);
    }
});
```

2. **精确动画控制**：自定义动画逻辑
3. **性能监控**：检测主线程卡顿

---

## 四、同步屏障（Sync Barrier）机制

### 4.1 MessageQueue的同步屏障概念

同步屏障是Android MessageQueue中的特殊机制，用于**暂时阻塞同步消息，优先处理异步消息**。

#### 同步消息 vs 异步消息

```java
// 普通消息（同步消息）
Message syncMsg = Message.obtain();
handler.sendMessage(syncMsg);

// 异步消息
Message asyncMsg = Message.obtain();
asyncMsg.setAsynchronous(true);  // 标记为异步
handler.sendMessage(asyncMsg);
```

#### 同步屏障的本质

同步屏障是一个**target为null的特殊Message**：

```java
// MessageQueue.java
public int postSyncBarrier() {
    return postSyncBarrier(SystemClock.uptimeMillis());
}

private int postSyncBarrier(long when) {
    synchronized (this) {
        final int token = mNextBarrierToken++;
        // 创建一个target为null的Message
        final Message msg = Message.obtain();
        msg.markInUse();
        msg.when = when;
        msg.arg1 = token;
        // 注意：没有设置msg.target！
        
        // 插入到消息队列
        Message prev = null;
        Message p = mMessages;
        if (when != 0) {
            while (p != null && p.when <= when) {
                prev = p;
                p = p.next;
            }
        }
        if (prev != null) {
            msg.next = p;
            prev.next = msg;
        } else {
            msg.next = p;
            mMessages = msg;
        }
        return token;
    }
}
```

#### 同步屏障的工作原理

```java
// MessageQueue.next() 方法的核心逻辑
Message next() {
    for (;;) {
        synchronized (this) {
            Message msg = mMessages;
            
            // 检查是否遇到同步屏障
            if (msg != null && msg.target == null) {
                // 遇到屏障！跳过所有同步消息，只找异步消息
                do {
                    msg = msg.next;
                } while (msg != null && !msg.isAsynchronous());
            }
            
            if (msg != null) {
                // 找到可处理的消息
                if (now < msg.when) {
                    // 消息还没到时间，计算等待时间
                    nextPollTimeoutMillis = (int) Math.min(msg.when - now, 
                                                           Integer.MAX_VALUE);
                } else {
                    // 取出消息返回
                    mMessages = msg.next;
                    msg.next = null;
                    return msg;
                }
            }
        }
        // 阻塞等待
        nativePollOnce(ptr, nextPollTimeoutMillis);
    }
}
```

```
同步屏障工作示意：

消息队列状态：
    ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐
    │ Sync1 │→ │Barrier│→ │ Sync2 │→ │ Async │→ │ Sync3 │
    │target │   │target │   │target │   │target │   │target │
    │  =A   │   │ =null │   │  =B   │   │  =C   │   │  =D   │
    └───────┘   └───────┘   └───────┘   └───────┘   └───────┘
    
处理顺序：
    1. 处理Sync1（屏障之前的消息）
    2. 遇到Barrier，跳过Sync2、Sync3
    3. 处理Async（异步消息可以穿越屏障）
    4. 移除Barrier后，按序处理Sync2、Sync3
```

### 4.2 为什么UI绘制需要同步屏障

VSYNC信号到达后，UI绘制必须尽快开始执行，不能被其他普通消息阻塞。

考虑以下场景：

```
没有同步屏障的情况：

消息队列：
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ 网络回调消息  │→ │ 数据库查询    │→ │  VSYNC回调   │
    │  (耗时5ms)   │   │  (耗时10ms)  │   │   (绘制)     │
    └──────────────┘   └──────────────┘   └──────────────┘
    
时序：
    VSYNC到达    │          │     实际开始绘制
       ↓        │          │        ↓
       ├────5ms─┼───10ms───┼────────┤
           网络回调    数据库查询    绘制（已经晚了15ms！）
       
结果：严重掉帧
```

```
使用同步屏障后：

消息队列：
    ┌─────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐
    │ Barrier │→ │ 网络回调消息  │→ │ 数据库查询    │→ │ VSYNC回调   │
    │(target= │   │  (同步消息)  │   │  (同步消息)  │   │  (异步消息) │
    │  null)  │   │              │   │              │   │             │
    └─────────┘   └──────────────┘   └──────────────┘   └─────────────┘
    
时序：
    VSYNC到达+设屏障              移除屏障
       ↓                          ↓
       ├────────绘制────────┼───5ms──┼───10ms───┤
            VSYNC回调优先执行    网络回调    数据库查询
       
结果：绘制及时完成，不掉帧
```

### 4.3 ViewRootImpl中同步屏障的使用

#### 设置同步屏障

```java
// ViewRootImpl.java
void scheduleTraversals() {
    if (!mTraversalScheduled) {
        mTraversalScheduled = true;
        
        // 1. 设置同步屏障！
        mTraversalBarrier = mHandler.getLooper().getQueue().postSyncBarrier();
        
        // 2. 发送VSYNC请求，回调是异步消息
        mChoreographer.postCallback(
                Choreographer.CALLBACK_TRAVERSAL,
                mTraversalRunnable,  // 执行performTraversals
                null);
        
        // 3. 通知输入系统
        notifyRendererOfFramePending();
        pokeDrawLockIfNeeded();
    }
}
```

#### 移除同步屏障

```java
void unscheduleTraversals() {
    if (mTraversalScheduled) {
        mTraversalScheduled = false;
        
        // 移除同步屏障
        mHandler.getLooper().getQueue().removeSyncBarrier(mTraversalBarrier);
        
        // 取消Choreographer回调
        mChoreographer.removeCallbacks(
                Choreographer.CALLBACK_TRAVERSAL,
                mTraversalRunnable,
                null);
    }
}

void doTraversal() {
    if (mTraversalScheduled) {
        mTraversalScheduled = false;
        
        // 先移除同步屏障
        mHandler.getLooper().getQueue().removeSyncBarrier(mTraversalBarrier);
        
        // 然后执行绘制
        performTraversals();
    }
}
```

### 4.4 同步屏障泄露的风险和排查

如果同步屏障没有被正确移除，会导致**所有同步消息永远得不到处理**，表现为：
- 点击事件无响应
- Handler.post的Runnable不执行
- 界面看起来"假死"

#### 泄露场景

```java
// 危险代码示例
void scheduleTraversals() {
    mTraversalBarrier = queue.postSyncBarrier();  // 设置屏障
    mChoreographer.postCallback(...);
}

// 如果在performTraversals之前发生异常
// 或者removeCallbacks被意外调用
// 屏障将永远不会被移除！
```

#### 排查方法

1. **日志检查**：搜索`MessageQueue`相关的ANR日志
2. **Dump MessageQueue**：
```java
// 通过反射获取MessageQueue状态
Field messagesField = MessageQueue.class.getDeclaredField("mMessages");
messagesField.setAccessible(true);
Message msg = (Message) messagesField.get(Looper.getMainLooper().getQueue());
while (msg != null) {
    if (msg.target == null) {
        Log.e("Barrier", "Found sync barrier at: " + msg.when);
    }
    msg = msg.next;
}
```

3. **systrace分析**：查看是否有`SyncBarrier`相关的长时间阻塞

---

## 五、CPU/GPU工作时序详解

### 5.1 一帧的完整生命周期

以60Hz刷新率（16.6ms帧预算）为例，一帧的完整生命周期如下：

```
完整帧渲染时序图（60Hz）：

时间轴(ms)：  0      4      8      12     16     20     24     28     32
             │      │      │      │      │      │      │      │      │
HW-VSYNC:    │                     │                     │
             ↓                     ↓                     ↓
VSYNC-app:   ↓(+1ms)               ↓(+1ms)               ↓(+1ms)
             │                     │                     │
VSYNC-sf:         ↓(+6ms)               ↓(+6ms)               ↓(+6ms)
                  │                     │                     │

Frame N的生命周期：
─────────────────────────────────────────────────────────────────────────
阶段1：CPU处理（App主线程 + RenderThread）
       │
       ↓ T0: VSYNC-app到达
       ├─────────── CPU工作 ───────────┤
       │  · measure()                  │
       │  · layout()                   │
       │  · draw() → 录制DisplayList   │
       │  · syncFrameState()           │
       │                               │
       └─ T1: CPU完成（约6-8ms）────────┘
                                       │
阶段2：GPU渲染（RenderThread）          ↓
                                       ├───── GPU工作 ─────┤
                                       │  · 执行OpenGL命令  │
                                       │  · 像素着色        │
                                       │  · 写入Buffer      │
                                       │                   │
                                       └─ T2: GPU完成 ─────┘
                                                           │
阶段3：合成（SurfaceFlinger）                               ↓
                                                           │ VSYNC-sf
                                                           ↓
                                       ├────── SF合成 ──────┤
                                       │  · acquireBuffer() │
                                       │  · HWC合成决策     │
                                       │  · 提交到Display   │
                                       │                   │
                                       └─ T3: 合成完成 ────┘
                                                           │
阶段4：显示输出                                             ↓
                                                           │ 下一个HW-VSYNC
                                                           ↓
                                                   ┌───────────────┐
                                                   │  Display扫描   │
                                                   │   输出Frame N  │
                                                   └───────────────┘
```

### 5.2 流水线视角下的CPU和GPU并行工作

Android采用**流水线（Pipeline）** 架构，使CPU和GPU可以并行工作：

```
三级流水线示意（理想情况）：

VSYNC:    │        │        │        │        │        │
          N       N+1      N+2      N+3      N+4      N+5
          
CPU:      ├─Frame1─┤        ├─Frame3─┤        ├─Frame5─┤
                   ├─Frame2─┤        ├─Frame4─┤        
                   
GPU:               ├─Frame1─┤        ├─Frame3─┤        
                            ├─Frame2─┤        ├─Frame4─┤
                            
SF:                         ├─Frame1─┤        ├─Frame3─┤
                                     ├─Frame2─┤        ├─Frame4─┤
                                     
Display:                             │Frame1  │Frame2  │Frame3  │Frame4
                                     └────────┴────────┴────────┴──────

观察：
- 在VSYNC N+2时刻：
  · CPU正在处理Frame3
  · GPU正在渲染Frame2  
  · SF正在合成Frame1
  · Display正在显示Frame0
  
- 流水线深度：约2-3帧延迟
- CPU/GPU利用率：接近100%
```

### 5.3 Jank产生的时序分析

**Jank（卡顿）** 发生在CPU或GPU无法在一个VSYNC周期内完成工作时：

#### 场景1：CPU超时

```
CPU超时导致的Jank：

VSYNC:    │        │        │        │        │
          N       N+1      N+2      N+3      N+4
          
CPU:      ├────── Frame1（超时）──────┤
                  │                   │
                  │ 应该在这完成      │ 实际完成时间
                  ↓                   ↓
                  
GPU:                                  ├─Frame1─┤
                            （等待CPU）        
                            
Display:          │Frame0  │Frame0  │Frame0  │Frame1
                  └────────┴────────┴────────┴──────
                           ↑        ↑
                         重复显示Frame0两次 = 卡顿！
```

#### 场景2：GPU超时

```
GPU超时导致的Jank：

VSYNC:    │        │        │        │        │
          N       N+1      N+2      N+3      N+4
          
CPU:      ├Frame1─┤├Frame2─┤├Frame3─┤
                   
GPU:      ├────── Frame1（超时）──────┤├Frame2┤
                  │                   │
                  │ Buffer未就绪      │
                  ↓                   ↓
                  
SF:               （无Buffer可合成）  ├Frame1┤
                            
Display:          │Frame0  │Frame0  │Frame0  │Frame1
                  └────────┴────────┴────────┴──────
```

#### 常见导致Jank的原因

**CPU侧**：
- 主线程执行耗时操作（IO、复杂计算）
- 过度绘制（Overdraw）导致measure/layout耗时
- 频繁的内存分配触发GC
- 锁竞争

**GPU侧**：
- 复杂的着色器程序
- 大量透明图层（需要混合）
- 高分辨率纹理
- 过多的draw call

---

## 六、不同刷新率的影响

### 6.1 帧预算对比

| 刷新率 | 帧周期 | 帧预算 | 典型设备 |
|--------|--------|--------|----------|
| 60Hz | 16.67ms | ~10-12ms（留Buffer余量） | 入门/中端手机 |
| 90Hz | 11.11ms | ~7-8ms | 中高端手机 |
| 120Hz | 8.33ms | ~5-6ms | 旗舰手机、游戏手机 |
| 144Hz | 6.94ms | ~4-5ms | 电竞手机 |

```
不同刷新率的帧预算对比：

60Hz (16.6ms):
├─────────────────────────────────────────────────────────────────┤
│         CPU工作         │    GPU工作    │ Buffer │

90Hz (11.1ms):
├──────────────────────────────────────────────┤
│      CPU工作     │  GPU工作  │ Buf │

120Hz (8.3ms):
├──────────────────────────────────┤
│   CPU工作   │ GPU工作 │Buf│

高刷新率要求：
- 更短的CPU处理时间
- 更高效的GPU渲染
- 更少的主线程阻塞
```

### 6.2 可变刷新率（VRR/LTPO）的工作原理

**VRR（Variable Refresh Rate）** 允许显示器根据内容动态调整刷新率，**LTPO（Low Temperature Polycrystalline Oxide）** 是实现VRR的一种显示技术。

#### VRR的核心思想

```
固定刷新率（120Hz）vs 可变刷新率：

固定120Hz - 静止画面仍高频刷新（浪费功耗）：
VSYNC:    │    │    │    │    │    │    │    │
          ├─F1─┼─F1─┼─F1─┼─F1─┼─F1─┼─F2─┼─F2─┤
           8ms  8ms  8ms  8ms  8ms  8ms  8ms
          └─────── 静止画面 ───────┘│变化│
          
可变刷新率 - 静止时降低刷新率：
VSYNC:    │              │              │    │
          ├───── F1 ─────┼───── F1 ─────┼─F2─┤
              30Hz (33ms)    30Hz         120Hz
          └─────── 静止画面 ───────────┘│变化│

优势：
- 静止场景：低至1Hz，极大省电
- 动态场景：自动提升到高刷新率
- 滚动/动画：平滑过渡刷新率
```

#### LTPO技术原理

LTPO结合了LTPS（高速切换）和IGZO（低漏电）两种晶体管技术：

```
LTPO显示面板结构：

┌─────────────────────────────────────┐
│         LTPS晶体管                  │
│    （高迁移率，快速驱动像素）        │
├─────────────────────────────────────┤
│         IGZO晶体管                  │
│    （低漏电，维持像素电荷）          │
├─────────────────────────────────────┤
│         OLED像素层                  │
└─────────────────────────────────────┘

工作模式：
- 高刷新率：LTPS主导，快速刷新
- 低刷新率：IGZO维持电荷，减少刷新
```

### 6.3 Android 11+ 的多刷新率支持

Android 11引入了系统级的多刷新率支持机制：

#### 刷新率策略

```java
// Android系统的刷新率决策因素
enum RefreshRateVote {
    // 应用请求
    APP_REQUEST,          // setFrameRate() API
    
    // 系统策略  
    TOUCH_BOOST,          // 触摸时提升刷新率
    ANIMATION_RUNNING,    // 动画运行中
    LOW_POWER_MODE,       // 省电模式降低刷新率
    
    // 内容特性
    VIDEO_PLAYING,        // 视频播放（匹配视频帧率）
    GAME_RUNNING,         // 游戏运行
}
```

#### SurfaceFlinger的刷新率调度

```cpp
// frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp

struct RefreshRateScore {
    float overallScore;      // 综合评分
    float layerScore;        // 图层需求评分
    float touchBoostScore;   // 触摸加速评分
    float powerScore;        // 功耗评分
};

RefreshRate RefreshRateSelector::selectRefreshRate() {
    // 1. 收集所有图层的刷新率需求
    for (const auto& layer : layers) {
        votes.push_back(layer.getDesiredRefreshRate());
    }
    
    // 2. 考虑系统级约束
    if (isTouchActive) {
        votes.push_back(touchBoostRate);
    }
    if (isLowPowerMode) {
        votes.push_back(lowPowerRate);
    }
    
    // 3. 计算最优刷新率
    return calculateOptimalRate(votes);
}
```

### 6.4 刷新率切换对应用的影响

#### 潜在问题

1. **动画时长不一致**：
```java
// 问题代码：假设固定帧率
void updateAnimation() {
    // 假设每帧16ms，实际可能是8ms或11ms
    position += velocity * 16;  // 错误！
}

// 正确做法：使用实际时间间隔
void updateAnimation(long frameTimeNanos) {
    float deltaSeconds = (frameTimeNanos - lastFrameTime) / 1_000_000_000f;
    position += velocity * deltaSeconds;  // 正确
    lastFrameTime = frameTimeNanos;
}
```

2. **帧率检测失效**：硬编码的帧率阈值不再适用

3. **性能预算变化**：120Hz下需要更高效的代码

### 6.5 setFrameRate() API的使用

Android 11引入了`Surface.setFrameRate()` API，允许应用声明期望的帧率：

```java
// 请求特定帧率
surface.setFrameRate(
    60.0f,                              // 期望帧率
    Surface.FRAME_RATE_COMPATIBILITY_DEFAULT,  // 兼容性
    Surface.CHANGE_FRAME_RATE_ALWAYS    // 切换策略
);

// 视频播放：匹配视频帧率
surface.setFrameRate(
    24.0f,                              // 24fps视频
    Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,  // 固定源帧率
    Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS     // 仅无缝切换
);
```

#### 兼容性参数

```java
// FRAME_RATE_COMPATIBILITY_DEFAULT
// 系统可以选择任何兼容的刷新率（如60fps内容可用60/120Hz）

// FRAME_RATE_COMPATIBILITY_FIXED_SOURCE  
// 内容帧率固定（如视频），系统应选择最接近的刷新率

// CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS
// 仅当切换不会导致闪烁时才切换刷新率

// CHANGE_FRAME_RATE_ALWAYS
// 允许任何刷新率切换（可能短暂黑屏）
```

#### 最佳实践

```java
// 游戏场景：请求最高帧率
if (isHighPerformanceMode) {
    surface.setFrameRate(120f, FRAME_RATE_COMPATIBILITY_DEFAULT,
                         CHANGE_FRAME_RATE_ALWAYS);
}

// 视频场景：匹配视频帧率
surface.setFrameRate(videoFrameRate, FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
                     CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);

// 阅读场景：降低帧率省电
if (isReadingMode) {
    surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_DEFAULT,
                         CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
}
```

---

## 总结

本文深入分析了Android VSYNC同步机制和Choreographer的工作原理：

1. **VSYNC信号**：从CRT时代演变而来，现代LCD/OLED通过HWComposer产生硬件中断，DispSync/VSyncPredictor进行软件预测

2. **信号分发**：DispSync将VSYNC分为VSYNC-app和VSYNC-sf两路，通过EventThread和BitTube分发给应用和SurfaceFlinger

3. **Choreographer**：采用ThreadLocal单例，管理四种优先级的回调队列，协调输入、动画、绘制的执行顺序

4. **同步屏障**：通过target==null的特殊Message，确保VSYNC回调（异步消息）优先于其他同步消息执行

5. **CPU/GPU流水线**：三级流水线架构实现CPU和GPU的并行工作，Jank发生在任一阶段超时

6. **多刷新率适配**：VRR/LTPO技术实现可变刷新率，setFrameRate() API允许应用声明帧率需求

理解这些机制对于开发高性能、流畅的Android应用至关重要，是性能优化和问题排查的基础知识。

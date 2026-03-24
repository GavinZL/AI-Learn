# EGL与OpenGL ES渲染管线详细解析

> 深入剖析EGL作为渲染API与本地窗口系统之间桥梁的工作原理，掌握Android GPU渲染的核心机制

---

## 核心结论（TL;DR）

**EGL是连接OpenGL ES渲染API与Android本地窗口系统的关键桥梁，它解决了跨平台图形渲染的核心问题：如何让与平台无关的渲染代码能够在特定平台的窗口系统上显示。**

1. **EGL是什么**：Khronos定义的渲染API与本地窗口系统之间的接口规范，全称Embedded-System Graphics Library
2. **三大核心组件**：EGLDisplay（显示设备）、EGLSurface（渲染目标）、EGLContext（渲染上下文）
3. **关键作用**：管理渲染上下文、创建渲染表面、处理缓冲区交换、实现OpenGL ES与ANativeWindow的对接
4. **在Android中的位置**：App → OpenGL ES → EGL → ANativeWindow/Surface → BufferQueue → SurfaceFlinger

**关键洞察**：
- EGL类似于"画室管理员"：提供画布（EGLSurface）、画笔状态（EGLContext）、工作台（EGLDisplay）
- OpenGL ES类似于"画家"：在画布上执行实际的绑制操作
- `eglSwapBuffers`是渲染完成后提交帧的关键调用，它触发BufferQueue的dequeue/queue流程

---

## 第一部分：EGL核心概念与定位

### 1.1 EGL的基本定义

**EGL（Embedded-System Graphics Library）** 是由Khronos Group定义的一套接口规范，用于在渲染API（如OpenGL ES、OpenVG）与底层本地平台窗口系统之间建立桥梁。

EGL的核心职责包括：

| 职责 | 说明 |
|------|------|
| **上下文管理** | 创建、销毁和切换OpenGL ES渲染上下文 |
| **表面管理** | 创建可渲染的表面（Window Surface、PBuffer、Pixmap） |
| **缓冲区交换** | 管理前后缓冲区的交换，实现双缓冲/三缓冲 |
| **配置选择** | 查询和选择帧缓冲配置（颜色深度、深度缓冲等） |
| **同步机制** | 提供渲染同步原语（Fence、Sync Object） |

```cpp
// EGL核心数据类型定义（简化）
typedef void *EGLDisplay;    // 显示设备句柄
typedef void *EGLSurface;    // 渲染表面句柄  
typedef void *EGLContext;    // 渲染上下文句柄
typedef void *EGLConfig;     // 帧缓冲配置句柄
```

### 1.2 EGL在Android图形系统中的定位

EGL在Android图形栈中处于承上启下的核心位置，它连接了应用层的渲染API与系统层的窗口管理：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层 (Application)                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │          OpenGL ES / Vulkan 绑制命令                              │   │
│  │          glDrawArrays() / glDrawElements()                       │   │
│  └───────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                      │
│                                  ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         EGL 层                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │ EGLDisplay  │  │ EGLContext  │  │      EGLSurface         │  │   │
│  │  │ (显示设备)   │  │ (渲染上下文) │  │  (渲染目标/画布)         │  │   │
│  │  └─────────────┘  └─────────────┘  └───────────┬─────────────┘  │   │
│  └───────────────────────────────────────────────┼─────────────────┘   │
│                                                  │                      │
│                                                  ▼                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  ANativeWindow / Surface                         │   │
│  │                  (本地窗口抽象接口)                                │   │
│  └───────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                      │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          BufferQueue                                     │
│           (生产者-消费者模型，管理GraphicBuffer)                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SurfaceFlinger                                    │
│                    (系统合成器，负责最终显示)                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 为什么需要EGL

**核心问题**：OpenGL ES是一套跨平台的图形渲染API，但它本身不知道如何在特定平台上创建窗口、管理显示设备。不同操作系统的窗口系统差异巨大：

| 平台 | 窗口系统 | 窗口类型 |
|------|---------|---------|
| Android | SurfaceFlinger | ANativeWindow/Surface |
| iOS | CoreAnimation | CAEAGLLayer |
| Windows | Win32/WGL | HWND |
| Linux | X11/Wayland | Window/wl_surface |

**EGL的解耦设计**：

```
┌─────────────────────────────────────────────────────────────────┐
│                     渲染代码 (跨平台)                             │
│                                                                  │
│   // 这段代码可以在任何支持OpenGL ES的平台运行                     │
│   glClearColor(0.0f, 0.0f, 0.0f, 1.0f);                         │
│   glClear(GL_COLOR_BUFFER_BIT);                                 │
│   glDrawArrays(GL_TRIANGLES, 0, 3);                             │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EGL (抽象层)                                │
│                                                                  │
│   // EGL提供统一的接口，隐藏平台差异                               │
│   eglGetDisplay(EGL_DEFAULT_DISPLAY);                           │
│   eglCreateWindowSurface(display, config, nativeWindow, ...);   │
│   eglSwapBuffers(display, surface);                             │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Android  │    │   iOS    │    │  Linux   │
        │ 实现     │    │  实现    │    │  实现    │
        └──────────┘    └──────────┘    └──────────┘
```

### 1.4 Android中的EGL实现

Android系统通过多层架构实现EGL：

**libEGL.so**：Android的EGL入口库，位于`/system/lib64/libEGL.so`，负责加载和分发调用到具体的GPU驱动实现。

```cpp
// frameworks/native/opengl/libs/EGL/egl.cpp
// libEGL.so 作为分发层，将调用转发到具体驱动

EGLDisplay eglGetDisplay(EGLNativeDisplayType display) {
    // 1. 加载GPU厂商的EGL驱动
    // 2. 调用驱动的eglGetDisplay实现
    return egl_display_t::get(display);
}
```

**GPU驱动实现**：真正的EGL实现由GPU厂商提供：

| GPU厂商 | 驱动库 | 常见设备 |
|--------|--------|---------|
| Qualcomm Adreno | libGLESv2_adreno.so | 高通骁龙系列 |
| ARM Mali | libGLES_mali.so | 三星Exynos、海思麒麟 |
| Imagination PowerVR | libGLESv2_POWERVR.so | 部分联发科芯片 |
| NVIDIA Tegra | libGLESv2_tegra.so | NVIDIA Shield |

**EGL驱动加载流程**：

```
┌─────────────────────────────────────────────────────────────┐
│                        应用调用                              │
│                   eglGetDisplay()                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    libEGL.so (分发层)                        │
│                                                             │
│   1. 读取 /vendor/lib64/egl/egl.cfg                         │
│   2. 加载配置中指定的GPU驱动库                                │
│   3. 获取驱动的函数指针表                                    │
│   4. 转发调用到驱动实现                                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              GPU厂商驱动 (如 libGLESv2_adreno.so)            │
│                                                             │
│   实际执行EGL操作，与GPU硬件交互                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 第二部分：EGL在Android图形栈中的架构层次

### 2.1 完整图形栈层级关系

Android图形系统是一个复杂的多层架构，EGL处于中间核心位置：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              应用层                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Java层API                                                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │ Canvas API   │  │GLSurfaceView │  │      TextureView       │   │ │
│  │  │ (2D绑制)     │  │ (OpenGL ES)  │  │   (SurfaceTexture)     │   │ │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                              渲染API层                                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │ Skia (2D)    │  │ OpenGL ES    │  │       Vulkan           │   │ │
│  │  │              │  │ (3D/2D)      │  │    (下一代3D API)       │   │ │
│  │  └──────────────┘  └──────┬───────┘  └────────────────────────┘   │ │
│  └───────────────────────────┼────────────────────────────────────────┘ │
├───────────────────────────────┼─────────────────────────────────────────┤
│                               ▼            EGL层                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         libEGL.so                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │  EGLDisplay  │  │  EGLContext  │  │      EGLSurface        │   │ │
│  │  │  显示设备抽象 │  │  GL状态容器   │  │   渲染目标抽象          │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────┬─────────────┘   │ │
│  └─────────────────────────────────────────────────┼──────────────────┘ │
├─────────────────────────────────────────────────────┼───────────────────┤
│                                                     ▼    Native窗口层    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │ANativeWindow │  │   Surface    │  │    SurfaceControl      │   │ │
│  │  │ (接口抽象)   │  │ (Producer端) │  │   (属性控制句柄)        │   │ │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                              缓冲区管理层                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │ BufferQueue  │  │GraphicBuffer │  │       Gralloc          │   │ │
│  │  │(生产者-消费者)│  │ (图形缓冲区) │  │   (内存分配HAL)         │   │ │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                              服务层 (system_server / surfaceflinger)     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │SurfaceFlinger│  │   HWComposer │  │    DisplayManager      │   │ │
│  │  │  (合成器)    │  │ (硬件合成)   │  │    (显示管理)          │   │ │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                              HAL层                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │  Gralloc HAL │  │   HWC HAL    │  │     GPU Driver         │   │ │
│  │  │ (内存分配)   │  │(硬件合成接口) │  │   (GPU驱动程序)         │   │ │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                              硬件层                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │     GPU      │  │Display Ctrl  │  │       Memory           │   │ │
│  │  │  (图形处理)  │  │(显示控制器)   │  │   (显存/共享内存)       │   │ │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 EGL与OpenGL ES的关系

**类比理解**：如果把GPU渲染比作绑画，那么：
- **EGL** = 画室管理员（提供画布、管理画笔状态、安排工作台）
- **OpenGL ES** = 画家（在画布上执行实际的绑制操作）
- **EGLDisplay** = 工作室（代表物理显示设备）
- **EGLSurface** = 画布（渲染目标）
- **EGLContext** = 画家的工具箱和当前状态（着色器、纹理、缓冲对象等）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           EGL管理范畴                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      EGLDisplay (工作室)                         │   │
│  │  ┌───────────────────────┐  ┌───────────────────────────────┐  │   │
│  │  │    EGLContext         │  │        EGLSurface             │  │   │
│  │  │    (工具箱/状态)       │  │        (画布)                  │  │   │
│  │  │  ┌─────────────────┐  │  │  ┌───────────────────────┐   │  │   │
│  │  │  │ 当前着色器程序   │  │  │  │  前缓冲区 (显示中)    │   │  │   │
│  │  │  │ 绑定的纹理      │  │  │  │                       │   │  │   │
│  │  │  │ 绑定的VBO/VAO   │  │  │  └───────────────────────┘   │  │   │
│  │  │  │ 视口设置        │  │  │  ┌───────────────────────┐   │  │   │
│  │  │  │ 混合模式        │  │  │  │  后缓冲区 (渲染中)    │   │  │   │
│  │  │  │ 深度测试状态    │  │  │  │                       │   │  │   │
│  │  │  └─────────────────┘  │  │  └───────────────────────┘   │  │   │
│  │  └───────────────────────┘  └───────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    OpenGL ES操作范畴                              │   │
│  │                                                                   │   │
│  │   glClear()        → 清空画布                                     │   │
│  │   glDrawArrays()   → 绑制图形                                     │   │
│  │   glUseProgram()   → 选择着色器（切换画笔）                        │   │
│  │   glBindTexture()  → 绑定纹理（选择颜料）                          │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**关键交互点**：

```cpp
// 1. EGL创建上下文，为OpenGL ES提供执行环境
EGLContext context = eglCreateContext(display, config, EGL_NO_CONTEXT, attribs);

// 2. EGL绑定上下文，使OpenGL ES命令生效
eglMakeCurrent(display, drawSurface, readSurface, context);

// 3. OpenGL ES在上下文中执行绘制
glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
glClear(GL_COLOR_BUFFER_BIT);
glDrawArrays(GL_TRIANGLES, 0, 3);

// 4. EGL交换缓冲区，将渲染结果提交显示
eglSwapBuffers(display, surface);
```

### 2.3 EGL与Surface/ANativeWindow的关系

EGLSurface底层包装了ANativeWindow（即Surface的Native层实现），通过`eglCreateWindowSurface`建立关联：

```cpp
// frameworks/native/opengl/libs/EGL/eglApi.cpp
EGLSurface eglCreateWindowSurface(EGLDisplay dpy, EGLConfig config,
                                   EGLNativeWindowType window,
                                   const EGLint *attrib_list) {
    // window参数就是ANativeWindow*（Surface的Native层）
    // 内部会调用GPU驱动的实现来创建实际的渲染表面
    
    egl_display_ptr dp = validate_display(dpy);
    
    // 验证ANativeWindow有效性
    ANativeWindow* anw = reinterpret_cast<ANativeWindow*>(window);
    
    // 调用驱动层创建Surface
    EGLSurface surface = cnx->egl.eglCreateWindowSurface(
            dp->disp.dpy, config, window, attrib_list);
    
    return surface;
}
```

**Java层到Native层的传递**：

```java
// Android Java层：通过Surface获取ANativeWindow
public class EGL14 {
    public static EGLSurface eglCreateWindowSurface(
            EGLDisplay dpy, EGLConfig config,
            Object win,  // 可以是Surface、SurfaceHolder或SurfaceTexture
            int[] attrib_list, int offset) {
        
        // JNI调用，将Surface转换为ANativeWindow*
        return _eglCreateWindowSurface(dpy, config, win, attrib_list, offset);
    }
}

// JNI实现
static EGLSurface android_eglCreateWindowSurface(
        EGLDisplay dpy, EGLConfig config, jobject win, jintArray attrib_list) {
    
    // 从Java Surface对象获取ANativeWindow
    ANativeWindow* window = ANativeWindow_fromSurface(env, win);
    
    // 调用EGL创建Surface
    EGLSurface surface = eglCreateWindowSurface(dpy, config, window, attribs);
    
    return surface;
}
```

### 2.4 EGL与BufferQueue的交互

`eglSwapBuffers`是EGL与BufferQueue交互的核心函数，它触发了完整的缓冲区流转：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       eglSwapBuffers() 内部流程                           │
│                                                                          │
│   应用线程                                                                │
│       │                                                                  │
│       │ eglSwapBuffers(display, surface)                                 │
│       ▼                                                                  │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    EGL驱动层                                     │   │
│   │                                                                  │   │
│   │   1. 等待GPU完成当前缓冲区的渲染                                   │   │
│   │   2. 调用ANativeWindow->queueBuffer()                            │   │
│   │   3. 调用ANativeWindow->dequeueBuffer() 获取下一个缓冲区          │   │
│   │                                                                  │   │
│   └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     Surface (Producer)                           │   │
│   │                                                                  │   │
│   │   queueBuffer()  → 将渲染完成的Buffer放入队列                     │   │
│   │   dequeueBuffer() → 获取下一个可用的Buffer                        │   │
│   │                                                                  │   │
│   └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                      BufferQueue                                 │   │
│   │                                                                  │   │
│   │   ┌─────┐ ┌─────┐ ┌─────┐                                       │   │
│   │   │ [0] │ │ [1] │ │ [2] │  ... Buffer Slots                     │   │
│   │   │FREE │ │QUEUE│ │ACQU │                                       │   │
│   │   └─────┘ └─────┘ └─────┘                                       │   │
│   │                     │                                            │   │
│   │      onFrameAvailable() 通知Consumer                             │   │
│   │                     │                                            │   │
│   └─────────────────────┼───────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                  SurfaceFlinger (Consumer)                       │   │
│   │                                                                  │   │
│   │   acquireBuffer() → 获取待显示的Buffer                            │   │
│   │   合成 → 与其他Layer合成                                          │   │
│   │   releaseBuffer() → 释放Buffer回BufferQueue                       │   │
│   │                                                                  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**eglSwapBuffers的实现细节**：

```cpp
// frameworks/native/libs/gui/Surface.cpp
// ANativeWindow->queueBuffer 最终调用到这里

status_t Surface::queueBuffer(
        android_native_buffer_t* buffer, int fenceFd) {
    
    // 1. 获取Buffer的slot索引
    int slot = buffer->index;
    
    // 2. 设置Buffer的元数据
    IGraphicBufferProducer::QueueBufferInput input(
            timestamp,
            isAutoTimestamp,
            dataSpace,
            crop,
            scalingMode,
            transform,
            fence);
    
    // 3. 通过Binder调用BufferQueue的queueBuffer
    status_t err = mGraphicBufferProducer->queueBuffer(slot, input, &output);
    
    return err;
}
```

### 2.5 EGL与SurfaceFlinger的协作

EGL与SurfaceFlinger通过BufferQueue间接协作，实现了高效的帧传递：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              协作时序图                                   │
│                                                                          │
│     应用进程                  BufferQueue              SurfaceFlinger    │
│        │                         │                          │           │
│        │                         │                          │           │
│        │ dequeueBuffer()         │                          │           │
│        │────────────────────────>│                          │           │
│        │<────────────────────────│                          │           │
│        │   返回Buffer[0]         │                          │           │
│        │                         │                          │           │
│        │ [GPU渲染到Buffer[0]]    │                          │           │
│        │                         │                          │           │
│        │ queueBuffer()           │                          │           │
│        │────────────────────────>│                          │           │
│        │                         │ onFrameAvailable()       │           │
│        │                         │─────────────────────────>│           │
│        │                         │                          │           │
│        │ dequeueBuffer()         │                          │           │
│        │────────────────────────>│  acquireBuffer()         │           │
│        │<────────────────────────│<─────────────────────────│           │
│        │   返回Buffer[1]         │   返回Buffer[0]          │           │
│        │                         │                          │           │
│        │ [GPU渲染到Buffer[1]]    │      [合成Buffer[0]]      │           │
│        │                         │                          │           │
│        │                         │  releaseBuffer()         │           │
│        │                         │<─────────────────────────│           │
│        │                         │                          │           │
│        │ queueBuffer()           │                          │           │
│        │────────────────────────>│                          │           │
│        │                         │                          │           │
│        ▼                         ▼                          ▼           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 第三部分：EGL关键组件详解

### 3.1 EGLDisplay

**定义**：EGLDisplay代表底层显示设备的抽象，是EGL操作的根对象。所有EGL资源（Context、Surface、Config）都属于某个EGLDisplay。

**获取方式**：

```cpp
// 获取默认显示设备
EGLDisplay display = eglGetDisplay(EGL_DEFAULT_DISPLAY);

// Android中EGL_DEFAULT_DISPLAY通常映射到主显示屏
// 多屏场景下可以使用eglGetPlatformDisplay获取特定显示
```

**初始化**：

```cpp
EGLint major, minor;
if (!eglInitialize(display, &major, &minor)) {
    // 初始化失败处理
    EGLint error = eglGetError();
    // EGL_NOT_INITIALIZED, EGL_BAD_DISPLAY等
}

// 成功后major/minor包含EGL版本号
// 如：major=1, minor=5 表示EGL 1.5
```

**Android中的实现细节**：

```cpp
// frameworks/native/opengl/libs/EGL/egl_display.cpp
class egl_display_t {
    // 内部持有的资源
    DisplayImpl          disp;          // 驱动层Display句柄
    EGLConfig*          configs;        // 可用配置数组
    size_t              numConfigs;     // 配置数量
    
    // 引用的Context和Surface列表
    ObjectList<egl_context_t>  contexts;
    ObjectList<egl_surface_t>  surfaces;
};
```

### 3.2 EGLConfig

**定义**：EGLConfig描述帧缓冲区的配置，包括颜色深度、深度缓冲、模板缓冲、抗锯齿等属性。

**常用属性表**：

| 属性 | 说明 | 典型值 |
|------|------|--------|
| EGL_RED_SIZE | 红色位数 | 8 |
| EGL_GREEN_SIZE | 绿色位数 | 8 |
| EGL_BLUE_SIZE | 蓝色位数 | 8 |
| EGL_ALPHA_SIZE | Alpha位数 | 8 (透明) / 0 (不透明) |
| EGL_DEPTH_SIZE | 深度缓冲位数 | 0 / 16 / 24 |
| EGL_STENCIL_SIZE | 模板缓冲位数 | 0 / 8 |
| EGL_SAMPLE_BUFFERS | 多重采样缓冲数 | 0 / 1 |
| EGL_SAMPLES | 每像素采样数 | 0 / 4 |
| EGL_RENDERABLE_TYPE | 支持的渲染API | EGL_OPENGL_ES2_BIT / EGL_OPENGL_ES3_BIT |

> **注意**：`EGL_OPENGL_ES3_BIT` 在 Android 中定义于 `EGL15`（API 26+），使用 `EGL14` 时应设置 `EGL_OPENGL_ES2_BIT` 并通过 `EGL_CONTEXT_CLIENT_VERSION = 3` 来请求 OpenGL ES 3.x 上下文。
| EGL_SURFACE_TYPE | 支持的Surface类型 | EGL_WINDOW_BIT / EGL_PBUFFER_BIT |
| EGL_CONFIG_CAVEAT | 配置限制 | EGL_NONE / EGL_SLOW_CONFIG |

**选择策略**：

```cpp
// 方式1：eglChooseConfig - 系统自动选择最佳配置
const EGLint configAttribs[] = {
    EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,  // 要求OpenGL ES 3.0
    EGL_SURFACE_TYPE, EGL_WINDOW_BIT,         // Window Surface
    EGL_RED_SIZE, 8,
    EGL_GREEN_SIZE, 8,
    EGL_BLUE_SIZE, 8,
    EGL_ALPHA_SIZE, 8,
    EGL_DEPTH_SIZE, 24,                       // 24位深度缓冲
    EGL_STENCIL_SIZE, 8,                      // 8位模板缓冲
    EGL_NONE                                  // 属性列表结束
};

EGLConfig config;
EGLint numConfigs;
eglChooseConfig(display, configAttribs, &config, 1, &numConfigs);

// 方式2：eglGetConfigs - 获取所有配置后手动选择
EGLConfig configs[100];
EGLint numConfigs;
eglGetConfigs(display, configs, 100, &numConfigs);

// 遍历并选择最合适的配置
for (int i = 0; i < numConfigs; i++) {
    EGLint redSize, depthSize;
    eglGetConfigAttrib(display, configs[i], EGL_RED_SIZE, &redSize);
    eglGetConfigAttrib(display, configs[i], EGL_DEPTH_SIZE, &depthSize);
    // 根据需求选择
}
```

**不同场景的配置推荐**：

| 场景 | 颜色格式 | 深度 | 模板 | 多重采样 |
|------|---------|------|------|---------|
| 2D UI | RGBA8888 | 0 | 0 | 无 |
| 视频播放 | RGB565/RGBA8888 | 0 | 0 | 无 |
| 3D游戏 | RGBA8888 | 24 | 8 | 4x MSAA |
| AR应用 | RGBA8888 | 24 | 0 | 无 |

### 3.3 EGLSurface

**定义**：EGLSurface是渲染目标的抽象，GPU的绘制结果写入到EGLSurface关联的缓冲区。

**三种类型**：

| 类型 | 创建函数 | 用途 | 可见性 |
|------|---------|------|--------|
| **Window Surface** | eglCreateWindowSurface | 屏幕渲染 | 可见 |
| **PBuffer Surface** | eglCreatePbufferSurface | 离屏渲染 | 不可见 |
| **Pixmap Surface** | eglCreatePixmapSurface | 像素图渲染 | 不可见（Android不常用） |

**Window Surface创建**：

```cpp
// 从ANativeWindow创建Window Surface
EGLSurface createWindowSurface(EGLDisplay display, EGLConfig config,
                                ANativeWindow* window) {
    const EGLint surfaceAttribs[] = {
        EGL_NONE  // 可选属性，如EGL_RENDER_BUFFER
    };
    
    EGLSurface surface = eglCreateWindowSurface(
            display,
            config,
            (EGLNativeWindowType)window,
            surfaceAttribs);
    
    if (surface == EGL_NO_SURFACE) {
        EGLint error = eglGetError();
        // 处理错误：EGL_BAD_NATIVE_WINDOW, EGL_BAD_MATCH等
    }
    
    return surface;
}
```

**PBuffer Surface创建**（离屏渲染）：

```cpp
EGLSurface createPbufferSurface(EGLDisplay display, EGLConfig config,
                                 int width, int height) {
    const EGLint pbufferAttribs[] = {
        EGL_WIDTH, width,
        EGL_HEIGHT, height,
        EGL_TEXTURE_FORMAT, EGL_NO_TEXTURE,  // 不作为纹理使用
        EGL_TEXTURE_TARGET, EGL_NO_TEXTURE,
        EGL_NONE
    };
    
    EGLSurface surface = eglCreatePbufferSurface(display, config, pbufferAttribs);
    return surface;
}
```

**交换缓冲区**：

```cpp
// 将后缓冲区的内容提交到前缓冲区（显示）
EGLBoolean success = eglSwapBuffers(display, surface);
if (!success) {
    EGLint error = eglGetError();
    // EGL_BAD_SURFACE: Surface已无效
    // EGL_CONTEXT_LOST: 上下文丢失（GPU重置）
}
```

### 3.4 EGLContext

**定义**：EGLContext是OpenGL ES的状态容器，包含了所有渲染状态（当前着色器、绑定的纹理、VBO、VAO等）。

**创建**：

```cpp
EGLContext createContext(EGLDisplay display, EGLConfig config,
                          EGLContext shareContext = EGL_NO_CONTEXT) {
    // 指定OpenGL ES版本
    const EGLint contextAttribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,  // OpenGL ES 3.0
        EGL_NONE
    };
    
    // shareContext用于资源共享（纹理、缓冲区）
    EGLContext context = eglCreateContext(
            display,
            config,
            shareContext,  // EGL_NO_CONTEXT表示不共享
            contextAttribs);
    
    return context;
}
```

**线程绑定**：

```cpp
// 将Context绑定到当前线程
// 一个Context同时只能绑定到一个线程
EGLBoolean success = eglMakeCurrent(
        display,
        drawSurface,  // 绑制目标Surface
        readSurface,  // 读取源Surface（通常与drawSurface相同）
        context);

// 解绑当前线程
eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
```

**上下文共享**：

```cpp
// 创建共享上下文，可以在多个线程间共享纹理等资源
EGLContext mainContext = eglCreateContext(display, config, EGL_NO_CONTEXT, attribs);
EGLContext sharedContext = eglCreateContext(display, config, mainContext, attribs);

// mainContext和sharedContext可以访问相同的纹理、缓冲区等
// 但着色器程序、VAO等是Context私有的
```

**版本选择**：

| 版本 | EGL_CONTEXT_CLIENT_VERSION | 特性 |
|------|---------------------------|------|
| OpenGL ES 2.0 | 2 | 可编程着色器基础支持 |
| OpenGL ES 3.0 | 3 | 多渲染目标、遮挡查询、变换反馈 |
| OpenGL ES 3.1 | 3 + EGL_CONTEXT_MINOR_VERSION=1 | 计算着色器、独立着色器对象 |
| OpenGL ES 3.2 | 3 + EGL_CONTEXT_MINOR_VERSION=2 | 几何着色器、曲面细分 |

### 3.5 EGL对象关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            EGLDisplay                                    │
│                         (显示设备抽象)                                    │
│                               │                                          │
│               ┌───────────────┼───────────────┐                          │
│               │               │               │                          │
│               ▼               ▼               ▼                          │
│        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │
│        │  EGLConfig  │ │  EGLConfig  │ │  EGLConfig  │  ...             │
│        │    [0]      │ │    [1]      │ │    [2]      │                  │
│        │ RGBA8888    │ │ RGB565      │ │ RGBA8888    │                  │
│        │ Depth24     │ │ Depth0      │ │ Depth16     │                  │
│        └──────┬──────┘ └─────────────┘ └─────────────┘                  │
│               │                                                          │
│       ┌───────┴───────┐                                                 │
│       │               │                                                 │
│       ▼               ▼                                                 │
│ ┌───────────────┐  ┌───────────────┐                                   │
│ │  EGLSurface   │  │  EGLContext   │                                   │
│ │               │  │               │                                   │
│ │ Window Surface│  │ OpenGL ES 3.0│                                   │
│ │      或       │  │    状态容器   │                                   │
│ │ PBuffer       │  │               │                                   │
│ └───────┬───────┘  └───────┬───────┘                                   │
│         │                   │                                           │
│         │   eglMakeCurrent  │                                           │
│         └─────────┬─────────┘                                           │
│                   │                                                     │
│                   ▼                                                     │
│         ┌───────────────────┐                                          │
│         │   当前渲染线程     │                                          │
│         │                   │                                          │
│         │  Context绑定到    │                                          │
│         │  Surface，可以    │                                          │
│         │  执行GL命令       │                                          │
│         └───────────────────┘                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 第四部分：EGL完整工作流程

### 4.1 EGL初始化流程

完整的EGL初始化包含以下步骤：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EGL初始化完整流程                                 │
│                                                                          │
│   ┌─────────────────┐                                                   │
│   │ 1. eglGetDisplay │  获取Display句柄                                  │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │ 2. eglInitialize │  初始化EGL，获取版本号                             │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │3. eglChooseConfig│  选择帧缓冲配置                                   │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────────┐                                              │
│   │4. eglCreateWindowSurf│  创建渲染Surface                              │
│   └────────┬─────────────┘                                              │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │5. eglCreateContext│  创建渲染上下文                                   │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │ 6. eglMakeCurrent │  绑定上下文到当前线程                             │
│   └────────┬────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌─────────────────┐                                                   │
│   │   可以开始渲染   │                                                   │
│   └─────────────────┘                                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**完整C++代码示例**：

```cpp
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <android/native_window.h>

class EGLHelper {
private:
    EGLDisplay mDisplay = EGL_NO_DISPLAY;
    EGLConfig mConfig = nullptr;
    EGLSurface mSurface = EGL_NO_SURFACE;
    EGLContext mContext = EGL_NO_CONTEXT;

public:
    bool initialize(ANativeWindow* window) {
        // Step 1: 获取Display
        mDisplay = eglGetDisplay(EGL_DEFAULT_DISPLAY);
        if (mDisplay == EGL_NO_DISPLAY) {
            LOGE("eglGetDisplay failed");
            return false;
        }

        // Step 2: 初始化EGL
        EGLint major, minor;
        if (!eglInitialize(mDisplay, &major, &minor)) {
            LOGE("eglInitialize failed: 0x%x", eglGetError());
            return false;
        }
        LOGI("EGL initialized: version %d.%d", major, minor);

        // Step 3: 选择配置
        const EGLint configAttribs[] = {
            EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
            EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
            EGL_RED_SIZE, 8,
            EGL_GREEN_SIZE, 8,
            EGL_BLUE_SIZE, 8,
            EGL_ALPHA_SIZE, 8,
            EGL_DEPTH_SIZE, 24,
            EGL_STENCIL_SIZE, 8,
            EGL_NONE
        };

        EGLint numConfigs;
        if (!eglChooseConfig(mDisplay, configAttribs, &mConfig, 1, &numConfigs)
                || numConfigs == 0) {
            LOGE("eglChooseConfig failed: 0x%x", eglGetError());
            return false;
        }

        // Step 4: 创建Window Surface
        const EGLint surfaceAttribs[] = { EGL_NONE };
        mSurface = eglCreateWindowSurface(mDisplay, mConfig, window, surfaceAttribs);
        if (mSurface == EGL_NO_SURFACE) {
            LOGE("eglCreateWindowSurface failed: 0x%x", eglGetError());
            return false;
        }

        // Step 5: 创建Context
        const EGLint contextAttribs[] = {
            EGL_CONTEXT_CLIENT_VERSION, 3,  // OpenGL ES 3.0
            EGL_NONE
        };
        mContext = eglCreateContext(mDisplay, mConfig, EGL_NO_CONTEXT, contextAttribs);
        if (mContext == EGL_NO_CONTEXT) {
            LOGE("eglCreateContext failed: 0x%x", eglGetError());
            return false;
        }

        // Step 6: 绑定Context
        if (!eglMakeCurrent(mDisplay, mSurface, mSurface, mContext)) {
            LOGE("eglMakeCurrent failed: 0x%x", eglGetError());
            return false;
        }

        LOGI("EGL initialization complete");
        return true;
    }
};
```

**Java版本（使用EGL14）**：

```java
import android.opengl.EGL14;
import android.opengl.EGLConfig;
import android.opengl.EGLContext;
import android.opengl.EGLDisplay;
import android.opengl.EGLSurface;
import android.view.Surface;

public class EGLHelper {
    private EGLDisplay mEGLDisplay = EGL14.EGL_NO_DISPLAY;
    private EGLConfig mEGLConfig;
    private EGLSurface mEGLSurface = EGL14.EGL_NO_SURFACE;
    private EGLContext mEGLContext = EGL14.EGL_NO_CONTEXT;

    public boolean initialize(Surface surface) {
        // Step 1: 获取Display
        mEGLDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
        if (mEGLDisplay == EGL14.EGL_NO_DISPLAY) {
            throw new RuntimeException("eglGetDisplay failed");
        }

        // Step 2: 初始化EGL
        int[] version = new int[2];
        if (!EGL14.eglInitialize(mEGLDisplay, version, 0, version, 1)) {
            throw new RuntimeException("eglInitialize failed");
        }

        // Step 3: 选择配置
        int[] configAttribs = {
            EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,  // 兼容ES 2.0/3.0
            EGL14.EGL_SURFACE_TYPE, EGL14.EGL_WINDOW_BIT,
            EGL14.EGL_RED_SIZE, 8,
            EGL14.EGL_GREEN_SIZE, 8,
            EGL14.EGL_BLUE_SIZE, 8,
            EGL14.EGL_ALPHA_SIZE, 8,
            EGL14.EGL_DEPTH_SIZE, 24,
            EGL14.EGL_STENCIL_SIZE, 8,
            EGL14.EGL_NONE
        };

        EGLConfig[] configs = new EGLConfig[1];
        int[] numConfigs = new int[1];
        if (!EGL14.eglChooseConfig(mEGLDisplay, configAttribs, 0,
                configs, 0, 1, numConfigs, 0)) {
            throw new RuntimeException("eglChooseConfig failed");
        }
        mEGLConfig = configs[0];

        // Step 4: 创建Window Surface
        int[] surfaceAttribs = { EGL14.EGL_NONE };
        mEGLSurface = EGL14.eglCreateWindowSurface(mEGLDisplay, mEGLConfig,
                surface, surfaceAttribs, 0);
        if (mEGLSurface == EGL14.EGL_NO_SURFACE) {
            throw new RuntimeException("eglCreateWindowSurface failed");
        }

        // Step 5: 创建Context
        int[] contextAttribs = {
            EGL14.EGL_CONTEXT_CLIENT_VERSION, 3,
            EGL14.EGL_NONE
        };
        mEGLContext = EGL14.eglCreateContext(mEGLDisplay, mEGLConfig,
                EGL14.EGL_NO_CONTEXT, contextAttribs, 0);
        if (mEGLContext == EGL14.EGL_NO_CONTEXT) {
            throw new RuntimeException("eglCreateContext failed");
        }

        // Step 6: 绑定Context
        if (!EGL14.eglMakeCurrent(mEGLDisplay, mEGLSurface, mEGLSurface, mEGLContext)) {
            throw new RuntimeException("eglMakeCurrent failed");
        }

        return true;
    }
}
```

### 4.2 配置选择策略

**EGLConfig属性详解及推荐值**：

| 属性 | 2D UI | 视频播放 | 3D游戏 | AR/VR |
|------|-------|---------|--------|-------|
| EGL_RED_SIZE | 8 | 8 | 8 | 8 |
| EGL_GREEN_SIZE | 8 | 8 | 8 | 8 |
| EGL_BLUE_SIZE | 8 | 8 | 8 | 8 |
| EGL_ALPHA_SIZE | 8 | 0 | 8 | 8 |
| EGL_DEPTH_SIZE | 0 | 0 | 24 | 24 |
| EGL_STENCIL_SIZE | 0 | 0 | 8 | 8 |
| EGL_SAMPLE_BUFFERS | 0 | 0 | 1 | 1 |
| EGL_SAMPLES | 0 | 0 | 4 | 2 |

**配置选择的优先级策略**：

```cpp
// 自定义配置选择器
EGLConfig selectBestConfig(EGLDisplay display, bool needDepth, bool needMSAA) {
    EGLConfig configs[100];
    EGLint numConfigs;
    
    // 获取所有配置
    eglGetConfigs(display, configs, 100, &numConfigs);
    
    EGLConfig bestConfig = nullptr;
    int bestScore = -1;
    
    for (int i = 0; i < numConfigs; i++) {
        EGLint redSize, greenSize, blueSize, alphaSize;
        EGLint depthSize, stencilSize, samples;
        EGLint caveat;
        
        eglGetConfigAttrib(display, configs[i], EGL_RED_SIZE, &redSize);
        eglGetConfigAttrib(display, configs[i], EGL_GREEN_SIZE, &greenSize);
        eglGetConfigAttrib(display, configs[i], EGL_BLUE_SIZE, &blueSize);
        eglGetConfigAttrib(display, configs[i], EGL_ALPHA_SIZE, &alphaSize);
        eglGetConfigAttrib(display, configs[i], EGL_DEPTH_SIZE, &depthSize);
        eglGetConfigAttrib(display, configs[i], EGL_STENCIL_SIZE, &stencilSize);
        eglGetConfigAttrib(display, configs[i], EGL_SAMPLES, &samples);
        eglGetConfigAttrib(display, configs[i], EGL_CONFIG_CAVEAT, &caveat);
        
        // 跳过慢速配置
        if (caveat == EGL_SLOW_CONFIG) continue;
        
        // 计算得分
        int score = 0;
        
        // 颜色位数得分
        if (redSize == 8 && greenSize == 8 && blueSize == 8) {
            score += 100;
            if (alphaSize == 8) score += 10;
        }
        
        // 深度缓冲得分
        if (needDepth && depthSize >= 24) score += 50;
        else if (!needDepth && depthSize == 0) score += 20;
        
        // 多重采样得分
        if (needMSAA && samples >= 4) score += 30;
        else if (!needMSAA && samples == 0) score += 10;
        
        if (score > bestScore) {
            bestScore = score;
            bestConfig = configs[i];
        }
    }
    
    return bestConfig;
}
```

### 4.3 渲染循环

典型的渲染循环结构：

```java
// Java版渲染循环
public class RenderThread extends Thread {
    private volatile boolean mRunning = true;
    private EGLHelper mEglHelper;
    
    @Override
    public void run() {
        // 初始化EGL
        mEglHelper.initialize(mSurface);
        
        // 初始化OpenGL ES资源
        initGL();
        
        // 渲染循环
        while (mRunning) {
            // 1. 处理待处理的事件
            processEvents();
            
            // 2. 更新场景状态
            updateScene();
            
            // 3. 清除缓冲区
            GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT | GLES30.GL_DEPTH_BUFFER_BIT);
            
            // 4. 执行绑制
            drawScene();
            
            // 5. 交换缓冲区
            if (!EGL14.eglSwapBuffers(mEglHelper.getDisplay(), mEglHelper.getSurface())) {
                int error = EGL14.eglGetError();
                if (error == EGL14.EGL_BAD_SURFACE) {
                    // Surface丢失，需要重新创建
                    handleSurfaceLost();
                }
            }
        }
        
        // 清理资源
        mEglHelper.release();
    }
}
```

```cpp
// C++版渲染循环
void renderLoop() {
    while (running) {
        // 1. 检查Surface有效性
        if (!isSurfaceValid()) {
            waitForSurface();
            continue;
        }
        
        // 2. 清除缓冲区
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        
        // 3. 执行绑制
        drawScene();
        
        // 4. 交换缓冲区
        EGLBoolean result = eglSwapBuffers(mDisplay, mSurface);
        if (!result) {
            EGLint error = eglGetError();
            switch (error) {
                case EGL_BAD_SURFACE:
                    // Surface无效，可能被销毁
                    handleSurfaceLost();
                    break;
                case EGL_CONTEXT_LOST:
                    // GPU重置，需要重建所有资源
                    handleContextLost();
                    break;
                default:
                    LOGE("eglSwapBuffers error: 0x%x", error);
            }
        }
    }
}
```

### 4.4 EGL资源释放流程

资源释放必须按正确顺序进行，避免资源泄露：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EGL资源释放流程                                  │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────┐        │
│   │ 1. eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, │        │
│   │                   EGL_NO_CONTEXT)                          │        │
│   │    解绑当前Context                                         │        │
│   └───────────────────────────┬────────────────────────────────┘        │
│                               │                                          │
│                               ▼                                          │
│   ┌────────────────────────────────────────────────────────────┐        │
│   │ 2. eglDestroySurface(display, surface)                     │        │
│   │    销毁Surface                                             │        │
│   └───────────────────────────┬────────────────────────────────┘        │
│                               │                                          │
│                               ▼                                          │
│   ┌────────────────────────────────────────────────────────────┐        │
│   │ 3. eglDestroyContext(display, context)                     │        │
│   │    销毁Context                                             │        │
│   └───────────────────────────┬────────────────────────────────┘        │
│                               │                                          │
│                               ▼                                          │
│   ┌────────────────────────────────────────────────────────────┐        │
│   │ 4. eglTerminate(display)                                   │        │
│   │    终止Display                                             │        │
│   └────────────────────────────────────────────────────────────┘        │
│                                                                          │
│   ⚠️ 重要：必须按此顺序释放，否则可能导致资源泄露或崩溃                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**完整释放代码**：

```cpp
void EGLHelper::release() {
    if (mDisplay != EGL_NO_DISPLAY) {
        // Step 1: 解绑当前Context
        eglMakeCurrent(mDisplay, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        
        // Step 2: 销毁Surface
        if (mSurface != EGL_NO_SURFACE) {
            eglDestroySurface(mDisplay, mSurface);
            mSurface = EGL_NO_SURFACE;
        }
        
        // Step 3: 销毁Context
        if (mContext != EGL_NO_CONTEXT) {
            eglDestroyContext(mDisplay, mContext);
            mContext = EGL_NO_CONTEXT;
        }
        
        // Step 4: 终止Display
        eglTerminate(mDisplay);
        mDisplay = EGL_NO_DISPLAY;
    }
}
```

### 4.5 完整的生命周期状态图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EGL生命周期状态图                                  │
│                                                                          │
│                          ┌───────────┐                                   │
│                          │  未初始化  │                                   │
│                          └─────┬─────┘                                   │
│                                │                                         │
│                   eglGetDisplay + eglInitialize                          │
│                                │                                         │
│                                ▼                                         │
│                          ┌───────────┐                                   │
│                          │ Display   │                                   │
│                          │   已初始化 │                                   │
│                          └─────┬─────┘                                   │
│                                │                                         │
│                     eglChooseConfig                                      │
│                                │                                         │
│                                ▼                                         │
│                          ┌───────────┐                                   │
│                          │  Config   │                                   │
│                          │   已选择   │                                   │
│                          └─────┬─────┘                                   │
│                                │                                         │
│               ┌────────────────┴────────────────┐                        │
│               │                                  │                        │
│    eglCreateWindowSurface            eglCreateContext                    │
│               │                                  │                        │
│               ▼                                  ▼                        │
│        ┌───────────┐                      ┌───────────┐                  │
│        │  Surface  │                      │  Context  │                  │
│        │   已创建   │                      │   已创建   │                  │
│        └─────┬─────┘                      └─────┬─────┘                  │
│              │                                  │                        │
│              └────────────┬─────────────────────┘                        │
│                           │                                              │
│                    eglMakeCurrent                                        │
│                           │                                              │
│                           ▼                                              │
│                    ┌────────────┐                                        │
│      ┌─────────────│  渲染就绪   │─────────────┐                          │
│      │             └──────┬─────┘             │                          │
│      │                    │                    │                          │
│      │          ┌─────────┼─────────┐         │                          │
│      │          │         │         │         │                          │
│      │    glXxx调用   eglSwapBuffers  Surface丢失                        │
│      │          │         │         │         │                          │
│      │          ▼         ▼         │         │                          │
│      │     ┌─────────┐    │         │         │                          │
│      │     │  渲染中  │◄───┘         │         │                          │
│      │     └─────────┘              │         │                          │
│      │          │                   │         │                          │
│      │          │                   │         │                          │
│      │          │                   ▼         │                          │
│      │          │            ┌───────────┐    │                          │
│      │          │            │Surface丢失 │    │                          │
│      │          │            │需要重建    │    │                          │
│      │          │            └─────┬─────┘    │                          │
│      │          │                  │          │                          │
│      │          │         重新创建Surface     │                          │
│      │          │                  │          │                          │
│      │          └──────────────────┼──────────┘                          │
│      │                             │                                     │
│      │                             ▼                                     │
│      │                      eglMakeCurrent                               │
│      │                             │                                     │
│      └─────────────────────────────┘                                     │
│                                                                          │
│                    ┌──────────────┐                                      │
│                    │ 应用退出或   │                                      │
│                    │ 需要清理     │                                      │
│                    └──────┬───────┘                                      │
│                           │                                              │
│           eglMakeCurrent(NO_SURFACE, NO_CONTEXT)                         │
│                           │                                              │
│                           ▼                                              │
│              eglDestroySurface + eglDestroyContext                       │
│                           │                                              │
│                           ▼                                              │
│                     eglTerminate                                         │
│                           │                                              │
│                           ▼                                              │
│                     ┌───────────┐                                        │
│                     │   已释放   │                                        │
│                     └───────────┘                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

---

## 第五部分：实践应用指导

### 5.1 GLSurfaceView的EGL封装

GLSurfaceView是Android提供的OpenGL ES渲染View，它内部自动管理EGL生命周期，大大简化了开发工作。

**GLSurfaceView的内部架构**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          GLSurfaceView                                   │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        GLThread                                    │  │
│  │                    (独立渲染线程)                                   │  │
│  │                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────┐ │  │
│  │   │                   EglHelper                                  │ │  │
│  │   │                                                              │ │  │
│  │   │   mEglDisplay     EGL Display句柄                            │ │  │
│  │   │   mEglConfig      EGL配置                                    │ │  │
│  │   │   mEglSurface     EGL Surface                                │ │  │
│  │   │   mEglContext     EGL Context                                │ │  │
│  │   │                                                              │ │  │
│  │   │   start()         初始化EGL                                   │ │  │
│  │   │   createSurface() 创建EGLSurface                             │ │  │
│  │   │   swap()          eglSwapBuffers                             │ │  │
│  │   │   finish()        清理EGL资源                                 │ │  │
│  │   │                                                              │ │  │
│  │   └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                    │  │
│  │   guardedRun() {                                                   │  │
│  │       mEglHelper.start();           // 初始化EGL                   │  │
│  │       mEglHelper.createSurface();   // 创建Surface                 │  │
│  │       renderer.onSurfaceCreated();  // 回调Renderer                │  │
│  │       while (running) {                                            │  │
│  │           renderer.onDrawFrame();   // 执行绑制                    │  │
│  │           mEglHelper.swap();        // 交换缓冲区                  │  │
│  │       }                                                            │  │
│  │       mEglHelper.finish();          // 清理                        │  │
│  │   }                                                                │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Renderer接口                                  │  │
│  │                                                                    │  │
│  │   onSurfaceCreated(GL10 gl, EGLConfig config)                     │  │
│  │       // Surface创建后调用，初始化GL资源                            │  │
│  │                                                                    │  │
│  │   onSurfaceChanged(GL10 gl, int width, int height)                │  │
│  │       // Surface尺寸变化时调用                                      │  │
│  │                                                                    │  │
│  │   onDrawFrame(GL10 gl)                                            │  │
│  │       // 每帧调用，执行绑制                                         │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**GLThread.guardedRun()核心流程（源码分析）**：

```java
// android.opengl.GLSurfaceView.GLThread
private void guardedRun() throws InterruptedException {
    mEglHelper = new EglHelper(mGLSurfaceViewWeakRef);
    
    while (true) {
        synchronized (sGLThreadManager) {
            // 处理各种状态变化
            while (true) {
                if (mShouldExit) return;
                
                // 检查是否需要创建EGL Surface
                if (mHaveEglSurface && !mHaveEglContext) {
                    mEglHelper.start();
                    mHaveEglContext = true;
                    createEglContext = true;
                }
                
                // 检查是否需要创建Surface
                if (mHaveEglContext && !mHaveEglSurface) {
                    mHaveEglSurface = true;
                    createEglSurface = true;
                    sizeChanged = true;
                }
                
                if (readyToDraw()) break;
                sGLThreadManager.wait();
            }
        }
        
        // 创建EGL Surface
        if (createEglSurface) {
            if (mEglHelper.createSurface()) {
                createGlInterface = true;
            }
        }
        
        // 回调Renderer
        if (createEglContext) {
            mRenderer.onSurfaceCreated(gl, mEglHelper.mEglConfig);
        }
        
        if (sizeChanged) {
            mRenderer.onSurfaceChanged(gl, w, h);
        }
        
        // 执行绘制
        mRenderer.onDrawFrame(gl);
        
        // 交换缓冲区
        int swapError = mEglHelper.swap();
        switch (swapError) {
            case EGL14.EGL_SUCCESS:
                break;
            case EGL11.EGL_CONTEXT_LOST:
                // Context丢失，需要重建
                lostEglContext = true;
                break;
            default:
                // Surface丢失
                surfaceIsBad = true;
                break;
        }
    }
}
```

**自定义EGLContextFactory和EGLConfigChooser**：

```java
public class CustomGLSurfaceView extends GLSurfaceView {
    
    public CustomGLSurfaceView(Context context) {
        super(context);
        
        // 自定义EGL配置选择器
        setEGLConfigChooser(new EGLConfigChooser() {
            @Override
            public EGLConfig chooseConfig(EGL10 egl, EGLDisplay display) {
                int[] configAttribs = {
                    EGL10.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,  // 兼容ES 2.0/3.0
                    EGL10.EGL_RED_SIZE, 8,
                    EGL10.EGL_GREEN_SIZE, 8,
                    EGL10.EGL_BLUE_SIZE, 8,
                    EGL10.EGL_ALPHA_SIZE, 8,
                    EGL10.EGL_DEPTH_SIZE, 24,
                    EGL10.EGL_STENCIL_SIZE, 8,
                    EGL10.EGL_SAMPLE_BUFFERS, 1,  // 启用多重采样
                    EGL10.EGL_SAMPLES, 4,         // 4x MSAA
                    EGL10.EGL_NONE
                };
                
                EGLConfig[] configs = new EGLConfig[1];
                int[] numConfigs = new int[1];
                egl.eglChooseConfig(display, configAttribs, configs, 1, numConfigs);
                
                return configs[0];
            }
        });
        
        // 自定义EGL Context工厂
        setEGLContextFactory(new EGLContextFactory() {
            @Override
            public EGLContext createContext(EGL10 egl, EGLDisplay display, EGLConfig config) {
                int[] contextAttribs = {
                    EGL14.EGL_CONTEXT_CLIENT_VERSION, 3,  // OpenGL ES 3.0
                    EGL10.EGL_NONE
                };
                return egl.eglCreateContext(display, config, EGL10.EGL_NO_CONTEXT, contextAttribs);
            }
            
            @Override
            public void destroyContext(EGL10 egl, EGLDisplay display, EGLContext context) {
                egl.eglDestroyContext(display, context);
            }
        });
        
        setEGLContextClientVersion(3);
        setRenderer(new MyRenderer());
    }
}
```

### 5.2 SurfaceView + EGL手动管理

使用SurfaceView配合手动EGL管理，可以获得更灵活的控制：

**完整代码示例**：

```java
public class EGLSurfaceView extends SurfaceView implements SurfaceHolder.Callback {
    private RenderThread mRenderThread;
    
    public EGLSurfaceView(Context context) {
        super(context);
        getHolder().addCallback(this);
    }
    
    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        mRenderThread = new RenderThread(holder.getSurface());
        mRenderThread.start();
    }
    
    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        mRenderThread.onSurfaceChanged(width, height);
    }
    
    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        mRenderThread.requestExit();
        try {
            mRenderThread.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
    
    private static class RenderThread extends Thread {
        private final Surface mSurface;
        private volatile boolean mRunning = true;
        private int mWidth, mHeight;
        
        // EGL对象
        private EGLDisplay mEGLDisplay;
        private EGLConfig mEGLConfig;
        private EGLSurface mEGLSurface;
        private EGLContext mEGLContext;
        
        public RenderThread(Surface surface) {
            mSurface = surface;
        }
        
        @Override
        public void run() {
            // 初始化EGL
            initEGL();
            
            // 初始化OpenGL资源
            initGL();
            
            // 渲染循环
            while (mRunning) {
                // 清除
                GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT | GLES30.GL_DEPTH_BUFFER_BIT);
                
                // 绘制
                drawFrame();
                
                // 交换缓冲区
                if (!EGL14.eglSwapBuffers(mEGLDisplay, mEGLSurface)) {
                    handleSwapError();
                }
            }
            
            // 清理
            releaseEGL();
        }
        
        private void initEGL() {
            // 1. 获取Display
            mEGLDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
            
            // 2. 初始化
            int[] version = new int[2];
            EGL14.eglInitialize(mEGLDisplay, version, 0, version, 1);
            
            // 3. 选择配置
            int[] configAttribs = {
                EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,  // 兼容ES 2.0/3.0
                EGL14.EGL_SURFACE_TYPE, EGL14.EGL_WINDOW_BIT,
                EGL14.EGL_RED_SIZE, 8,
                EGL14.EGL_GREEN_SIZE, 8,
                EGL14.EGL_BLUE_SIZE, 8,
                EGL14.EGL_ALPHA_SIZE, 8,
                EGL14.EGL_DEPTH_SIZE, 24,
                EGL14.EGL_NONE
            };
            EGLConfig[] configs = new EGLConfig[1];
            int[] numConfigs = new int[1];
            EGL14.eglChooseConfig(mEGLDisplay, configAttribs, 0, configs, 0, 1, numConfigs, 0);
            mEGLConfig = configs[0];
            
            // 4. 创建Surface
            int[] surfaceAttribs = { EGL14.EGL_NONE };
            mEGLSurface = EGL14.eglCreateWindowSurface(mEGLDisplay, mEGLConfig, 
                    mSurface, surfaceAttribs, 0);
            
            // 5. 创建Context
            int[] contextAttribs = {
                EGL14.EGL_CONTEXT_CLIENT_VERSION, 3,
                EGL14.EGL_NONE
            };
            mEGLContext = EGL14.eglCreateContext(mEGLDisplay, mEGLConfig,
                    EGL14.EGL_NO_CONTEXT, contextAttribs, 0);
            
            // 6. 绑定
            EGL14.eglMakeCurrent(mEGLDisplay, mEGLSurface, mEGLSurface, mEGLContext);
        }
        
        private void releaseEGL() {
            EGL14.eglMakeCurrent(mEGLDisplay, EGL14.EGL_NO_SURFACE,
                    EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT);
            EGL14.eglDestroySurface(mEGLDisplay, mEGLSurface);
            EGL14.eglDestroyContext(mEGLDisplay, mEGLContext);
            EGL14.eglTerminate(mEGLDisplay);
        }
        
        public void requestExit() {
            mRunning = false;
        }
        
        public void onSurfaceChanged(int width, int height) {
            mWidth = width;
            mHeight = height;
        }
    }
}
```

### 5.3 TextureView + EGL

TextureView通过SurfaceTexture提供渲染目标，需要手动管理EGL：

```java
public class EGLTextureView extends TextureView implements TextureView.SurfaceTextureListener {
    private RenderThread mRenderThread;
    
    public EGLTextureView(Context context) {
        super(context);
        setSurfaceTextureListener(this);
    }
    
    @Override
    public void onSurfaceTextureAvailable(SurfaceTexture surfaceTexture, int width, int height) {
        // 从SurfaceTexture创建Surface
        Surface surface = new Surface(surfaceTexture);
        mRenderThread = new RenderThread(surface, width, height);
        mRenderThread.start();
    }
    
    @Override
    public void onSurfaceTextureSizeChanged(SurfaceTexture surfaceTexture, int width, int height) {
        if (mRenderThread != null) {
            mRenderThread.onSizeChanged(width, height);
        }
    }
    
    @Override
    public boolean onSurfaceTextureDestroyed(SurfaceTexture surfaceTexture) {
        if (mRenderThread != null) {
            mRenderThread.requestExit();
            try {
                mRenderThread.join();
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        return true;
    }
    
    @Override
    public void onSurfaceTextureUpdated(SurfaceTexture surfaceTexture) {
        // 内容更新时的回调
    }
}
```

**TextureView vs SurfaceView的EGL使用差异**：

| 特性 | TextureView | SurfaceView |
|------|-------------|-------------|
| Surface获取方式 | new Surface(surfaceTexture) | holder.getSurface() |
| 生命周期回调 | SurfaceTextureListener | SurfaceHolder.Callback |
| 可见时机 | onSurfaceTextureAvailable | surfaceCreated |
| 销毁处理 | onSurfaceTextureDestroyed | surfaceDestroyed |
| 返回值 | 返回true释放SurfaceTexture | 无返回值 |
| View变换 | 支持（旋转、缩放等） | 有限支持 |

### 5.4 MediaCodec + EGL（视频渲染/编码）

**使用EGL渲染MediaCodec解码输出**：

```java
public class VideoRenderer {
    private MediaCodec mDecoder;
    private Surface mDecoderInputSurface;
    private SurfaceTexture mSurfaceTexture;
    private int mTextureId;
    
    public void setup(Surface outputSurface) {
        // 初始化EGL并绑定到outputSurface
        initEGL(outputSurface);
        
        // 创建外部纹理用于接收解码帧
        int[] textures = new int[1];
        GLES30.glGenTextures(1, textures, 0);
        mTextureId = textures[0];
        
        GLES30.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, mTextureId);
        GLES30.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,
                GLES30.GL_TEXTURE_MIN_FILTER, GLES30.GL_LINEAR);
        GLES30.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,
                GLES30.GL_TEXTURE_MAG_FILTER, GLES30.GL_LINEAR);
        
        // 创建SurfaceTexture
        mSurfaceTexture = new SurfaceTexture(mTextureId);
        mSurfaceTexture.setOnFrameAvailableListener(surfaceTexture -> {
            // 有新帧可用，请求渲染
            requestRender();
        });
        
        // 创建Decoder输入Surface
        mDecoderInputSurface = new Surface(mSurfaceTexture);
        
        // 配置MediaCodec
        mDecoder = MediaCodec.createDecoderByType("video/avc");
        mDecoder.configure(format, mDecoderInputSurface, null, 0);
        mDecoder.start();
    }
    
    public void renderFrame() {
        // 更新纹理
        mSurfaceTexture.updateTexImage();
        
        // 获取变换矩阵
        float[] transformMatrix = new float[16];
        mSurfaceTexture.getTransformMatrix(transformMatrix);
        
        // 使用着色器绘制纹理
        drawTextureWithMatrix(mTextureId, transformMatrix);
        
        // 交换缓冲区
        EGL14.eglSwapBuffers(mEGLDisplay, mEGLSurface);
    }
}
```

**使用EGL创建MediaCodec编码输入Surface**：

```java
public class VideoEncoder {
    private MediaCodec mEncoder;
    private Surface mEncoderInputSurface;
    private EGLDisplay mEGLDisplay;
    private EGLSurface mEGLSurface;
    private EGLContext mEGLContext;
    
    public void setup(int width, int height) {
        // 配置编码器
        MediaFormat format = MediaFormat.createVideoFormat("video/avc", width, height);
        format.setInteger(MediaFormat.KEY_BIT_RATE, 2000000);
        format.setInteger(MediaFormat.KEY_FRAME_RATE, 30);
        format.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);
        format.setInteger(MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface);
        
        mEncoder = MediaCodec.createEncoderByType("video/avc");
        mEncoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
        
        // 获取编码器输入Surface
        mEncoderInputSurface = mEncoder.createInputSurface();
        
        // 创建EGL环境，绑定到编码器输入Surface
        initEGL(mEncoderInputSurface);
        
        mEncoder.start();
    }
    
    public void encodeFrame(int textureId, float[] transformMatrix) {
        // 绑定EGL上下文
        EGL14.eglMakeCurrent(mEGLDisplay, mEGLSurface, mEGLSurface, mEGLContext);
        
        // 设置时间戳
        EGLExt.eglPresentationTimeANDROID(mEGLDisplay, mEGLSurface, 
                System.nanoTime());
        
        // 绘制纹理到编码器输入Surface
        drawTexture(textureId, transformMatrix);
        
        // 交换缓冲区（将帧提交给编码器）
        EGL14.eglSwapBuffers(mEGLDisplay, mEGLSurface);
    }
}
```

### 5.5 离屏渲染（PBuffer Surface）

**PBuffer Surface创建和使用**：

```java
public class OffscreenRenderer {
    private EGLDisplay mEGLDisplay;
    private EGLConfig mEGLConfig;
    private EGLSurface mPbufferSurface;
    private EGLContext mEGLContext;
    private int mWidth, mHeight;
    
    public void initialize(int width, int height) {
        mWidth = width;
        mHeight = height;
        
        // 初始化EGL Display
        mEGLDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
        int[] version = new int[2];
        EGL14.eglInitialize(mEGLDisplay, version, 0, version, 1);
        
        // 选择配置（PBuffer需要EGL_PBUFFER_BIT）
        int[] configAttribs = {
            EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,  // 兼容ES 2.0/3.0
            EGL14.EGL_SURFACE_TYPE, EGL14.EGL_PBUFFER_BIT,  // PBuffer类型
            EGL14.EGL_RED_SIZE, 8,
            EGL14.EGL_GREEN_SIZE, 8,
            EGL14.EGL_BLUE_SIZE, 8,
            EGL14.EGL_ALPHA_SIZE, 8,
            EGL14.EGL_NONE
        };
        EGLConfig[] configs = new EGLConfig[1];
        int[] numConfigs = new int[1];
        EGL14.eglChooseConfig(mEGLDisplay, configAttribs, 0, configs, 0, 1, numConfigs, 0);
        mEGLConfig = configs[0];
        
        // 创建PBuffer Surface
        int[] pbufferAttribs = {
            EGL14.EGL_WIDTH, width,
            EGL14.EGL_HEIGHT, height,
            EGL14.EGL_NONE
        };
        mPbufferSurface = EGL14.eglCreatePbufferSurface(mEGLDisplay, mEGLConfig,
                pbufferAttribs, 0);
        
        // 创建Context
        int[] contextAttribs = {
            EGL14.EGL_CONTEXT_CLIENT_VERSION, 3,
            EGL14.EGL_NONE
        };
        mEGLContext = EGL14.eglCreateContext(mEGLDisplay, mEGLConfig,
                EGL14.EGL_NO_CONTEXT, contextAttribs, 0);
        
        // 绑定
        EGL14.eglMakeCurrent(mEGLDisplay, mPbufferSurface, mPbufferSurface, mEGLContext);
    }
    
    public Bitmap renderToBitmap() {
        // 执行渲染
        GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT);
        drawScene();
        
        // 读取像素
        ByteBuffer buffer = ByteBuffer.allocateDirect(mWidth * mHeight * 4);
        buffer.order(ByteOrder.nativeOrder());
        GLES30.glReadPixels(0, 0, mWidth, mHeight, GLES30.GL_RGBA,
                GLES30.GL_UNSIGNED_BYTE, buffer);
        
        // 创建Bitmap
        Bitmap bitmap = Bitmap.createBitmap(mWidth, mHeight, Bitmap.Config.ARGB_8888);
        buffer.rewind();
        bitmap.copyPixelsFromBuffer(buffer);
        
        // 翻转Y轴（OpenGL原点在左下角）
        Matrix matrix = new Matrix();
        matrix.preScale(1, -1);
        return Bitmap.createBitmap(bitmap, 0, 0, mWidth, mHeight, matrix, false);
    }
    
    public void release() {
        EGL14.eglMakeCurrent(mEGLDisplay, EGL14.EGL_NO_SURFACE,
                EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT);
        EGL14.eglDestroySurface(mEGLDisplay, mPbufferSurface);
        EGL14.eglDestroyContext(mEGLDisplay, mEGLContext);
        EGL14.eglTerminate(mEGLDisplay);
    }
}
```

### 5.6 跨线程纹理共享

**使用SharedContext实现多线程渲染**：

```java
public class SharedContextManager {
    private EGLDisplay mEGLDisplay;
    private EGLConfig mEGLConfig;
    private EGLContext mMainContext;      // 主渲染线程Context
    private EGLContext mBackgroundContext; // 后台线程Context
    
    public void initialize() {
        // 初始化Display和Config
        mEGLDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
        int[] version = new int[2];
        EGL14.eglInitialize(mEGLDisplay, version, 0, version, 1);
        
        int[] configAttribs = {
            EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,  // 兼容ES 2.0/3.0
            EGL14.EGL_SURFACE_TYPE, EGL14.EGL_WINDOW_BIT | EGL14.EGL_PBUFFER_BIT,
            EGL14.EGL_RED_SIZE, 8,
            EGL14.EGL_GREEN_SIZE, 8,
            EGL14.EGL_BLUE_SIZE, 8,
            EGL14.EGL_ALPHA_SIZE, 8,
            EGL14.EGL_NONE
        };
        EGLConfig[] configs = new EGLConfig[1];
        int[] numConfigs = new int[1];
        EGL14.eglChooseConfig(mEGLDisplay, configAttribs, 0, configs, 0, 1, numConfigs, 0);
        mEGLConfig = configs[0];
        
        // 创建主Context
        int[] contextAttribs = {
            EGL14.EGL_CONTEXT_CLIENT_VERSION, 3,
            EGL14.EGL_NONE
        };
        mMainContext = EGL14.eglCreateContext(mEGLDisplay, mEGLConfig,
                EGL14.EGL_NO_CONTEXT, contextAttribs, 0);
        
        // 创建共享Context（传入mMainContext作为shareContext）
        mBackgroundContext = EGL14.eglCreateContext(mEGLDisplay, mEGLConfig,
                mMainContext,  // 共享资源
                contextAttribs, 0);
    }
    
    // 后台线程加载纹理
    public int loadTextureInBackground(final String imagePath) {
        // 在后台线程创建PBuffer并绑定共享Context
        int[] pbufferAttribs = { EGL14.EGL_WIDTH, 1, EGL14.EGL_HEIGHT, 1, EGL14.EGL_NONE };
        EGLSurface pbuffer = EGL14.eglCreatePbufferSurface(mEGLDisplay, mEGLConfig,
                pbufferAttribs, 0);
        
        EGL14.eglMakeCurrent(mEGLDisplay, pbuffer, pbuffer, mBackgroundContext);
        
        // 加载纹理（此纹理可在主Context中使用）
        int textureId = loadTexture(imagePath);
        
        // 使用Fence同步，确保纹理数据可见
        GLES30.glFlush();
        
        // 清理
        EGL14.eglMakeCurrent(mEGLDisplay, EGL14.EGL_NO_SURFACE,
                EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT);
        EGL14.eglDestroySurface(mEGLDisplay, pbuffer);
        
        return textureId;
    }
}
```

**共享Context可共享的资源**：

| 可共享 | 不可共享 |
|--------|----------|
| 纹理对象 | VAO（顶点数组对象） |
| 缓冲对象（VBO/EBO/UBO） | FBO（帧缓冲对象） |
| 渲染缓冲对象 | 着色器程序 |
| 同步对象 | 查询对象 |
| 采样器对象 | 变换反馈对象 |

---

## 第六部分：性能优化建议

### 6.1 EGLConfig选择优化

**颜色格式选择的性能影响**：

| 颜色格式 | 内存占用 | 带宽消耗 | 视觉质量 | 适用场景 |
|---------|---------|---------|---------|----------|
| RGB565 | 2字节/像素 | 低 | 中（无Alpha，可能有色带） | 简单2D、低端设备 |
| RGBA8888 | 4字节/像素 | 高 | 高 | 3D游戏、需要透明 |
| RGB888 | 3字节/像素 | 中 | 高（无Alpha） | 视频播放 |
| RGBA1010102 | 4字节/像素 | 高 | 非常高（HDR） | HDR内容 |

**深度/模板缓冲优化**：

```java
// 2D UI渲染：不需要深度/模板缓冲
int[] configAttribs2D = {
    EGL14.EGL_DEPTH_SIZE, 0,     // 无深度缓冲
    EGL14.EGL_STENCIL_SIZE, 0,   // 无模板缓冲
    // ...
};

// 3D渲染：根据需求选择
int[] configAttribs3D = {
    EGL14.EGL_DEPTH_SIZE, 24,    // 24位深度（足够大部分场景）
    EGL14.EGL_STENCIL_SIZE, 8,   // 8位模板（阴影、镜像等）
    // ...
};

// 简单3D：可以使用16位深度
int[] configAttribsSimple3D = {
    EGL14.EGL_DEPTH_SIZE, 16,    // 16位深度，省内存
    EGL14.EGL_STENCIL_SIZE, 0,   // 无模板
    // ...
};
```

### 6.2 eglSwapBuffers性能考量

**SwapBuffers的阻塞行为**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    eglSwapBuffers时序分析                                │
│                                                                          │
│   VSYNC周期: ├────────────────┼────────────────┼────────────────┤       │
│              │     16.67ms    │     16.67ms    │     16.67ms    │       │
│                                                                          │
│   理想情况（渲染时间 < 16ms）：                                           │
│   ├──渲染──┤等待VSYNC├──渲染──┤等待VSYNC├──渲染──┤                       │
│   │  10ms  │  6ms    │  10ms  │  6ms    │  10ms  │                       │
│                                                                          │
│   阻塞情况（BufferQueue满）：                                             │
│   ├──渲染──┼─阻塞等待Buffer─┤渲染├─阻塞─┤                                │
│   │  10ms  │    等待消费者    │                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Swap Interval设置**：

```java
// 默认值1：与VSYNC同步，等待垂直同步信号
// 好处：无撕裂；坏处：最大帧率受限于刷新率
EGL14.eglSwapInterval(mEGLDisplay, 1);

// 值0：不等待VSYNC，立即交换
// 好处：低延迟；坏处：可能撕裂，GPU满载
EGL14.eglSwapInterval(mEGLDisplay, 0);

// 值2：每2个VSYNC交换一次（30fps）
// 用于：低功耗模式或渲染较慢的场景
EGL14.eglSwapInterval(mEGLDisplay, 2);
```

### 6.3 EGL上下文切换开销

**eglMakeCurrent的性能成本**：

```cpp
// eglMakeCurrent会触发以下操作：
// 1. 保存当前Context的状态
// 2. 加载新Context的状态
// 3. 更新线程本地存储（TLS）
// 4. 可能触发GPU状态刷新

// 典型开销：0.1ms - 1ms（取决于GPU和驱动）
```

**减少上下文切换的策略**：

```java
// 策略1：单线程渲染，避免切换
public class SingleThreadRenderer {
    // 所有渲染操作在同一线程，Context只绑定一次
}

// 策略2：每线程独立Context
public class PerThreadContext {
    private static ThreadLocal<EGLContext> sContexts = new ThreadLocal<>();
    
    public static void bindContext() {
        EGLContext context = sContexts.get();
        if (context == null) {
            context = createContext();
            sContexts.set(context);
        }
        eglMakeCurrent(display, surface, surface, context);
    }
}

// 策略3：批量处理，减少切换频率
public class BatchRenderer {
    private List<RenderTask> mPendingTasks = new ArrayList<>();
    
    public void submitTask(RenderTask task) {
        mPendingTasks.add(task);
    }
    
    public void processBatch() {
        // 一次绑定，处理所有任务
        eglMakeCurrent(display, surface, surface, context);
        for (RenderTask task : mPendingTasks) {
            task.execute();
        }
        mPendingTasks.clear();
    }
}
```

### 6.4 资源管理优化

**EGL资源泄露检测**：

```java
public class EGLResourceTracker {
    private static Set<WeakReference<EGLSurface>> sSurfaces = new HashSet<>();
    private static Set<WeakReference<EGLContext>> sContexts = new HashSet<>();
    
    public static EGLSurface trackSurface(EGLSurface surface) {
        sSurfaces.add(new WeakReference<>(surface));
        return surface;
    }
    
    public static void checkLeaks() {
        // 在适当时机检查未释放的资源
        for (WeakReference<EGLSurface> ref : sSurfaces) {
            EGLSurface surface = ref.get();
            if (surface != null && surface != EGL14.EGL_NO_SURFACE) {
                Log.w(TAG, "Potential EGLSurface leak detected");
            }
        }
    }
}
```

**Fence同步（EGL_ANDROID_native_fence_sync）**：

```java
// 创建Fence同步对象
int[] attribs = { EGL14.EGL_NONE };
EGLSync sync = EGLExt.eglCreateSyncKHR(mEGLDisplay,
        EGLExt.EGL_SYNC_NATIVE_FENCE_ANDROID, attribs, 0);

// 获取原生Fence FD
int fenceFd = EGLExt.eglDupNativeFenceFDANDROID(mEGLDisplay, sync);

// 等待Fence完成
EGLExt.eglClientWaitSyncKHR(mEGLDisplay, sync,
        EGLExt.EGL_SYNC_FLUSH_COMMANDS_BIT_KHR,
        EGLExt.EGL_FOREVER_KHR);

// 销毁Sync对象
EGLExt.eglDestroySyncKHR(mEGLDisplay, sync);
```

### 6.5 Android特有的EGL扩展

| 扩展 | 用途 | 使用场景 |
|------|------|----------|
| EGL_ANDROID_recordable | 标记Surface可用于录制 | MediaCodec编码 |
| EGL_ANDROID_presentation_time | 设置帧时间戳 | 视频编码/播放 |
| EGL_KHR_fence_sync | GPU同步原语 | 跨线程同步 |
| EGL_ANDROID_native_fence_sync | 原生Fence支持 | 与SurfaceFlinger同步 |
| EGL_ANDROID_image_native_buffer | 图像缓冲区支持 | 与Gralloc交互 |

```java
// 检查扩展支持
String extensions = EGL14.eglQueryString(mEGLDisplay, EGL14.EGL_EXTENSIONS);
boolean supportsRecordable = extensions.contains("EGL_ANDROID_recordable");
boolean supportsPresentationTime = extensions.contains("EGL_ANDROID_presentation_time");

// 使用EGL_ANDROID_recordable
if (supportsRecordable) {
    int[] configAttribs = {
        // ... 其他属性
        EGLExt.EGL_RECORDABLE_ANDROID, 1,  // 标记可录制
        EGL14.EGL_NONE
    };
}

// 使用EGL_ANDROID_presentation_time
if (supportsPresentationTime) {
    // 设置帧呈现时间（纳秒）
    EGLExt.eglPresentationTimeANDROID(mEGLDisplay, mEGLSurface,
            System.nanoTime());
}
```

---

## 第七部分：常见问题排查

### 7.1 EGL错误码大全

| 错误码 | 值 | 含义 | 常见原因 |
|--------|-----|------|----------|
| EGL_SUCCESS | 0x3000 | 成功 | - |
| EGL_NOT_INITIALIZED | 0x3001 | EGL未初始化 | 未调用eglInitialize |
| EGL_BAD_ACCESS | 0x3002 | 访问冲突 | Context已被其他线程使用 |
| EGL_BAD_ALLOC | 0x3003 | 内存分配失败 | 资源不足 |
| EGL_BAD_ATTRIBUTE | 0x3004 | 无效属性 | 属性值错误或不支持 |
| EGL_BAD_CONFIG | 0x3005 | 无效配置 | EGLConfig无效 |
| EGL_BAD_CONTEXT | 0x3006 | 无效上下文 | EGLContext无效或已销毁 |
| EGL_BAD_CURRENT_SURFACE | 0x3007 | 当前Surface无效 | 绑定的Surface已销毁 |
| EGL_BAD_DISPLAY | 0x3008 | 无效显示 | EGLDisplay无效 |
| EGL_BAD_MATCH | 0x3009 | 不匹配 | Config与Surface/Context不兼容 |
| EGL_BAD_NATIVE_PIXMAP | 0x300A | 无效原生Pixmap | Pixmap对象无效 |
| EGL_BAD_NATIVE_WINDOW | 0x300B | 无效原生窗口 | ANativeWindow无效或已销毁 |
| EGL_BAD_PARAMETER | 0x300C | 无效参数 | 函数参数值错误 |
| EGL_BAD_SURFACE | 0x300D | 无效Surface | EGLSurface无效或已销毁 |
| EGL_CONTEXT_LOST | 0x300E | 上下文丢失 | GPU重置或驱动问题 |

**错误处理工具函数**：

```java
public class EGLErrorHelper {
    public static void checkEglError(String operation) {
        int error = EGL14.eglGetError();
        if (error != EGL14.EGL_SUCCESS) {
            String errorName = getErrorName(error);
            throw new RuntimeException(operation + " failed: " + errorName + " (0x" + 
                    Integer.toHexString(error) + ")");
        }
    }
    
    public static String getErrorName(int error) {
        switch (error) {
            case EGL14.EGL_SUCCESS: return "EGL_SUCCESS";
            case EGL14.EGL_NOT_INITIALIZED: return "EGL_NOT_INITIALIZED";
            case EGL14.EGL_BAD_ACCESS: return "EGL_BAD_ACCESS";
            case EGL14.EGL_BAD_ALLOC: return "EGL_BAD_ALLOC";
            case EGL14.EGL_BAD_ATTRIBUTE: return "EGL_BAD_ATTRIBUTE";
            case EGL14.EGL_BAD_CONFIG: return "EGL_BAD_CONFIG";
            case EGL14.EGL_BAD_CONTEXT: return "EGL_BAD_CONTEXT";
            case EGL14.EGL_BAD_CURRENT_SURFACE: return "EGL_BAD_CURRENT_SURFACE";
            case EGL14.EGL_BAD_DISPLAY: return "EGL_BAD_DISPLAY";
            case EGL14.EGL_BAD_MATCH: return "EGL_BAD_MATCH";
            case EGL14.EGL_BAD_NATIVE_PIXMAP: return "EGL_BAD_NATIVE_PIXMAP";
            case EGL14.EGL_BAD_NATIVE_WINDOW: return "EGL_BAD_NATIVE_WINDOW";
            case EGL14.EGL_BAD_PARAMETER: return "EGL_BAD_PARAMETER";
            case EGL14.EGL_BAD_SURFACE: return "EGL_BAD_SURFACE";
            case EGL14.EGL_CONTEXT_LOST: return "EGL_CONTEXT_LOST";
            default: return "UNKNOWN";
        }
    }
}
```

### 7.2 常见崩溃场景与解决方案

**场景1：eglCreateWindowSurface failed**

```java
// 问题：Surface已销毁或无效
// 症状：返回EGL_NO_SURFACE，错误码EGL_BAD_NATIVE_WINDOW

// 解决方案
public EGLSurface createSurfaceSafe(EGLDisplay display, EGLConfig config, Surface surface) {
    // 1. 检查Surface有效性
    if (surface == null || !surface.isValid()) {
        Log.e(TAG, "Surface is invalid");
        return EGL14.EGL_NO_SURFACE;
    }
    
    // 2. 尝试创建
    int[] attribs = { EGL14.EGL_NONE };
    EGLSurface eglSurface = EGL14.eglCreateWindowSurface(display, config, surface, attribs, 0);
    
    // 3. 检查结果
    if (eglSurface == EGL14.EGL_NO_SURFACE) {
        int error = EGL14.eglGetError();
        if (error == EGL14.EGL_BAD_NATIVE_WINDOW) {
            Log.e(TAG, "Native window is invalid - Surface may have been destroyed");
            // 等待新Surface或重新请求
        } else {
            Log.e(TAG, "eglCreateWindowSurface failed: " + error);
        }
    }
    
    return eglSurface;
}
```

**场景2：eglMakeCurrent failed**

```java
// 问题：线程冲突或上下文无效
// 症状：返回false，可能是EGL_BAD_ACCESS或EGL_BAD_CONTEXT

// 解决方案
public boolean makeCurrentSafe(EGLDisplay display, EGLSurface surface, EGLContext context) {
    // 1. 检查是否在正确的线程
    if (context != EGL14.EGL_NO_CONTEXT) {
        // Context应该只在创建它的线程或之前解绑的线程使用
    }
    
    // 2. 先解绑其他线程的Context（如果需要）
    // 注意：这应该在其他线程执行
    
    // 3. 绑定
    boolean result = EGL14.eglMakeCurrent(display, surface, surface, context);
    if (!result) {
        int error = EGL14.eglGetError();
        switch (error) {
            case EGL14.EGL_BAD_ACCESS:
                Log.e(TAG, "Context is already current on another thread");
                break;
            case EGL14.EGL_BAD_CONTEXT:
                Log.e(TAG, "Context is invalid (may have been destroyed)");
                break;
            case EGL14.EGL_BAD_SURFACE:
                Log.e(TAG, "Surface is invalid");
                break;
            default:
                Log.e(TAG, "eglMakeCurrent failed: " + error);
        }
    }
    
    return result;
}
```

**场景3：eglSwapBuffers failed**

```java
// 问题：Surface丢失（如Activity暂停）
// 症状：返回false，错误码EGL_BAD_SURFACE

// 解决方案
public boolean swapBuffersSafe(EGLDisplay display, EGLSurface surface) {
    boolean result = EGL14.eglSwapBuffers(display, surface);
    
    if (!result) {
        int error = EGL14.eglGetError();
        switch (error) {
            case EGL14.EGL_BAD_SURFACE:
                // Surface丢失，需要重新创建
                Log.w(TAG, "Surface lost, need to recreate");
                handleSurfaceLost();
                return false;
                
            case EGL14.EGL_CONTEXT_LOST:
                // GPU重置，需要重建所有资源
                Log.e(TAG, "Context lost, need to recreate everything");
                handleContextLost();
                return false;
                
            default:
                Log.e(TAG, "eglSwapBuffers failed: " + error);
        }
    }
    
    return result;
}

private void handleSurfaceLost() {
    // 1. 销毁旧Surface
    EGL14.eglDestroySurface(mEGLDisplay, mEGLSurface);
    mEGLSurface = EGL14.EGL_NO_SURFACE;
    
    // 2. 等待新Surface（通过SurfaceHolder.Callback）
    // 3. 创建新的EGLSurface
}

private void handleContextLost() {
    // 1. 清理所有EGL资源
    // 2. 重新初始化EGL
    // 3. 重新创建所有GL资源（纹理、着色器等）
}
```

### 7.3 EGL与Activity生命周期

**正确处理生命周期**：

```java
public class EGLActivity extends Activity {
    private EGLRenderer mRenderer;
    
    @Override
    protected void onResume() {
        super.onResume();
        // Surface可能在此时可用
        if (mRenderer != null) {
            mRenderer.onResume();
        }
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        // Surface即将不可用
        if (mRenderer != null) {
            mRenderer.onPause();
        }
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        // 彻底清理
        if (mRenderer != null) {
            mRenderer.release();
        }
    }
}

public class EGLRenderer {
    private volatile boolean mPaused = false;
    
    public void onPause() {
        mPaused = true;
        // 可选：释放EGL Surface以节省内存
        // 但保留Context以复用GL资源
    }
    
    public void onResume() {
        mPaused = false;
        // 如果Surface已释放，等待新Surface创建
        // 如果Surface仍有效，继续渲染
    }
}
```

### 7.4 多线程EGL问题

**问题1：同一Context被多个线程使用**

```java
// 错误示例
Thread thread1 = new Thread(() -> {
    EGL14.eglMakeCurrent(display, surface, surface, context);
    // 渲染操作...
});

Thread thread2 = new Thread(() -> {
    // 错误！context已被thread1绑定
    EGL14.eglMakeCurrent(display, surface, surface, context);
});

// 正确做法：每个线程使用独立Context
EGLContext contextThread1 = eglCreateContext(...);
EGLContext contextThread2 = eglCreateContext(display, config, contextThread1, attribs);  // 共享
```

**问题2：线程间传递EGL对象**

```java
// 注意事项：
// 1. EGLContext只能在一个线程中使用
// 2. 纹理ID可以跨共享Context使用，但需要同步
// 3. 使用glFlush/glFinish确保命令完成

public class TextureProducer {
    private EGLContext mProducerContext;  // 共享Context
    private int mTextureId;
    private Object mLock = new Object();
    
    public void produceTexture() {
        EGL14.eglMakeCurrent(display, pbuffer, pbuffer, mProducerContext);
        
        // 渲染到纹理
        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER, fbo);
        drawToTexture();
        
        // 确保渲染完成
        GLES30.glFlush();
        
        synchronized (mLock) {
            mTextureId = textureId;
            mLock.notifyAll();
        }
    }
}

public class TextureConsumer {
    public int waitForTexture() {
        synchronized (mLock) {
            while (mTextureId == 0) {
                mLock.wait();
            }
            return mTextureId;
        }
    }
}
```

### 7.5 调试工具

**1. eglGetError()的正确使用**：

```java
// 每次EGL调用后检查错误
EGLSurface surface = EGL14.eglCreateWindowSurface(display, config, window, attribs, 0);
int error = EGL14.eglGetError();
if (error != EGL14.EGL_SUCCESS) {
    Log.e(TAG, "EGL error: " + error);
}

// 注意：eglGetError会清除错误状态，多次调用会返回EGL_SUCCESS
```

**2. Android GPU Inspector**：

```
使用步骤：
1. 下载Android GPU Inspector (AGI)
2. 连接设备并启动应用
3. 捕获帧进行分析
4. 查看GL命令、纹理、着色器等详细信息
```

**3. RenderDoc for Android**：

```
使用步骤：
1. 安装RenderDoc
2. 在AndroidManifest中启用调试
3. 使用RenderDoc启动应用
4. 按F12捕获帧
5. 分析绘制调用、资源等
```

**4. systrace中的GPU相关trace**：

```bash
# 捕获包含GPU信息的systrace
python systrace.py -o trace.html -t 10 gfx view sched freq

# 查看关键指标：
# - SurfaceFlinger的合成时间
# - GPU工作队列
# - Buffer交换时间
# - 帧率和丢帧
```

---

## 总结

### EGL核心流程全景图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EGL与OpenGL ES渲染全景                           │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        初始化阶段                                │    │
│  │                                                                  │    │
│  │   eglGetDisplay → eglInitialize → eglChooseConfig               │    │
│  │         │                │               │                       │    │
│  │         ▼                ▼               ▼                       │    │
│  │   [EGLDisplay]     [版本信息]      [EGLConfig]                   │    │
│  │                                                                  │    │
│  │   eglCreateWindowSurface → eglCreateContext → eglMakeCurrent    │    │
│  │             │                    │                │              │    │
│  │             ▼                    ▼                ▼              │    │
│  │      [EGLSurface]         [EGLContext]     [线程绑定完成]        │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        渲染循环阶段                              │    │
│  │                                                                  │    │
│  │   while (running) {                                              │    │
│  │       ┌─────────────────────────────────────────────────────┐   │    │
│  │       │           OpenGL ES 渲染命令                         │   │    │
│  │       │                                                      │   │    │
│  │       │   glClear()        清除缓冲区                        │   │    │
│  │       │   glUseProgram()   绑定着色器                        │   │    │
│  │       │   glBindTexture()  绑定纹理                          │   │    │
│  │       │   glDrawArrays()   绘制图形                          │   │    │
│  │       │                                                      │   │    │
│  │       └─────────────────────────────────────────────────────┘   │    │
│  │                          │                                       │    │
│  │                          ▼                                       │    │
│  │       ┌─────────────────────────────────────────────────────┐   │    │
│  │       │           eglSwapBuffers()                           │   │    │
│  │       │                                                      │   │    │
│  │       │   1. GPU完成渲染                                     │   │    │
│  │       │   2. queueBuffer() → BufferQueue                     │   │    │
│  │       │   3. dequeueBuffer() ← 获取下一缓冲区                 │   │    │
│  │       │   4. 等待VSYNC（如果Interval=1）                      │   │    │
│  │       │                                                      │   │    │
│  │       └─────────────────────────────────────────────────────┘   │    │
│  │   }                                                              │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        清理阶段                                  │    │
│  │                                                                  │    │
│  │   eglMakeCurrent(NO_SURFACE, NO_CONTEXT)  解绑Context           │    │
│  │                    │                                             │    │
│  │                    ▼                                             │    │
│  │   eglDestroySurface()  销毁Surface                               │    │
│  │                    │                                             │    │
│  │                    ▼                                             │    │
│  │   eglDestroyContext()  销毁Context                               │    │
│  │                    │                                             │    │
│  │                    ▼                                             │    │
│  │   eglTerminate()  终止Display                                    │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 关键知识点回顾

1. **EGL的核心定位**：连接OpenGL ES与平台窗口系统的桥梁，提供上下文管理、Surface创建、缓冲区交换

2. **三大核心对象**：
   - EGLDisplay：显示设备抽象，所有EGL资源的根
   - EGLSurface：渲染目标（Window/PBuffer/Pixmap）
   - EGLContext：OpenGL ES状态容器，线程独占

3. **初始化六步曲**：getDisplay → Initialize → ChooseConfig → CreateSurface → CreateContext → MakeCurrent

4. **eglSwapBuffers的关键作用**：触发BufferQueue的dequeue/queue流程，实现帧提交

5. **资源释放顺序**：MakeCurrent(NO) → DestroySurface → DestroyContext → Terminate

6. **多线程注意事项**：Context线程独占、使用SharedContext共享资源、Fence同步

7. **性能优化要点**：合理选择EGLConfig、减少Context切换、使用Fence同步

8. **常见问题处理**：Surface丢失重建、Context丢失恢复、线程冲突避免

---

## 参考资源

1. **Khronos EGL规范**
   - https://www.khronos.org/registry/EGL/
   - EGL 1.5 Specification

2. **AOSP源码路径**
   - EGL实现：`frameworks/native/opengl/libs/EGL/`
   - Surface：`frameworks/native/libs/gui/Surface.cpp`
   - BufferQueue：`frameworks/native/libs/gui/BufferQueue*.cpp`
   - GLSurfaceView：`frameworks/base/opengl/java/android/opengl/GLSurfaceView.java`

3. **Android官方文档**
   - https://developer.android.com/training/graphics/opengl
   - https://source.android.com/docs/core/graphics

4. **调试工具**
   - Android GPU Inspector：https://gpuinspector.dev/
   - RenderDoc：https://renderdoc.org/

5. **推荐学习资源**
   - 《OpenGL ES 3.0 Programming Guide》
   - 《Android图形系统深度剖析》

---

> 本文从源码角度深入分析了EGL与OpenGL ES渲染管线的完整工作机制。理解这些原理，对于Android GPU渲染开发、性能优化和问题排查至关重要。
```


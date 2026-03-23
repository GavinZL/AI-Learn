# Pipeline集成与系统优化详细解析

> 构建高效、低延迟的图像处理流水线系统

---

## 目录

1. [端到端Pipeline设计](#1-端到端pipeline设计)
2. [内存管理优化](#2-内存管理优化)
3. [功耗优化](#3-功耗优化)
4. [延迟优化](#4-延迟优化)
5. [可测试性设计](#5-可测试性设计)

---

## 1. 端到端Pipeline设计

### 1.1 Pipeline拓扑结构

```
Pipeline拓扑类型对比：

┌─────────────────────────────────────────────────────────────────────┐
│                    线性Pipeline (Linear)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐             │
│  │ 输入 │──→│ 去噪 │──→│ 缩放 │──→│ 增强 │──→│ 输出 │             │
│  └──────┘   └──────┘   └──────┘   └──────┘   └──────┘             │
│                                                                      │
│  特点：                                                              │
│  • 实现简单，易于理解和调试                                          │
│  • 每个阶段只有一个前驱和后继                                        │
│  • 延迟 = 各阶段延迟之和                                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    DAG Pipeline (Directed Acyclic Graph)            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                    ┌──────────┐                                     │
│              ┌────→│ 人脸检测 │────┐                                │
│              │     └──────────┘    │                                │
│  ┌──────┐   │                      ▼     ┌──────┐                  │
│  │ 输入 │───┼─────────────────→┌──────┐──→│ 输出 │                  │
│  └──────┘   │                  │ 合成  │  └──────┘                  │
│              │     ┌──────────┐│      │                             │
│              └────→│ 背景虚化 │┘      │                             │
│                    └──────────┘       │                             │
│                         ↑             │                             │
│                    ┌──────────┐       │                             │
│                    │ 深度估计 │───────┘                             │
│                    └──────────┘                                     │
│                                                                      │
│  特点：                                                              │
│  • 支持分支和并行处理                                                │
│  • 可表达复杂的依赖关系                                              │
│  • 需要依赖管理和调度器                                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 模块间数据流设计

```cpp
// 数据流设计模式

// 1. Push模式（生产者驱动）
class PushPipeline {
public:
    void onNewFrame(Frame* frame) {
        // 处理帧并推送到下游
        Frame* processed = process(frame);
        if (downstream) {
            downstream->onNewFrame(processed);
        }
    }
    
private:
    PipelineStage* downstream = nullptr;
};

// 2. Pull模式（消费者驱动）
class PullPipeline {
public:
    Frame* getNextFrame() {
        // 从上游拉取帧
        Frame* input = upstream->getNextFrame();
        if (input) {
            return process(input);
        }
        return nullptr;
    }
    
private:
    PipelineStage* upstream = nullptr;
};

// 3. Push-Pull混合模式（推荐）
class HybridPipeline {
public:
    // 输入端使用Push
    void submitFrame(Frame* frame) {
        std::lock_guard<std::mutex> lock(queueMutex);
        inputQueue.push(frame);
        cv.notify_one();
    }
    
    // 处理线程使用Pull
    void processingThread() {
        while (running) {
            Frame* frame = nullptr;
            {
                std::unique_lock<std::mutex> lock(queueMutex);
                cv.wait(lock, [&] { return !inputQueue.empty() || !running; });
                if (!running) break;
                frame = inputQueue.front();
                inputQueue.pop();
            }
            
            Frame* result = process(frame);
            
            // 输出端使用Push
            if (outputCallback) {
                outputCallback(result);
            }
        }
    }
    
private:
    std::queue<Frame*> inputQueue;
    std::mutex queueMutex;
    std::condition_variable cv;
    std::function<void(Frame*)> outputCallback;
    bool running = true;
};
```

```
数据流架构图：

┌─────────────────────────────────────────────────────────────────────┐
│                    典型Camera Pipeline数据流                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Camera HAL                                                      ││
│  │  ┌─────────┐                                                    ││
│  │  │ Sensor  │──RAW──┐                                            ││
│  │  └─────────┘       │                                            ││
│  │                    ▼                                            ││
│  │  ┌───────────────────────────────┐                              ││
│  │  │         ISP Pipeline          │                              ││
│  │  │  BLC→LSC→WB→Demosaic→CCM→Gamma│                              ││
│  │  └───────────────┬───────────────┘                              ││
│  │                  │                                              ││
│  │                  ▼ YUV                                          ││
│  └──────────────────┼──────────────────────────────────────────────┘│
│                     │                                                │
│  ┌──────────────────┼──────────────────────────────────────────────┐│
│  │  Application Pipeline                                           ││
│  │                  │                                              ││
│  │        ┌─────────┴─────────┐                                    ││
│  │        ▼                   ▼                                    ││
│  │  ┌──────────┐        ┌──────────┐                               ││
│  │  │ Preview  │        │ Capture  │                               ││
│  │  │ Path     │        │ Path     │                               ││
│  │  └────┬─────┘        └────┬─────┘                               ││
│  │       │                   │                                     ││
│  │       ▼                   ▼                                     ││
│  │  ┌──────────┐        ┌──────────┐                               ││
│  │  │ 美颜/滤镜│        │ HDR合成  │                               ││
│  │  └────┬─────┘        └────┬─────┘                               ││
│  │       │                   │                                     ││
│  │       ▼                   ▼                                     ││
│  │  ┌──────────┐        ┌──────────┐                               ││
│  │  │ Display  │        │ Encoder  │                               ││
│  │  └──────────┘        └──────────┘                               ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 缓冲区管理策略

```cpp
// 缓冲区管理设计

// 1. 零拷贝设计
class ZeroCopyBuffer {
public:
    // 使用引用计数管理生命周期
    void addRef() { refCount.fetch_add(1); }
    void release() {
        if (refCount.fetch_sub(1) == 1) {
            returnToPool();
        }
    }
    
    // 直接返回底层内存地址
    void* getData() { return data; }
    size_t getSize() const { return size; }
    
    // 支持跨进程共享（Android ION/iOS IOSurface）
    int getFd() const { return fd; }
    
private:
    void* data;
    size_t size;
    int fd;  // DMA-BUF文件描述符
    std::atomic<int> refCount{1};
    BufferPool* pool;
    
    void returnToPool() {
        if (pool) {
            pool->recycle(this);
        }
    }
};

// 2. 双缓冲（用于异步处理）
template<typename T>
class DoubleBuffer {
public:
    T* getFrontBuffer() { return &buffers[frontIndex]; }
    T* getBackBuffer() { return &buffers[1 - frontIndex]; }
    
    void swap() {
        std::lock_guard<std::mutex> lock(mutex);
        frontIndex = 1 - frontIndex;
    }
    
private:
    T buffers[2];
    int frontIndex = 0;
    std::mutex mutex;
};

// 3. 三缓冲（平衡延迟和吞吐量）
template<typename T>
class TripleBuffer {
public:
    // 生产者端
    T* getWriteBuffer() {
        std::lock_guard<std::mutex> lock(mutex);
        return &buffers[writeIndex];
    }
    
    void publish() {
        std::lock_guard<std::mutex> lock(mutex);
        std::swap(writeIndex, pendingIndex);
        newDataAvailable = true;
    }
    
    // 消费者端
    T* getReadBuffer() {
        std::lock_guard<std::mutex> lock(mutex);
        if (newDataAvailable) {
            std::swap(readIndex, pendingIndex);
            newDataAvailable = false;
        }
        return &buffers[readIndex];
    }
    
private:
    T buffers[3];
    int writeIndex = 0;
    int pendingIndex = 1;
    int readIndex = 2;
    bool newDataAvailable = false;
    std::mutex mutex;
};
```

```
缓冲区策略对比：

┌─────────────────────────────────────────────────────────────────────┐
│  策略       │ 延迟    │ 吞吐量  │ 内存占用 │ 适用场景              │
├─────────────────────────────────────────────────────────────────────┤
│  单缓冲     │ 最低    │ 低      │ 最低     │ 同步处理              │
│  双缓冲     │ 中      │ 中      │ 中       │ 简单异步              │
│  三缓冲     │ 中      │ 高      │ 较高     │ 生产消费速度不匹配    │
│  环形缓冲   │ 可变    │ 最高    │ 高       │ 流式处理、丢帧容忍    │
│  零拷贝     │ 最低    │ 最高    │ 最低     │ 跨模块/跨进程         │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 Pipeline并行策略

```cpp
// Pipeline并行策略实现

// 1. 阶段并行（Pipeline Parallelism）
class StagePipeline {
public:
    void start() {
        for (int i = 0; i < stages.size(); i++) {
            threads.emplace_back([this, i] {
                while (running) {
                    Frame* input = stages[i]->waitForInput();
                    if (!input) continue;
                    
                    Frame* output = stages[i]->process(input);
                    
                    if (i + 1 < stages.size()) {
                        stages[i + 1]->submitInput(output);
                    } else {
                        onOutput(output);
                    }
                }
            });
        }
    }
    
    // 帧时间线：
    // Stage0: [F1][F2][F3][F4][F5]...
    // Stage1:     [F1][F2][F3][F4]...
    // Stage2:         [F1][F2][F3]...
    // 延迟 = N * 单阶段时间，但吞吐量 = 1帧/单阶段时间
    
private:
    std::vector<std::unique_ptr<Stage>> stages;
    std::vector<std::thread> threads;
    bool running = true;
};

// 2. 数据并行（Data Parallelism）
class DataParallelStage {
public:
    void process(Frame* frame) {
        int height = frame->height;
        int numThreads = std::thread::hardware_concurrency();
        int rowsPerThread = height / numThreads;
        
        std::vector<std::future<void>> futures;
        for (int t = 0; t < numThreads; t++) {
            int startRow = t * rowsPerThread;
            int endRow = (t == numThreads - 1) ? height : (t + 1) * rowsPerThread;
            
            futures.push_back(std::async(std::launch::async, [=] {
                processRows(frame, startRow, endRow);
            }));
        }
        
        for (auto& f : futures) {
            f.get();
        }
    }
    
private:
    void processRows(Frame* frame, int startRow, int endRow) {
        // 处理[startRow, endRow)范围的像素
    }
};

// 3. 任务并行（Task Parallelism）
class TaskParallelPipeline {
public:
    void process(Frame* frame) {
        // 独立任务并行执行
        auto faceTask = std::async(std::launch::async, [=] {
            return detectFaces(frame);
        });
        
        auto depthTask = std::async(std::launch::async, [=] {
            return estimateDepth(frame);
        });
        
        auto segmentTask = std::async(std::launch::async, [=] {
            return segmentImage(frame);
        });
        
        // 等待所有任务完成
        auto faces = faceTask.get();
        auto depth = depthTask.get();
        auto segments = segmentTask.get();
        
        // 合成最终结果（依赖上述结果）
        compose(frame, faces, depth, segments);
    }
};
```

```
并行策略可视化：

┌─────────────────────────────────────────────────────────────────────┐
│  阶段并行 (Pipeline Parallelism)                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  时间 →                                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ T1: [去噪F1][去噪F2][去噪F3][去噪F4][去噪F5]                  │  │
│  │ T2:        [缩放F1][缩放F2][缩放F3][缩放F4][缩放F5]          │  │
│  │ T3:               [增强F1][增强F2][增强F3][增强F4][增强F5]   │  │
│  │                          ↑每帧输出间隔相同                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  数据并行 (Data Parallelism)                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  图像分块：                                                          │
│  ┌────────┬────────┬────────┬────────┐                             │
│  │ Thread0│ Thread1│ Thread2│ Thread3│                             │
│  │  处理  │  处理  │  处理  │  处理  │                             │
│  │ 0-269行│270-539行│540-809行│810-1079│                            │
│  └────────┴────────┴────────┴────────┘                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 内存管理优化

### 2.1 图像内存布局

```
图像内存布局对比：

┌─────────────────────────────────────────────────────────────────────┐
│  Packed (交错) 布局                                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  内存地址 →                                                          │
│  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬─────────────┐  │
│  │R0 │G0 │B0 │R1 │G1 │B1 │R2 │G2 │B2 │R3 │G3 │B3 │ ...         │  │
│  └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴─────────────┘  │
│                                                                      │
│  优点：单像素访问高效、硬件友好                                       │
│  缺点：单通道处理效率低                                              │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Planar (平面) 布局                                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Y平面: ┌───┬───┬───┬───┬───┬───┬───┬───┬───────────────────────┐  │
│         │Y0 │Y1 │Y2 │Y3 │Y4 │Y5 │Y6 │Y7 │ ...                   │  │
│         └───┴───┴───┴───┴───┴───┴───┴───┴───────────────────────┘  │
│  U平面: ┌───┬───┬───┬───┬───────────────────────────────────────┐  │
│         │U0 │U1 │U2 │U3 │ ...                                   │  │
│         └───┴───┴───┴───┴───────────────────────────────────────┘  │
│  V平面: ┌───┬───┬───┬───┬───────────────────────────────────────┐  │
│         │V0 │V1 │V2 │V3 │ ...                                   │  │
│         └───┴───┴───┴───┴───────────────────────────────────────┘  │
│                                                                      │
│  优点：单通道SIMD处理高效                                            │
│  缺点：多次内存访问、缓存利用率可能较低                               │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Semi-planar (半平面) 布局 - NV12/NV21                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Y平面:  ┌───┬───┬───┬───┬───┬───┬───┬───┬──────────────────────┐  │
│          │Y0 │Y1 │Y2 │Y3 │Y4 │Y5 │Y6 │Y7 │ ...                  │  │
│          └───┴───┴───┴───┴───┴───┴───┴───┴──────────────────────┘  │
│  UV交错: ┌───┬───┬───┬───┬───┬───┬───┬───┬──────────────────────┐  │
│          │U0 │V0 │U1 │V1 │U2 │V2 │U3 │V3 │ ...                  │  │
│          └───┴───┴───┴───┴───┴───┴───┴───┴──────────────────────┘  │
│                                                                      │
│  优点：硬件codec友好、Y平面处理高效                                   │
│  应用：视频编解码、Camera输出                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 内存对齐与Stride

```cpp
// 内存对齐实现

// 计算对齐的stride
inline int alignStride(int width, int alignment) {
    return (width + alignment - 1) & ~(alignment - 1);
}

// 典型对齐要求
struct AlignmentRequirements {
    static constexpr int CACHE_LINE = 64;      // CPU缓存行
    static constexpr int SIMD_128 = 16;        // SSE/NEON
    static constexpr int SIMD_256 = 32;        // AVX
    static constexpr int SIMD_512 = 64;        // AVX-512
    static constexpr int GPU_TEXTURE = 256;    // GPU纹理
    static constexpr int DMA = 4096;           // DMA传输（页对齐）
};

class AlignedImage {
public:
    AlignedImage(int width, int height, int channels, int alignment = 64) {
        this->width = width;
        this->height = height;
        this->channels = channels;
        
        // 计算对齐的stride
        stride = alignStride(width * channels, alignment);
        
        // 分配对齐的内存
        size_t totalSize = stride * height + alignment;
        rawData = new uint8_t[totalSize];
        
        // 计算对齐的起始地址
        uintptr_t addr = reinterpret_cast<uintptr_t>(rawData);
        uintptr_t alignedAddr = (addr + alignment - 1) & ~(alignment - 1);
        data = reinterpret_cast<uint8_t*>(alignedAddr);
    }
    
    ~AlignedImage() {
        delete[] rawData;
    }
    
    // 获取指定行的指针
    uint8_t* getRow(int y) {
        return data + y * stride;
    }
    
    // 填充区域（stride > width*channels时的无效数据）
    void fillPadding(uint8_t value) {
        int rowWidth = width * channels;
        for (int y = 0; y < height; y++) {
            memset(data + y * stride + rowWidth, value, stride - rowWidth);
        }
    }
    
private:
    uint8_t* rawData;  // 原始分配的指针
    uint8_t* data;     // 对齐后的指针
    int width, height, channels;
    int stride;
};
```

### 2.3 内存池设计

```cpp
// 高性能内存池

template<typename T>
class ObjectPool {
public:
    ObjectPool(size_t initialSize = 16) {
        for (size_t i = 0; i < initialSize; i++) {
            pool.push(createNew());
        }
    }
    
    ~ObjectPool() {
        while (!pool.empty()) {
            delete pool.top();
            pool.pop();
        }
    }
    
    T* acquire() {
        std::lock_guard<std::mutex> lock(mutex);
        if (pool.empty()) {
            return createNew();
        }
        T* obj = pool.top();
        pool.pop();
        return obj;
    }
    
    void release(T* obj) {
        std::lock_guard<std::mutex> lock(mutex);
        obj->reset();  // 重置状态
        pool.push(obj);
    }
    
private:
    T* createNew() {
        return new T();
    }
    
    std::stack<T*> pool;
    std::mutex mutex;
};

// 帧缓冲池
class FrameBufferPool {
public:
    struct FrameBuffer {
        uint8_t* data;
        size_t size;
        int width, height;
        int format;
        std::atomic<int> refCount{0};
        
        void addRef() { refCount.fetch_add(1); }
        void release() {
            if (refCount.fetch_sub(1) == 1) {
                // 返回池
            }
        }
    };
    
    FrameBufferPool(int width, int height, int format, int poolSize) {
        size_t bufferSize = calculateBufferSize(width, height, format);
        
        for (int i = 0; i < poolSize; i++) {
            FrameBuffer* fb = new FrameBuffer();
            fb->data = allocateAligned(bufferSize, 64);
            fb->size = bufferSize;
            fb->width = width;
            fb->height = height;
            fb->format = format;
            freeBuffers.push(fb);
        }
    }
    
    FrameBuffer* acquire() {
        std::unique_lock<std::mutex> lock(mutex);
        cv.wait(lock, [&] { return !freeBuffers.empty(); });
        
        FrameBuffer* fb = freeBuffers.front();
        freeBuffers.pop();
        fb->addRef();
        return fb;
    }
    
    void release(FrameBuffer* fb) {
        if (fb->refCount.fetch_sub(1) == 1) {
            std::lock_guard<std::mutex> lock(mutex);
            freeBuffers.push(fb);
            cv.notify_one();
        }
    }
    
private:
    std::queue<FrameBuffer*> freeBuffers;
    std::mutex mutex;
    std::condition_variable cv;
    
    static uint8_t* allocateAligned(size_t size, size_t alignment) {
        void* ptr = nullptr;
        posix_memalign(&ptr, alignment, size);
        return static_cast<uint8_t*>(ptr);
    }
    
    static size_t calculateBufferSize(int width, int height, int format) {
        // 根据格式计算大小
        switch (format) {
            case FORMAT_NV12: return width * height * 3 / 2;
            case FORMAT_RGBA: return width * height * 4;
            default: return width * height * 3;
        }
    }
};
```

### 2.4 DMA与物理连续内存

```cpp
// Android ION / DMA-BUF 分配器
#ifdef __ANDROID__
#include <linux/ion.h>
#include <sys/ioctl.h>

class DMABufferAllocator {
public:
    DMABufferAllocator() {
        ionFd = open("/dev/ion", O_RDONLY);
        if (ionFd < 0) {
            // 尝试使用DMA-BUF heap
            ionFd = open("/dev/dma_heap/system", O_RDONLY);
        }
    }
    
    ~DMABufferAllocator() {
        if (ionFd >= 0) close(ionFd);
    }
    
    struct DMABuffer {
        int fd;           // DMA-BUF文件描述符
        void* vaddr;      // 虚拟地址映射
        size_t size;
    };
    
    DMABuffer* allocate(size_t size, unsigned int flags = 0) {
        DMABuffer* buf = new DMABuffer();
        buf->size = size;
        
        // ION分配
        struct ion_allocation_data allocData = {};
        allocData.len = size;
        allocData.heap_id_mask = ION_HEAP_SYSTEM_MASK;
        allocData.flags = flags;
        
        if (ioctl(ionFd, ION_IOC_ALLOC, &allocData) < 0) {
            delete buf;
            return nullptr;
        }
        
        buf->fd = allocData.fd;
        
        // 映射到用户空间
        buf->vaddr = mmap(nullptr, size, PROT_READ | PROT_WRITE,
                          MAP_SHARED, buf->fd, 0);
        
        return buf;
    }
    
    void free(DMABuffer* buf) {
        if (buf->vaddr != MAP_FAILED) {
            munmap(buf->vaddr, buf->size);
        }
        close(buf->fd);
        delete buf;
    }
    
private:
    int ionFd;
};
#endif

// iOS IOSurface
#ifdef __APPLE__
#include <IOSurface/IOSurface.h>

class IOSurfaceAllocator {
public:
    struct SurfaceBuffer {
        IOSurfaceRef surface;
        void* baseAddress;
        size_t width, height;
        size_t bytesPerRow;
    };
    
    SurfaceBuffer* allocate(size_t width, size_t height, OSType pixelFormat) {
        NSDictionary* props = @{
            (id)kIOSurfaceWidth: @(width),
            (id)kIOSurfaceHeight: @(height),
            (id)kIOSurfacePixelFormat: @(pixelFormat),
            (id)kIOSurfaceBytesPerElement: @(4),
        };
        
        IOSurfaceRef surface = IOSurfaceCreate((CFDictionaryRef)props);
        if (!surface) return nullptr;
        
        SurfaceBuffer* buf = new SurfaceBuffer();
        buf->surface = surface;
        buf->width = width;
        buf->height = height;
        buf->bytesPerRow = IOSurfaceGetBytesPerRow(surface);
        
        return buf;
    }
    
    void lock(SurfaceBuffer* buf) {
        IOSurfaceLock(buf->surface, 0, nullptr);
        buf->baseAddress = IOSurfaceGetBaseAddress(buf->surface);
    }
    
    void unlock(SurfaceBuffer* buf) {
        IOSurfaceUnlock(buf->surface, 0, nullptr);
        buf->baseAddress = nullptr;
    }
    
    void free(SurfaceBuffer* buf) {
        CFRelease(buf->surface);
        delete buf;
    }
};
#endif
```

---

## 3. 功耗优化

### 3.1 移动端功耗模型

```
移动端功耗构成：

┌─────────────────────────────────────────────────────────────────────┐
│                    SoC功耗分布模型                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  总功耗 = P_CPU + P_GPU + P_DDR + P_ISP + P_NPU + P_其他            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  组件      │ 空闲功耗 │ 峰值功耗 │ 典型占比 │ 优化潜力        │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  CPU       │  50mW   │  3000mW │  30-40%  │ 高              │ │
│  │  GPU       │  30mW   │  2500mW │  20-30%  │ 高              │ │
│  │  DDR       │  100mW  │  1500mW │  15-25%  │ 中              │ │
│  │  ISP       │  20mW   │  500mW  │  5-10%   │ 低（固定）      │ │
│  │  NPU       │  10mW   │  1000mW │  10-15%  │ 高效替代方案    │ │
│  │  显示      │  200mW  │  800mW  │  10-20%  │ 低              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  功耗与性能关系：                                                    │
│                                                                      │
│  功耗 ≈ C × V² × f                                                  │
│                                                                      │
│  其中：C = 电容（固定）                                              │
│        V = 电压（与频率相关）                                        │
│        f = 频率                                                      │
│                                                                      │
│  降频50% → 功耗降低约75%（电压也会降低）                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 降分辨率处理策略

```cpp
// 自适应分辨率处理

class AdaptiveResolutionProcessor {
public:
    enum Quality {
        FULL,      // 原始分辨率
        HIGH,      // 3/4分辨率
        MEDIUM,    // 1/2分辨率
        LOW        // 1/4分辨率
    };
    
    void setQuality(Quality q) {
        quality = q;
        updateScaleFactors();
    }
    
    void process(const Frame* input, Frame* output) {
        Frame* workingFrame = input;
        Frame* scaledFrame = nullptr;
        
        // 步骤1：可选的下采样
        if (scaleFactor < 1.0f) {
            scaledFrame = downscale(input, scaleFactor);
            workingFrame = scaledFrame;
        }
        
        // 步骤2：在低分辨率下处理
        Frame* processed = processAtScale(workingFrame);
        
        // 步骤3：可选的上采样
        if (scaleFactor < 1.0f) {
            upscale(processed, output, input->width, input->height);
            releaseFrame(processed);
            releaseFrame(scaledFrame);
        } else {
            copyFrame(processed, output);
            releaseFrame(processed);
        }
    }
    
    // 功耗估算
    float estimatePowerSaving() {
        // 处理量与分辨率的平方成正比
        return 1.0f - (scaleFactor * scaleFactor);
    }
    
private:
    Quality quality = FULL;
    float scaleFactor = 1.0f;
    
    void updateScaleFactors() {
        switch (quality) {
            case FULL:   scaleFactor = 1.0f; break;
            case HIGH:   scaleFactor = 0.75f; break;
            case MEDIUM: scaleFactor = 0.5f; break;
            case LOW:    scaleFactor = 0.25f; break;
        }
    }
    
    Frame* downscale(const Frame* src, float scale) {
        int newWidth = static_cast<int>(src->width * scale);
        int newHeight = static_cast<int>(src->height * scale);
        // 使用快速下采样算法
        return bilinearDownscale(src, newWidth, newHeight);
    }
    
    void upscale(const Frame* src, Frame* dst, int targetWidth, int targetHeight) {
        // 使用适当的上采样算法
        bilinearUpscale(src, dst, targetWidth, targetHeight);
    }
};
```

### 3.3 自适应处理质量

```cpp
// 基于设备状态的自适应处理

class AdaptiveQualityController {
public:
    struct DeviceState {
        float batteryLevel;      // 0-100
        float temperature;       // 摄氏度
        bool isCharging;
        int thermalState;        // 0=正常, 1=中等, 2=严重, 3=临界
    };
    
    struct ProcessingConfig {
        float denoiseStrength;
        float sharpenStrength;
        int resolutionScale;     // 百分比: 25, 50, 75, 100
        bool enableHDR;
        bool enableAI;
        int maxFPS;
    };
    
    ProcessingConfig getConfig(const DeviceState& state) {
        ProcessingConfig config;
        
        // 基于温度调整
        if (state.thermalState >= 2) {
            // 严重过热：最低质量
            config.resolutionScale = 50;
            config.enableHDR = false;
            config.enableAI = false;
            config.maxFPS = 15;
            config.denoiseStrength = 0.3f;
            config.sharpenStrength = 0.2f;
        } else if (state.thermalState == 1) {
            // 中等温度：降低质量
            config.resolutionScale = 75;
            config.enableHDR = false;
            config.enableAI = true;
            config.maxFPS = 24;
            config.denoiseStrength = 0.5f;
            config.sharpenStrength = 0.4f;
        } else {
            // 正常温度
            config.resolutionScale = 100;
            config.enableHDR = true;
            config.enableAI = true;
            config.maxFPS = 30;
            config.denoiseStrength = 0.7f;
            config.sharpenStrength = 0.6f;
        }
        
        // 基于电量调整
        if (!state.isCharging && state.batteryLevel < 20) {
            config.resolutionScale = std::min(config.resolutionScale, 50);
            config.enableHDR = false;
            config.maxFPS = std::min(config.maxFPS, 15);
        } else if (!state.isCharging && state.batteryLevel < 50) {
            config.resolutionScale = std::min(config.resolutionScale, 75);
            config.maxFPS = std::min(config.maxFPS, 24);
        }
        
        return config;
    }
    
    // 平滑过渡（避免突变）
    ProcessingConfig smoothTransition(const ProcessingConfig& current,
                                       const ProcessingConfig& target,
                                       float alpha = 0.1f) {
        ProcessingConfig result;
        result.denoiseStrength = lerp(current.denoiseStrength, 
                                       target.denoiseStrength, alpha);
        result.sharpenStrength = lerp(current.sharpenStrength,
                                       target.sharpenStrength, alpha);
        result.resolutionScale = static_cast<int>(
            lerp(static_cast<float>(current.resolutionScale),
                 static_cast<float>(target.resolutionScale), alpha));
        result.enableHDR = target.enableHDR;
        result.enableAI = target.enableAI;
        result.maxFPS = target.maxFPS;
        return result;
    }
    
private:
    float lerp(float a, float b, float t) {
        return a + t * (b - a);
    }
};
```

### 3.4 硬件ISP vs 软件处理功耗对比

```
┌─────────────────────────────────────────────────────────────────────┐
│                    处理方式功耗对比                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  场景：1080p 30fps 图像处理                                         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  处理方式           │ 功耗(mW) │ 延迟(ms) │ 质量    │ 灵活性  │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  硬件ISP            │  200     │  2       │ 固定    │ 低      │ │
│  │  CPU (标量)         │  2500    │  80      │ 可调    │ 高      │ │
│  │  CPU (NEON)         │  800     │  15      │ 可调    │ 高      │ │
│  │  GPU (OpenGL ES)    │  600     │  8       │ 可调    │ 中      │ │
│  │  GPU (Compute)      │  500     │  5       │ 可调    │ 高      │ │
│  │  DSP (Hexagon)      │  150     │  4       │ 可调    │ 中      │ │
│  │  NPU (AI处理)       │  300     │  6       │ 自适应  │ 低      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  最佳实践：                                                          │
│  • 优先使用硬件ISP进行基础处理                                       │
│  • 仅对需要自定义的环节使用软件处理                                  │
│  • 复杂AI处理使用NPU而非CPU/GPU                                      │
│  • 避免在CPU上进行大量像素级处理                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 延迟优化

### 4.1 端到端延迟分析

```
Camera到显示的延迟分解：

┌─────────────────────────────────────────────────────────────────────┐
│                    端到端延迟时间线                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  时间(ms) 0    10    20    30    40    50    60    70    80        │
│           │     │     │     │     │     │     │     │     │        │
│           ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼        │
│  ┌────────┬─────┬─────┬──────┬──────┬──────┬─────┬──────────────┐  │
│  │ Sensor │ ISP │Trans│ App  │Encode│Trans │Disp │              │  │
│  │ 曝光   │处理 │ fer │处理  │      │ fer  │     │              │  │
│  └────────┴─────┴─────┴──────┴──────┴──────┴─────┴──────────────┘  │
│  │← 16ms →│← 5ms│← 2ms│← 10ms│← 8ms │← 2ms │← 8ms│              │  │
│                                                                      │
│  典型延迟组成（30fps预览）：                                         │
│  • 传感器曝光：     16-33 ms （取决于帧率和曝光时间）                │
│  • ISP处理：        3-8 ms                                          │
│  • CPU/GPU后处理：  5-20 ms （取决于算法复杂度）                     │
│  • 显示刷新：       8-16 ms （60Hz = 16ms）                          │
│  ─────────────────────────────────                                  │
│  总计：             33-77 ms （约2-4帧延迟）                         │
│                                                                      │
│  直播/视频通话额外延迟：                                             │
│  • 编码：           10-50 ms                                        │
│  • 网络传输：       50-300 ms                                       │
│  • 解码：           10-30 ms                                        │
│  • 接收端显示：     8-16 ms                                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 流水线化降低延迟

```cpp
// 流水线处理实现

class PipelinedProcessor {
public:
    // 配置流水线深度
    PipelinedProcessor(int stages, int bufferDepth) {
        this->numStages = stages;
        this->bufferDepth = bufferDepth;
        
        // 为每个阶段创建缓冲队列
        for (int i = 0; i < stages; i++) {
            stageQueues.emplace_back();
            stageThreads.emplace_back([this, i] { stageWorker(i); });
        }
    }
    
    // 提交帧到流水线
    void submitFrame(Frame* frame) {
        frame->timestamp = getCurrentTime();
        stageQueues[0].push(frame);
    }
    
    // 获取处理完成的帧
    Frame* getResult() {
        return outputQueue.pop();
    }
    
    // 获取延迟统计
    struct LatencyStats {
        float avgLatency;    // 平均延迟
        float p95Latency;    // 95分位延迟
        float p99Latency;    // 99分位延迟
        float minLatency;
        float maxLatency;
    };
    
    LatencyStats getLatencyStats() {
        // 计算统计数据
        std::sort(latencyHistory.begin(), latencyHistory.end());
        
        LatencyStats stats;
        stats.minLatency = latencyHistory.front();
        stats.maxLatency = latencyHistory.back();
        
        float sum = 0;
        for (float l : latencyHistory) sum += l;
        stats.avgLatency = sum / latencyHistory.size();
        
        stats.p95Latency = latencyHistory[latencyHistory.size() * 95 / 100];
        stats.p99Latency = latencyHistory[latencyHistory.size() * 99 / 100];
        
        return stats;
    }
    
private:
    void stageWorker(int stageIndex) {
        while (running) {
            Frame* frame = stageQueues[stageIndex].pop();
            if (!frame) continue;
            
            // 处理当前阶段
            auto startTime = getCurrentTime();
            processStage(stageIndex, frame);
            auto endTime = getCurrentTime();
            
            // 记录阶段延迟
            frame->stageLatencies[stageIndex] = endTime - startTime;
            
            // 传递到下一阶段或输出
            if (stageIndex + 1 < numStages) {
                stageQueues[stageIndex + 1].push(frame);
            } else {
                // 记录总延迟
                float totalLatency = getCurrentTime() - frame->timestamp;
                latencyHistory.push_back(totalLatency);
                
                outputQueue.push(frame);
            }
        }
    }
    
    void processStage(int stage, Frame* frame) {
        switch (stage) {
            case 0: denoise(frame); break;
            case 1: colorCorrect(frame); break;
            case 2: sharpen(frame); break;
            case 3: scale(frame); break;
        }
    }
    
    int numStages;
    int bufferDepth;
    std::vector<ThreadSafeQueue<Frame*>> stageQueues;
    std::vector<std::thread> stageThreads;
    ThreadSafeQueue<Frame*> outputQueue;
    std::vector<float> latencyHistory;
    bool running = true;
};
```

### 4.3 预测性处理与异步执行

```cpp
// 预测性处理

class PredictiveProcessor {
public:
    // 基于历史数据预测下一帧特性
    struct FramePrediction {
        float brightness;
        float contrast;
        int motionLevel;  // 0=静止, 1=轻微, 2=中等, 3=剧烈
    };
    
    FramePrediction predictNextFrame() {
        FramePrediction pred;
        
        // 使用指数移动平均预测
        pred.brightness = emaPredict(brightnessHistory, 0.3f);
        pred.contrast = emaPredict(contrastHistory, 0.3f);
        pred.motionLevel = predictMotion();
        
        return pred;
    }
    
    // 基于预测预分配资源
    void prepareResources(const FramePrediction& pred) {
        // 根据亮度预测选择降噪强度
        if (pred.brightness < 30) {
            preallocateDenoiseBuffers(STRONG_DENOISE);
        } else {
            preallocateDenoiseBuffers(LIGHT_DENOISE);
        }
        
        // 根据运动预测选择处理策略
        if (pred.motionLevel >= 2) {
            // 高运动场景：降低处理质量换取速度
            setProcessingMode(FAST_MODE);
        } else {
            setProcessingMode(QUALITY_MODE);
        }
    }
    
private:
    std::deque<float> brightnessHistory;
    std::deque<float> contrastHistory;
    std::deque<int> motionHistory;
    
    float emaPredict(const std::deque<float>& history, float alpha) {
        if (history.empty()) return 0;
        
        float ema = history.front();
        for (size_t i = 1; i < history.size(); i++) {
            ema = alpha * history[i] + (1 - alpha) * ema;
        }
        // 预测下一个值（简单线性外推）
        if (history.size() >= 2) {
            float trend = history.back() - history[history.size() - 2];
            return ema + trend;
        }
        return ema;
    }
    
    int predictMotion() {
        if (motionHistory.size() < 2) return 0;
        
        // 基于历史运动趋势预测
        int sum = 0;
        for (int m : motionHistory) sum += m;
        return sum / motionHistory.size();
    }
};

// 异步处理管理器
class AsyncProcessingManager {
public:
    using Callback = std::function<void(Frame*)>;
    
    // 异步提交处理请求
    std::future<Frame*> submitAsync(Frame* input, Callback onComplete = nullptr) {
        auto promise = std::make_shared<std::promise<Frame*>>();
        auto future = promise->get_future();
        
        threadPool.submit([=] {
            Frame* result = process(input);
            
            if (onComplete) {
                onComplete(result);
            }
            
            promise->set_value(result);
        });
        
        return future;
    }
    
    // 批量异步处理
    std::vector<std::future<Frame*>> submitBatch(std::vector<Frame*>& inputs) {
        std::vector<std::future<Frame*>> futures;
        
        for (Frame* input : inputs) {
            futures.push_back(submitAsync(input));
        }
        
        return futures;
    }
    
    // 超时等待
    Frame* waitWithTimeout(std::future<Frame*>& future, 
                           std::chrono::milliseconds timeout) {
        auto status = future.wait_for(timeout);
        if (status == std::future_status::ready) {
            return future.get();
        }
        return nullptr;  // 超时
    }
    
private:
    ThreadPool threadPool;
    
    Frame* process(Frame* input) {
        // 实际处理逻辑
        return applyFilters(input);
    }
};
```

---

## 5. 可测试性设计

### 5.1 Pipeline中间结果Dump

```cpp
// 调试Dump系统

class DebugDumper {
public:
    enum DumpFormat {
        RAW_BYTES,    // 原始字节
        PNG,          // PNG图像
        YUV_FILE,     // YUV文件
        JSON_META     // JSON元数据
    };
    
    struct DumpConfig {
        bool enabled = false;
        std::string outputDir = "/tmp/debug";
        DumpFormat format = PNG;
        int maxFrames = 100;      // 最大dump帧数
        int frameInterval = 1;     // 每N帧dump一次
        std::set<std::string> stages;  // 要dump的阶段
    };
    
    void setConfig(const DumpConfig& config) {
        this->config = config;
        if (config.enabled) {
            createDirectory(config.outputDir);
        }
    }
    
    // 在Pipeline阶段调用
    void dumpStageOutput(const std::string& stageName, 
                          const Frame* frame, 
                          int frameIndex) {
        if (!config.enabled) return;
        if (frameIndex % config.frameInterval != 0) return;
        if (frameCount >= config.maxFrames) return;
        if (!config.stages.empty() && 
            config.stages.find(stageName) == config.stages.end()) return;
        
        std::string filename = generateFilename(stageName, frameIndex);
        
        switch (config.format) {
            case RAW_BYTES:
                dumpRaw(filename + ".bin", frame);
                break;
            case PNG:
                dumpPng(filename + ".png", frame);
                break;
            case YUV_FILE:
                dumpYuv(filename + ".yuv", frame);
                break;
            case JSON_META:
                dumpMetadata(filename + ".json", frame);
                break;
        }
        
        frameCount++;
    }
    
    // Dump比较（两帧差异）
    void dumpDiff(const std::string& name,
                   const Frame* a, const Frame* b) {
        if (!config.enabled) return;
        
        Frame* diff = computeDiff(a, b);
        
        std::string filename = config.outputDir + "/" + name + "_diff.png";
        dumpPng(filename, diff);
        
        // 计算统计信息
        DiffStats stats = computeDiffStats(diff);
        std::string statsFile = config.outputDir + "/" + name + "_stats.json";
        writeJson(statsFile, {
            {"psnr", stats.psnr},
            {"ssim", stats.ssim},
            {"maxDiff", stats.maxDiff},
            {"avgDiff", stats.avgDiff}
        });
        
        releaseFrame(diff);
    }
    
private:
    DumpConfig config;
    int frameCount = 0;
    
    std::string generateFilename(const std::string& stage, int frameIndex) {
        char buf[256];
        snprintf(buf, sizeof(buf), "%s/frame_%05d_%s", 
                 config.outputDir.c_str(), frameIndex, stage.c_str());
        return buf;
    }
    
    void dumpRaw(const std::string& filename, const Frame* frame) {
        FILE* f = fopen(filename.c_str(), "wb");
        fwrite(frame->data, 1, frame->size, f);
        fclose(f);
    }
    
    void dumpPng(const std::string& filename, const Frame* frame) {
        // 使用libpng或stb_image_write
        // 需要先转换为RGB格式
    }
    
    void dumpYuv(const std::string& filename, const Frame* frame) {
        FILE* f = fopen(filename.c_str(), "wb");
        // 写入Y平面
        fwrite(frame->yPlane, 1, frame->width * frame->height, f);
        // 写入UV平面
        fwrite(frame->uvPlane, 1, frame->width * frame->height / 2, f);
        fclose(f);
    }
    
    void dumpMetadata(const std::string& filename, const Frame* frame) {
        nlohmann::json j = {
            {"width", frame->width},
            {"height", frame->height},
            {"format", frame->formatString()},
            {"timestamp", frame->timestamp},
            {"exposureTime", frame->exposureTime},
            {"iso", frame->iso},
            {"whiteBalance", {frame->wbR, frame->wbG, frame->wbB}}
        };
        
        std::ofstream f(filename);
        f << j.dump(2);
    }
};
```

### 5.2 模块级Bypass测试

```cpp
// Bypass测试框架

class BypassTestFramework {
public:
    // 模块Bypass配置
    struct BypassConfig {
        bool bypassDenoise = false;
        bool bypassSharpen = false;
        bool bypassColorCorrect = false;
        bool bypassToneMap = false;
        bool bypassResize = false;
    };
    
    void setBypass(const BypassConfig& config) {
        this->bypass = config;
    }
    
    // 在Pipeline中检查bypass
    void processPipeline(Frame* frame) {
        // 去噪
        if (!bypass.bypassDenoise) {
            denoise(frame);
        } else {
            logBypass("denoise");
        }
        
        // 色彩校正
        if (!bypass.bypassColorCorrect) {
            colorCorrect(frame);
        } else {
            logBypass("colorCorrect");
        }
        
        // 锐化
        if (!bypass.bypassSharpen) {
            sharpen(frame);
        } else {
            logBypass("sharpen");
        }
        
        // 色调映射
        if (!bypass.bypassToneMap) {
            toneMap(frame);
        } else {
            logBypass("toneMap");
        }
        
        // 缩放
        if (!bypass.bypassResize) {
            resize(frame);
        } else {
            logBypass("resize");
        }
    }
    
    // A/B测试：比较有无某个模块的效果
    struct ABTestResult {
        std::string moduleName;
        float processingTimeWith;    // 开启时的处理时间
        float processingTimeWithout; // 关闭时的处理时间
        float psnrDiff;              // 图像质量差异
        float ssimDiff;
    };
    
    ABTestResult runABTest(const std::string& moduleName, 
                            const std::vector<Frame*>& testFrames) {
        ABTestResult result;
        result.moduleName = moduleName;
        
        // 运行开启模块的测试
        setModuleEnabled(moduleName, true);
        auto [timeWith, outputsWith] = processFrames(testFrames);
        
        // 运行关闭模块的测试
        setModuleEnabled(moduleName, false);
        auto [timeWithout, outputsWithout] = processFrames(testFrames);
        
        // 计算差异
        result.processingTimeWith = timeWith;
        result.processingTimeWithout = timeWithout;
        result.psnrDiff = computeAvgPSNR(outputsWith, outputsWithout);
        result.ssimDiff = computeAvgSSIM(outputsWith, outputsWithout);
        
        return result;
    }
    
private:
    BypassConfig bypass;
    
    void logBypass(const std::string& module) {
        // 记录bypass事件用于调试
    }
    
    void setModuleEnabled(const std::string& name, bool enabled) {
        if (name == "denoise") bypass.bypassDenoise = !enabled;
        else if (name == "sharpen") bypass.bypassSharpen = !enabled;
        else if (name == "colorCorrect") bypass.bypassColorCorrect = !enabled;
        else if (name == "toneMap") bypass.bypassToneMap = !enabled;
        else if (name == "resize") bypass.bypassResize = !enabled;
    }
};
```

### 5.3 回放测试（RAW录制与离线回放）

```cpp
// RAW录制与回放系统

class RawRecorder {
public:
    struct RecordingConfig {
        std::string outputPath;
        int maxFrames = 300;          // 最大录制帧数
        bool recordMetadata = true;    // 是否录制元数据
        bool compressRaw = false;      // 是否压缩RAW数据
    };
    
    void startRecording(const RecordingConfig& config) {
        this->config = config;
        recording = true;
        frameIndex = 0;
        
        // 创建输出目录
        createDirectory(config.outputPath);
        
        // 写入录制信息
        writeManifest();
    }
    
    void recordFrame(const RawFrame* raw, const FrameMetadata* meta) {
        if (!recording || frameIndex >= config.maxFrames) return;
        
        // 写入RAW数据
        std::string rawFile = getRawFilename(frameIndex);
        writeRawFile(rawFile, raw);
        
        // 写入元数据
        if (config.recordMetadata) {
            std::string metaFile = getMetaFilename(frameIndex);
            writeMetadata(metaFile, meta);
        }
        
        frameIndex++;
        
        if (frameIndex >= config.maxFrames) {
            stopRecording();
        }
    }
    
    void stopRecording() {
        recording = false;
        updateManifest();
    }
    
private:
    RecordingConfig config;
    bool recording = false;
    int frameIndex = 0;
    
    void writeRawFile(const std::string& filename, const RawFrame* raw) {
        FILE* f = fopen(filename.c_str(), "wb");
        
        // 写入头部
        RawFileHeader header;
        header.width = raw->width;
        header.height = raw->height;
        header.bitDepth = raw->bitDepth;
        header.bayerPattern = raw->bayerPattern;
        header.dataSize = raw->dataSize;
        fwrite(&header, sizeof(header), 1, f);
        
        // 写入RAW数据
        if (config.compressRaw) {
            // 使用LZ4压缩
            size_t compressedSize;
            void* compressed = compressLZ4(raw->data, raw->dataSize, &compressedSize);
            fwrite(compressed, 1, compressedSize, f);
            free(compressed);
        } else {
            fwrite(raw->data, 1, raw->dataSize, f);
        }
        
        fclose(f);
    }
    
    void writeMetadata(const std::string& filename, const FrameMetadata* meta) {
        nlohmann::json j = {
            {"timestamp", meta->timestamp},
            {"exposureTime", meta->exposureTime},
            {"iso", meta->iso},
            {"aperture", meta->aperture},
            {"focalLength", meta->focalLength},
            {"whiteBalance", {
                {"r", meta->wbGains[0]},
                {"g", meta->wbGains[1]},
                {"b", meta->wbGains[2]}
            }},
            {"colorMatrix", meta->colorMatrix},
            {"sensorTemperature", meta->sensorTemp}
        };
        
        std::ofstream f(filename);
        f << j.dump(2);
    }
};

class RawPlayer {
public:
    bool loadRecording(const std::string& path) {
        recordingPath = path;
        
        // 读取manifest
        if (!loadManifest()) return false;
        
        // 预加载元数据索引
        loadMetadataIndex();
        
        return true;
    }
    
    int getFrameCount() const {
        return manifest.frameCount;
    }
    
    // 获取指定帧
    RawFrame* getFrame(int index) {
        std::string rawFile = getRawFilename(index);
        return loadRawFile(rawFile);
    }
    
    FrameMetadata* getMetadata(int index) {
        std::string metaFile = getMetaFilename(index);
        return loadMetadata(metaFile);
    }
    
    // 回放处理测试
    void runPlaybackTest(Pipeline* pipeline, const std::string& outputPath) {
        for (int i = 0; i < getFrameCount(); i++) {
            RawFrame* raw = getFrame(i);
            FrameMetadata* meta = getMetadata(i);
            
            // 通过Pipeline处理
            Frame* result = pipeline->process(raw, meta);
            
            // 保存结果
            saveResult(outputPath, i, result);
            
            // 比较与参考结果
            Frame* reference = loadReference(i);
            if (reference) {
                compareWithReference(i, result, reference);
            }
            
            releaseFrame(result);
            releaseRawFrame(raw);
        }
        
        generateReport(outputPath);
    }
    
private:
    std::string recordingPath;
    Manifest manifest;
    
    void compareWithReference(int index, Frame* result, Frame* reference) {
        float psnr = computePSNR(result, reference);
        float ssim = computeSSIM(result, reference);
        
        // 记录比较结果
        comparisonResults.push_back({index, psnr, ssim});
        
        // 如果差异过大，标记为异常
        if (psnr < 30.0f || ssim < 0.9f) {
            anomalies.push_back({index, psnr, ssim});
        }
    }
    
    void generateReport(const std::string& outputPath) {
        // 生成测试报告
        nlohmann::json report = {
            {"totalFrames", getFrameCount()},
            {"anomalies", anomalies.size()},
            {"avgPSNR", computeAverage(comparisonResults, &Result::psnr)},
            {"avgSSIM", computeAverage(comparisonResults, &Result::ssim)},
            {"details", comparisonResults}
        };
        
        std::ofstream f(outputPath + "/report.json");
        f << report.dump(2);
    }
    
    std::vector<ComparisonResult> comparisonResults;
    std::vector<ComparisonResult> anomalies;
};
```

---

## 参考资源

### 技术文档

- [Android Camera HAL3](https://source.android.com/devices/camera/camera3)
- [Apple AVFoundation Programming Guide](https://developer.apple.com/documentation/avfoundation)
- [ARM Memory System Design](https://developer.arm.com/documentation/)

### 开源项目

- [libcamera](https://libcamera.org/) - Linux Camera框架
- [GStreamer](https://gstreamer.freedesktop.org/) - 多媒体Pipeline框架
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理框架

### 相关文档

- [SIMD与硬件加速_详细解析](./SIMD与硬件加速_详细解析.md)
- [跨平台实现差异_详细解析](./跨平台实现差异_详细解析.md)

# iOS Metal 渲染技术 — 金字塔结构深度解析

> **核心结论**：Metal 是 Apple 平台的底层图形与计算 API，采用统一内存架构（UMA）消除 CPU-GPU 数据拷贝，提供比 OpenGL ES 低 10 倍的 CPU 开销。掌握 Metal 需要理解其命令提交模型、管线状态预编译、资源存储模式三大核心设计，并结合 Apple GPU 的 TBDR 架构进行针对性优化。

---

## 文章结构概览

```mermaid
graph TB
    A[iOS Metal 渲染技术] --> B[核心概念层<br/>What & Why]
    A --> C[基础使用层<br/>How to Use]
    A --> D[高级优化层<br/>How to Master]
    
    B --> B1[Metal 架构与组件]
    B --> B2[核心对象关系]
    B --> B3[vs OpenGL ES]
    B --> B4[Metal Shading Language]
    
    C --> C1[渲染管线搭建]
    C --> C2[Compute Pipeline]
    C --> C3[纹理加载与采样]
    C --> C4[顶点数据管理]
    C --> C5[Shader 编写]
    
    D --> D1[性能优化策略]
    D --> D2[内存管理]
    D --> D3[并行计算优化]
    D --> D4[调试与分析工具]
```

---

# 第一层：核心概念层

## 1. Metal 架构概述

**结论先行**：Metal 的设计哲学是「最小化 CPU 开销、最大化 GPU 利用率」。它通过预编译管线状态、多线程命令编码、统一内存架构三大核心设计，将驱动层面的验证和编译开销从运行时提前到构建时，使得每帧 Draw Call 的 CPU 成本降至微秒级。

### 1.1 Metal 在 Apple 技术栈中的位置

```mermaid
graph TB
    subgraph 应用层
        APP[应用程序]
        GAME[游戏引擎]
        ML[Core ML]
    end
    
    subgraph 框架层
        SPRITEKIT[SpriteKit]
        SCENEKIT[SceneKit]
        REALITYKIT[RealityKit]
        CI[Core Image]
        MPS[Metal Performance Shaders]
        MPSGRAPH[MPS Graph]
    end
    
    subgraph Metal API 层
        METAL[Metal API]
        MSL[Metal Shading Language]
        METALFX[MetalFX]
    end
    
    subgraph 硬件层
        GPU[Apple GPU<br/>TBDR 架构]
        UMA[统一内存<br/>Unified Memory]
    end
    
    APP --> SPRITEKIT
    APP --> SCENEKIT
    APP --> CI
    GAME --> METAL
    ML --> MPS
    ML --> MPSGRAPH
    
    SPRITEKIT --> METAL
    SCENEKIT --> METAL
    REALITYKIT --> METAL
    CI --> METAL
    MPS --> METAL
    MPSGRAPH --> METAL
    
    METAL --> GPU
    MSL --> GPU
    METALFX --> METAL
    GPU <--> UMA
```

### 1.2 Apple GPU 的 TBDR 架构

**结论先行**：Apple GPU 采用 Tile-Based Deferred Rendering（TBDR）架构，这与桌面 GPU 的 Immediate Mode 架构有本质区别。理解 TBDR 是写出高性能 Metal 代码的前提。

> **知识关联**：TBDR 的 Tile 分块思想与 [图像处理并行化](./thread/06_工程应用实战/图像处理并行化_详细解析.md) 中的 Tile-based 分块并行策略一脉相承——都是通过局部性优化提升缓存命中率。

```mermaid
graph LR
    subgraph 传统 IMR 架构
        V1[顶点处理] --> R1[光栅化]
        R1 --> F1[片段处理]
        F1 --> FB1[帧缓冲区<br/>外部内存]
    end
    
    subgraph Apple TBDR 架构
        V2[顶点处理] --> TILE[Tiling 阶段<br/>三角形分配到 Tile]
        TILE --> HSR[隐面消除<br/>Hidden Surface Removal]
        HSR --> F2[片段处理<br/>仅可见像素]
        F2 --> TM[Tile Memory<br/>片上内存]
        TM --> |Tile完成后| FB2[帧缓冲区<br/>外部内存]
    end
```

**TBDR 关键特性**：

| 特性 | IMR（桌面GPU） | TBDR（Apple GPU） | 对开发者的影响 |
|------|---------------|-------------------|--------------|
| **渲染流程** | 逐三角形处理 | 先分Tile、再逐Tile处理 | 几何数据需遍历两遍 |
| **帧缓冲访问** | 每次片段写入都访问外部内存 | 先写Tile Memory（片上SRAM） | 带宽节省巨大 |
| **隐面消除** | 依赖 Early-Z | 硬件级 HSR，完全消除 Overdraw | 无需手动排序不透明物体 |
| **Tile Memory** | 无 | 每个 Tile 有独立片上内存 | 可用 `imageblock`/`memoryless` |
| **带宽节省** | 基准 | 节省 50-80% 内存带宽 | 显著降低功耗 |
| **适合场景** | 超大规模几何体 | 移动端、高能效比 | 适配移动端功耗限制 |

---

## 2. Metal 核心组件

**结论先行**：Metal 的核心对象模型遵循「Device → Queue → Buffer → Encoder」的层次化命令提交架构。理解这些对象的创建时机和生命周期是正确使用 Metal 的基础。

### 2.1 核心对象关系图

```mermaid
graph TB
    subgraph 设备层
        DEV[MTLDevice<br/>GPU 抽象]
    end
    
    subgraph 资源层
        BUF[MTLBuffer<br/>通用数据缓冲区]
        TEX[MTLTexture<br/>纹理数据]
        SAMP[MTLSamplerState<br/>采样器]
        HEAP[MTLHeap<br/>内存堆]
    end
    
    subgraph 管线状态层
        RPS[MTLRenderPipelineState<br/>渲染管线状态]
        CPS[MTLComputePipelineState<br/>计算管线状态]
        DSS[MTLDepthStencilState<br/>深度模板状态]
        LIB[MTLLibrary<br/>Shader 库]
        FUNC[MTLFunction<br/>Shader 函数]
    end
    
    subgraph 命令提交层
        CQ[MTLCommandQueue<br/>命令队列]
        CB[MTLCommandBuffer<br/>命令缓冲区]
        RCE[MTLRenderCommandEncoder<br/>渲染编码器]
        CCE[MTLComputeCommandEncoder<br/>计算编码器]
        BCE[MTLBlitCommandEncoder<br/>拷贝编码器]
    end
    
    DEV --> BUF
    DEV --> TEX
    DEV --> SAMP
    DEV --> HEAP
    DEV --> RPS
    DEV --> CPS
    DEV --> DSS
    DEV --> LIB
    DEV --> CQ
    
    HEAP --> BUF
    HEAP --> TEX
    LIB --> FUNC
    FUNC --> RPS
    FUNC --> CPS
    
    CQ --> CB
    CB --> RCE
    CB --> CCE
    CB --> BCE
    
    RCE -.-> RPS
    RCE -.-> BUF
    RCE -.-> TEX
    CCE -.-> CPS
    CCE -.-> BUF
    CCE -.-> TEX
```

### 2.2 核心组件详解

| 组件 | 职责 | 创建时机 | 生命周期 | 线程安全 |
|------|------|---------|---------|---------|
| **MTLDevice** | GPU 硬件抽象 | App 启动时 | App 级别 | ✅ |
| **MTLCommandQueue** | 命令队列，串行提交 | 初始化时 | App 级别 | ✅ |
| **MTLCommandBuffer** | 单帧命令容器 | 每帧创建 | 单帧使用 | ❌ |
| **MTLRenderPipelineState** | 预编译的渲染管线 | 加载时 | App 级别 | ✅ |
| **MTLComputePipelineState** | 预编译的计算管线 | 加载时 | App 级别 | ✅ |
| **MTLBuffer** | 顶点/Uniform/通用数据 | 按需创建 | 资源依赖 | ❌（需同步） |
| **MTLTexture** | 图像/纹理数据 | 按需创建 | 资源依赖 | ❌（需同步） |
| **MTLLibrary** | 编译后的 Shader 集合 | 加载时 | App 级别 | ✅ |
| **MTLSamplerState** | 纹理采样参数 | 加载时 | App 级别 | ✅ |
| **MTLDepthStencilState** | 深度测试/模板配置 | 加载时 | App 级别 | ✅ |
| **MTLHeap** | 内存分配池 | 初始化时 | App 级别 | ❌（需同步） |

### 2.3 命令提交流水线

```mermaid
sequenceDiagram
    participant CPU as CPU Thread
    participant CQ as CommandQueue
    participant CB as CommandBuffer
    participant GPU as GPU
    
    CPU->>CQ: makeCommandBuffer()
    CQ-->>CB: 创建 CommandBuffer
    
    CPU->>CB: makeRenderCommandEncoder()
    Note over CPU: 设置管线状态、绑定资源、发起 Draw Call
    CPU->>CB: endEncoding()
    
    CPU->>CB: makeComputeCommandEncoder()
    Note over CPU: 设置计算管线、绑定资源、dispatch
    CPU->>CB: endEncoding()
    
    CPU->>CB: commit()
    CB->>GPU: 提交到 GPU 执行
    
    Note over CPU,GPU: CPU 继续编码下一帧<br/>GPU 异步执行当前帧
    
    GPU-->>CB: 执行完成回调
    CB-->>CPU: addCompletedHandler
```

---

## 3. Metal vs OpenGL ES 对比

**结论先行**：Metal 相比 OpenGL ES 的核心优势不在于 GPU 计算能力（硬件相同），而在于 CPU 端开销降低 10 倍以上。这来源于管线状态预编译、多线程命令编码、显式资源管理三大设计。

| 维度 | OpenGL ES | Metal | 收益 |
|------|-----------|-------|------|
| **管线状态** | 运行时验证和编译 | 构建时预编译 (MTLRenderPipelineState) | CPU 开销降低 10x |
| **命令编码** | 单线程（全局状态机） | 多线程并行编码 | 多核 CPU 利用率提升 |
| **资源绑定** | 隐式状态跟踪 | 显式绑定 & Argument Buffer | 减少驱动验证开销 |
| **Shader 编译** | 运行时 GLSL→GPU IR | 离线编译为 AIR→GPU IR | 消除运行时卡顿 |
| **同步模型** | 隐式（驱动管理） | 显式（App 管理） | 精确控制，避免不必要等待 |
| **内存管理** | 驱动自动管理 | App 显式指定 Storage Mode | 优化带宽和功耗 |
| **API 复杂度** | 低（状态机模型） | 高（命令模式） | 需要更多学习成本 |
| **调试工具** | 有限 | Xcode GPU Capture 全面 | 更强大的性能分析 |

> **知识关联**：更详细的 Metal vs OpenGL vs Vulkan 跨平台差异参见 [跨平台实现差异](./Image_Processing_Algorithms/07_工程实践与性能优化/跨平台实现差异_详细解析.md)，其中 iOS 平台的 Metal Compute 在 1080P 图像处理上仅需 2.8ms，是标量 C 实现的 28 倍。

### 3.1 Draw Call 开销对比

```
┌─────────────────────────────────────────────────────────────────┐
│                  Draw Call CPU 开销对比                           │
├─────────────────────────────────────────────────────────────────┤
│  Draw Call 数量  │ OpenGL ES (ms) │ Metal (ms) │ 加速比         │
├─────────────────────────────────────────────────────────────────┤
│  100            │   0.5          │   0.05     │  10x            │
│  500            │   2.5          │   0.25     │  10x            │
│  1,000          │   5.0          │   0.5      │  10x            │
│  5,000          │   25.0         │   2.5      │  10x            │
│  10,000         │   50.0+        │   5.0      │  10x+           │
│  50,000         │   不可行       │   25.0     │  ∞              │
└─────────────────────────────────────────────────────────────────┘
测试环境：iPhone 13, A15 Bionic
```

---

## 4. Metal Shading Language（MSL）基础

**结论先行**：MSL 基于 C++14 标准，天然支持 SIMD 类型和 GPU 特有的地址空间限定符。与 GLSL 不同，MSL 使用 `[[attribute]]` 语法绑定输入输出，所有资源通过函数参数显式传入。

### 4.1 MSL 与 GLSL/HLSL 对照

| 特性 | MSL | GLSL | HLSL |
|------|-----|------|------|
| **基础语言** | C++14 | C-like | C-like |
| **类型系统** | float4, half4, int4... | vec4, ivec4... | float4, int4... |
| **矩阵类型** | float4x4 | mat4 | float4x4 |
| **地址空间** | device, constant, thread, threadgroup | 无显式控制 | 部分 |
| **纹理类型** | texture2d<T, access> | sampler2D | Texture2D |
| **属性绑定** | `[[attribute(0)]]` | `layout(location=0)` | `: POSITION` |
| **入口点限定** | `vertex`, `fragment`, `kernel` | `void main()` | 语义标注 |
| **半精度** | `half` (原生支持) | `mediump`(提示) | `min16float` |

### 4.2 MSL 基础语法示例

```metal
// Metal Shading Language 基础示例
#include <metal_stdlib>
using namespace metal;

// ========== 数据结构定义 ==========

// 顶点输入结构（对应 CPU 端的顶点缓冲区布局）
struct VertexIn {
    float3 position [[attribute(0)]];
    float3 normal   [[attribute(1)]];
    float2 texCoord [[attribute(2)]];
};

// 顶点到片段的插值数据
struct VertexOut {
    float4 position [[position]];   // 裁剪空间位置（必须）
    float3 worldPos;
    float3 worldNormal;
    float2 texCoord;
};

// Uniform 缓冲区
struct Uniforms {
    float4x4 modelMatrix;
    float4x4 viewProjectionMatrix;
    float4x4 normalMatrix;
    float3 cameraPosition;
    float time;
};

struct LightData {
    float3 position;
    float3 color;
    float intensity;
    float radius;
};

// ========== 顶点着色器 ==========

vertex VertexOut vertexShader(
    VertexIn in [[stage_in]],                    // 顶点输入
    constant Uniforms& uniforms [[buffer(0)]],    // Uniform 数据
    uint vertexID [[vertex_id]])                  // 顶点索引
{
    VertexOut out;
    
    float4 worldPos = uniforms.modelMatrix * float4(in.position, 1.0);
    out.position = uniforms.viewProjectionMatrix * worldPos;
    out.worldPos = worldPos.xyz;
    out.worldNormal = (uniforms.normalMatrix * float4(in.normal, 0.0)).xyz;
    out.texCoord = in.texCoord;
    
    return out;
}

// ========== 片段着色器 ==========

fragment float4 fragmentShader(
    VertexOut in [[stage_in]],                      // 插值后的数据
    constant Uniforms& uniforms [[buffer(0)]],
    constant LightData* lights [[buffer(1)]],
    constant uint& lightCount [[buffer(2)]],
    texture2d<float> baseColorMap [[texture(0)]],   // 纹理
    sampler texSampler [[sampler(0)]])               // 采样器
{
    // 采样基础颜色
    float4 baseColor = baseColorMap.sample(texSampler, in.texCoord);
    
    // Blinn-Phong 光照
    float3 N = normalize(in.worldNormal);
    float3 V = normalize(uniforms.cameraPosition - in.worldPos);
    
    float3 finalColor = float3(0.0);
    float3 ambient = baseColor.rgb * 0.1;
    
    for (uint i = 0; i < lightCount; i++) {
        float3 L = normalize(lights[i].position - in.worldPos);
        float3 H = normalize(L + V);
        
        float NdotL = max(dot(N, L), 0.0);
        float NdotH = max(dot(N, H), 0.0);
        
        // 距离衰减
        float dist = length(lights[i].position - in.worldPos);
        float attenuation = 1.0 / (1.0 + dist * dist / (lights[i].radius * lights[i].radius));
        
        float3 diffuse = baseColor.rgb * NdotL;
        float3 specular = float3(pow(NdotH, 64.0));
        
        finalColor += (diffuse + specular) * lights[i].color * lights[i].intensity * attenuation;
    }
    
    return float4(ambient + finalColor, baseColor.a);
}
```

---

# 第二层：基础使用层

## 5. 渲染管线搭建

**结论先行**：Metal 渲染管线的搭建遵循「描述符配置 → 状态预编译 → 编码器绑定 → 提交执行」四步模式。管线状态（RenderPipelineState）应在加载阶段预编译，而非每帧创建，这是 Metal 低 CPU 开销的关键。

### 5.1 完整渲染管线搭建（Swift）

```swift
import MetalKit

class MetalRenderer: NSObject, MTKViewDelegate {
    // ===== 长生命周期对象（App 级别）=====
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue
    private let renderPipelineState: MTLRenderPipelineState
    private let depthStencilState: MTLDepthStencilState
    private let samplerState: MTLSamplerState
    
    // ===== 资源 =====
    private var vertexBuffer: MTLBuffer
    private var indexBuffer: MTLBuffer
    private var uniformBuffer: MTLBuffer
    private var baseColorTexture: MTLTexture?
    
    init?(metalView: MTKView) {
        // 1. 获取 Device
        guard let device = MTLCreateSystemDefaultDevice() else { return nil }
        self.device = device
        metalView.device = device
        metalView.depthStencilPixelFormat = .depth32Float
        metalView.colorPixelFormat = .bgra8Unorm_srgb
        metalView.clearColor = MTLClearColor(red: 0.1, green: 0.1, blue: 0.1, alpha: 1.0)
        
        // 2. 创建命令队列
        guard let queue = device.makeCommandQueue() else { return nil }
        self.commandQueue = queue
        
        // 3. 创建渲染管线状态（预编译）
        let library = device.makeDefaultLibrary()!
        let vertexFunc = library.makeFunction(name: "vertexShader")!
        let fragmentFunc = library.makeFunction(name: "fragmentShader")!
        
        let pipelineDescriptor = MTLRenderPipelineDescriptor()
        pipelineDescriptor.vertexFunction = vertexFunc
        pipelineDescriptor.fragmentFunction = fragmentFunc
        pipelineDescriptor.colorAttachments[0].pixelFormat = metalView.colorPixelFormat
        pipelineDescriptor.depthAttachmentPixelFormat = metalView.depthStencilPixelFormat
        
        // 顶点描述符
        let vertexDescriptor = MTLVertexDescriptor()
        // Position: float3
        vertexDescriptor.attributes[0].format = .float3
        vertexDescriptor.attributes[0].offset = 0
        vertexDescriptor.attributes[0].bufferIndex = 0
        // Normal: float3
        vertexDescriptor.attributes[1].format = .float3
        vertexDescriptor.attributes[1].offset = 12
        vertexDescriptor.attributes[1].bufferIndex = 0
        // TexCoord: float2
        vertexDescriptor.attributes[2].format = .float2
        vertexDescriptor.attributes[2].offset = 24
        vertexDescriptor.attributes[2].bufferIndex = 0
        // Layout
        vertexDescriptor.layouts[0].stride = 32
        vertexDescriptor.layouts[0].stepFunction = .perVertex
        pipelineDescriptor.vertexDescriptor = vertexDescriptor
        
        // Alpha 混合
        pipelineDescriptor.colorAttachments[0].isBlendingEnabled = true
        pipelineDescriptor.colorAttachments[0].sourceRGBBlendFactor = .sourceAlpha
        pipelineDescriptor.colorAttachments[0].destinationRGBBlendFactor = .oneMinusSourceAlpha
        
        self.renderPipelineState = try! device.makeRenderPipelineState(descriptor: pipelineDescriptor)
        
        // 4. 创建深度模板状态
        let depthDescriptor = MTLDepthStencilDescriptor()
        depthDescriptor.depthCompareFunction = .less
        depthDescriptor.isDepthWriteEnabled = true
        self.depthStencilState = device.makeDepthStencilState(descriptor: depthDescriptor)!
        
        // 5. 创建采样器
        let samplerDescriptor = MTLSamplerDescriptor()
        samplerDescriptor.minFilter = .linear
        samplerDescriptor.magFilter = .linear
        samplerDescriptor.mipFilter = .linear
        samplerDescriptor.sAddressMode = .repeat
        samplerDescriptor.tAddressMode = .repeat
        samplerDescriptor.maxAnisotropy = 8
        self.samplerState = device.makeSamplerState(descriptor: samplerDescriptor)!
        
        // 6. 创建顶点/索引缓冲区（示例：一个四边形）
        let vertices: [Float] = [
            // position(3)     normal(3)        texCoord(2)
            -1, -1, 0,        0, 0, 1,         0, 1,
             1, -1, 0,        0, 0, 1,         1, 1,
             1,  1, 0,        0, 0, 1,         1, 0,
            -1,  1, 0,        0, 0, 1,         0, 0,
        ]
        self.vertexBuffer = device.makeBuffer(
            bytes: vertices, length: vertices.count * MemoryLayout<Float>.size,
            options: .storageModeShared)!
        
        let indices: [UInt16] = [0, 1, 2, 0, 2, 3]
        self.indexBuffer = device.makeBuffer(
            bytes: indices, length: indices.count * MemoryLayout<UInt16>.size,
            options: .storageModeShared)!
        
        self.uniformBuffer = device.makeBuffer(
            length: MemoryLayout<Uniforms>.size, options: .storageModeShared)!
        
        super.init()
    }
    
    // ===== 每帧渲染 =====
    func draw(in view: MTKView) {
        guard let drawable = view.currentDrawable,
              let renderPassDescriptor = view.currentRenderPassDescriptor else { return }
        
        // 更新 Uniform
        updateUniforms()
        
        // 创建命令缓冲区
        guard let commandBuffer = commandQueue.makeCommandBuffer() else { return }
        
        // 创建渲染编码器
        guard let encoder = commandBuffer.makeRenderCommandEncoder(
            descriptor: renderPassDescriptor) else { return }
        
        encoder.setRenderPipelineState(renderPipelineState)
        encoder.setDepthStencilState(depthStencilState)
        encoder.setCullMode(.back)
        encoder.setFrontFacing(.counterClockwise)
        
        // 绑定资源
        encoder.setVertexBuffer(vertexBuffer, offset: 0, index: 0)
        encoder.setVertexBuffer(uniformBuffer, offset: 0, index: 1)
        encoder.setFragmentBuffer(uniformBuffer, offset: 0, index: 0)
        
        if let texture = baseColorTexture {
            encoder.setFragmentTexture(texture, index: 0)
        }
        encoder.setFragmentSamplerState(samplerState, index: 0)
        
        // 绘制
        encoder.drawIndexedPrimitives(
            type: .triangle,
            indexCount: 6,
            indexType: .uint16,
            indexBuffer: indexBuffer,
            indexBufferOffset: 0)
        
        encoder.endEncoding()
        
        // 提交
        commandBuffer.present(drawable)
        commandBuffer.commit()
    }
    
    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) { }
    
    private func updateUniforms() {
        // 更新变换矩阵等
        let ptr = uniformBuffer.contents().bindMemory(to: Uniforms.self, capacity: 1)
        // ... 设置 modelMatrix, viewProjectionMatrix 等
    }
}

// Uniform 结构体（Swift 侧，需与 MSL 侧一致）
struct Uniforms {
    var modelMatrix: simd_float4x4
    var viewProjectionMatrix: simd_float4x4
    var normalMatrix: simd_float4x4
    var cameraPosition: simd_float3
    var time: Float
}
```

### 5.2 渲染管线搭建（Objective-C++）

```objc
// MetalRenderer.mm — Objective-C++ 实现
#import <Metal/Metal.h>
#import <MetalKit/MetalKit.h>
#include <simd/simd.h>

struct Uniforms {
    simd_float4x4 modelMatrix;
    simd_float4x4 viewProjectionMatrix;
    simd_float4x4 normalMatrix;
    simd_float3 cameraPosition;
    float time;
};

@interface MetalRenderer : NSObject <MTKViewDelegate>
@end

@implementation MetalRenderer {
    id<MTLDevice> _device;
    id<MTLCommandQueue> _commandQueue;
    id<MTLRenderPipelineState> _renderPipeline;
    id<MTLDepthStencilState> _depthState;
    id<MTLBuffer> _vertexBuffer;
    id<MTLBuffer> _uniformBuffer;
}

- (instancetype)initWithView:(MTKView *)view {
    self = [super init];
    if (self) {
        _device = MTLCreateSystemDefaultDevice();
        view.device = _device;
        view.depthStencilPixelFormat = MTLPixelFormatDepth32Float;
        
        _commandQueue = [_device newCommandQueue];
        
        [self buildPipeline:view];
        [self buildResources];
    }
    return self;
}

- (void)buildPipeline:(MTKView *)view {
    id<MTLLibrary> library = [_device newDefaultLibrary];
    
    MTLRenderPipelineDescriptor *desc = [[MTLRenderPipelineDescriptor alloc] init];
    desc.vertexFunction = [library newFunctionWithName:@"vertexShader"];
    desc.fragmentFunction = [library newFunctionWithName:@"fragmentShader"];
    desc.colorAttachments[0].pixelFormat = view.colorPixelFormat;
    desc.depthAttachmentPixelFormat = view.depthStencilPixelFormat;
    
    NSError *error = nil;
    _renderPipeline = [_device newRenderPipelineStateWithDescriptor:desc error:&error];
    NSAssert(_renderPipeline, @"Pipeline creation failed: %@", error);
    
    MTLDepthStencilDescriptor *depthDesc = [[MTLDepthStencilDescriptor alloc] init];
    depthDesc.depthCompareFunction = MTLCompareFunctionLess;
    depthDesc.depthWriteEnabled = YES;
    _depthState = [_device newDepthStencilStateWithDescriptor:depthDesc];
}

- (void)drawInMTKView:(MTKView *)view {
    id<MTLCommandBuffer> commandBuffer = [_commandQueue commandBuffer];
    MTLRenderPassDescriptor *rpd = view.currentRenderPassDescriptor;
    if (!rpd) return;
    
    id<MTLRenderCommandEncoder> encoder = [commandBuffer renderCommandEncoderWithDescriptor:rpd];
    [encoder setRenderPipelineState:_renderPipeline];
    [encoder setDepthStencilState:_depthState];
    [encoder setVertexBuffer:_vertexBuffer offset:0 atIndex:0];
    [encoder setVertexBuffer:_uniformBuffer offset:0 atIndex:1];
    
    [encoder drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:6];
    [encoder endEncoding];
    
    [commandBuffer presentDrawable:view.currentDrawable];
    [commandBuffer commit];
}

@end
```

---

## 6. Compute Pipeline 搭建

**结论先行**：Metal Compute Pipeline 是 GPU 通用计算的入口，适合图像处理、物理模拟、AI 推理等场景。相比渲染管线，计算管线配置更简单——只需一个 kernel 函数和线程组配置。

> **知识关联**：Metal Compute 的线程组（Threadgroup）概念对应 [图像处理并行化](./thread/06_工程应用实战/图像处理并行化_详细解析.md) 中的 GPU 并行计算模型，threadgroup 大小的选择直接影响 GPU 占用率和性能。

### 6.1 Compute Shader 示例

```metal
// ImageProcessing.metal — 图像处理 Compute Kernels
#include <metal_stdlib>
using namespace metal;

// ========== 高斯模糊 Kernel ==========
kernel void gaussianBlur5x5(
    texture2d<half, access::read>  inTexture  [[texture(0)]],
    texture2d<half, access::write> outTexture [[texture(1)]],
    uint2 gid [[thread_position_in_grid]])
{
    if (gid.x >= outTexture.get_width() || gid.y >= outTexture.get_height()) {
        return;
    }
    
    // 5x5 高斯核权重（sigma ≈ 1.0）
    constexpr half weights[5][5] = {
        {1.0h/273, 4.0h/273, 7.0h/273, 4.0h/273, 1.0h/273},
        {4.0h/273, 16.0h/273, 26.0h/273, 16.0h/273, 4.0h/273},
        {7.0h/273, 26.0h/273, 41.0h/273, 26.0h/273, 7.0h/273},
        {4.0h/273, 16.0h/273, 26.0h/273, 16.0h/273, 4.0h/273},
        {1.0h/273, 4.0h/273, 7.0h/273, 4.0h/273, 1.0h/273}
    };
    
    half4 sum = half4(0.0h);
    int2 texSize = int2(outTexture.get_width(), outTexture.get_height());
    
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            int2 samplePos = clamp(
                int2(gid) + int2(x, y),
                int2(0),
                texSize - 1
            );
            sum += inTexture.read(uint2(samplePos)) * weights[y + 2][x + 2];
        }
    }
    
    outTexture.write(sum, gid);
}

// ========== 使用 Threadgroup Memory 优化的模糊 ==========
kernel void gaussianBlurOptimized(
    texture2d<half, access::read>  inTexture  [[texture(0)]],
    texture2d<half, access::write> outTexture [[texture(1)]],
    uint2 gid [[thread_position_in_grid]],
    uint2 tid [[thread_position_in_threadgroup]],
    uint2 tgSize [[threads_per_threadgroup]])
{
    // 使用 threadgroup memory 缓存 Tile 数据
    constexpr int HALO = 2;
    constexpr int TG_SIZE = 16;
    constexpr int SHARED_SIZE = TG_SIZE + 2 * HALO; // 20
    
    threadgroup half4 sharedMem[SHARED_SIZE][SHARED_SIZE];
    
    // 加载当前线程对应的像素到共享内存
    int2 texSize = int2(inTexture.get_width(), inTexture.get_height());
    
    // 每个线程加载一个像素到共享内存（含 Halo 区域协同加载）
    int2 basePos = int2(gid) - int2(tid) - int2(HALO);
    
    for (int y = tid.y; y < SHARED_SIZE; y += tgSize.y) {
        for (int x = tid.x; x < SHARED_SIZE; x += tgSize.x) {
            int2 samplePos = clamp(basePos + int2(x, y), int2(0), texSize - 1);
            sharedMem[y][x] = inTexture.read(uint2(samplePos));
        }
    }
    
    // 同步确保所有线程完成加载
    threadgroup_barrier(mem_flags::mem_threadgroup);
    
    if (gid.x >= uint(texSize.x) || gid.y >= uint(texSize.y)) return;
    
    // 从共享内存读取进行卷积
    constexpr half weights[5][5] = {
        {1.0h/273, 4.0h/273, 7.0h/273, 4.0h/273, 1.0h/273},
        {4.0h/273, 16.0h/273, 26.0h/273, 16.0h/273, 4.0h/273},
        {7.0h/273, 26.0h/273, 41.0h/273, 26.0h/273, 7.0h/273},
        {4.0h/273, 16.0h/273, 26.0h/273, 16.0h/273, 4.0h/273},
        {1.0h/273, 4.0h/273, 7.0h/273, 4.0h/273, 1.0h/273}
    };
    
    half4 sum = half4(0.0h);
    int2 localPos = int2(tid) + int2(HALO);
    
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            sum += sharedMem[localPos.y + y][localPos.x + x] * weights[y+2][x+2];
        }
    }
    
    outTexture.write(sum, gid);
}

// ========== 色彩空间转换 Kernel ==========
kernel void rgbToYuv(
    texture2d<half, access::read>  rgbTexture [[texture(0)]],
    texture2d<half, access::write> yTexture   [[texture(1)]],
    texture2d<half, access::write> uvTexture  [[texture(2)]],
    uint2 gid [[thread_position_in_grid]])
{
    if (gid.x >= rgbTexture.get_width() || gid.y >= rgbTexture.get_height()) return;
    
    half4 rgb = rgbTexture.read(gid);
    
    // BT.601 转换
    half Y  =  0.299h * rgb.r + 0.587h * rgb.g + 0.114h * rgb.b;
    half Cb = -0.169h * rgb.r - 0.331h * rgb.g + 0.500h * rgb.b + 0.5h;
    half Cr =  0.500h * rgb.r - 0.419h * rgb.g - 0.081h * rgb.b + 0.5h;
    
    yTexture.write(half4(Y, 0, 0, 1), gid);
    
    // UV 降采样 2x2
    if (gid.x % 2 == 0 && gid.y % 2 == 0) {
        uvTexture.write(half4(Cb, Cr, 0, 1), gid / 2);
    }
}
```

### 6.2 Compute Pipeline 搭建（Swift 主机端）

```swift
class MetalComputeProcessor {
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue
    private var blurPipeline: MTLComputePipelineState!
    private var yuvPipeline: MTLComputePipelineState!
    
    init?() {
        guard let device = MTLCreateSystemDefaultDevice(),
              let queue = device.makeCommandQueue() else { return nil }
        self.device = device
        self.commandQueue = queue
        
        do {
            let library = device.makeDefaultLibrary()!
            blurPipeline = try device.makeComputePipelineState(
                function: library.makeFunction(name: "gaussianBlurOptimized")!)
            yuvPipeline = try device.makeComputePipelineState(
                function: library.makeFunction(name: "rgbToYuv")!)
        } catch {
            print("Pipeline creation failed: \(error)")
            return nil
        }
    }
    
    /// 对纹理执行高斯模糊
    func applyGaussianBlur(input: MTLTexture, output: MTLTexture) {
        guard let commandBuffer = commandQueue.makeCommandBuffer(),
              let encoder = commandBuffer.makeComputeCommandEncoder() else { return }
        
        encoder.setComputePipelineState(blurPipeline)
        encoder.setTexture(input, index: 0)
        encoder.setTexture(output, index: 1)
        
        // 计算最优 Threadgroup 大小
        let w = blurPipeline.threadExecutionWidth                    // 通常 32
        let h = blurPipeline.maxTotalThreadsPerThreadgroup / w       // 通常 16–32
        let threadsPerGroup = MTLSize(width: w, height: h, depth: 1)
        let threadsPerGrid = MTLSize(
            width: input.width, height: input.height, depth: 1)
        
        // 使用 dispatchThreads 自动处理边界
        encoder.dispatchThreads(threadsPerGrid, threadsPerThreadgroup: threadsPerGroup)
        encoder.endEncoding()
        
        commandBuffer.commit()
        commandBuffer.waitUntilCompleted()
    }
    
    /// 创建纹理
    func makeTexture(width: Int, height: Int,
                     format: MTLPixelFormat = .rgba8Unorm,
                     usage: MTLTextureUsage = [.shaderRead, .shaderWrite]) -> MTLTexture? {
        let desc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: format, width: width, height: height, mipmapped: false)
        desc.usage = usage
        desc.storageMode = .shared  // UMA: CPU/GPU 共享
        return device.makeTexture(descriptor: desc)
    }
}
```

### 6.3 Threadgroup 大小选择策略

| 配置 | 线程数 | 适用场景 | 注意事项 |
|------|---------|---------|--------|
| **16×16** | 256 | 通用图像处理 | Apple GPU 默认推荐 |
| **32×8** | 256 | 行为主的处理 | 利用 SIMD Group 宽度 |
| **8×8** | 64 | Threadgroup Memory 大 | 当每线程需大量共享内存时 |
| **threadExecutionWidth × N** | 自动 | 让系统决定 | 推荐使用 `dispatchThreads` |

> **最佳实践**：使用 `pipeline.threadExecutionWidth` 和 `pipeline.maxTotalThreadsPerThreadgroup` 动态计算，而非硬编码。

---

## 7. 纹理加载与采样

**结论先行**：纹理是 Metal 中最常用的资源类型。iOS 上应优先使用 `MTKTextureLoader` 简化加载流程，并通过 `IOSurface` 实现与 CoreVideo/Camera Pipeline 的零拷贝互操作。

> **知识关联**：Metal Texture 与 IOSurface 的零拷贝交互是 [iOS 内存优化](./cpp_memory_optimization/03_系统级优化/iOS内存优化.md) 中 Metal Buffer 共享内存技术的纹理版本。两者都利用了 Apple Silicon 统一内存架构的优势。

### 7.1 纹理加载方式对比

| 加载方式 | 复杂度 | 性能 | 适用场景 |
|---------|---------|------|--------|
| **MTKTextureLoader** | 低 | 良好 | 从文件/Asset 加载静态纹理 |
| **手动创建 + blit** | 中 | 灵活 | 动态生成纹理数据 |
| **IOSurface 零拷贝** | 高 | 最优 | 相机/视频帧处理 |
| **CVMetalTextureCache** | 中 | 优秀 | 视频流实时处理 |

### 7.2 CVMetalTextureCache：视频帧零拷贝到 Metal Texture

```swift
import CoreVideo
import Metal

class VideoTextureProvider {
    private let device: MTLDevice
    private var textureCache: CVMetalTextureCache?
    
    init(device: MTLDevice) {
        self.device = device
        CVMetalTextureCacheCreate(
            kCFAllocatorDefault, nil, device, nil, &textureCache)
    }
    
    /// 将 CVPixelBuffer 零拷贝转换为 MTLTexture
    func texture(from pixelBuffer: CVPixelBuffer) -> MTLTexture? {
        guard let cache = textureCache else { return nil }
        
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        
        var cvTexture: CVMetalTexture?
        let status = CVMetalTextureCacheCreateTextureFromImage(
            kCFAllocatorDefault,
            cache,
            pixelBuffer,
            nil,                        // textureAttributes
            .bgra8Unorm,               // pixelFormat
            width, height,
            0,                          // planeIndex
            &cvTexture)
        
        guard status == kCVReturnSuccess, let cvTex = cvTexture else { return nil }
        
        return CVMetalTextureGetTexture(cvTex)
        // 注意：返回的 MTLTexture 与 pixelBuffer 共享同一块内存，零拷贝！
    }
    
    /// 处理 NV12 格式视频帧（双平面）
    func textures(fromNV12 pixelBuffer: CVPixelBuffer) -> (y: MTLTexture, uv: MTLTexture)? {
        guard let cache = textureCache else { return nil }
        
        // Y 平面
        var yTexture: CVMetalTexture?
        CVMetalTextureCacheCreateTextureFromImage(
            kCFAllocatorDefault, cache, pixelBuffer, nil,
            .r8Unorm,
            CVPixelBufferGetWidthOfPlane(pixelBuffer, 0),
            CVPixelBufferGetHeightOfPlane(pixelBuffer, 0),
            0, &yTexture)
        
        // UV 平面
        var uvTexture: CVMetalTexture?
        CVMetalTextureCacheCreateTextureFromImage(
            kCFAllocatorDefault, cache, pixelBuffer, nil,
            .rg8Unorm,
            CVPixelBufferGetWidthOfPlane(pixelBuffer, 1),
            CVPixelBufferGetHeightOfPlane(pixelBuffer, 1),
            1, &uvTexture)
        
        guard let yTex = yTexture, let uvTex = uvTexture,
              let y = CVMetalTextureGetTexture(yTex),
              let uv = CVMetalTextureGetTexture(uvTex) else { return nil }
        
        return (y, uv)
    }
}
```

### 7.3 IOSurface 零拷贝创建 Metal Texture

> **知识关联**：IOSurface 是 iOS 平台对应 Android dma-buf 的零拷贝机制，详见 [DMA机制详解](./cpp_memory_optimization/04_DMA与缓存优化/DMA机制详解.md) 中的平台对照表。

```objc
// IOSurface + Metal 零拷贝（Objective-C++）
#import <Metal/Metal.h>
#import <IOSurface/IOSurface.h>
#import <CoreVideo/CoreVideo.h>

class IOSurfaceMetalBridge {
public:
    /// 从 CVPixelBuffer 的底层 IOSurface 创建 Metal Texture——零拷贝
    static id<MTLTexture> textureFromPixelBuffer(
        CVPixelBufferRef pixelBuffer, id<MTLDevice> device)
    {
        IOSurfaceRef surface = CVPixelBufferGetIOSurface(pixelBuffer);
        if (!surface) return nil;
        
        size_t width = IOSurfaceGetWidth(surface);
        size_t height = IOSurfaceGetHeight(surface);
        
        MTLTextureDescriptor *desc = [MTLTextureDescriptor
            texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm
            width:width height:height mipmapped:NO];
        desc.usage = MTLTextureUsageShaderRead | MTLTextureUsageShaderWrite;
        desc.storageMode = MTLStorageModeShared;
        
        // 直接从 IOSurface 创建 Texture，不拷贝数据
        id<MTLTexture> texture = [device newTextureWithDescriptor:desc
                                                       iosurface:surface
                                                           plane:0];
        return texture;
    }
    
    /// 创建 IOSurface-backed 的 MTLTexture（可跨进程共享）
    static id<MTLTexture> createSharedTexture(
        id<MTLDevice> device, int width, int height)
    {
        NSDictionary *props = @{
            (id)kIOSurfaceWidth: @(width),
            (id)kIOSurfaceHeight: @(height),
            (id)kIOSurfaceBytesPerElement: @4,
            (id)kIOSurfacePixelFormat: @(kCVPixelFormatType_32BGRA),
        };
        
        IOSurfaceRef surface = IOSurfaceCreate((__bridge CFDictionaryRef)props);
        if (!surface) return nil;
        
        MTLTextureDescriptor *desc = [MTLTextureDescriptor
            texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm
            width:width height:height mipmapped:NO];
        desc.usage = MTLTextureUsageShaderRead | MTLTextureUsageShaderWrite;
        
        id<MTLTexture> texture = [device newTextureWithDescriptor:desc
                                                       iosurface:surface
                                                           plane:0];
        CFRelease(surface);
        return texture;
    }
};
```

---

## 8. 顶点数据管理

**结论先行**：Metal 的顶点数据通过 `MTLVertexDescriptor` 描述布局，并通过 `MTLBuffer` 储存。对于复杂场景，应使用索引绘制（Indexed Drawing）减少顶点重复，并考虑交错布局（Interleaved）以优化缓存局部性。

### 8.1 顶点布局策略对比

```mermaid
graph LR
    subgraph 交错布局 Interleaved
        I[P0 N0 T0 | P1 N1 T1 | P2 N2 T2 | ...]
    end
    
    subgraph 分离布局 Separate
        S1[P0 P1 P2 ...]
        S2[N0 N1 N2 ...]
        S3[T0 T1 T2 ...]
    end
```

| 布局方式 | 缓存友好度 | 更新灵活性 | 推荐场景 |
|---------|---------|---------|--------|
| **交错布局** | ⭐⭐⭐ | 中 | 静态网格（推荐默认） |
| **分离布局** | ⭐⭐ | 高 | 需频繁更新某个属性时 |
| **混合布局** | ⭐⭐⭐ | 高 | 分离静态/动态属性 |

### 8.2 动态网格数据加载示例

```swift
// 从 Model I/O 加载 3D 模型
import ModelIO
import MetalKit

func loadMesh(device: MTLDevice, url: URL) -> MTKMesh? {
    let allocator = MTKMeshBufferAllocator(device: device)
    
    let vertexDescriptor = MDLVertexDescriptor()
    vertexDescriptor.attributes[0] = MDLVertexAttribute(
        name: MDLVertexAttributePosition, format: .float3, offset: 0, bufferIndex: 0)
    vertexDescriptor.attributes[1] = MDLVertexAttribute(
        name: MDLVertexAttributeNormal, format: .float3, offset: 12, bufferIndex: 0)
    vertexDescriptor.attributes[2] = MDLVertexAttribute(
        name: MDLVertexAttributeTextureCoordinate, format: .float2, offset: 24, bufferIndex: 0)
    vertexDescriptor.layouts[0] = MDLVertexBufferLayout(stride: 32)
    
    let asset = MDLAsset(
        url: url, vertexDescriptor: vertexDescriptor,
        bufferAllocator: allocator)
    
    guard let mdlMesh = asset.childObjects(of: MDLMesh.self).first as? MDLMesh else {
        return nil
    }
    
    return try? MTKMesh(mesh: mdlMesh, device: device)
}
```

---

# 第三层：高级优化层

## 9. 性能优化策略

**结论先行**：Metal 性能优化的核心原则是「让 CPU 和 GPU 并行工作，永不互相等待」。Triple Buffering 是实现这一目标的基础技术，而 Indirect Command Buffer 和 GPU-Driven Rendering 则进一步将决策逻辑从 CPU 转移到 GPU。

### 9.1 Triple Buffering 实现

```mermaid
sequenceDiagram
    participant CPU
    participant GPU
    
    Note over CPU,GPU: Triple Buffering 时序
    
    CPU->>CPU: 编码 Frame N (Buffer A)
    CPU->>GPU: 提交 Frame N
    
    CPU->>CPU: 编码 Frame N+1 (Buffer B)
    GPU->>GPU: 执行 Frame N
    CPU->>GPU: 提交 Frame N+1
    
    CPU->>CPU: 编码 Frame N+2 (Buffer C)
    GPU->>GPU: 执行 Frame N+1
    CPU->>GPU: 提交 Frame N+2
    
    Note over CPU: Buffer A 现在可复用
    CPU->>CPU: 编码 Frame N+3 (Buffer A)
    GPU->>GPU: 执行 Frame N+2
```

```swift
import Metal

class TripleBufferedRenderer {
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue
    
    // Triple Buffering: 3 份 Uniform 缓冲区
    private static let maxFramesInFlight = 3
    private var uniformBuffers: [MTLBuffer] = []
    private var currentBufferIndex = 0
    
    // 信号量控制并发
    private let frameSemaphore = DispatchSemaphore(value: maxFramesInFlight)
    
    init?(device: MTLDevice) {
        self.device = device
        guard let queue = device.makeCommandQueue() else { return nil }
        self.commandQueue = queue
        
        // 创建 3 份 Uniform Buffer
        for _ in 0..<Self.maxFramesInFlight {
            guard let buffer = device.makeBuffer(
                length: MemoryLayout<Uniforms>.size,
                options: .storageModeShared) else { return nil }
            uniformBuffers.append(buffer)
        }
    }
    
    func draw(in view: MTKView) {
        // 等待可用的 Buffer——如果 3 帧都在飞行中，则阻塞
        frameSemaphore.wait()
        
        // 使用当前索引的 Buffer
        let uniformBuffer = uniformBuffers[currentBufferIndex]
        updateUniforms(buffer: uniformBuffer)
        
        guard let commandBuffer = commandQueue.makeCommandBuffer() else {
            frameSemaphore.signal()
            return
        }
        
        // GPU 完成后释放信号量
        commandBuffer.addCompletedHandler { [weak self] _ in
            self?.frameSemaphore.signal()
        }
        
        // 编码渲染命令...
        if let rpd = view.currentRenderPassDescriptor,
           let encoder = commandBuffer.makeRenderCommandEncoder(descriptor: rpd) {
            encoder.setVertexBuffer(uniformBuffer, offset: 0, index: 1)
            // ... 绑定其他资源并绘制
            encoder.endEncoding()
        }
        
        if let drawable = view.currentDrawable {
            commandBuffer.present(drawable)
        }
        commandBuffer.commit()
        
        // 轮转到下一个 Buffer
        currentBufferIndex = (currentBufferIndex + 1) % Self.maxFramesInFlight
    }
    
    private func updateUniforms(buffer: MTLBuffer) {
        let ptr = buffer.contents().bindMemory(to: Uniforms.self, capacity: 1)
        // 更新变换矩阵等数据
    }
}
```

### 9.2 Indirect Command Buffer（ICB）

**结论先行**：ICB 允许 GPU 直接编码绘制命令，无需 CPU 每帧重新编码。这是 GPU-Driven Rendering 的基础，可将 Culling、LOD 选择等逻辑完全转移到 GPU。

```swift
// Indirect Command Buffer 示例
func setupIndirectCommandBuffer() {
    let icbDescriptor = MTLIndirectCommandBufferDescriptor()
    icbDescriptor.commandTypes = [.draw, .drawIndexed]
    icbDescriptor.inheritBuffers = false
    icbDescriptor.inheritPipelineState = true
    icbDescriptor.maxVertexBufferBindCount = 10
    icbDescriptor.maxFragmentBufferBindCount = 10
    
    let maxCommands = 1000  // 最大绘制命令数
    guard let icb = device.makeIndirectCommandBuffer(
        descriptor: icbDescriptor,
        maxCommandCount: maxCommands,
        options: .storageModeShared) else { return }
    
    // 在 Compute Shader 中填充 ICB
    // GPU 可以根据 Frustum Culling / Occlusion Query 结果
    // 动态决定哪些对象需要绘制
}
```

```metal
// GPU-Driven Rendering: 在 Compute Shader 中填充 ICB
kernel void encodeDrawCommands(
    device const ObjectData* objects [[buffer(0)]],
    device const FrustumPlanes& frustum [[buffer(1)]],
    device atomic_uint& drawCount [[buffer(2)]],
    command_buffer icb [[buffer(3)]],
    uint objectIndex [[thread_position_in_grid]])
{
    ObjectData obj = objects[objectIndex];
    
    // GPU 端 Frustum Culling
    if (!isInFrustum(obj.boundingSphere, frustum)) {
        return;
    }
    
    // LOD 选择
    float distance = length(obj.position - frustum.cameraPos);
    uint lodLevel = selectLOD(distance);
    
    // 编码绘制命令
    uint cmdIndex = atomic_fetch_add_explicit(&drawCount, 1, memory_order_relaxed);
    render_command cmd(icb, cmdIndex);
    
    cmd.set_vertex_buffer(obj.vertexBuffers[lodLevel], 0);
    cmd.draw_indexed_primitives(
        primitive_type::triangle,
        obj.indexCounts[lodLevel],
        obj.indexBuffers[lodLevel],
        1, 0, 0);
}
```

### 9.3 利用 TBDR 架构优化

```mermaid
graph TB
    subgraph TBDR 优化策略
        A[使用 Memoryless 附件] --> |"MSAA/Depth 不写回内存"| SAVE1["节省带宽"]
        B[正确设置 LoadAction/StoreAction] --> SAVE2["避免不必要的加载/存储"]
        C[使用 Tile Shading] --> SAVE3["利用片上内存"]
        D[避免中途刷新 Tile] --> SAVE4["减少 Tile 写回"]
    end
```

```swift
// TBDR 优化示例：正确配置 RenderPassDescriptor
func optimizedRenderPassDescriptor() -> MTLRenderPassDescriptor {
    let rpd = MTLRenderPassDescriptor()
    
    // 颜色附件：如果不需要保留上一帧，用 .dontCare
    rpd.colorAttachments[0].loadAction = .clear
    rpd.colorAttachments[0].storeAction = .store     // 需要显示
    
    // 深度附件：如果不需要回读，用 .dontCare
    rpd.depthAttachment.loadAction = .clear
    rpd.depthAttachment.storeAction = .dontCare     // ⭐ TBDR 关键！不写回内存
    
    // MSAA 解析纹理：使用 Memoryless
    // rpd.colorAttachments[0].texture = msaaTexture    // multisampleColorTexture
    // rpd.colorAttachments[0].resolveTexture = resolvedTexture
    // rpd.colorAttachments[0].storeAction = .multisampleResolve
    
    return rpd
}

// Memoryless 纹理（仅存在于 Tile Memory，不占内存）
func createMemorylessTexture(width: Int, height: Int) -> MTLTexture? {
    let desc = MTLTextureDescriptor.texture2DDescriptor(
        pixelFormat: .depth32Float, width: width, height: height, mipmapped: false)
    desc.storageMode = .memoryless  // ⭐ 仅存在于片上 Tile Memory
    desc.usage = .renderTarget
    return device.makeTexture(descriptor: desc)
}
```

**Load/Store Action 对性能的影响**：

| 配置 | loadAction | storeAction | 带宽开销 | 适用场景 |
|------|-----------|-------------|---------|--------|
| **最优** | `.clear`/`.dontCare` | `.dontCare` | 最低 | Depth/Stencil（不回读） |
| **标准** | `.clear` | `.store` | 中等 | 颜色附件（需显示） |
| **最差** | `.load` | `.store` | 最高 | 避免！除非确实需要读取上一帧 |

---

## 10. 内存管理

**结论先行**：Metal 的内存管理核心是 Resource Storage Mode 的正确选择。Apple Silicon 的统一内存架构（UMA）意味着 `.shared` 模式不产生数据拷贝，但并非所有场景都应用 `.shared`——`.private` 可让 GPU 对内存布局做专属优化，`.memoryless` 则完全避免内存分配。

> **知识关联**：Metal 的 Resource Storage Mode 与 [iOS 内存优化](./cpp_memory_optimization/03_系统级优化/iOS内存优化.md) 中的 Clean/Dirty Memory 分类密切相关——Metal Buffer 使用的内存计入 Dirty Memory（footprint），直接影响 Jetsam 阀值。

### 10.1 Resource Storage Mode

```mermaid
graph TB
    subgraph Storage Modes
        SHARED[".shared<br/>CPU+GPU 都可访问"] --> |"UMA 下零拷贝"| UMA[Unified Memory]
        PRIVATE[".private<br/>仅 GPU 可访问"] --> |"GPU 专属优化"| VRAM[GPU 优化布局]
        MEMORYLESS[".memoryless<br/>仅 Tile Memory"] --> |"不占系统内存"| TILE[Tile SRAM]
    end
    
    subgraph 选择指南
        Q1{"需要 CPU 访问？"}
        Q1 --> |"Yes"| SHARED
        Q1 --> |"No"| Q2{"需要持久化？"}
        Q2 --> |"Yes"| PRIVATE
        Q2 --> |"No（仅 Render Pass 内）"| MEMORYLESS
    end
```

| Storage Mode | CPU 访问 | GPU 访问 | 内存占用 | 适用场景 |
|-------------|---------|---------|---------|--------|
| **`.shared`** | ✅ 可读写 | ✅ 可读写 | 计入 footprint | Uniform、动态顶点、CPU 回读结果 |
| **`.private`** | ❌ | ✅ 最优性能 | 计入 footprint | 纹理、静态 Mesh、渲染目标 |
| **`.memoryless`** | ❌ | ✅ 仅 Tile 内 | ⭐ 不占内存 | MSAA 解析纹理、临时 Depth/Stencil |

### 10.2 Purgeable / Volatile 资源

```swift
/// Purgeable 资源管理——内存压力时系统可自动回收
class PurgeableTextureCache {
    private let device: MTLDevice
    private var cachedTextures: [String: MTLTexture] = [:]
    
    init(device: MTLDevice) {
        self.device = device
    }
    
    func cacheTexture(_ texture: MTLTexture, forKey key: String) {
        // 标记为可清除状态
        texture.setPurgeableState(.volatile)
        cachedTextures[key] = texture
    }
    
    func getTexture(forKey key: String) -> MTLTexture? {
        guard let texture = cachedTextures[key] else { return nil }
        
        // 检查是否已被系统回收
        let oldState = texture.setPurgeableState(.nonVolatile)
        if oldState == .empty {
            // 内存已被回收，需要重新加载
            cachedTextures.removeValue(forKey: key)
            return nil
        }
        
        return texture
    }
    
    func releaseUnderMemoryPressure() {
        // 主动释放所有缓存纹理
        for (key, texture) in cachedTextures {
            texture.setPurgeableState(.empty)
            cachedTextures.removeValue(forKey: key)
        }
    }
}
```

### 10.3 MTLHeap 内存池管理

```swift
/// 使用 MTLHeap 进行批量资源分配，减少内存碎片
class HeapResourceManager {
    private let device: MTLDevice
    private var heap: MTLHeap?
    
    init(device: MTLDevice) {
        self.device = device
    }
    
    func createHeap(forTextures texDescriptors: [MTLTextureDescriptor]) {
        // 计算所有纹理所需的总内存
        var heapSize: Int = 0
        for desc in texDescriptors {
            let sizeAlign = device.heapTextureSizeAndAlign(descriptor: desc)
            heapSize += sizeAlign.size + sizeAlign.align  // 加上对齐开销
        }
        
        let heapDescriptor = MTLHeapDescriptor()
        heapDescriptor.size = heapSize
        heapDescriptor.storageMode = .private
        heapDescriptor.cpuCacheMode = .defaultCache
        heapDescriptor.hazardTrackingMode = .tracked
        
        heap = device.makeHeap(descriptor: heapDescriptor)
    }
    
    func allocateTexture(descriptor: MTLTextureDescriptor) -> MTLTexture? {
        return heap?.makeTexture(descriptor: descriptor)
    }
    
    /// 通过 Aliasing 复用内存：同一块内存在不同时间段分配给不同资源
    func aliasTexture(descriptor: MTLTextureDescriptor) -> MTLTexture? {
        // 通过 makeAliasable() 标记旧资源的内存可被复用
        // 然后从同一 Heap 分配新资源，可能复用同一块内存
        return heap?.makeTexture(descriptor: descriptor)
    }
}
```

### 10.4 内存优化效果对比

| 优化手段 | 内存节省 | 带宽节省 | 实现复杂度 | 典型场景 |
|---------|---------|---------|---------|--------|
| **Memoryless 深度/MSAA** | 30-50% | 20-40% | 低 | MSAA 渲染 |
| **Shared 替代 Private+Blit** | 0%（UMA） | 减少拷贝 | 低 | 动态数据 |
| **MTLHeap Aliasing** | 20-40% | 0% | 中 | 多 Pass 渲染 |
| **Purgeable 缓存** | 自动调节 | 0% | 低 | 纹理缓存 |
| **IOSurface 零拷贝** | 50%+ | 90%+ | 中 | 视频/相机处理 |

---

## 11. 并行计算优化

**结论先行**：Metal 的 GPU 并行性能取决于三个因素：线程组大小、SIMD Group 利用率、GPU 占用率。理解 Apple GPU 的 SIMD Group（32 线程宽度）是写出高效 Compute Shader 的关键。

> **知识关联**：SIMD Group 的概念类似于 [图像处理并行化](./thread/06_工程应用实战/图像处理并行化_详细解析.md) 中的 CPU SIMD（NEON 16 像素/指令），但 GPU SIMD Group 宽度更大（32 线程），且支持线程间直接通信（Shuffle）。

### 11.1 GPU 并行层次

```mermaid
graph TB
    subgraph Apple GPU 并行层次
        GRID[Grid<br/>全局线程网格] --> TG1[Threadgroup 0]
        GRID --> TG2[Threadgroup 1]
        GRID --> TGN[Threadgroup N...]
        
        TG1 --> SG1[SIMD Group 0<br/>32 线程]
        TG1 --> SG2[SIMD Group 1<br/>32 线程]
        TG1 --> SGM[SIMD Group M...]
        
        SG1 --> T0[Thread 0]
        SG1 --> T1[Thread 1]
        SG1 --> T31[Thread 31]
    end
    
    subgraph 内存层次
        DM[Device Memory<br/>全局内存] --> TGM[Threadgroup Memory<br/>线程组共享]
        TGM --> SIMDM[SIMD-scoped Memory<br/>SIMD 组内共享]
        SIMDM --> TM[Thread Memory<br/>寄存器]
    end
```

### 11.2 SIMD Group 优化

```metal
// SIMD Group 内约缩操作——极快的并行归约
kernel void simdReduction(
    device const float* input [[buffer(0)]],
    device float* output [[buffer(1)]],
    uint gid [[thread_position_in_grid]],
    uint simd_lane_id [[thread_index_in_simdgroup]],
    uint simd_group_id [[simdgroup_index_in_threadgroup]])
{
    float value = input[gid];
    
    // SIMD Group 内求和（无需共享内存！）
    float sum = simd_sum(value);
    
    // 只有每个 SIMD Group 的第一个线程写入结果
    if (simd_lane_id == 0) {
        output[simd_group_id] = sum;
    }
}

// SIMD Shuffle 优化的前缀和
kernel void simdPrefixSum(
    device const float* input [[buffer(0)]],
    device float* output [[buffer(1)]],
    uint gid [[thread_position_in_grid]],
    uint simd_lane_id [[thread_index_in_simdgroup]])
{
    float value = input[gid];
    
    // SIMD Group 内前缀和 (inclusive)
    float prefix = simd_prefix_inclusive_sum(value);
    
    output[gid] = prefix;
}

// SIMD Group Matrix 乘法（Apple GPU 特有，A14+）
kernel void simdMatrixMultiply(
    device const float* A [[buffer(0)]],
    device const float* B [[buffer(1)]],
    device float* C [[buffer(2)]],
    uint2 gid [[thread_position_in_grid]])
{
    // 使用 simdgroup_matrix 进行硬件加速矩阵运算
    simdgroup_float8x8 a, b, c;
    
    simdgroup_load(a, A, /* elements per row */8);
    simdgroup_load(b, B, 8);
    
    simdgroup_multiply_accumulate(c, a, b, c);
    
    simdgroup_store(c, C, 8);
}
```

### 11.3 GPU 占用率优化

| 因素 | 描述 | 优化方向 |
|------|------|--------|
| **线程组大小** | 太小导致 GPU 空闲，太大导致寄存器压力 | 用 `threadExecutionWidth` 动态计算 |
| **寄存器压力** | 每线程寄存器多，占用率低 | 减少局部变量，用 `half` 替代 `float` |
| **Threadgroup Memory** | 过多共享内存限制并发线程组数 | 控制共享内存用量 |
| **分支发散** | SIMD Group 内分支导致线程空等 | 减少条件分支，用 `select()` 替代 `if` |
| **内存访问模式** | 非合并访问浪费带宽 | 确保 SIMD Group 内连续访问 |

### 11.4 性能对比数据

| 操作 | CPU (8线程+NEON) | Metal Compute | 加速比 | 注释 |
|------|---------------|---------------|--------|------|
| **4K 高斯模糊 5×5** | 18.0 ms | 2.1 ms | 8.6x | MPS 可达 1.5ms |
| **4K 色彩转换** | 4.5 ms | 0.5 ms | 9.0x | 带宽受限 |
| **1M 元素归约** | 1.2 ms | 0.08 ms | 15x | SIMD Reduction |
| **矩阵乘法 1024×1024** | 350 ms | 5.2 ms | 67x | simdgroup_matrix |
| **双边滤波 4K** | 85 ms | 4.8 ms | 17.7x | Threadgroup Memory |

*测试设备：iPhone 14 Pro, A16 Bionic*

---

## 12. 调试与性能分析工具

**结论先行**：Xcode 提供了业界最强大的 GPU 调试工具链。GPU Capture 可以“回放”每一个 GPU 操作的状态，Metal System Trace 揭示 CPU/GPU 时间线，Shader Profiler 定位瀑颈指令。

### 12.1 工具概览

```mermaid
graph LR
    subgraph Xcode GPU 工具链
        A[GPU Capture] --> |"单帧截取"| B[查看每个 Draw Call]
        B --> C[检查资源绑定]
        B --> D[查看 Shader 输入/输出]
        B --> E[Shader Profiler]
        
        F[Metal System Trace] --> G[CPU/GPU 时间线]
        G --> H[识别空泡/阻塞]
        
        I[GPU Counter Profiler] --> J[硬件计数器]
        J --> K[ALU/带宽/占用率]
    end
```

### 12.2 GPU Capture 使用流程

| 步骤 | 操作 | 检查点 |
|------|------|--------|
| 1 | Xcode → Debug → Capture GPU Workload | - |
| 2 | 查看 Command Buffer 列表 | 是否有不必要的 Pass |
| 3 | 点击每个 Encoder | 绑定的资源是否正确 |
| 4 | 查看 Shader 调试器 | 检查变量值、踊结果 |
| 5 | Dependency Viewer | 资源依赖是否引起不必要等待 |
| 6 | Performance 标签 | GPU 时间、带宽、占用率 |

### 12.3 Metal System Trace

```
┌─────────────────────────────────────────────────────────────┐
│             Metal System Trace 时间线示例                     │
├─────────────────────────────────────────────────────────────┤
│  时间 →   0ms    4ms    8ms    12ms   16ms (1帧)    │
│  ─────────────────────────────────────────────    │
│  CPU:  [编码 N]         [编码 N+1]          [编码 N+2]  │
│  GPU:        [顶点 N][片段 N]   [顶点 N+1][片段 N+1]  │
│  显示:              [待显示][显示 N]       [待显示]    │
│  ─────────────────────────────────────────────    │
│                                                               │
│  ⭐ 关注点：                                                  │
│  • CPU/GPU 之间是否有空洞（互相等待）                      │
│  • 顶点处理和片段处理的时间比例                        │
│  • 每帧总时间是否在 16.6ms 内                          │
└─────────────────────────────────────────────────────────────┘
```

### 12.4 Shader Profiler 指标

| 指标 | 含义 | 理想值 | 警告阀值 |
|------|------|--------|--------|
| **ALU Utilization** | 计算单元利用率 | >70% | <40% 表示带宽受限 |
| **Memory Bandwidth** | 内存带宽使用率 | <80% | >90% 表示带宽瓶颈 |
| **GPU Occupancy** | GPU 线程占用率 | >60% | <30% 需调整线程组 |
| **Shader Time** | 单 Shader 执行时间 | - | 超过帧预算卖7定位优化 |
| **Overdraw** | 像素重复绘制次数 | 1.0x | >2.0x 需优化 |

### 12.5 调试代码示例

```swift
// 在代码中插入 GPU 时间戳
 func drawWithTimestamps(in view: MTKView) {
    guard let commandBuffer = commandQueue.makeCommandBuffer() else { return }
    
    // 创建事件用于计时
    let startEvent = device.makeEvent()!
    let endEvent = device.makeEvent()!
    
    commandBuffer.encodeSignalEvent(startEvent, value: 1)
    
    // ... 渲染命令 ...
    
    commandBuffer.encodeSignalEvent(endEvent, value: 1)
    
    commandBuffer.addCompletedHandler { _ in
        // 计算 GPU 执行时间
        print("GPU frame time: calculated from events")
    }
    
    commandBuffer.commit()
}

// 使用 MTLCounterSampleBuffer 读取硬件计数器
func setupGPUCounters() {
    guard let counterSets = device.counterSets else { return }
    
    for counterSet in counterSets {
        print("计数器组: \(counterSet.name)")
        for counter in counterSet.counters {
            print("  - \(counter.name)")
        }
    }
}
```

---

## 总结

```mermaid
graph TB
    subgraph 核心概念层
        A["统一内存架构 (UMA)"] 
        B["TBDR 架构"]
        C["命令提交模型"]
        D["MSL 基于 C++14"]
    end
    
    subgraph 基础使用层
        E["管线状态预编译"]
        F["多线程命令编码"]
        G["CVMetalTextureCache 零拷贝"]
        H["Compute Pipeline"]
    end
    
    subgraph 高级优化层
        I["Triple Buffering"]
        J["Indirect Command Buffer"]
        K["SIMD Group 优化"]
        L["Memoryless + TBDR"]
        M["GPU Capture 调试"]
    end
    
    A --> E
    B --> L
    C --> F
    D --> H
    E --> I
    F --> J
    G --> K
    H --> K
    I --> M
    J --> M
    K --> M
    L --> M
```

### 关键要点回顾

| 层次 | 核心要点 | 最重要的一句话 |
|------|---------|-------------|
| **核心概念** | UMA + TBDR + 命令模型 | Metal 的优势在 CPU 端，不在 GPU 端 |
| **基础使用** | 预编译管线 + 多线程编码 | 管线状态必须在加载时创建，不可每帧创建 |
| **内存管理** | Storage Mode + Memoryless | `.dontCare` 是 TBDR 架构下最重要的优化 |
| **计算优化** | SIMD Group + Threadgroup Memory | `half` 类型是 Apple GPU 上的免费性能提升 |
| **性能分析** | GPU Capture + System Trace | 每次优化都应用 Profiler 验证，而非猜测 |

### 性能优化检查清单

- [ ] 是否使用 Triple Buffering 避免 CPU/GPU 互等？
- [ ] Depth/Stencil 的 `storeAction` 是否设为 `.dontCare`？
- [ ] MSAA 解析纹理是否使用 `.memoryless`？
- [ ] 是否优先使用 `half` 类型而非 `float`？
- [ ] Compute Shader 的 Threadgroup 大小是否基于 `threadExecutionWidth` 计算？
- [ ] 视频/相机处理是否使用 CVMetalTextureCache/IOSurface 零拷贝？
- [ ] 是否用 GPU Capture 验证了每次优化的效果？
- [ ] 静态资源是否使用 `.private` Storage Mode？
- [ ] 是否通过 MTLHeap 管理临时资源以减少碎片？
- [ ] Shader 中是否避免了 SIMD Group 内的分支发散？

---

## 13. 多线程 CommandBuffer 提交

**结论先行**：Metal 的 `MTLCommandQueue` 是线程安全的，可多线程并发创建 `MTLCommandBuffer`；但每个 `CommandBuffer` 本身不是线程安全的，编码操作必须串行。最佳实践是「多线程并行准备数据 + 单线程顺序提交」或「每个线程独立 CommandBuffer 并行提交」。

### 13.1 多线程提交核心原则

```mermaid
graph TB
    subgraph 线程安全规则
        Q[MTLCommandQueue<br/>✅ 线程安全] --> CB1[CommandBuffer A]
        Q --> CB2[CommandBuffer B]
        Q --> CB3[CommandBuffer C]
        
        CB1 --> |❌ 非线程安全| E1[Encoder A1]
        CB1 --> |❌ 非线程安全| E2[Encoder A2]
        
        CB2 --> |❌ 非线程安全| E3[Encoder B1]
    end
    
    subgraph 两种模式
        M1[模式1: 并行准备 + 串行提交] --> M1_D[多个线程准备数据<br/>主线程统一提交]
        M2[模式2: 独立队列并行提交] --> M2_D[每个线程独立 Queue<br/>并行编码和提交]
    end
```

| 组件 | 线程安全 | 说明 |
|------|---------|------|
| **MTLCommandQueue** | ✅ | 可多线程同时 `makeCommandBuffer()` |
| **MTLCommandBuffer** | ❌ | 编码器创建和命令编码需串行 |
| **MTLRenderPipelineState** | ✅ | 只读状态对象，可多线程绑定 |
| **MTLBuffer/MTLTexture** | ⚠️ | 内容读写需同步，对象本身线程安全 |

### 13.2 Camera + 前处理 多线程架构

**场景描述**：
- **Camera 线程**：从 AVCaptureSession 获取帧，进行基础格式转换
- **前处理线程**：执行 Metal Compute Shader（色彩空间转换、缩放、归一化）
- **主线程**：渲染到屏幕

```mermaid
sequenceDiagram
    participant CT as Camera Thread<br/>AVCaptureSession
    participant PT as Preprocess Thread<br/>Metal Compute
    participant MT as Main Thread<br/>Render
    participant GPU as GPU
    
    Note over CT,GPU: Triple Buffering 机制
    
    CT->>CT: Frame N 采集
    CT->>CT: CVPixelBuffer → MTLTexture
    CT->>PT: 信号: Frame N 就绪
    
    PT->>PT: 等待信号量 (maxFramesInFlight)
    PT->>PT: 获取可用 Buffer Index
    PT->>GPU: 创建 CommandBuffer
    PT->>GPU: Encode Compute Shader<br/>色彩转换/缩放/归一化
    PT->>GPU: Commit CommandBuffer
    PT->>MT: 信号: 前处理完成
    
    GPU->>GPU: 执行 Compute
    GPU-->>PT: addCompletedHandler<br/>释放信号量
    
    MT->>MT: 等待前处理完成
    MT->>GPU: 创建 Render CommandBuffer
    MT->>GPU: Encode Render Pass
    MT->>GPU: Present Drawable
    MT->>GPU: Commit
    
    CT->>CT: Frame N+1 采集
    CT->>PT: 信号: Frame N+1 就绪
    PT->>PT: 使用下一个 Buffer Index
    Note over PT: 与 GPU 执行 Frame N 并行
```

### 13.3 完整代码实现

```swift
import Metal
import MetalKit
import AVFoundation

// MARK: - 多线程 Metal 相机处理器

class MultithreadedCameraProcessor: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    
    // MARK: Metal 资源
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue          // 主队列用于渲染
    private let computeQueue: MTLCommandQueue          // 独立队列用于前处理
    
    // MARK: 管线状态
    private var computePipeline: MTLComputePipelineState!   // 前处理 Compute
    private var renderPipeline: MTLRenderPipelineState!     // 渲染管线
    
    // MARK: 多线程同步
    private let frameSemaphore: DispatchSemaphore
    private static let maxFramesInFlight = 3
    
    // MARK: 缓冲区管理 (Triple Buffering)
    private var intermediateTextures: [MTLTexture] = []  // Compute 输出 / Render 输入
    private var availableBufferIndices: [Int] = [0, 1, 2]
    private var bufferIndexLock = NSLock()
    
    // MARK: 线程
    private let cameraQueue = DispatchQueue(label: "com.example.camera", qos: .userInitiated)
    private let preprocessQueue = DispatchQueue(label: "com.example.preprocess", qos: .userInitiated)
    private var textureCache: CVMetalTextureCache?
    
    // MARK: 状态
    private var currentFrameIndex = 0
    @Published var fps: Double = 0
    private var lastFrameTime: CFTimeInterval = 0
    
    init?(metalView: MTKView) {
        guard let device = MTLCreateSystemDefaultDevice(),
              let commandQueue = device.makeCommandQueue(),
              let computeQueue = device.makeCommandQueue() else {
            return nil
        }
        
        self.device = device
        self.commandQueue = commandQueue
        self.computeQueue = computeQueue
        self.frameSemaphore = DispatchSemaphore(value: Self.maxFramesInFlight)
        
        super.init()
        
        // 初始化纹理缓存
        CVMetalTextureCacheCreate(nil, nil, device, nil, &textureCache)
        
        // 设置 MetalView
        metalView.device = device
        metalView.delegate = self
        metalView.colorPixelFormat = .bgra8Unorm
        
        // 创建资源
        createPipelines()
        createIntermediateTextures(width: 1920, height: 1080)
        setupCamera()
    }
    
    // MARK: - 资源创建
    
    private func createPipelines() {
        let library = device.makeDefaultLibrary()!
        
        // Compute Pipeline: 色彩转换 + 缩放
        let computeFunc = library.makeFunction(name: "preprocessCameraFrame")!
        computePipeline = try! device.makeComputePipelineState(function: computeFunc)
        
        // Render Pipeline: 显示结果
        let vertexFunc = library.makeFunction(name: "vertexShader")!
        let fragmentFunc = library.makeFunction(name: "fragmentShader")!
        
        let renderDesc = MTLRenderPipelineDescriptor()
        renderDesc.vertexFunction = vertexFunc
        renderDesc.fragmentFunction = fragmentFunc
        renderDesc.colorAttachments[0].pixelFormat = .bgra8Unorm
        renderPipeline = try! device.makeRenderPipelineState(descriptor: renderDesc)
    }
    
    private func createIntermediateTextures(width: Int, height: Int) {
        let desc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: .rgba8Unorm,
            width: width,
            height: height,
            mipmapped: false
        )
        desc.usage = [.shaderRead, .shaderWrite, .renderTarget]
        desc.storageMode = .private  // GPU 独占，优化性能
        
        for _ in 0..<Self.maxFramesInFlight {
            intermediateTextures.append(device.makeTexture(descriptor: desc)!)
        }
    }
    
    // MARK: - Camera 设置
    
    private func setupCamera() {
        let captureSession = AVCaptureSession()
        captureSession.sessionPreset = .hd1920x1080
        
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device) else {
            return
        }
        
        captureSession.addInput(input)
        
        let output = AVCaptureVideoDataOutput()
        output.setSampleBufferDelegate(self, queue: cameraQueue)
        output.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ]
        captureSession.addOutput(output)
        
        DispatchQueue.global(qos: .background).async {
            captureSession.startRunning()
        }
    }
    
    // MARK: - AVCaptureVideoDataOutputSampleBufferDelegate
    
    func captureOutput(_ output: AVCaptureOutput, 
                       didOutput sampleBuffer: CMSampleBuffer, 
                       from connection: AVCaptureConnection) {
        
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        // 计算 FPS
        let currentTime = CACurrentMediaTime()
        let delta = currentTime - lastFrameTime
        lastFrameTime = currentTime
        fps = 1.0 / delta
        
        // 获取当前帧的 Buffer Index
        frameSemaphore.wait()  // 等待可用槽位
        
        let bufferIndex = getNextBufferIndex()
        
        // 将工作提交到前处理线程
        preprocessQueue.async { [weak self] in
            self?.preprocessFrame(pixelBuffer: pixelBuffer, bufferIndex: bufferIndex)
        }
    }
    
    // MARK: - 前处理线程 (Metal Compute)
    
    private func preprocessFrame(pixelBuffer: CVPixelBuffer, bufferIndex: Int) {
        // 1. 创建 CommandBuffer (在 computeQueue 上)
        guard let commandBuffer = computeQueue.makeCommandBuffer() else {
            releaseBufferIndex(bufferIndex)
            return
        }
        
        // 2. 从 CVPixelBuffer 创建 MTLTexture (零拷贝)
        let cameraTexture = createTextureFromPixelBuffer(pixelBuffer)
        let outputTexture = intermediateTextures[bufferIndex]
        
        // 3. 创建 Compute Encoder
        guard let encoder = commandBuffer.makeComputeCommandEncoder() else {
            releaseBufferIndex(bufferIndex)
            return
        }
        
        encoder.setComputePipelineState(computePipeline)
        encoder.setTexture(cameraTexture, index: 0)
        encoder.setTexture(outputTexture, index: 1)
        
        // 设置参数 (例如：归一化参数)
        var params = PreprocessParams(
            mean: simd_float3(0.485, 0.456, 0.406),
            std: simd_float3(0.229, 0.224, 0.225)
        )
        encoder.setBytes(&params, length: MemoryLayout<PreprocessParams>.size, index: 0)
        
        // 计算线程组
        let threadGroupSize = MTLSize(width: 16, height: 16, depth: 1)
        let threadGroups = MTLSize(
            width: (outputTexture.width + 15) / 16,
            height: (outputTexture.height + 15) / 16,
            depth: 1
        )
        
        encoder.dispatchThreadgroups(threadGroups, threadsPerThreadgroup: threadGroupSize)
        encoder.endEncoding()
        
        // 4. 添加完成回调，释放信号量
        commandBuffer.addCompletedHandler { [weak self] _ in
            // GPU 完成 Compute，可以开始渲染
            // 注意：这里不释放信号量，等渲染完成后再释放
        }
        
        // 5. 提交 Compute 命令
        commandBuffer.commit()
        
        // 6. 通知主线程渲染 (携带 bufferIndex)
        DispatchQueue.main.async { [weak self] in
            self?.renderFrame(bufferIndex: bufferIndex)
        }
    }
    
    // MARK: - 主线程渲染
    
    private func renderFrame(bufferIndex: Int) {
        // 注意：这里应该在 MTKViewDelegate 的 draw(in:) 中调用
        // 简化示例直接渲染
        currentFrameIndex = bufferIndex
        // 触发 MTKView 重绘
    }
    
    // MARK: - 缓冲区索引管理
    
    private func getNextBufferIndex() -> Int {
        bufferIndexLock.lock()
        defer { bufferIndexLock.unlock() }
        
        // 简单轮转
        let index = availableBufferIndices.removeFirst()
        availableBufferIndices.append(index)
        return index
    }
    
    private func releaseBufferIndex(_ index: Int) {
        frameSemaphore.signal()
    }
    
    private func createTextureFromPixelBuffer(_ pixelBuffer: CVPixelBuffer) -> MTLTexture? {
        var cvTexture: CVMetalTexture?
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        
        CVMetalTextureCacheCreateTextureFromImage(
            nil,
            textureCache!,
            pixelBuffer,
            nil,
            .bgra8Unorm,
            width,
            height,
            0,
            &cvTexture
        )
        
        return cvTexture.flatMap { CVMetalTextureGetTexture($0) }
    }
}

// MARK: - MTKViewDelegate

extension MultithreadedCameraProcessor: MTKViewDelegate {
    
    func draw(in view: MTKView) {
        guard let drawable = view.currentDrawable,
              let renderPassDescriptor = view.currentRenderPassDescriptor else {
            return
        }
        
        // 使用当前帧对应的纹理
        let inputTexture = intermediateTextures[currentFrameIndex]
        
        // 在主线程创建 Render CommandBuffer
        guard let commandBuffer = commandQueue.makeCommandBuffer() else { return }
        
        // 创建 Render Encoder
        guard let encoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor) else {
            return
        }
        
        encoder.setRenderPipelineState(renderPipeline)
        encoder.setFragmentTexture(inputTexture, index: 0)
        // ... 设置顶点缓冲区等
        encoder.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 6)
        encoder.endEncoding()
        
        // 显示并提交
        commandBuffer.present(drawable)
        
        // 渲染完成后释放信号量
        commandBuffer.addCompletedHandler { [weak self] _ in
            self?.releaseBufferIndex(self?.currentFrameIndex ?? 0)
        }
        
        commandBuffer.commit()
    }
    
    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}
}

// MARK: - 数据结构

struct PreprocessParams {
    let mean: simd_float3
    let std: simd_float3
}
```

### 13.4 Metal Shaders

```metal
// CameraProcessing.metal
#include <metal_stdlib>
using namespace metal;

// 前处理 Kernel：色彩空间转换 + 归一化
kernel void preprocessCameraFrame(
    texture2d<float, access::read> cameraTexture [[texture(0)]],
    texture2d<float, access::write> outputTexture [[texture(1)]],
    constant PreprocessParams& params [[buffer(0)]],
    uint2 gid [[thread_position_in_grid]])
{
    if (gid.x >= outputTexture.get_width() || gid.y >= outputTexture.get_height()) {
        return;
    }
    
    // 读取相机帧 (BGRA)
    float4 color = cameraTexture.read(gid);
    
    // BGR → RGB 并归一化到 [0,1]
    float3 rgb = float3(color.b, color.g, color.r);
    
    // ImageNet 标准化
    rgb = (rgb - params.mean) / params.std;
    
    outputTexture.write(float4(rgb, 1.0), gid);
}

// 渲染 Shader
vertex VertexOut vertexShader(
    uint vertexID [[vertex_id]])
{
    // 全屏四边形顶点
    float2 positions[4] = {
        float2(-1, -1), float2(1, -1),
        float2(-1,  1), float2(1,  1)
    };
    float2 texCoords[4] = {
        float2(0, 1), float2(1, 1),
        float2(0, 0), float2(1, 0)
    };
    
    VertexOut out;
    out.position = float4(positions[vertexID], 0, 1);
    out.texCoord = texCoords[vertexID];
    return out;
}

fragment float4 fragmentShader(
    VertexOut in [[stage_in]],
    texture2d<float> inputTexture [[texture(0)]])
{
    constexpr sampler texSampler;
    return inputTexture.sample(texSampler, in.texCoord);
}

struct VertexOut {
    float4 position [[position]];
    float2 texCoord;
};

struct PreprocessParams {
    float3 mean;
    float3 std;
};
```

### 13.5 关键设计要点

| 设计决策 | 原因 | 替代方案 |
|---------|------|---------|
| **独立 ComputeQueue** | 避免 Compute 和 Render 互相阻塞 | 共用 Queue 会导致序列化 |
| **Triple Buffering** | CPU/GPU 并行，避免等待 | Double Buffering 可能不够用 |
| **Private 存储模式** | Compute → Render 无需 CPU 参与 | Shared 模式增加带宽消耗 |
| **信号量控制** | 防止内存爆炸（过多帧积压） | 无限制提交会耗尽内存 |
| **CVMetalTextureCache** | 零拷贝相机帧 → Metal | 手动拷贝增加延迟 |

### 13.6 性能优化检查清单

- [ ] Camera 线程只做轻量工作（格式转换），重计算移到 Compute 线程？
- [ ] Compute 和 Render 使用独立的 CommandQueue？
- [ ] 中间纹理使用 `.private` 存储模式？
- [ ] 使用 `CVMetalTextureCache` 实现相机帧零拷贝？
- [ ] Triple Buffering 确保 CPU/GPU 并行？
- [ ] 信号量防止帧积压导致内存爆炸？
- [ ] Compute 完成后通过 `addCompletedHandler` 通知渲染？
- [ ] 避免在 CommandBuffer 编码时跨线程访问？

---

## 14. 多线程 MTLTexture 共享

**结论先行**：`MTLTexture` 对象本身是线程安全的（只读引用），但其**内容访问需要同步**。多线程共享纹理的核心原则是：「对象可跨线程传递，内容访问需串行化，GPU 写入后需同步点才能读取」。

### 14.1 线程安全模型

```mermaid
graph TB
    subgraph MTLTexture 线程安全模型
        T[MTLTexture 对象] --> |✅ 线程安全| REF[引用/指针传递]
        T --> |❌ 需同步| CONTENT[内容读写]
        
        CONTENT --> CPU_READ[CPU 读取]
        CONTENT --> CPU_WRITE[CPU 写入]
        CONTENT --> GPU_WRITE[GPU 写入]
        
        GPU_WRITE --> SYNC[同步点<br/>blitCommandEncoder/<br/>addCompletedHandler]
        SYNC --> CPU_READ
    end
    
    subgraph 存储模式影响
        SHARED[.shared] --> |CPU+GPU 访问| SYNC_NEED[需要显式同步]
        PRIVATE[.private] --> |仅 GPU 访问| NO_CPU[CPU 无法直接访问]
        MEMORYLESS[.memoryless] --> |仅 Tile 内| RENDER_PASS[RenderPass 内有效]
    end
```

### 14.2 多线程共享场景与方案

| 场景 | 方案 | 同步机制 |
|------|------|---------|
| **Producer-Consumer** (Compute → Render) | 同一纹理，先 Write 后 Read | `addCompletedHandler` 或 `waitUntilCompleted` |
| **Ping-Pong 双缓冲** | 两个纹理交替读写 | 索引切换，无需等待 |
| **CPU 读取 GPU 结果** | `.shared` 纹理 + 同步 | `blitCommandEncoder` 拷贝到 `.shared` Buffer |
| **多线程并发写入** | 不同纹理区域/不同 Mipmap | 无需同步（无重叠） |
| **跨帧复用** | Triple Buffering | 信号量控制帧索引 |

### 14.3 完整代码示例：多线程纹理共享

```swift
import Metal
import MetalKit

// MARK: - 多线程纹理共享管理器

class MultithreadedTextureManager {
    private let device: MTLDevice
    
    // 两个 CommandQueue：一个用于 Compute，一个用于 Render
    private let computeQueue: MTLCommandQueue
    private let renderQueue: MTLCommandQueue
    
    // 共享纹理池 (Triple Buffering)
    private var sharedTextures: [MTLTexture] = []
    private static let textureCount = 3
    
    // 同步原语
    private let textureIndexLock = NSLock()
    private var availableIndices: [Int] = [0, 1, 2]
    private let gpuCompleteSemaphore: DispatchSemaphore
    
    // 工作线程
    private let producerQueue = DispatchQueue(label: "com.example.producer", qos: .userInitiated)
    private let consumerQueue = DispatchQueue(label: "com.example.consumer", qos: .userInitiated)
    
    // 管线状态
    private var computePipeline: MTLComputePipelineState!
    private var renderPipeline: MTLRenderPipelineState!
    
    init?(device: MTLDevice) {
        self.device = device
        guard let computeQueue = device.makeCommandQueue(),
              let renderQueue = device.makeCommandQueue() else {
            return nil
        }
        self.computeQueue = computeQueue
        self.renderQueue = renderQueue
        self.gpuCompleteSemaphore = DispatchSemaphore(value: Self.textureCount)
        
        createResources()
    }
    
    // MARK: - 资源创建
    
    private func createResources() {
        // 创建共享纹理 (Compute 写入，Render 读取)
        let textureDesc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: .rgba8Unorm,
            width: 1920,
            height: 1080,
            mipmapped: false
        )
        
        // 关键：.private 模式，GPU 独占访问，性能最优
        // 如果 CPU 需要读取，改用 .shared
        textureDesc.usage = [.shaderRead, .shaderWrite, .renderTarget]
        textureDesc.storageMode = .private
        
        for i in 0..<Self.textureCount {
            guard let texture = device.makeTexture(descriptor: textureDesc) else {
                fatalError("Failed to create texture \(i)")
            }
            texture.label = "SharedTexture_\(i)"
            sharedTextures.append(texture)
        }
        
        // 创建管线状态
        let library = device.makeDefaultLibrary()!
        
        let computeFunc = library.makeFunction(name: "producerKernel")!
        computePipeline = try! device.makeComputePipelineState(function: computeFunc)
        
        let vertexFunc = library.makeFunction(name: "vertexShader")!
        let fragmentFunc = library.makeFunction(name: "consumerFragment")!
        
        let renderDesc = MTLRenderPipelineDescriptor()
        renderDesc.vertexFunction = vertexFunc
        renderDesc.fragmentFunction = fragmentFunc
        renderDesc.colorAttachments[0].pixelFormat = .bgra8Unorm
        renderPipeline = try! device.makeRenderPipelineState(descriptor: renderDesc)
    }
    
    // MARK: - Producer 线程：写入纹理
    
    func startProducing() {
        producerQueue.async { [weak self] in
            while let self = self {
                // 等待可用纹理槽位
                self.gpuCompleteSemaphore.wait()
                
                let textureIndex = self.acquireTextureIndex()
                let targetTexture = self.sharedTextures[textureIndex]
                
                // 创建 CommandBuffer
                guard let commandBuffer = self.computeQueue.makeCommandBuffer() else {
                    self.releaseTextureIndex(textureIndex)
                    continue
                }
                
                // Encode Compute 命令：写入纹理
                self.encodeProducerWork(commandBuffer: commandBuffer, 
                                       targetTexture: targetTexture)
                
                // 关键：GPU 完成后通知 Consumer
                commandBuffer.addCompletedHandler { [weak self] _ in
                    // GPU 写入完成，通知 Consumer 可以读取
                    self?.notifyConsumer(textureIndex: textureIndex)
                }
                
                commandBuffer.commit()
                
                // 模拟工作间隔
                Thread.sleep(forTimeInterval: 0.016) // ~60fps
            }
        }
    }
    
    private func encodeProducerWork(commandBuffer: MTLCommandBuffer, 
                                    targetTexture: MTLTexture) {
        guard let encoder = commandBuffer.makeComputeCommandEncoder() else { return }
        
        encoder.setComputePipelineState(computePipeline)
        encoder.setTexture(targetTexture, index: 0)
        
        // 设置其他资源...
        var time = CACurrentMediaTime()
        encoder.setBytes(&time, length: MemoryLayout<Double>.size, index: 0)
        
        let threadGroupSize = MTLSize(width: 16, height: 16, depth: 1)
        let threadGroups = MTLSize(
            width: (targetTexture.width + 15) / 16,
            height: (targetTexture.height + 15) / 16,
            depth: 1
        )
        
        encoder.dispatchThreadgroups(threadGroups, threadsPerThreadgroup: threadGroupSize)
        encoder.endEncoding()
    }
    
    // MARK: - Consumer 线程：读取纹理
    
    private func notifyConsumer(textureIndex: Int) {
        consumerQueue.async { [weak self] in
            self?.consumeTexture(index: textureIndex)
        }
    }
    
    private func consumeTexture(index: Int) {
        let sourceTexture = sharedTextures[index]
        
        // 创建 Render CommandBuffer
        guard let commandBuffer = renderQueue.makeCommandBuffer() else { return }
        
        // 创建临时 RenderPass (简化示例)
        let renderPassDesc = MTLRenderPassDescriptor()
        // ... 配置 renderPassDesc
        
        guard let encoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDesc) else {
            return
        }
        
        // 关键：这里读取 Producer 写入的纹理
        // 由于 addCompletedHandler 保证，GPU 写入已完成
        encoder.setRenderPipelineState(renderPipeline)
        encoder.setFragmentTexture(sourceTexture, index: 0)
        // ... 绘制全屏四边形
        encoder.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 6)
        encoder.endEncoding()
        
        // Render 完成后释放纹理给 Producer 复用
        commandBuffer.addCompletedHandler { [weak self] _ in
            self?.releaseTextureIndex(index)
            self?.gpuCompleteSemaphore.signal()
        }
        
        commandBuffer.commit()
    }
    
    // MARK: - 纹理索引管理
    
    private func acquireTextureIndex() -> Int {
        textureIndexLock.lock()
        defer { textureIndexLock.unlock() }
        
        // 获取下一个可用索引
        let index = availableIndices.removeFirst()
        return index
    }
    
    private func releaseTextureIndex(_ index: Int) {
        textureIndexLock.lock()
        defer { textureIndexLock.unlock() }
        
        availableIndices.append(index)
    }
}

// MARK: - 方案2：Ping-Pong 双缓冲 (无需等待)

class PingPongTextureManager {
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue
    
    // 两个纹理交替读写
    private var textureA: MTLTexture!
    private var textureB: MTLTexture!
    private var writeToA = true
    
    init?(device: MTLDevice) {
        self.device = device
        guard let queue = device.makeCommandQueue() else { return nil }
        self.commandQueue = queue
        
        createTextures()
    }
    
    private func createTextures() {
        let desc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: .rgba16Float,
            width: 1024,
            height: 1024,
            mipmapped: false
        )
        desc.usage = [.shaderRead, .shaderWrite]
        desc.storageMode = .private
        
        textureA = device.makeTexture(descriptor: desc)!
        textureB = device.makeTexture(descriptor: desc)!
        textureA.label = "PingPong_A"
        textureB.label = "PingPong_B"
    }
    
    /// 迭代处理：输出作为下一次输入
    func iterateProcess(iterations: Int, completion: @escaping () -> Void) {
        guard let commandBuffer = commandQueue.makeCommandBuffer() else { return }
        
        for i in 0..<iterations {
            let sourceTexture = writeToA ? textureB : textureA
            let destTexture = writeToA ? textureA : textureB
            
            encodeIteration(commandBuffer: commandBuffer,
                          source: sourceTexture,
                          destination: destTexture,
                          iteration: i)
            
            writeToA.toggle()
        }
        
        commandBuffer.addCompletedHandler { _ in
            completion()
        }
        commandBuffer.commit()
    }
    
    private func encodeIteration(commandBuffer: MTLCommandBuffer,
                                source: MTLTexture,
                                destination: MTLTexture,
                                iteration: Int) {
        guard let encoder = commandBuffer.makeComputeCommandEncoder() else { return }
        
        encoder.setTexture(source, index: 0)
        encoder.setTexture(destination, index: 1)
        
        var iter = Int32(iteration)
        encoder.setBytes(&iter, length: 4, index: 0)
        
        // 分派线程...
        encoder.endEncoding()
    }
    
    /// 获取最终结果
    var finalResult: MTLTexture {
        return writeToA ? textureB : textureA
    }
}

// MARK: - 方案3：CPU 读取 GPU 结果

class CPUReadableTexture {
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue
    
    // GPU 端纹理 (private)
    private var gpuTexture: MTLTexture!
    
    // CPU 可读缓冲区 (shared)
    private var cpuBuffer: MTLBuffer!
    
    init?(device: MTLDevice) {
        self.device = device
        guard let queue = device.makeCommandQueue() else { return nil }
        self.commandQueue = queue
        
        createResources()
    }
    
    private func createResources() {
        // GPU 纹理 (private)
        let textureDesc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: .r32Float,
            width: 512,
            height: 512,
            mipmapped: false
        )
        textureDesc.usage = [.shaderWrite]
        textureDesc.storageMode = .private
        gpuTexture = device.makeTexture(descriptor: textureDesc)
        
        // CPU 可读缓冲区 (shared)
        let bufferSize = 512 * 512 * MemoryLayout<Float>.size
        cpuBuffer = device.makeBuffer(length: bufferSize, options: .storageModeShared)
    }
    
    /// GPU 写入后，拷贝到 CPU 可读缓冲区
    func readResultFromGPU(completion: @escaping ([Float]) -> Void) {
        guard let commandBuffer = commandQueue.makeCommandBuffer(),
              let blitEncoder = commandBuffer.makeBlitCommandEncoder() else {
            return
        }
        
        // 将纹理内容拷贝到缓冲区
        blitEncoder.copy(from: gpuTexture,
                        sourceSlice: 0,
                        sourceLevel: 0,
                        sourceOrigin: MTLOrigin(x: 0, y: 0, z: 0),
                        sourceSize: MTLSize(width: 512, height: 512, depth: 1),
                        to: cpuBuffer,
                        destinationOffset: 0,
                        destinationBytesPerRow: 512 * MemoryLayout<Float>.size,
                        destinationBytesPerImage: 512 * 512 * MemoryLayout<Float>.size)
        
        blitEncoder.endEncoding()
        
        commandBuffer.addCompletedHandler { [weak self] _ in
            guard let self = self else { return }
            
            // 现在可以安全地从 CPU 读取
            let ptr = self.cpuBuffer.contents().bindMemory(to: Float.self, capacity: 512 * 512)
            let results = Array(UnsafeBufferPointer(start: ptr, count: 512 * 512))
            completion(results)
        }
        
        commandBuffer.commit()
    }
}
```

### 14.4 Metal Shaders

```metal
// MultithreadedTexture.metal
#include <metal_stdlib>
using namespace metal;

// Producer Kernel：生成动态内容
kernel void producerKernel(
    texture2d<float, access::write> outputTexture [[texture(0)]],
    constant double& time [[buffer(0)]],
    uint2 gid [[thread_position_in_grid]])
{
    if (gid.x >= outputTexture.get_width() || gid.y >= outputTexture.get_height()) {
        return;
    }
    
    float2 uv = float2(gid) / float2(outputTexture.get_width(), outputTexture.get_height());
    
    // 动态生成内容
    float t = float(time);
    float3 color = 0.5 + 0.5 * cos(t + uv.xyx + float3(0, 2, 4));
    
    outputTexture.write(float4(color, 1.0), gid);
}

// Consumer Fragment：读取并显示
fragment float4 consumerFragment(
    VertexOut in [[stage_in]],
    texture2d<float> inputTexture [[texture(0)]])
{
    constexpr sampler texSampler(mag_filter::linear, min_filter::linear);
    return inputTexture.sample(texSampler, in.texCoord);
}

struct VertexOut {
    float4 position [[position]];
    float2 texCoord;
};
```

### 14.5 关键要点总结

| 要点 | 说明 |
|------|------|
| **对象线程安全** | `MTLTexture` 引用可自由跨线程传递 |
| **内容访问同步** | GPU 写入 → CPU 读取 需要 `addCompletedHandler` 或 `waitUntilCompleted` |
| **GPU-GPU 传递** | Compute 写入 → Render 读取，同一纹理无需额外同步（CommandBuffer 顺序提交即可） |
| **存储模式选择** | 纯 GPU 用 `.private`；CPU 读取用 `.shared` + Blit 拷贝 |
| **避免竞争** | 多线程同时写入同一纹理的不同区域是安全的；同一区域需串行 |

### 14.6 常见错误

```swift
// ❌ 错误：GPU 写入后立即 CPU 读取
computeEncoder.dispatchThreadgroups(...)
computeEncoder.endEncoding()
commandBuffer.commit()

// 立即读取 - 错误！GPU 可能还没完成
let pixel = texture.getBytes(...)  // 数据可能未就绪

// ✅ 正确：等待 GPU 完成
commandBuffer.addCompletedHandler { _ in
    // GPU 完成后再读取
    let pixel = texture.getBytes(...)
}
commandBuffer.commit()
```

---

## 参考资源

### 内部知识库关联

- [iOS 内存优化](./cpp_memory_optimization/03_系统级优化/iOS内存优化.md)——Jetsam、Metal Buffer 共享内存、IOSurface
- [DMA 机制详解](./cpp_memory_optimization/04_DMA与缓存优化/DMA机制详解.md)——零拷贝、dma-buf/IOSurface 对比
- [图像处理并行化](./thread/06_工程应用实战/图像处理并行化_详细解析.md)——GPU 并行计算、线程组、SIMD
- [跨平台实现差异](./Image_Processing_Algorithms/07_工程实践与性能优化/跨平台实现差异_详细解析.md)——Metal vs OpenGL vs Vulkan

### 官方文档

- [Metal Programming Guide](https://developer.apple.com/documentation/metal)
- [Metal Shading Language Specification](https://developer.apple.com/metal/Metal-Shading-Language-Specification.pdf)
- [Metal Best Practices Guide](https://developer.apple.com/library/archive/documentation/3DDrawing/Conceptual/MTLBestPracticesGuide/)
- [WWDC: Discover Metal debugging, profiling, and asset creation tools](https://developer.apple.com/videos/play/wwdc2023/10164/)
- [WWDC: Go Bindless with Metal 3](https://developer.apple.com/videos/play/wwdc2022/10101/)


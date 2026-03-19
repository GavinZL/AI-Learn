# iOS 硬件编解码实践

> VideoToolbox 框架详解：从编码会话创建到 Metal 协同的完整实践指南

---

## 核心结论（TL;DR）

**iOS 硬件编解码的核心是 VideoToolbox 框架，它提供了对 Apple Silicon 专用媒体引擎的直接访问，实现低延迟、低功耗的视频编解码。**

关键要点：
1. **VideoToolbox** 是 iOS/macOS 上直接控制硬件编解码的 C 语言框架，位于 AVFoundation 之下
2. **VTCompressionSession** 用于硬件编码，**VTDecompressionSession** 用于硬件解码
3. **CVPixelBuffer** 可直接映射为 Metal 纹理，实现 GPU 处理与硬件编解码的零拷贝协同
4. Apple Silicon 拥有专用的 Media Engine，不同代际芯片支持的编解码能力差异显著
5. 硬件编码存在后台限制、并发会话数限制等约束，需要针对性优化

---

## 一、iOS 硬件编解码架构总览

### 1.1 Apple 视频编解码架构层次

```
┌─────────────────────────────────────────────────────┐
│                   应用层 (App)                       │
├─────────────────────────────────────────────────────┤
│              AVFoundation（高层封装）                 │
│    AVAssetWriter / AVAssetReader / AVCaptureSession │
├─────────────────────────────────────────────────────┤
│              VideoToolbox（中间层）                   │
│   VTCompressionSession / VTDecompressionSession     │
├─────────────────────────────────────────────────────┤
│              Core Media（数据类型）                   │
│    CMSampleBuffer / CVPixelBuffer / CMTime          │
├─────────────────────────────────────────────────────┤
│           Apple Silicon Media Engine（硬件）         │
│      专用编码器 / 解码器 / ProRes 加速器             │
└─────────────────────────────────────────────────────┘
```

| 层级 | 框架 | 核心类/API | 控制粒度 | 适用场景 |
|------|------|-----------|---------|---------|
| 最上层 | AVFoundation | AVAssetWriter, AVPlayer | 低 | 简单录制、播放 |
| 中间层 | VideoToolbox | VTCompressionSession | 高 | 直播推流、自定义编码 |
| 底层 | Media Engine | 硬件直接访问 | 不可直接访问 | 由系统管理 |

### 1.2 Apple Silicon 的视频编解码硬件

Apple Silicon（A 系列 / M 系列芯片）内置专用的 **Media Engine**，这是独立于 GPU 的 ASIC：

- **非 GPU Shader 实现**：专用硬件，不占用 GPU 计算资源
- **超低功耗**：专用电路效率远高于软件编码
- **固定功能**：支持特定编解码标准，无法自定义算法

| 编解码器 | 编码支持 | 解码支持 | 最低芯片要求 |
|---------|---------|---------|-------------|
| H.264/AVC | ✅ | ✅ | A4（iPhone 4） |
| H.265/HEVC | ✅ | ✅ | A10（iPhone 7）编码 |
| ProRes | ✅ | ✅ | A15 Pro（iPhone 13 Pro） |
| AV1 | ❌ | ✅ | A17 Pro / M3 |

### 1.3 与 Android 架构的对比

| 特性 | iOS（Apple） | Android |
|-----|-------------|---------|
| 硬件整合 | 垂直整合，软硬件高度统一 | 碎片化，不同厂商实现各异 |
| API 一致性 | VideoToolbox API 统一 | MediaCodec API 统一，但实现差异大 |
| 编码质量 | 稳定可预期 | 厂商实现质量参差不齐 |
| 调试难度 | 较低，行为一致 | 较高，需适配多厂商 |

---

## 二、VideoToolbox 框架详解

### 2.1 框架定位

**VideoToolbox** 是 Apple 提供的底层视频编解码框架：C 语言接口，Core Foundation 风格，是 iOS/macOS 上直接控制硬件编解码的唯一方式。

### 2.2 核心数据类型

| 类型 | 作用 | 关键 API |
|-----|------|---------|
| CMSampleBuffer | 封装压缩/未压缩帧 + 时间戳 | `CMSampleBufferGetImageBuffer()` |
| CVPixelBuffer | 未压缩像素数据（YUV/RGB） | `CVPixelBufferGetWidth()` |
| CMBlockBuffer | 压缩后的码流数据 | `CMBlockBufferGetDataPointer()` |
| CMFormatDescription | 媒体格式描述（SPS/PPS） | `CMVideoFormatDescriptionGetDimensions()` |
| CMTime | 精确时间表示 | `CMTimeGetSeconds()` |

```swift
// 从 CMSampleBuffer 获取关键信息
func extractInfo(from sampleBuffer: CMSampleBuffer) {
    let pts = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
    
    if let formatDesc = CMSampleBufferGetFormatDescription(sampleBuffer) {
        let dimensions = CMVideoFormatDescriptionGetDimensions(formatDesc)
        print("分辨率: \(dimensions.width) x \(dimensions.height)")
    }
    
    // 判断是否为关键帧
    if let attachments = CMSampleBufferGetSampleAttachmentsArray(sampleBuffer, createIfNecessary: false) as? [[CFString: Any]],
       let first = attachments.first {
        let isKeyFrame = !(first[kCMSampleAttachmentKey_NotSync] as? Bool ?? false)
    }
}
```

**常用像素格式：**

| 格式常量 | FourCC | 说明 |
|---------|--------|------|
| `kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange` | 420v | NV12，视频范围 |
| `kCVPixelFormatType_420YpCbCr8BiPlanarFullRange` | 420f | NV12，全范围 |
| `kCVPixelFormatType_32BGRA` | BGRA | 32位 BGRA |

---

## 三、VTCompressionSession（硬件编码）

### 3.1 完整的硬件编码器实现

```swift
import VideoToolbox
import CoreMedia

class HardwareEncoder {
    private var compressionSession: VTCompressionSession?
    var onEncodedFrame: ((CMSampleBuffer) -> Void)?
    var onError: ((OSStatus) -> Void)?
    
    /// 创建硬件编码器
    func createEncoder(width: Int32, height: Int32, frameRate: Int = 30, 
                       bitRate: Int = 2_000_000, useHEVC: Bool = false) throws {
        let codecType: CMVideoCodecType = useHEVC ? kCMVideoCodecType_HEVC : kCMVideoCodecType_H264
        
        let outputCallback: VTCompressionOutputCallback = { refCon, _, status, _, sampleBuffer in
            guard let refCon = refCon else { return }
            let encoder = Unmanaged<HardwareEncoder>.fromOpaque(refCon).takeUnretainedValue()
            if status != noErr { encoder.onError?(status); return }
            if let buffer = sampleBuffer { encoder.onEncodedFrame?(buffer) }
        }
        
        let selfPointer = Unmanaged.passUnretained(self).toOpaque()
        var session: VTCompressionSession?
        
        let status = VTCompressionSessionCreate(
            allocator: kCFAllocatorDefault, width: width, height: height,
            codecType: codecType, encoderSpecification: nil, imageBufferAttributes: nil,
            compressedDataAllocator: nil, outputCallback: outputCallback,
            refcon: selfPointer, compressionSessionOut: &session
        )
        
        guard status == noErr, let session = session else {
            throw EncoderError.sessionCreationFailed(status)
        }
        self.compressionSession = session
        try configureSession(session: session, frameRate: frameRate, bitRate: bitRate, useHEVC: useHEVC)
    }
    
    private func configureSession(session: VTCompressionSession, frameRate: Int, 
                                  bitRate: Int, useHEVC: Bool) throws {
        // 实时编码模式（降低延迟）
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_RealTime, value: true as CFTypeRef)
        
        // Profile/Level
        let profileLevel: CFString = useHEVC ? kVTProfileLevel_HEVC_Main_AutoLevel 
                                              : kVTProfileLevel_H264_High_AutoLevel
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_ProfileLevel, value: profileLevel)
        
        // 码率控制
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_AverageBitRate, value: bitRate as CFNumber)
        let dataRateLimits: [Double] = [Double(bitRate) / 8.0 * 1.5, 1.0]
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_DataRateLimits, value: dataRateLimits as CFArray)
        
        // 关键帧间隔
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_MaxKeyFrameInterval, value: frameRate * 2 as CFNumber)
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_MaxKeyFrameIntervalDuration, value: 2.0 as CFNumber)
        
        // 禁用 B 帧（降低延迟）
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_AllowFrameReordering, value: false as CFTypeRef)
        
        // 帧率
        VTSessionSetProperty(session, key: kVTCompressionPropertyKey_ExpectedFrameRate, value: frameRate as CFNumber)
        
        // H.264 熵编码（CABAC 压缩效率更高）
        if !useHEVC {
            VTSessionSetProperty(session, key: kVTCompressionPropertyKey_H264EntropyMode, value: kVTH264EntropyMode_CABAC)
        }
        
        let prepareStatus = VTCompressionSessionPrepareToEncodeFrames(session)
        if prepareStatus != noErr { throw EncoderError.prepareFailed(prepareStatus) }
    }
    
    /// 编码一帧
    func encode(pixelBuffer: CVPixelBuffer, presentationTime: CMTime, forceKeyFrame: Bool = false) throws {
        guard let session = compressionSession else { throw EncoderError.sessionNotCreated }
        
        var frameProperties: [CFString: Any]? = nil
        if forceKeyFrame { frameProperties = [kVTEncodeFrameOptionKey_ForceKeyFrame: true] }
        
        let status = VTCompressionSessionEncodeFrame(session, imageBuffer: pixelBuffer,
            presentationTimeStamp: presentationTime, duration: CMTime.invalid,
            frameProperties: frameProperties as CFDictionary?, sourceFrameRefcon: nil, infoFlagsOut: nil)
        if status != noErr { throw EncoderError.encodeFailed(status) }
    }
    
    func flush() throws {
        guard let session = compressionSession else { return }
        let status = VTCompressionSessionCompleteFrames(session, untilPresentationTimeStamp: CMTime.invalid)
        if status != noErr { throw EncoderError.flushFailed(status) }
    }
    
    func destroy() {
        if let session = compressionSession {
            VTCompressionSessionInvalidate(session)
            compressionSession = nil
        }
    }
}

enum EncoderError: Error {
    case sessionCreationFailed(OSStatus), sessionNotCreated, prepareFailed(OSStatus)
    case encodeFailed(OSStatus), flushFailed(OSStatus)
}
```

### 3.2 关键属性速查表

| 属性 | 类型 | 推荐值（直播） | 推荐值（录制） | 说明 |
|-----|------|--------------|--------------|------|
| RealTime | Bool | true | false | 实时模式降低延迟 |
| ProfileLevel | CFString | High_AutoLevel | High_AutoLevel | 编码 Profile |
| AverageBitRate | Int | 2-4 Mbps | 8-15 Mbps | 目标码率 |
| MaxKeyFrameInterval | Int | 30-60 | 60-120 | GOP 大小 |
| AllowFrameReordering | Bool | false | true | B 帧开关 |
| H264EntropyMode | CFString | CABAC | CABAC | 熵编码方式 |

### 3.3 从 CMSampleBuffer 提取 H.264 NAL 数据

VideoToolbox 输出 **AVCC 格式**（长度前缀），网络传输需要 **Annex B 格式**（起始码 0x00000001）：

```swift
extension HardwareEncoder {
    /// 提取 SPS/PPS
    func extractParameterSets(from sampleBuffer: CMSampleBuffer) -> (sps: Data, pps: Data)? {
        guard let formatDesc = CMSampleBufferGetFormatDescription(sampleBuffer) else { return nil }
        
        var spsSize = 0, spsPointer: UnsafePointer<UInt8>?
        CMVideoFormatDescriptionGetH264ParameterSetAtIndex(formatDesc, parameterSetIndex: 0,
            parameterSetPointerOut: &spsPointer, parameterSetSizeOut: &spsSize, parameterSetCountOut: nil, nalUnitHeaderLengthOut: nil)
        guard let spsPtr = spsPointer else { return nil }
        let sps = Data(bytes: spsPtr, count: spsSize)
        
        var ppsSize = 0, ppsPointer: UnsafePointer<UInt8>?
        CMVideoFormatDescriptionGetH264ParameterSetAtIndex(formatDesc, parameterSetIndex: 1,
            parameterSetPointerOut: &ppsPointer, parameterSetSizeOut: &ppsSize, parameterSetCountOut: nil, nalUnitHeaderLengthOut: nil)
        guard let ppsPtr = ppsPointer else { return nil }
        let pps = Data(bytes: ppsPtr, count: ppsSize)
        
        return (sps, pps)
    }
    
    /// AVCC → Annex B 格式转换
    func convertToAnnexB(sampleBuffer: CMSampleBuffer) -> Data? {
        guard let blockBuffer = CMSampleBufferGetDataBuffer(sampleBuffer) else { return nil }
        
        var totalLength = 0, dataPointer: UnsafeMutablePointer<Int8>?
        let status = CMBlockBufferGetDataPointer(blockBuffer, atOffset: 0, lengthAtOffsetOut: nil,
            totalLengthOut: &totalLength, dataPointerOut: &dataPointer)
        guard status == kCMBlockBufferNoErr, let pointer = dataPointer else { return nil }
        
        var annexBData = Data()
        let startCode = Data([0x00, 0x00, 0x00, 0x01])
        var offset = 0
        
        while offset < totalLength {
            var nalLength: UInt32 = 0
            memcpy(&nalLength, pointer.advanced(by: offset), 4)
            nalLength = CFSwapInt32BigToHost(nalLength)
            offset += 4
            annexBData.append(startCode)
            annexBData.append(Data(bytes: pointer.advanced(by: offset), count: Int(nalLength)))
            offset += Int(nalLength)
        }
        return annexBData
    }
}
```

---

## 四、VTDecompressionSession（硬件解码）

### 4.1 完整的硬件解码器实现

```swift
class HardwareDecoder {
    private var decompressionSession: VTDecompressionSession?
    private var formatDescription: CMVideoFormatDescription?
    var onDecodedFrame: ((CVPixelBuffer, CMTime) -> Void)?
    var onError: ((OSStatus) -> Void)?
    
    /// 使用 SPS/PPS 创建解码器
    func createDecoder(sps: Data, pps: Data) throws {
        let parameterSets: [Data] = [sps, pps]
        var formatDesc: CMVideoFormatDescription?
        
        try sps.withUnsafeBytes { spsBytes in
            try pps.withUnsafeBytes { ppsBytes in
                let pointers = [spsBytes.baseAddress!.assumingMemoryBound(to: UInt8.self),
                               ppsBytes.baseAddress!.assumingMemoryBound(to: UInt8.self)]
                let sizes = [sps.count, pps.count]
                
                let status = pointers.withUnsafeBufferPointer { ptrBuf in
                    sizes.withUnsafeBufferPointer { sizeBuf in
                        CMVideoFormatDescriptionCreateFromH264ParameterSets(
                            allocator: kCFAllocatorDefault, parameterSetCount: 2,
                            parameterSetPointers: ptrBuf.baseAddress!, parameterSetSizes: sizeBuf.baseAddress!,
                            nalUnitHeaderLength: 4, formatDescriptionOut: &formatDesc)
                    }
                }
                if status != noErr { throw DecoderError.formatDescriptionFailed(status) }
            }
        }
        
        self.formatDescription = formatDesc
        try createSession(formatDescription: formatDesc!)
    }
    
    private func createSession(formatDescription: CMVideoFormatDescription) throws {
        let destinationAttributes: [CFString: Any] = [
            kCVPixelBufferPixelFormatTypeKey: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange,
            kCVPixelBufferMetalCompatibilityKey: true
        ]
        
        var callbackRecord = VTDecompressionOutputCallbackRecord(
            decompressionOutputCallback: { refCon, _, status, _, imageBuffer, pts, _ in
                guard let refCon = refCon else { return }
                let decoder = Unmanaged<HardwareDecoder>.fromOpaque(refCon).takeUnretainedValue()
                if status != noErr { decoder.onError?(status); return }
                if let pixelBuffer = imageBuffer { decoder.onDecodedFrame?(pixelBuffer, pts) }
            },
            decompressionOutputRefCon: Unmanaged.passUnretained(self).toOpaque()
        )
        
        var session: VTDecompressionSession?
        let status = VTDecompressionSessionCreate(allocator: kCFAllocatorDefault,
            formatDescription: formatDescription, decoderSpecification: nil,
            imageBufferAttributes: destinationAttributes as CFDictionary,
            outputCallback: &callbackRecord, decompressionSessionOut: &session)
        
        guard status == noErr, let session = session else {
            throw DecoderError.sessionCreationFailed(status)
        }
        self.decompressionSession = session
    }
    
    func flush() { 
        guard let session = decompressionSession else { return }
        VTDecompressionSessionWaitForAsynchronousFrames(session)
    }
    
    func destroy() {
        if let session = decompressionSession {
            VTDecompressionSessionInvalidate(session)
            decompressionSession = nil
        }
    }
}

enum DecoderError: Error {
    case formatDescriptionFailed(OSStatus), sessionCreationFailed(OSStatus)
    case blockBufferFailed(OSStatus), decodeFailed(OSStatus)
}
```

---

## 五、iOS 硬件编解码的限制与优化

### 5.1 已知限制

| 限制类型 | 详细说明 | 应对策略 |
|---------|---------|---------|
| **后台编码** | App 进入后台时编码会话可能被终止 | 使用 `beginBackgroundTask` |
| **并发会话数** | 同时存在的编解码器会话数限制（3-4 个） | 复用会话 |
| **B 帧支持** | iOS 硬件编码器对 B 帧支持有限 | 直播场景禁用 |
| **CBR 精度** | 硬件编码的恒定码率精度不如软编 | 接受码率波动 |
| **HEVC 编码** | 需要 A10（iPhone 7）及以上 | 检测设备能力 |
| **AV1 解码** | 需要 A17 Pro / M3 及以上 | 运行时检测 |

### 5.2 优化策略

```swift
// 1. 使用 CVPixelBufferPool 复用内存
func createPixelBufferPool(width: Int, height: Int) -> CVPixelBufferPool? {
    let poolAttributes: [CFString: Any] = [kCVPixelBufferPoolMinimumBufferCountKey: 3]
    let pixelBufferAttributes: [CFString: Any] = [
        kCVPixelBufferPixelFormatTypeKey: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange,
        kCVPixelBufferWidthKey: width, kCVPixelBufferHeightKey: height,
        kCVPixelBufferIOSurfacePropertiesKey: [:], kCVPixelBufferMetalCompatibilityKey: true
    ]
    var pool: CVPixelBufferPool?
    CVPixelBufferPoolCreate(kCFAllocatorDefault, poolAttributes as CFDictionary,
                           pixelBufferAttributes as CFDictionary, &pool)
    return pool
}

// 2. 后台编码保护
func startBackgroundEncoding() {
    var backgroundTaskID: UIBackgroundTaskIdentifier = .invalid
    backgroundTaskID = UIApplication.shared.beginBackgroundTask {
        UIApplication.shared.endBackgroundTask(backgroundTaskID)
    }
    // 执行编码... 完成后：
    UIApplication.shared.endBackgroundTask(backgroundTaskID)
}

// 3. 动态调整码率（无需重建会话）
func adjustBitRate(session: VTCompressionSession, newBitRate: Int) {
    VTSessionSetProperty(session, key: kVTCompressionPropertyKey_AverageBitRate, value: newBitRate as CFNumber)
}
```

### 5.3 错误处理

```swift
func handleEncoderError(_ status: OSStatus) {
    switch status {
    case kVTVideoEncoderUnavailableNowError:  // -12915
        print("编码器暂时不可用，稍后重试")
    case -12911:  // kVTVideoEncoderMalfunctionError
        print("编码器故障，需要重建会话")
    case kVTInvalidSessionErr:  // -12903
        print("会话已失效，需要重建")
    default:
        print("编码错误: \(status)")
    }
}
```

---

## 六、Metal 与 VideoToolbox 的协同

### 6.1 CVPixelBuffer ↔ Metal Texture 零拷贝

```swift
import Metal
import CoreVideo

class MetalVideoProcessor {
    let device: MTLDevice
    var textureCache: CVMetalTextureCache?
    
    init?() {
        guard let device = MTLCreateSystemDefaultDevice() else { return nil }
        self.device = device
        var cache: CVMetalTextureCache?
        CVMetalTextureCacheCreate(kCFAllocatorDefault, nil, device, nil, &cache)
        self.textureCache = cache
    }
    
    /// CVPixelBuffer → Metal 纹理（零拷贝）
    func createTexture(from pixelBuffer: CVPixelBuffer) -> MTLTexture? {
        guard let cache = textureCache else { return nil }
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        
        var cvTexture: CVMetalTexture?
        let status = CVMetalTextureCacheCreateTextureFromImage(kCFAllocatorDefault, cache,
            pixelBuffer, nil, .bgra8Unorm, width, height, 0, &cvTexture)
        
        guard status == kCVReturnSuccess, let cvTex = cvTexture else { return nil }
        return CVMetalTextureGetTexture(cvTex)
    }
    
    /// NV12 格式：获取 Y 和 UV 纹理
    func createNV12Textures(from pixelBuffer: CVPixelBuffer) -> (y: MTLTexture, uv: MTLTexture)? {
        guard let cache = textureCache else { return nil }
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        
        var yTexture: CVMetalTexture?, uvTexture: CVMetalTexture?
        CVMetalTextureCacheCreateTextureFromImage(kCFAllocatorDefault, cache, pixelBuffer, nil, .r8Unorm, width, height, 0, &yTexture)
        CVMetalTextureCacheCreateTextureFromImage(kCFAllocatorDefault, cache, pixelBuffer, nil, .rg8Unorm, width/2, height/2, 1, &uvTexture)
        
        guard let y = yTexture, let uv = uvTexture,
              let yMetal = CVMetalTextureGetTexture(y), let uvMetal = CVMetalTextureGetTexture(uv) else { return nil }
        return (yMetal, uvMetal)
    }
}
```

### 6.2 典型工作流：相机 → Metal 处理 → 编码

```swift
class CameraToEncoderPipeline: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let videoProcessor = MetalVideoProcessor()!
    let encoder = HardwareEncoder()
    
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        // 1. CVPixelBuffer → Metal 纹理（零拷贝）
        guard let texture = videoProcessor.createTexture(from: pixelBuffer) else { return }
        
        // 2. Metal Shader 处理（美颜/滤镜）
        // let processedTexture = applyFilter(texture)
        
        // 3. 编码
        let pts = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
        try? encoder.encode(pixelBuffer: pixelBuffer, presentationTime: pts)
    }
}
```

### 6.3 Metal Performance Shaders 应用

```swift
import MetalPerformanceShaders

extension MetalVideoProcessor {
    func scaleTexture(source: MTLTexture, destination: MTLTexture, commandBuffer: MTLCommandBuffer) {
        let scaler = MPSImageLanczosScale(device: device)
        scaler.encode(commandBuffer: commandBuffer, sourceTexture: source, destinationTexture: destination)
    }
    
    func applyGaussianBlur(source: MTLTexture, destination: MTLTexture, sigma: Float, commandBuffer: MTLCommandBuffer) {
        let blur = MPSImageGaussianBlur(device: device, sigma: sigma)
        blur.encode(commandBuffer: commandBuffer, sourceTexture: source, destinationTexture: destination)
    }
}
```

---

## 七、AVFoundation 高层接口

### 7.1 AVFoundation vs VideoToolbox 对比

| 特性 | AVFoundation | VideoToolbox |
|-----|-------------|--------------|
| API 复杂度 | 简单，Swift/ObjC 友好 | 复杂，C 风格 |
| 控制粒度 | 低，参数有限 | 高，可调所有参数 |
| 码流访问 | 不直接暴露 NAL | 完全访问 |
| 适用场景 | 本地录制、简单转码 | 直播推流、RTC |
| 学习曲线 | 平缓 | 陡峭 |

**选择建议：**
- **AVFoundation**：本地视频录制、简单播放、文件格式转换
- **VideoToolbox**：RTMP/WebRTC 推流、需要访问原始码流、自定义码率控制

---

## 八、Apple 芯片代际编解码能力

| 芯片 | 设备 | H.264 编码 | HEVC 编码 | HEVC 10bit | ProRes | AV1 解码 |
|------|------|-----------|-----------|------------|--------|---------|
| A9 | iPhone 6s | 4K30 | ❌ | ❌ | ❌ | ❌ |
| A10 | iPhone 7 | 4K30 | 4K30 | ❌ | ❌ | ❌ |
| A12 | iPhone XS | 4K60 | 4K60 | 4K60 | ❌ | ❌ |
| A14 | iPhone 12 | 4K60 | 4K60 | 4K60 | ❌ | ❌ |
| A15 | iPhone 13 | 4K60 | 4K60 | 4K60 | 4K30 (Pro) | ❌ |
| A16 | iPhone 14 Pro | 4K60 | 4K60 | 4K60 | 4K30 | ❌ |
| A17 Pro | iPhone 15 Pro | 4K60 | 4K60 | 4K60 | 4K60 | 4K60 |
| M1/M2 | iPad Pro/Mac | 8K | 8K | 8K | ✅ | ❌ |
| M3+ | Mac | 8K | 8K | 8K | ✅ | 8K |

**运行时能力检测：**

```swift
func checkEncoderAvailability() {
    let hevcSupported = VTIsHardwareDecodeSupported(kCMVideoCodecType_HEVC)
    print("HEVC 硬件解码: \(hevcSupported)")
    
    if #available(iOS 14.5, *) {
        VTCopySupportedPropertyDictionaryForEncoder(width: 1920, height: 1080,
            codecType: kCMVideoCodecType_HEVC, encoderSpecification: nil) { status, properties in
            if status == noErr, let props = properties {
                print("HEVC 编码器属性: \(props)")
            }
        }
    }
}
```

---

## 参考资源

### Apple 官方文档
- [VideoToolbox Framework Reference](https://developer.apple.com/documentation/videotoolbox)
- [Core Media Framework Reference](https://developer.apple.com/documentation/coremedia)
- [AVFoundation Programming Guide](https://developer.apple.com/documentation/avfoundation)

### WWDC Sessions
- **WWDC 2014** - Session 513: *Direct Access to Video Encoding and Decoding*
- **WWDC 2017** - Session 503: *Introducing HEIF and HEVC*
- **WWDC 2020** - Session 10090: *Edit and Playback HDR Video with AVFoundation*
- **WWDC 2022** - Session 110332: *Discover advancements in iOS camera capture*
- **WWDC 2023** - Session 10122: *Support HDR images in your app*

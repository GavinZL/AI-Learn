# Android 硬件编解码实践

> 深入理解 Android 平台的 MediaCodec API、底层框架架构、芯片厂商差异，以及如何在生产环境中正确使用硬件编解码。

---

## 核心结论（TL;DR）

1. **MediaCodec 是统一入口**：无论硬编硬解还是软编软解，上层 API 相同，由系统选择具体实现
2. **优先使用 Surface 模式**：零拷贝、最佳性能，尤其是与 Camera/OpenGL 集成时
3. **异步模式是最佳实践**：避免阻塞 UI 线程，更好地处理背压
4. **芯片差异显著**：同一 API 在高通/MTK/三星芯片上行为可能不同，需要充分测试
5. **Codec2 是未来**：Android 10+ 新框架，逐步替代 OMX

---

## 一、Android 硬件编解码架构总览

### 1.1 分层架构

Android 的视频编解码系统是一个典型的分层架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                        App 层                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   MediaCodec API / MediaRecorder / ExoPlayer / Camera   │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     Framework 层 (Java)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  MediaCodec.java                         │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │ JNI                                  │
├──────────────────────────┼──────────────────────────────────────┤
│                   Native 层 (C++)                               │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │               android_media_MediaCodec.cpp               │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │              MediaCodec (libstagefright)                 │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │                      ACodec                              │   │
│  └───────────────────────┬─────────────────────────────────┘   │
├──────────────────────────┼──────────────────────────────────────┤
│                     HAL 层                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │        OMX IL (Legacy) / Codec2 (Modern)                 │   │
│  └───────────────────────┬─────────────────────────────────┘   │
├──────────────────────────┼──────────────────────────────────────┤
│                   硬件层 (Vendor)                               │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │     SoC 厂商驱动 (Qualcomm/MTK/Samsung/HiSilicon)       │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │                    VPU 硬件                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 各层职责

| 层级 | 组件 | 职责 |
|------|------|------|
| App | MediaCodec API | 提供统一的编解码接口 |
| Framework | MediaCodec.java | Java 层封装，参数校验 |
| Native | ACodec | 状态机管理，缓冲区调度 |
| HAL | OMX/Codec2 | 硬件抽象，厂商适配 |
| Vendor | SoC 驱动 | 硬件寄存器操作 |
| Hardware | VPU | 实际编解码执行 |

### 1.3 数据流路径

**编码数据流**：
```
Camera/Surface → GraphicBuffer → OMX/C2 输入端口 → VPU 编码 
    → OMX/C2 输出端口 → MediaCodec OutputBuffer → App 获取码流
```

**解码数据流**：
```
App 码流 → MediaCodec InputBuffer → OMX/C2 输入端口 → VPU 解码 
    → OMX/C2 输出端口 → GraphicBuffer/Surface → 显示或后处理
```

---

## 二、MediaCodec API 详解

### 2.1 核心概念

MediaCodec 是 Android 提供的统一编解码接口，特点：
- 同时支持硬件编解码和软件编解码
- 系统自动选择最优实现（优先硬件）
- 同步/异步两种工作模式
- 支持 Surface 零拷贝

**状态机**：

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌──────────┐   configure()   ┌────────────┐   start()   ┌─────────┐
│Uninitialized│────────────▶│ Configured │────────────▶│ Running │
└──────────┘                 └────────────┘              └────┬────┘
     ▲                            │                          │
     │                            │ release()                │ stop()
     │                            │                          │
     │                            ▼                          ▼
     │                      ┌──────────┐              ┌──────────┐
     └──────────────────────│ Released │◀─────────────│  Stopped │
                            └──────────┘   release()  └──────────┘
```

### 2.2 编码流程（硬编）

#### 基础同步模式

```kotlin
class BasicH264Encoder {
    private lateinit var encoder: MediaCodec
    private val bufferInfo = MediaCodec.BufferInfo()
    
    fun setup(width: Int, height: Int, bitrate: Int, fps: Int) {
        // 创建 H.264 编码器
        encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        
        // 配置编码参数
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, width, height
        ).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, bitrate)
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2) // 2秒一个I帧
            setInteger(MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
        }
        
        encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        encoder.start()
    }
    
    fun encodeFrame(yuvData: ByteArray, presentationTimeUs: Long) {
        // 获取输入缓冲区
        val inputIndex = encoder.dequeueInputBuffer(10_000) // 10ms 超时
        if (inputIndex >= 0) {
            val inputBuffer = encoder.getInputBuffer(inputIndex)!!
            inputBuffer.clear()
            inputBuffer.put(yuvData)
            encoder.queueInputBuffer(inputIndex, 0, yuvData.size, 
                presentationTimeUs, 0)
        }
        
        // 获取输出
        drainOutput()
    }
    
    private fun drainOutput() {
        while (true) {
            val outputIndex = encoder.dequeueOutputBuffer(bufferInfo, 0)
            when {
                outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    // 获取 SPS/PPS 等编码器配置
                    val newFormat = encoder.outputFormat
                    Log.d(TAG, "Output format changed: $newFormat")
                }
                outputIndex >= 0 -> {
                    val outputBuffer = encoder.getOutputBuffer(outputIndex)!!
                    // 处理编码后的 NAL 数据
                    val encodedData = ByteArray(bufferInfo.size)
                    outputBuffer.get(encodedData)
                    
                    // 检查是否是关键帧
                    val isKeyFrame = (bufferInfo.flags and 
                        MediaCodec.BUFFER_FLAG_KEY_FRAME) != 0
                    
                    onEncodedFrame(encodedData, bufferInfo.presentationTimeUs, isKeyFrame)
                    
                    encoder.releaseOutputBuffer(outputIndex, false)
                }
                else -> break
            }
        }
    }
    
    fun release() {
        encoder.stop()
        encoder.release()
    }
}
```

#### 推荐的异步模式

```kotlin
class AsyncH264Encoder(
    private val width: Int,
    private val height: Int,
    private val bitrate: Int,
    private val fps: Int,
    private val onEncoded: (ByteArray, Long, Boolean) -> Unit,
    private val onError: (Exception) -> Unit
) {
    private lateinit var encoder: MediaCodec
    private val pendingInputBuffers = ArrayDeque<Int>()
    private val inputLock = Object()
    
    fun start() {
        encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, width, height
        ).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, bitrate)
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
            setInteger(MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
            // 码率控制模式
            setInteger(MediaFormat.KEY_BITRATE_MODE,
                MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_VBR)
        }
        
        encoder.setCallback(object : MediaCodec.Callback() {
            override fun onInputBufferAvailable(codec: MediaCodec, index: Int) {
                synchronized(inputLock) {
                    pendingInputBuffers.addLast(index)
                    inputLock.notify()
                }
            }
            
            override fun onOutputBufferAvailable(
                codec: MediaCodec, index: Int, info: MediaCodec.BufferInfo
            ) {
                try {
                    if (info.size > 0) {
                        val buffer = codec.getOutputBuffer(index)!!
                        val data = ByteArray(info.size)
                        buffer.get(data)
                        
                        val isKeyFrame = (info.flags and 
                            MediaCodec.BUFFER_FLAG_KEY_FRAME) != 0
                        onEncoded(data, info.presentationTimeUs, isKeyFrame)
                    }
                    codec.releaseOutputBuffer(index, false)
                } catch (e: Exception) {
                    onError(e)
                }
            }
            
            override fun onOutputFormatChanged(
                codec: MediaCodec, format: MediaFormat
            ) {
                Log.d(TAG, "Encoder output format: $format")
                // 可以从 format 获取 SPS/PPS
                val sps = format.getByteBuffer("csd-0")
                val pps = format.getByteBuffer("csd-1")
            }
            
            override fun onError(
                codec: MediaCodec, e: MediaCodec.CodecException
            ) {
                onError(e)
            }
        })
        
        encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        encoder.start()
    }
    
    fun feedFrame(yuvData: ByteArray, timestampUs: Long) {
        val index = synchronized(inputLock) {
            while (pendingInputBuffers.isEmpty()) {
                inputLock.wait(100)
            }
            pendingInputBuffers.removeFirst()
        }
        
        val buffer = encoder.getInputBuffer(index)!!
        buffer.clear()
        buffer.put(yuvData)
        encoder.queueInputBuffer(index, 0, yuvData.size, timestampUs, 0)
    }
    
    fun stop() {
        encoder.stop()
        encoder.release()
    }
}
```

### 2.3 解码流程（硬解）

#### Surface 模式（推荐）

```kotlin
class H264SurfaceDecoder(
    private val surface: Surface,  // 通常是 SurfaceView 或 TextureView 的 Surface
    private val onFormatChanged: (MediaFormat) -> Unit
) {
    private lateinit var decoder: MediaCodec
    private val bufferInfo = MediaCodec.BufferInfo()
    
    fun start(width: Int, height: Int, sps: ByteArray, pps: ByteArray) {
        decoder = MediaCodec.createDecoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, width, height
        ).apply {
            // 设置 SPS/PPS（csd-0 和 csd-1）
            setByteBuffer("csd-0", ByteBuffer.wrap(sps))
            setByteBuffer("csd-1", ByteBuffer.wrap(pps))
        }
        
        // 第二个参数传 Surface，启用零拷贝输出
        decoder.configure(format, surface, null, 0)
        decoder.start()
    }
    
    fun feedPacket(nalData: ByteArray, timestampUs: Long, isKeyFrame: Boolean) {
        val index = decoder.dequeueInputBuffer(10_000)
        if (index >= 0) {
            val buffer = decoder.getInputBuffer(index)!!
            buffer.clear()
            buffer.put(nalData)
            
            val flags = if (isKeyFrame) MediaCodec.BUFFER_FLAG_KEY_FRAME else 0
            decoder.queueInputBuffer(index, 0, nalData.size, timestampUs, flags)
        }
        
        // 渲染输出
        drainAndRender()
    }
    
    private fun drainAndRender() {
        while (true) {
            val index = decoder.dequeueOutputBuffer(bufferInfo, 0)
            when {
                index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    onFormatChanged(decoder.outputFormat)
                }
                index >= 0 -> {
                    // render = true 表示将帧渲染到 Surface
                    decoder.releaseOutputBuffer(index, true)
                }
                else -> break
            }
        }
    }
    
    fun stop() {
        decoder.stop()
        decoder.release()
    }
}
```

#### ByteBuffer 模式

```kotlin
class H264BufferDecoder(
    private val onDecodedFrame: (ByteBuffer, Int, Int, Long) -> Unit
) {
    private lateinit var decoder: MediaCodec
    private var outputWidth = 0
    private var outputHeight = 0
    
    fun start(width: Int, height: Int) {
        decoder = MediaCodec.createDecoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, width, height
        )
        
        // 不传 Surface，输出到 ByteBuffer
        decoder.configure(format, null, null, 0)
        decoder.start()
    }
    
    private fun drainOutput() {
        val info = MediaCodec.BufferInfo()
        while (true) {
            val index = decoder.dequeueOutputBuffer(info, 0)
            when {
                index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    val format = decoder.outputFormat
                    outputWidth = format.getInteger(MediaFormat.KEY_WIDTH)
                    outputHeight = format.getInteger(MediaFormat.KEY_HEIGHT)
                    // 注意：实际图像可能有 stride 和 padding
                    val stride = format.getIntegerOrDefault(MediaFormat.KEY_STRIDE, outputWidth)
                    val sliceHeight = format.getIntegerOrDefault(
                        MediaFormat.KEY_SLICE_HEIGHT, outputHeight)
                }
                index >= 0 -> {
                    val buffer = decoder.getOutputBuffer(index)!!
                    // YUV 数据在 buffer 中，需要手动处理
                    onDecodedFrame(buffer, outputWidth, outputHeight, 
                        info.presentationTimeUs)
                    
                    decoder.releaseOutputBuffer(index, false) // false = 不渲染
                }
                else -> break
            }
        }
    }
}

// 扩展函数：安全获取 Integer
fun MediaFormat.getIntegerOrDefault(key: String, default: Int): Int {
    return if (containsKey(key)) getInteger(key) else default
}
```

### 2.4 Surface vs ByteBuffer 模式对比

| 特性 | Surface 模式 | ByteBuffer 模式 |
|------|-------------|-----------------|
| **性能** | 最优（零拷贝） | 较差（需要拷贝） |
| **用途** | 直接显示/渲染 | 后处理/分析 |
| **内存占用** | 低 | 高 |
| **使用复杂度** | 低 | 高（需处理 stride） |
| **灵活性** | 低（只能显示） | 高（可任意处理） |
| **与 OpenGL 集成** | 原生支持 | 需要上传纹理 |

**选择建议**：
- 仅显示视频：Surface 模式
- 需要对解码帧做 CV/ML 处理：ByteBuffer 模式
- 需要同时显示和处理：两个解码器，或 Surface + readPixels

### 2.5 关键配置参数

#### MediaFormat 核心参数

```kotlin
fun createEncoderFormat(
    width: Int,
    height: Int,
    bitrate: Int,
    fps: Int,
    iFrameInterval: Int = 2
): MediaFormat {
    return MediaFormat.createVideoFormat(
        MediaFormat.MIMETYPE_VIDEO_AVC, width, height
    ).apply {
        // 必需参数
        setInteger(MediaFormat.KEY_BIT_RATE, bitrate)
        setInteger(MediaFormat.KEY_FRAME_RATE, fps)
        setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, iFrameInterval)
        setInteger(MediaFormat.KEY_COLOR_FORMAT,
            MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface) // Surface 输入
        
        // 码率控制模式（重要）
        setInteger(MediaFormat.KEY_BITRATE_MODE,
            MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_VBR)
        
        // Profile 和 Level
        setInteger(MediaFormat.KEY_PROFILE,
            MediaCodecInfo.CodecProfileLevel.AVCProfileHigh)
        setInteger(MediaFormat.KEY_LEVEL,
            MediaCodecInfo.CodecProfileLevel.AVCLevel41)
        
        // Android 10+ B 帧支持
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            setInteger(MediaFormat.KEY_MAX_B_FRAMES, 0) // 直播场景禁用 B 帧
        }
        
        // Android 11+ 低延迟模式
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
        }
    }
}
```

#### 码率控制模式详解

| 模式 | 常量 | 描述 | 适用场景 |
|------|------|------|----------|
| **CBR** | `BITRATE_MODE_CBR` | 恒定码率，严格控制 | 直播推流、带宽受限 |
| **VBR** | `BITRATE_MODE_VBR` | 可变码率，质量优先 | 本地录制、离线编码 |
| **CQ** | `BITRATE_MODE_CQ` | 恒定质量，码率波动大 | 高质量归档 |

```kotlin
// CBR 模式：码率稳定，但复杂场景质量下降
format.setInteger(MediaFormat.KEY_BITRATE_MODE,
    MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_CBR)

// VBR 模式：质量稳定，但码率波动
format.setInteger(MediaFormat.KEY_BITRATE_MODE,
    MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_VBR)

// CQ 模式（需要 API 28+）：指定 QP 值而非码率
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
    format.setInteger(MediaFormat.KEY_BITRATE_MODE,
        MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_CQ)
    format.setInteger(MediaFormat.KEY_QUALITY, 23) // 类似 x264 的 CRF
}
```

### 2.6 Input Surface 模式

用于屏幕录制或 Camera 直接编码，实现零拷贝。

```kotlin
class SurfaceEncoder(
    private val width: Int,
    private val height: Int,
    private val bitrate: Int,
    private val fps: Int
) {
    private lateinit var encoder: MediaCodec
    lateinit var inputSurface: Surface
        private set
    
    fun start() {
        encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, width, height
        ).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, bitrate)
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
            // 使用 Surface 输入
            setInteger(MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
        }
        
        encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        
        // 创建 Input Surface
        inputSurface = encoder.createInputSurface()
        
        encoder.start()
    }
    
    // 在 GL 线程中使用
    fun signalEndOfInputStream() {
        encoder.signalEndOfInputStream()
    }
}
```

#### 与 Camera2 集成

```kotlin
class CameraEncoder(
    private val cameraManager: CameraManager,
    private val cameraId: String,
    private val width: Int,
    private val height: Int
) {
    private lateinit var encoder: MediaCodec
    private lateinit var cameraDevice: CameraDevice
    private lateinit var captureSession: CameraCaptureSession
    
    fun start() {
        // 1. 创建编码器和 Input Surface
        encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, width, height
        ).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, 4_000_000)
            setInteger(MediaFormat.KEY_FRAME_RATE, 30)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
            setInteger(MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
        }
        encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        val encoderSurface = encoder.createInputSurface()
        encoder.start()
        
        // 2. 打开 Camera
        cameraManager.openCamera(cameraId, object : CameraDevice.StateCallback() {
            override fun onOpened(camera: CameraDevice) {
                cameraDevice = camera
                // 3. 创建 Capture Session，目标为编码器 Surface
                val surfaces = listOf(encoderSurface)
                camera.createCaptureSession(surfaces, 
                    object : CameraCaptureSession.StateCallback() {
                        override fun onConfigured(session: CameraCaptureSession) {
                            captureSession = session
                            // 4. 开始预览/录制
                            val request = camera.createCaptureRequest(
                                CameraDevice.TEMPLATE_RECORD
                            ).apply {
                                addTarget(encoderSurface)
                            }.build()
                            session.setRepeatingRequest(request, null, null)
                        }
                        override fun onConfigureFailed(session: CameraCaptureSession) {}
                    }, null)
            }
            override fun onDisconnected(camera: CameraDevice) {}
            override fun onError(camera: CameraDevice, error: Int) {}
        }, null)
    }
}
```

#### 与 OpenGL/EGL 集成

```kotlin
class GLEncoder(
    private val width: Int,
    private val height: Int
) {
    private lateinit var encoder: MediaCodec
    private lateinit var eglDisplay: EGLDisplay
    private lateinit var eglContext: EGLContext
    private lateinit var eglSurface: EGLSurface
    
    fun setup() {
        // 1. 创建编码器
        encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        // ... configure ...
        val inputSurface = encoder.createInputSurface()
        encoder.start()
        
        // 2. 创建 EGL 环境
        eglDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
        val version = IntArray(2)
        EGL14.eglInitialize(eglDisplay, version, 0, version, 1)
        
        val configAttribs = intArrayOf(
            EGL14.EGL_RED_SIZE, 8,
            EGL14.EGL_GREEN_SIZE, 8,
            EGL14.EGL_BLUE_SIZE, 8,
            EGL14.EGL_ALPHA_SIZE, 8,
            EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
            EGLExt.EGL_RECORDABLE_ANDROID, 1, // 重要：支持录制
            EGL14.EGL_NONE
        )
        val configs = arrayOfNulls<EGLConfig>(1)
        val numConfigs = IntArray(1)
        EGL14.eglChooseConfig(eglDisplay, configAttribs, 0, 
            configs, 0, 1, numConfigs, 0)
        
        val contextAttribs = intArrayOf(
            EGL14.EGL_CONTEXT_CLIENT_VERSION, 2,
            EGL14.EGL_NONE
        )
        eglContext = EGL14.eglCreateContext(eglDisplay, configs[0], 
            EGL14.EGL_NO_CONTEXT, contextAttribs, 0)
        
        // 3. 创建基于编码器 Surface 的 EGL Surface
        val surfaceAttribs = intArrayOf(EGL14.EGL_NONE)
        eglSurface = EGL14.eglCreateWindowSurface(eglDisplay, configs[0], 
            inputSurface, surfaceAttribs, 0)
        
        EGL14.eglMakeCurrent(eglDisplay, eglSurface, eglSurface, eglContext)
    }
    
    fun renderFrame(timestampNs: Long) {
        // 使用 OpenGL 渲染到 EGL Surface
        // ... GLES20 绑定代码 ...
        
        // 设置时间戳并提交
        EGLExt.eglPresentationTimeANDROID(eglDisplay, eglSurface, timestampNs)
        EGL14.eglSwapBuffers(eglDisplay, eglSurface)
    }
}
```

---

## 三、OMX 与 Codec2 框架

### 3.1 OpenMAX IL（OMX）

OMX IL 是 Android 早期（Android 4.0 - Android 9）的编解码器抽象层。

**核心概念**：

```
OMX 组件模型：

┌────────────┐     ┌────────────┐     ┌────────────┐
│   Source   │────▶│   Filter   │────▶│    Sink    │
│  (数据源)   │     │  (处理器)   │     │  (输出)    │
└────────────┘     └────────────┘     └────────────┘
      │                  │                  │
      ▼                  ▼                  ▼
  ┌───────┐         ┌────────┐         ┌───────┐
  │输出端口│         │输入端口│         │输入端口│
  └───────┘         │输出端口│         └───────┘
                    └────────┘
```

**状态机**：

```
┌─────────┐  LoadedToIdle  ┌──────┐  IdleToExecuting  ┌───────────┐
│ Loaded  │───────────────▶│ Idle │──────────────────▶│ Executing │
└─────────┘                └──────┘                   └───────────┘
     ▲                         │                           │
     │                         │                           │
     │    IdleToLoaded         │     ExecutingToIdle       │
     └─────────────────────────┴───────────────────────────┘
```

**OMX 的问题**：
- API 复杂，回调嵌套
- 线程模型混乱，容易死锁
- 缓冲区生命周期管理困难
- 错误处理机制不完善

### 3.2 Codec2（C2）

Codec2 是 Android 10+ 引入的新框架，目标是替代 OMX。

**核心改进**：

| 方面 | OMX | Codec2 |
|------|-----|--------|
| 缓冲区管理 | 混乱的所有权转移 | 清晰的池化管理 |
| 线程模型 | 不明确 | 明确的异步模型 |
| 错误处理 | 简陋 | 完善的错误报告 |
| HAL 接口 | 传统 binderized | HIDL/AIDL |
| 配置方式 | OMX_SetParameter | 类型安全的 C2Param |

**C2 核心类**：

```
C2Component
├── C2Buffer          // 数据缓冲区
├── C2Work            // 一帧工作单元
│   ├── C2FrameData   // 输入帧数据
│   └── C2Worklet     // 输出结果
├── C2BlockPool       // 内存池
└── C2Param           // 配置参数
```

**厂商迁移状态**（2024）：

| 厂商 | Codec2 支持 |
|------|------------|
| Qualcomm | Android 10+ 全面支持 |
| MediaTek | Android 10+ 全面支持 |
| Samsung | Android 10+ 全面支持 |
| 国产芯片 | 部分支持，持续改进中 |

---

## 四、芯片厂商硬件编解码特性

### 4.1 Qualcomm Snapdragon（骁龙）

**架构组成**：
- Adreno GPU：图形渲染
- Spectra ISP：图像信号处理
- Venus Video Engine：视频编解码

**编码能力对比**：

| 芯片 | H.264 编码 | H.265 编码 | AV1 编码 | 最大分辨率 |
|------|-----------|-----------|---------|-----------|
| 骁龙 888 | HP@5.2 | Main10@5.1 | - | 4K@120fps |
| 骁龙 8 Gen 1 | HP@5.2 | Main10@5.1 | - | 8K@30fps |
| 骁龙 8 Gen 2 | HP@5.2 | Main10@5.1 | 有限支持 | 8K@30fps |
| 骁龙 8 Gen 3 | HP@5.2 | Main10@5.1 | 完整支持 | 8K@60fps |

**高通特有功能**：
- HDR10+ 硬件编码
- HEIF 硬件编解码
- 多路 4K 同时编码
- 低延迟模式支持好

**高通编码器参数提示**：

```kotlin
// 高通设备上推荐的 H.265 配置
fun createQualcommHevcFormat(width: Int, height: Int, bitrate: Int): MediaFormat {
    return MediaFormat.createVideoFormat(
        MediaFormat.MIMETYPE_VIDEO_HEVC, width, height
    ).apply {
        setInteger(MediaFormat.KEY_BIT_RATE, bitrate)
        setInteger(MediaFormat.KEY_FRAME_RATE, 30)
        setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
        setInteger(MediaFormat.KEY_COLOR_FORMAT,
            MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
        
        // 高通支持的高级参数
        setInteger(MediaFormat.KEY_PROFILE,
            MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10)
        setInteger(MediaFormat.KEY_LEVEL,
            MediaCodecInfo.CodecProfileLevel.HEVCMainTierLevel51)
        
        // 高通低延迟模式
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
        }
    }
}
```

### 4.2 MediaTek Dimensity（天玑）

**架构组成**：
- APU（AI 处理单元）：AI 加速
- MDP（Multimedia Data Path）：多媒体数据通路
- VENC/VDEC：视频编解码

**特色功能**：
- APU 辅助超分辨率
- 低功耗模式优化
- 双芯片联合编码（部分型号）

**编码能力对比**：

| 芯片 | H.264 编码 | H.265 编码 | AV1 编码 | 最大分辨率 |
|------|-----------|-----------|---------|-----------|
| 天玑 1200 | HP@5.2 | Main10@5.1 | - | 4K@60fps |
| 天玑 8100 | HP@5.2 | Main10@5.1 | - | 4K@60fps |
| 天玑 9000 | HP@5.2 | Main10@5.1 | 解码 | 8K@30fps |
| 天玑 9200 | HP@5.2 | Main10@5.1 | 编解码 | 8K@30fps |

**MTK 与高通差异**：

| 方面 | 高通 | MTK |
|------|------|-----|
| 编码质量 | 略好 | 中等 |
| 功耗优化 | 优秀 | 优秀 |
| 参数支持 | 全面 | 部分受限 |
| B 帧支持 | 完整 | 部分芯片 |
| 低延迟模式 | 稳定 | 部分芯片不稳定 |

### 4.3 Samsung Exynos

**核心组件**：
- MFC（Multi-Format Codec）：视频编解码
- G2D：2D 图形加速
- JPEG 编解码：硬件加速

**编码能力**（以 Exynos 2200 为例）：
- H.264 HP@5.2：支持
- H.265 Main10@5.1：支持
- AV1：解码支持
- 最大分辨率：8K@30fps

**三星特有问题**：
- 部分 Exynos 芯片发热严重，降频后编码性能下降
- 海外版和国内版可能使用不同芯片

### 4.4 厂商差异的实际影响

**同一 API 在不同芯片上的行为差异**：

```kotlin
// 问题 1：COLOR_FormatYUV420Flexible 的实际格式不同
// 高通通常返回 NV12
// MTK 通常返回 I420
// 三星可能是 NV21

fun getActualColorFormat(codecInfo: MediaCodecInfo, mimeType: String): Int {
    val caps = codecInfo.getCapabilitiesForType(mimeType)
    // 不能假设 Flexible 对应的实际格式
    val supportedFormats = caps.colorFormats
    // 优先使用明确的格式
    return when {
        supportedFormats.contains(COLOR_FormatYUV420SemiPlanar) -> 
            COLOR_FormatYUV420SemiPlanar  // NV12
        supportedFormats.contains(COLOR_FormatYUV420Planar) -> 
            COLOR_FormatYUV420Planar      // I420
        else -> COLOR_FormatYUV420Flexible
    }
}
```

**编码质量差异**：

```
同一参数（1080p, 4Mbps, CBR）在不同芯片上的质量：

骁龙 8 Gen 2:  PSNR ≈ 37.5dB, 码率稳定
天玑 9000:     PSNR ≈ 36.8dB, 码率略有波动
Exynos 2200:   PSNR ≈ 36.5dB, 发热后质量下降
```

**参数兼容性问题**：

```kotlin
// 部分设备不支持某些 Profile/Level
fun safeSetProfile(format: MediaFormat, profile: Int, level: Int) {
    try {
        format.setInteger(MediaFormat.KEY_PROFILE, profile)
        format.setInteger(MediaFormat.KEY_LEVEL, level)
    } catch (e: Exception) {
        // 回退到基础配置
        Log.w(TAG, "Profile/Level not supported, using default")
    }
}

// 部分 MTK 芯片上 KEY_LOW_LATENCY 会导致崩溃
fun safeSetLowLatency(format: MediaFormat) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
        if (!isProblematicDevice()) {
            format.setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
        }
    }
}

private fun isProblematicDevice(): Boolean {
    // 维护已知问题设备列表
    val problematicModels = listOf("SPECIFIC_MODEL_1", "SPECIFIC_MODEL_2")
    return Build.MODEL in problematicModels
}
```

---

## 五、最佳实践与常见问题

### 5.1 性能优化

**1. 使用 Surface 模式避免内存拷贝**

```kotlin
// 不推荐：ByteBuffer 模式，存在拷贝
val buffer = encoder.getInputBuffer(index)
buffer.put(yuvData)  // 内存拷贝

// 推荐：Surface 模式，零拷贝
val inputSurface = encoder.createInputSurface()
// Camera/OpenGL 直接渲染到 Surface
```

**2. 合理设置缓冲区数量**

```kotlin
// 通过 MediaFormat 提示缓冲区数量
format.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, width * height * 3 / 2)

// 监控缓冲区使用情况
fun monitorBufferUsage() {
    val inputPending = pendingInputBuffers.size
    val outputPending = pendingOutputBuffers.size
    if (inputPending > 5 || outputPending > 5) {
        Log.w(TAG, "Buffer backlog: input=$inputPending, output=$outputPending")
    }
}
```

**3. 编码器预热**

```kotlin
fun warmupEncoder(encoder: MediaCodec, format: MediaFormat) {
    // 发送几帧空数据让编码器"热身"
    repeat(3) {
        val index = encoder.dequeueInputBuffer(10_000)
        if (index >= 0) {
            val buffer = encoder.getInputBuffer(index)!!
            buffer.clear()
            // 填充空帧
            encoder.queueInputBuffer(index, 0, 0, 0, 0)
        }
    }
    // 等待输出
    Thread.sleep(100)
    drainAllOutput(encoder)
}
```

### 5.2 常见坑与解决方案

#### Q1: 不同 Android 版本的 API 行为差异

```kotlin
// Android 版本兼容性处理
class VersionCompatMediaCodec {
    fun configure(format: MediaFormat) {
        when {
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q -> {
                // Android 10+: 支持 B 帧配置
                format.setInteger(MediaFormat.KEY_MAX_B_FRAMES, 0)
            }
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.M -> {
                // Android 6+: 异步模式完整支持
            }
            else -> {
                // Android 5: 只能用同步模式
            }
        }
    }
}
```

#### Q2: 某些设备不支持特定 Profile/Level

```kotlin
fun selectBestProfile(codecInfo: MediaCodecInfo, mimeType: String): Pair<Int, Int> {
    val caps = codecInfo.getCapabilitiesForType(mimeType)
    val profileLevels = caps.profileLevels
    
    // 按优先级尝试
    val preferredProfiles = listOf(
        MediaCodecInfo.CodecProfileLevel.AVCProfileHigh to 
            MediaCodecInfo.CodecProfileLevel.AVCLevel41,
        MediaCodecInfo.CodecProfileLevel.AVCProfileMain to 
            MediaCodecInfo.CodecProfileLevel.AVCLevel31,
        MediaCodecInfo.CodecProfileLevel.AVCProfileBaseline to 
            MediaCodecInfo.CodecProfileLevel.AVCLevel31
    )
    
    for ((profile, level) in preferredProfiles) {
        if (profileLevels.any { it.profile == profile && it.level >= level }) {
            return profile to level
        }
    }
    
    // 返回默认值
    return MediaCodecInfo.CodecProfileLevel.AVCProfileBaseline to 
        MediaCodecInfo.CodecProfileLevel.AVCLevel31
}
```

#### Q3: 编码器释放不当导致资源泄漏

```kotlin
class SafeEncoder {
    private var encoder: MediaCodec? = null
    private val releaseLock = Object()
    private var isReleased = false
    
    fun release() {
        synchronized(releaseLock) {
            if (isReleased) return
            isReleased = true
            
            try {
                encoder?.signalEndOfInputStream()
            } catch (e: Exception) {
                Log.w(TAG, "signalEndOfInputStream failed: ${e.message}")
            }
            
            try {
                // 先 stop 再 release
                encoder?.stop()
            } catch (e: IllegalStateException) {
                // 可能已经 stopped
            }
            
            try {
                encoder?.release()
            } catch (e: Exception) {
                Log.e(TAG, "Release failed: ${e.message}")
            }
            
            encoder = null
        }
    }
    
    protected fun finalize() {
        if (!isReleased) {
            Log.w(TAG, "Encoder not properly released!")
            release()
        }
    }
}
```

#### Q4: dequeueOutputBuffer 超时处理

```kotlin
class TimeoutHandler(
    private val maxTimeoutCount: Int = 10,
    private val onTimeout: () -> Unit
) {
    private var timeoutCount = 0
    
    fun handleDequeueResult(result: Int) {
        when (result) {
            MediaCodec.INFO_TRY_AGAIN_LATER -> {
                timeoutCount++
                if (timeoutCount >= maxTimeoutCount) {
                    Log.e(TAG, "Too many consecutive timeouts")
                    onTimeout()
                }
            }
            else -> {
                // 收到有效结果，重置计数
                timeoutCount = 0
            }
        }
    }
}
```

#### Q5: CodecException 处理策略

```kotlin
fun handleCodecException(e: MediaCodec.CodecException): RecoveryAction {
    return when {
        e.isRecoverable -> {
            // 可恢复错误：重启编码器
            Log.w(TAG, "Recoverable error, restarting codec")
            RecoveryAction.RESTART_CODEC
        }
        e.isTransient -> {
            // 临时错误：重试
            Log.w(TAG, "Transient error, retrying")
            RecoveryAction.RETRY
        }
        else -> {
            // 不可恢复错误：回退软编
            Log.e(TAG, "Unrecoverable error: ${e.diagnosticInfo}")
            RecoveryAction.FALLBACK_TO_SOFTWARE
        }
    }
}

enum class RecoveryAction {
    RETRY,
    RESTART_CODEC,
    FALLBACK_TO_SOFTWARE
}
```

### 5.3 调试技巧

**1. 查看编解码器状态**

```bash
# 查看所有编解码器
adb shell dumpsys media.codec

# 查看 MediaCodec 详细信息
adb shell dumpsys media.player

# 查看硬件编解码器
adb shell cat /sys/class/video_codec/video_encoder/status
```

**2. 日志分析**

```bash
# 开启 MediaCodec 详细日志
adb shell setprop log.tag.MediaCodec DEBUG

# 过滤编解码相关日志
adb logcat -s MediaCodec:V ACodec:V OMX:V

# Codec2 相关日志
adb logcat | grep -E "(C2|Codec2)"
```

**3. 查询编解码器能力**

```kotlin
fun dumpCodecCapabilities() {
    val codecList = MediaCodecList(MediaCodecList.ALL_CODECS)
    for (info in codecList.codecInfos) {
        Log.d(TAG, "Codec: ${info.name}")
        Log.d(TAG, "  Is Encoder: ${info.isEncoder}")
        Log.d(TAG, "  Is Hardware: ${!info.isSoftwareOnly}")
        
        for (type in info.supportedTypes) {
            Log.d(TAG, "  Type: $type")
            val caps = info.getCapabilitiesForType(type)
            
            if (info.isEncoder) {
                val videoCaps = caps.videoCapabilities
                Log.d(TAG, "    Width: ${videoCaps.supportedWidths}")
                Log.d(TAG, "    Height: ${videoCaps.supportedHeights}")
                Log.d(TAG, "    FPS: ${videoCaps.supportedFrameRates}")
                Log.d(TAG, "    Bitrate: ${videoCaps.bitrateRange}")
                
                val encoderCaps = caps.encoderCapabilities
                Log.d(TAG, "    CBR: ${encoderCaps.isBitrateModeSupported(
                    MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_CBR)}")
                Log.d(TAG, "    VBR: ${encoderCaps.isBitrateModeSupported(
                    MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_VBR)}")
            }
            
            Log.d(TAG, "    Profiles: ${caps.profileLevels.map { 
                "P${it.profile}/L${it.level}" 
            }}")
            Log.d(TAG, "    Colors: ${caps.colorFormats.toList()}")
        }
    }
}
```

---

## 六、完整示例：视频录制编码器

```kotlin
/**
 * 完整的硬件编码器封装
 * 支持 Camera 输入和 ByteBuffer 输入
 */
class VideoRecordEncoder(
    private val config: EncoderConfig,
    private val callback: EncoderCallback
) {
    data class EncoderConfig(
        val width: Int,
        val height: Int,
        val bitrate: Int,
        val fps: Int,
        val iFrameInterval: Int = 2,
        val useSurface: Boolean = true,
        val lowLatency: Boolean = false
    )
    
    interface EncoderCallback {
        fun onFormatChanged(format: MediaFormat)
        fun onEncodedData(data: ByteBuffer, info: MediaCodec.BufferInfo)
        fun onError(error: Exception)
    }
    
    private var encoder: MediaCodec? = null
    private var inputSurface: Surface? = null
    private val bufferInfo = MediaCodec.BufferInfo()
    private var isRunning = false
    
    fun start(): Surface? {
        try {
            encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
            
            val format = createFormat()
            encoder?.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            
            if (config.useSurface) {
                inputSurface = encoder?.createInputSurface()
            }
            
            encoder?.setCallback(codecCallback, Handler(Looper.getMainLooper()))
            encoder?.start()
            isRunning = true
            
            return inputSurface
        } catch (e: Exception) {
            callback.onError(e)
            return null
        }
    }
    
    private fun createFormat(): MediaFormat {
        return MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, 
            config.width, 
            config.height
        ).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, config.bitrate)
            setInteger(MediaFormat.KEY_FRAME_RATE, config.fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, config.iFrameInterval)
            setInteger(MediaFormat.KEY_BITRATE_MODE,
                MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_VBR)
            
            val colorFormat = if (config.useSurface) {
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface
            } else {
                MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible
            }
            setInteger(MediaFormat.KEY_COLOR_FORMAT, colorFormat)
            
            // 可选：配置 Profile/Level
            setInteger(MediaFormat.KEY_PROFILE,
                MediaCodecInfo.CodecProfileLevel.AVCProfileHigh)
            
            // Android 11+ 低延迟
            if (config.lowLatency && Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
            }
        }
    }
    
    private val codecCallback = object : MediaCodec.Callback() {
        override fun onInputBufferAvailable(codec: MediaCodec, index: Int) {
            // Surface 模式下不需要处理
            if (!config.useSurface) {
                // 通知外部可以填充数据
            }
        }
        
        override fun onOutputBufferAvailable(
            codec: MediaCodec, 
            index: Int, 
            info: MediaCodec.BufferInfo
        ) {
            if (!isRunning) return
            
            try {
                val buffer = codec.getOutputBuffer(index)
                if (buffer != null && info.size > 0) {
                    callback.onEncodedData(buffer, info)
                }
                codec.releaseOutputBuffer(index, false)
            } catch (e: Exception) {
                callback.onError(e)
            }
        }
        
        override fun onOutputFormatChanged(codec: MediaCodec, format: MediaFormat) {
            callback.onFormatChanged(format)
        }
        
        override fun onError(codec: MediaCodec, e: MediaCodec.CodecException) {
            callback.onError(e)
        }
    }
    
    fun requestKeyFrame() {
        try {
            val params = Bundle()
            params.putInt(MediaCodec.PARAMETER_KEY_REQUEST_SYNC_FRAME, 0)
            encoder?.setParameters(params)
        } catch (e: Exception) {
            Log.w(TAG, "Request key frame failed: ${e.message}")
        }
    }
    
    fun updateBitrate(newBitrate: Int) {
        try {
            val params = Bundle()
            params.putInt(MediaCodec.PARAMETER_KEY_VIDEO_BITRATE, newBitrate)
            encoder?.setParameters(params)
        } catch (e: Exception) {
            Log.w(TAG, "Update bitrate failed: ${e.message}")
        }
    }
    
    fun stop() {
        isRunning = false
        try {
            inputSurface?.let {
                encoder?.signalEndOfInputStream()
            }
            encoder?.stop()
            encoder?.release()
        } catch (e: Exception) {
            Log.w(TAG, "Stop encoder failed: ${e.message}")
        }
        encoder = null
        inputSurface = null
    }
    
    companion object {
        private const val TAG = "VideoRecordEncoder"
    }
}
```

---

## 参考资源

### 官方文档
- [Android MediaCodec 官方文档](https://developer.android.com/reference/android/media/MediaCodec)
- [Android Media API 指南](https://developer.android.com/guide/topics/media/media-codecs)
- [MediaFormat 参数参考](https://developer.android.com/reference/android/media/MediaFormat)

### 示例项目
- [Google Grafika](https://github.com/google/grafika) - MediaCodec 最佳示例
- [CameraX](https://developer.android.com/training/camerax) - 现代 Camera API
- [ExoPlayer](https://github.com/google/ExoPlayer) - 工业级播放器

### 深入学习
- [Android 音视频开发进阶指南](https://blog.csdn.net/yanbober/article/details/52661720)
- [Stagefright 源码分析](https://source.android.com/docs/core/media)
- [Codec2 设计文档](https://source.android.com/docs/core/media/codec2)

### 芯片厂商文档
- [Qualcomm Video SDK](https://developer.qualcomm.com/software/snapdragon-video-sdk)
- [MediaTek 开发者中心](https://www.mediatek.com/developer)
- [Samsung Exynos 文档](https://developer.samsung.com/galaxy-gamedev/documentation.html)

# 端到端Gamma系统与EOTF机制

> 首次学习：2026-03-21
> 最近更新：2026-03-21
> 使用场景：工作（音视频开发）
> 掌握水平：1 → 学习后

<!-- 更新日志 -->
<!-- [2026-03-21] 首次创建：从对话中提取EOTF隐式/显式应用机制、Android/iOS显示管线 -->

---

## 一句话理解（费曼版）

SDR视频播放时EOTF不是被省略了，而是手机屏幕硬件自动帮你做了——就像相机拍照时"压缩"了亮度信息，屏幕显示时自动"解压"回来，中间的传输和处理环节只要不破坏这个压缩后的信号就行。

---

## 知识框架

1. 端到端Gamma系统原理（OETF↔EOTF闭环）
2. 显示面板隐式EOTF机制（CRT历史→现代面板校准→OS默认假设）
3. 需要显式EOTF的四种场景（线性运算/HDR/跨色域/sRGB FB）
4. Android显示管线（SDR路径/HDR路径/关键API）
5. iOS显示管线（SDR路径/EDR系统）

---

## 核心概念

### OETF（光电转换函数）
相机采集时将线性光信号"压缩"为非线性电信号的函数，类似于gamma编码≈1/2.2。目的是利用人眼对暗部更敏感的特性，让有限的bit数更多分配给暗部细节。

### EOTF（电光转换函数）
显示端将非线性电信号"还原"为线性光输出的函数。对于SDR就是gamma解码≈2.2~2.4。关键认知：这一步由显示面板硬件自动完成，不需要软件显式处理。

### YCbCr→RGB转换的本质
这只是颜色模型的变换（亮度+色度→红绿蓝），不改变传递函数。转换后的RGB仍然是gamma编码的非线性值，不是线性光。

### 显示面板Gamma LUT
现代LCD/OLED面板的驱动芯片内置Gamma校正查找表，校准为模拟CRT的幂律响应。广播级遵循BT.1886(γ=2.4)，消费级遵循sRGB(γ≈2.2)。

### sRGB Framebuffer陷阱
GPU的sRGB framebuffer(GL_SRGB8_ALPHA8)会自动做gamma编码。视频内容本身已经是gamma编码的，写入sRGB FB会导致双重编码，画面发白。视频渲染应使用普通的GL_RGBA8。

### EDR（Extended Dynamic Range）
iOS的HDR显示机制。Shader输出线性光值到浮点framebuffer，0.0=黑，1.0=SDR白(≈200nit)，>1.0=HDR区域。必须显式做PQ EOTF。

---

## 端到端Gamma系统原理

整个视频系统从设计之初就是一个闭合的 OETF-EOTF 对称链路：

```
场景光线 → 相机 OETF (gamma编码 ≈ 1/2.2) → 非线性信号 →
→ YUV编码 (仍然是非线性的) → 传输 → 解码 →
→ Shader: YCbCr → RGB (仍然是非线性/gamma编码的RGB) →
→ 写入 Framebuffer (非线性RGB值) →
→ 显示面板 EOTF (gamma解码 ≈ 2.2~2.4) → 光输出
```

Shader中的YCbCr→RGB转换本质上只是颜色模型的变换（从亮度+色度分量变为R/G/B三通道），并不改变传递函数。转换后的RGB值仍然是gamma编码的非线性值。

---

## 显示面板隐式完成EOTF的原因

**历史原因（CRT）**：CRT电子枪天然具有幂律响应 `光输出 = 电压^γ (γ≈2.2~2.4)`，这本身就是EOTF。

**现代面板（LCD/OLED）**：驱动芯片（Driver IC）和Gamma校正LUT被校准为模拟CRT响应曲线：
- 广播级：BT.1886标准（纯幂律γ=2.4，黑电平修正）
- 计算机显示：sRGB标准（γ≈2.2，低端有线性段）
- 手机面板：通常校准为sRGB 2.2或DCI-P3 2.2

**操作系统默认假设**：Android和iOS都默认Framebuffer内容是sRGB gamma编码的。

---

## 需要显式应用EOTF的四种情况

### 情况一：Shader内需要线性空间运算
混合、Alpha合成、光照、模糊等物理正确运算必须在线性空间进行。

### 情况二：HDR内容显示
- PQ(ST 2084)编码值动态范围0~10000 nit，传统面板gamma LUT只理解0~100 nit的sRGB编码
- HLG有场景参考特性，需要OOTF适配不同亮度的显示器
- 必须通过HDR显示通路或Shader中做PQ EOTF→色调映射→sRGB OETF

### 情况三：跨色域转换（如BT.2020→BT.709）
转换矩阵假设输入是线性光，必须先EOTF解码→矩阵变换→OETF编码。

### 情况四：sRGB Framebuffer陷阱
视频内容已经是gamma编码的，如果写入sRGB framebuffer，GPU会再编码一次→双重gamma→画面发白。正确做法：视频渲染应使用非sRGB framebuffer（GL_RGBA8/VK_FORMAT_R8G8B8A8_UNORM）。

---

## Android显示管线

### SDR路径
```
MediaCodec解码 → SurfaceTexture(GPU纹理) →
→ Shader: samplerExternalOES → YCbCr→RGB(非线性) →
→ 写入EGLSurface(framebuffer, 非sRGB) →
→ SurfaceFlinger合成(假设sRGB) →
→ HWC(Hardware Composer) →
→ 显示面板(gamma LUT完成隐式EOTF) → 光输出
```

### HDR路径（Android 10+）
- **路径A**：显示器支持HDR → 直通HWC → 面板切换PQ EOTF模式
- **路径B**：显示器不支持HDR → SurfaceFlinger做色调映射 → SDR输出
- **路径C**：自定义处理 → Shader中做PQ EOTF + 色调映射 + sRGB OETF

**关键API**：MediaFormat.KEY_COLOR_STANDARD / KEY_COLOR_TRANSFER / KEY_COLOR_RANGE

---

## iOS显示管线

### SDR路径
```
AVPlayer → CVPixelBuffer(YCbCr, 含color attachment) →
→ Metal/OpenGL texture → Shader: YCbCr→RGB(非线性) →
→ 写入CAMetalLayer(默认.bgra8Unorm, sRGB) →
→ Core Animation合成 → 显示驱动(gamma LUT) → 光输出
```

### HDR路径（EDR系统）
- EDR值域：0.0=黑, 1.0=SDR白(≈200nit), >1.0=HDR区域
- Shader必须显式做PQ EOTF，输出线性光值到浮点framebuffer

---

## 比喻 & 例子

**比喻**：
整个视频系统就像一个"压缩-传输-解压"的快递系统。相机端把物品（光信号）压缩打包（OETF），中间所有环节（编码/传输/解码/YCbCr→RGB）只是在搬运和转换包裹的标签格式，不拆开包裹。最后屏幕收到包裹后自动拆封解压（EOTF），还原出原始物品。你的Shader只是负责把标签从"亮度+色度"格式改写成"红绿蓝"格式，并没有拆开包裹。

**工作例子**：
SDR视频播放场景中，MediaCodec解码输出NV12纹理 → Shader用BT.709矩阵做YCbCr→RGB → 写入普通EGLSurface → SurfaceFlinger合成 → 面板Gamma LUT自动完成EOTF。全程不需要任何显式的gamma处理。

但如果你要在Shader中对两路视频做Alpha混合（如画中画），就必须先EOTF解码到线性空间再混合，否则混合边缘会出现亮度不自然的问题。

---

## 总结对比表

| 场景 | 是否需要显式EOTF | 原因 |
|------|------------------|------|
| SDR视频直接显示 | 不需要 | 面板gamma LUT隐式完成 |
| Shader内线性运算（混合/模糊/光照） | 需要 | 物理正确的运算必须在线性空间 |
| HDR视频 + HDR面板直通 | 不需要 | 面板切换到PQ/HLG EOTF模式 |
| HDR视频 + SDR面板 | 需要 | 必须做PQ EOTF + 色调映射 + sRGB OETF |
| iOS EDR路径 | 需要 | EDR要求输出线性光到浮点buffer |
| 跨色域转换（BT.2020→709） | 需要 | 色域转换矩阵要求线性光输入 |
| sRGB Framebuffer | 需要注意 | 避免双重gamma编码 |

---

## 边界 & 反例

- **HDR内容不能套用SDR的隐式EOTF逻辑**：PQ/HLG传递函数与gamma 2.2完全不同，面板的标准gamma LUT无法正确处理
- **跨色域转换必须在线性空间**：如果在gamma空间直接用矩阵做BT.2020→BT.709转换，会产生色彩偏移
- **任何需要物理正确的图像运算（模糊、混合、光照）都不能在gamma空间进行**：否则暗部运算结果会偏暗，亮部偏亮
- **iOS EDR路径是例外**：即使是SDR内容，如果走EDR通路也需要输出线性光到浮点buffer

---

## 常见误区

| 误区 | 正确理解 |
|------|----------|
| "解码后YCbCr→RGB就得到了正确的线性RGB可以直接运算" | YCbCr→RGB只是颜色模型变换，输出仍是gamma编码的非线性值，不能直接做线性运算 |
| "SDR视频播放不需要EOTF" | 不是不需要，是显示面板硬件自动做了，整条链路的EOTF从未缺席 |
| "写入sRGB framebuffer能自动处理好gamma" | 视频已经是gamma编码的，sRGB FB会再编码一次导致双重gamma，应该用普通RGBA8 |
| "HDR视频只要解码后直接显示就行" | PQ/HLG与传统gamma完全不同，必须走专门的HDR通路或做显式色调映射 |
| "Android和iOS的HDR处理方式一样" | Android走DATASPACE标记+HWC直通或SurfaceFlinger色调映射；iOS走EDR线性光浮点buffer，机制完全不同 |

---

## 代码示例

### Shader中需要线性运算时的正确做法（GLSL）
```glsl
// 1. YCbCr → RGB（仍是gamma编码）
vec3 rgb_gamma = YCbCrToRGB(ycbcr);

// 2. 显式EOTF：gamma解码 → 线性光
vec3 rgb_linear = pow(rgb_gamma, vec3(2.2));

// 3. 在线性空间做运算
vec3 result_linear = mix(rgb_linear, other_linear, factor);

// 4. 显式OETF：线性光 → gamma编码
vec3 result_gamma = pow(result_linear, vec3(1.0/2.2));

// 5. 输出到非sRGB framebuffer
gl_FragColor = vec4(result_gamma, 1.0);
```

### Android HDR关键API
```java
MediaFormat format = decoder.getOutputFormat();
int colorTransfer = format.getInteger(MediaFormat.KEY_COLOR_TRANSFER);
// COLOR_TRANSFER_SDR_VIDEO (gamma) / COLOR_TRANSFER_ST2084 (PQ) / COLOR_TRANSFER_HLG
```

### iOS EDR配置
```swift
metalLayer.wantsExtendedDynamicRangeContent = true
metalLayer.pixelFormat = .rgba16Float
metalLayer.colorspace = CGColorSpace(name: CGColorSpace.extendedLinearDisplayP3)
```

---

## 自测题

1. **为什么SDR视频播放时Shader不需要显式调用EOTF就能正确显示？**
   > 答：因为整个视频系统是端到端的OETF↔EOTF闭环。相机端做了OETF(gamma编码)，Shader的YCbCr→RGB只是颜色模型变换不改变传递函数，最终由显示面板的Gamma LUT硬件自动完成EOTF(gamma解码)。EOTF并未缺席，只是由硬件隐式完成了。

2. **如果在Shader中对两路SDR视频做Alpha混合，不做EOTF/OETF会有什么问题？怎么解决？**
   > 答：在gamma空间做混合会导致亮度响应不正确——混合边缘出现暗带或亮度不自然。解决方法是先EOTF解码到线性空间，在线性空间做混合，再OETF编码回gamma空间输出。

3. **为什么视频渲染不能使用sRGB Framebuffer？**
   > 答：因为视频解码后的数据已经是gamma编码的非线性值。sRGB framebuffer（如GL_SRGB8_ALPHA8）会在写入时自动做一次sRGB OETF编码，导致双重gamma编码，画面会发白过亮。应使用普通的GL_RGBA8/VK_FORMAT_R8G8B8A8_UNORM framebuffer。

---

## 延伸阅读 / 关联知识

1. **BT.1886标准**：定义了现代平板显示器的参考EOTF，是"显示面板隐式EOTF"的理论依据
2. **PQ (ST 2084) 传递函数**：HDR的核心传递函数，与传统gamma完全不同的数学模型，能表示0~10000 nit
3. **Android SurfaceFlinger色彩管理**：Android 10+引入的完整色彩管理框架，处理SDR/HDR混合显示场景

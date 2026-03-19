# HDR色彩管理深度解析 - 文档导航

> 本目录包含关于颜色空间、色彩管理和HDR技术的系统性深度文章

---

## 📚 文档结构

本文档采用**金字塔结构**组织，主文章提供全景视图，子文件深入关键概念。

### 主文章

| 文件 | 描述 | 行数 |
|------|------|------|
| **[HDR色彩管理深度解析.md](./HDR色彩管理深度解析.md)** | 系统性梳理颜色空间、色彩管理和HDR的核心概念、技术原理与实践应用 | 498 |

### 子文件（按主题分类）

#### 🎨 基础理论

| 文件 | 描述 | 行数 |
|------|------|------|
| [色度图_详细解析.md](./01_基础理论/色度图_详细解析.md) | CIE 1931色彩空间体系、颜色匹配函数、色度图原理 | 369 |
| [颜色空间_数学定义.md](./01_基础理论/颜色空间_数学定义.md) | RGB颜色空间的数学构造、转换矩阵推导 | 350 |
| [传递函数_详细解析.md](./01_基础理论/传递函数_详细解析.md) | Gamma校正、PQ、HLG等传递函数的深入解析 | 421 |

#### 📺 SDR与HDR对比

| 文件 | 描述 | 行数 |
|------|------|------|
| [SDR渲染管线_详细解析.md](./02_SDR与HDR对比/SDR渲染管线_详细解析.md) | 标准动态范围渲染的完整流程与关键技术 | 517 |
| [HDR显示标准_详细解析.md](./02_SDR与HDR对比/HDR显示标准_详细解析.md) | HDR10、Dolby Vision、HLG等主流HDR标准详解 | 422 |
| [色调映射算法_详细解析.md](./02_SDR与HDR对比/色调映射算法_详细解析.md) | 从Reinhard到ACES的色调映射算法演进 | 392 |

#### 📷 输入域处理

| 文件 | 描述 | 行数 |
|------|------|------|
| **[RAW_YUV域深度解析.md](./03_输入域处理/RAW_YUV域深度解析.md)** | RAW域与YUV域的系统性概览，从传感器到编码的完整链路 | 527 |
| [RAW域_详细解析.md](./03_输入域处理/RAW域_详细解析.md) | Bayer格式、Demosaic算法、白平衡、CCM、噪点处理 | 960 |
| [YUV域_详细解析.md](./03_输入域处理/YUV域_详细解析.md) | 亮度-色度分离、子采样、标准转换矩阵、应用场景 | 1074 |
| [RAW到YUV转换管线_详细解析.md](./03_输入域处理/RAW到YUV转换管线_详细解析.md) | 完整ISP流程、色彩空间转换、质量与性能权衡 | 727 |
| [工程实践与优化_详细解析.md](./03_输入域处理/工程实践与优化_详细解析.md) | 移动端ISP优化、GPU加速、跨平台兼容性 | 929 |

#### 🎮 工程实践

| 文件 | 描述 | 行数 |
|------|------|------|
| [ACES工作流_详细解析.md](./04_工程实践/ACES工作流_详细解析.md) | 学院色彩编码系统的架构、转换与应用 | 455 |
| [游戏中HDR实现_详细解析.md](./04_工程实践/游戏中HDR实现_详细解析.md) | 现代游戏引擎的HDR渲染管线实现 | 511 |
| [色彩管理管线_详细解析.md](./04_工程实践/色彩管理管线_详细解析.md) | 端到端色彩管理工作流的设计与实现 | 539 |

#### 📹 Camera Pipeline

| 文件 | 描述 | 行数 |
|------|------|------|
| **[Camera_Pipeline_总览.md](./05_Camera_Pipeline/Camera_Pipeline_总览.md)** | Camera成像管线系统性概览，从传感器到最终图像输出 | 631 |
| [图像传感器与RAW采集_详细解析.md](./05_Camera_Pipeline/图像传感器与RAW采集_详细解析.md) | CMOS传感器架构、Bayer阵列、噪声模型、RAW数据格式 | 1435 |
| [3A算法系统_详细解析.md](./05_Camera_Pipeline/3A算法系统_详细解析.md) | 自动曝光(AE)、自动白平衡(AWB)、自动对焦(AF)算法详解 | 1662 |
| [ISP图像处理流水线_详细解析.md](./05_Camera_Pipeline/ISP图像处理流水线_详细解析.md) | ISP硬件架构、处理流水线各模块、实时处理约束 | 1871 |
| [HDR相机成像技术_详细解析.md](./05_Camera_Pipeline/HDR相机成像技术_详细解析.md) | 多帧HDR合成、单帧HDR传感器、HDR视频采集技术 | 1263 |
| [ISP调试与图像质量评估_详细解析.md](./05_Camera_Pipeline/ISP调试与图像质量评估_详细解析.md) | ISP Tuning工作流、图像质量评价(IQ)、色彩标定方法 | 1367 |

---

## 🗺️ 学习路径

### 路径一：理论基础
```
HDR色彩管理深度解析（概览）
    ↓
色度图_详细解析
    ↓
颜色空间_数学定义
    ↓
传递函数_详细解析
```

### 路径二：技术对比
```
HDR色彩管理深度解析（概览）
    ↓
SDR渲染管线_详细解析
    ↓
HDR显示标准_详细解析
    ↓
色调映射算法_详细解析
```

### 路径三：工程实践
```
HDR色彩管理深度解析（概览）
    ↓
ACES工作流_详细解析
    ↓
游戏中HDR实现_详细解析
    ↓
色彩管理管线_详细解析
```

### 路径四：RAW/YUV域处理
```
RAW_YUV域深度解析（概览）
    ↓
RAW域_详细解析
    ↓
YUV域_详细解析
    ↓
RAW到YUV转换管线_详细解析
    ↓
工程实践与优化_详细解析
```

### 路径五：Camera Pipeline（新增）
```
Camera_Pipeline_总览（概览）
    ↓
图像传感器与RAW采集_详细解析
    ↓
3A算法系统_详细解析
    ↓
ISP图像处理流水线_详细解析
    ↓
HDR相机成像技术_详细解析
    ↓
ISP调试与图像质量评估_详细解析
```

### 完整学习路径（推荐）
```
基础理论 → 输入域处理 → Camera Pipeline → 技术对比 → 工程实践
    ↓           ↓              ↓              ↓          ↓
 色度图      RAW域         传感器         SDR管线    ACES工作流
 颜色空间    YUV域         3A算法         HDR标准    游戏实现
 传递函数    ISP管线       ISP流水线      色调映射   管线设计
```

---

## 📊 内容统计

- **总文件数**: 21个Markdown文件
- **总行数**: 约16,000+行
- **总字数**: 约500,000+字
- **参考文章**: 基于Lele Feng的知乎专栏文章及相关技术资料整理

---

## 🔗 快速导航

### 核心概念速查

| 概念 | 所在文件 |
|------|---------|
| CIE 1931 XYZ | [色度图_详细解析.md](./01_基础理论/色度图_详细解析.md) |
| 颜色匹配函数 | [色度图_详细解析.md](./01_基础理论/色度图_详细解析.md) |
| xy色度图 | [色度图_详细解析.md](./01_基础理论/色度图_详细解析.md) |
| RGB颜色空间定义 | [颜色空间_数学定义.md](./01_基础理论/颜色空间_数学定义.md) |
| 颜色空间转换矩阵 | [颜色空间_数学定义.md](./01_基础理论/颜色空间_数学定义.md) |
| Gamma校正 | [传递函数_详细解析.md](./01_基础理论/传递函数_详细解析.md) |
| PQ传递函数 | [传递函数_详细解析.md](./01_基础理论/传递函数_详细解析.md) |
| HLG传递函数 | [传递函数_详细解析.md](./01_基础理论/传递函数_详细解析.md) |
| SDR渲染管线 | [SDR渲染管线_详细解析.md](./02_SDR与HDR对比/SDR渲染管线_详细解析.md) |
| HDR10标准 | [HDR显示标准_详细解析.md](./02_SDR与HDR对比/HDR显示标准_详细解析.md) |
| Dolby Vision | [HDR显示标准_详细解析.md](./02_SDR与HDR对比/HDR显示标准_详细解析.md) |
| 色调映射算法 | [色调映射算法_详细解析.md](./02_SDR与HDR对比/色调映射算法_详细解析.md) |
| ACES颜色空间 | [ACES工作流_详细解析.md](./04_工程实践/ACES工作流_详细解析.md) |
| IDT/RRT/ODT | [ACES工作流_详细解析.md](./04_工程实践/ACES工作流_详细解析.md) |
| 游戏HDR实现 | [游戏中HDR实现_详细解析.md](./04_工程实践/游戏中HDR实现_详细解析.md) |
| CLUT/LUT | [游戏中HDR实现_详细解析.md](./04_工程实践/游戏中HDR实现_详细解析.md) |
| OCIO集成 | [色彩管理管线_详细解析.md](./04_工程实践/色彩管理管线_详细解析.md) |
| Bayer格式 | [RAW域_详细解析.md](./03_输入域处理/RAW域_详细解析.md) |
| Demosaic算法 | [RAW域_详细解析.md](./03_输入域处理/RAW域_详细解析.md) |
| 白平衡/AWB | [RAW域_详细解析.md](./03_输入域处理/RAW域_详细解析.md) |
| 色彩校正矩阵CCM | [RAW域_详细解析.md](./03_输入域处理/RAW域_详细解析.md) |
| YUV/YCbCr | [YUV域_详细解析.md](./03_输入域处理/YUV域_详细解析.md) |
| 色度子采样 | [YUV域_详细解析.md](./03_输入域处理/YUV域_详细解析.md) |
| BT.601/BT.709/BT.2020 | [YUV域_详细解析.md](./03_输入域处理/YUV域_详细解析.md) |
| ISP管线 | [RAW到YUV转换管线_详细解析.md](./03_输入域处理/RAW到YUV转换管线_详细解析.md) |
| 镜头阴影校正LSC | [RAW到YUV转换管线_详细解析.md](./03_输入域处理/RAW到YUV转换管线_详细解析.md) |
| 多帧降噪 | [工程实践与优化_详细解析.md](./03_输入域处理/工程实践与优化_详细解析.md) |
| GPU加速 | [工程实践与优化_详细解析.md](./03_输入域处理/工程实践与优化_详细解析.md) |
| CMOS传感器架构 | [图像传感器与RAW采集_详细解析.md](./05_Camera_Pipeline/图像传感器与RAW采集_详细解析.md) |
| Bayer阵列与CFA变体 | [图像传感器与RAW采集_详细解析.md](./05_Camera_Pipeline/图像传感器与RAW采集_详细解析.md) |
| 传感器噪声模型 | [图像传感器与RAW采集_详细解析.md](./05_Camera_Pipeline/图像传感器与RAW采集_详细解析.md) |
| 自动曝光(AE) | [3A算法系统_详细解析.md](./05_Camera_Pipeline/3A算法系统_详细解析.md) |
| 自动白平衡(AWB) | [3A算法系统_详细解析.md](./05_Camera_Pipeline/3A算法系统_详细解析.md) |
| 自动对焦(AF) | [3A算法系统_详细解析.md](./05_Camera_Pipeline/3A算法系统_详细解析.md) |
| 3A协同机制 | [3A算法系统_详细解析.md](./05_Camera_Pipeline/3A算法系统_详细解析.md) |
| ISP硬件架构 | [ISP图像处理流水线_详细解析.md](./05_Camera_Pipeline/ISP图像处理流水线_详细解析.md) |
| ISP处理流水线 | [ISP图像处理流水线_详细解析.md](./05_Camera_Pipeline/ISP图像处理流水线_详细解析.md) |
| 实时ISP约束 | [ISP图像处理流水线_详细解析.md](./05_Camera_Pipeline/ISP图像处理流水线_详细解析.md) |
| HDR采集技术 | [HDR相机成像技术_详细解析.md](./05_Camera_Pipeline/HDR相机成像技术_详细解析.md) |
| 多帧HDR合成 | [HDR相机成像技术_详细解析.md](./05_Camera_Pipeline/HDR相机成像技术_详细解析.md) |
| 单帧HDR传感器 | [HDR相机成像技术_详细解析.md](./05_Camera_Pipeline/HDR相机成像技术_详细解析.md) |
| ISP Tuning工作流 | [ISP调试与图像质量评估_详细解析.md](./05_Camera_Pipeline/ISP调试与图像质量评估_详细解析.md) |
| 图像质量评价(IQ) | [ISP调试与图像质量评估_详细解析.md](./05_Camera_Pipeline/ISP调试与图像质量评估_详细解析.md) |
| 色彩标定 | [ISP调试与图像质量评估_详细解析.md](./05_Camera_Pipeline/ISP调试与图像质量评估_详细解析.md) |

---

## 📝 写作原则

本文档遵循以下原则：

1. **金字塔原理**：结论先行、以上统下、归类分组、逻辑递进
2. **MECE原则**：相互独立、完全穷尽
3. **理论与实践结合**：既有数学推导，也有代码示例
4. **系统性组织**：从基础概念到工程实践，层层递进

---

## 🎯 目标读者

- 图形渲染工程师
- 技术美术（TA）
- 游戏开发者
- 影视后期制作人员
- **相机/ISP算法工程师**
- **计算机视觉工程师**
- **移动端图像处理开发者**
- 对色彩管理感兴趣的技术人员

---

## 📖 参考资源

### HDR与色彩管理
- [Lele Feng - 漫谈HDR和色彩管理系列](https://zhuanlan.zhihu.com/p/129095380)
- [ACES官方网站](https://acescentral.com/)
- [OpenColorIO](https://opencolorio.org/)
- [HDR in Call of Duty (Digital Dragons 2018)](https://www.youtube.com/watch?v=5xCqCnB1mC0)
- [CG Cinematography](https://chrisbrejon.com/cg-cinematography/)

### RAW与ISP处理
- [LibRaw - 开源RAW处理库](https://www.libraw.org/)
- [Adobe DNG Specification](https://helpx.adobe.com/photoshop/digital-negative.html)
- [ISP Algorithm Tuning Guide](https://www.quectel.com/)

### YUV与视频编码
- [ITU-R BT.601/BT.709/BT.2020 标准](https://www.itu.int/rec/R-REC-BT)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [VideoLAN Wiki - YUV](https://wiki.videolan.org/YUV)

### Camera Pipeline与ISP
- [Qualcomm Spectra ISP技术文档](https://www.qualcomm.com/)
- [Samsung ISOCELL传感器白皮书](https://semiconductor.samsung.com/image-sensor/)
- [Sony IMX传感器系列规格书](https://www.sony-semicon.com/en/products/is/mobile/)
- [Google Camera HAL3 Documentation](https://source.android.com/docs/core/camera)
- [ARM Mali ISP Architecture Guide](https://developer.arm.com/)
- [Image Engineering - 图像质量测试标准](https://www.image-engineering.de/)

---

*本文档由AI助手基于用户提供的参考资料整理创作，遵循知识共享原则。*

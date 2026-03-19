# RAW到YUV转换管线详细解析

> 完整ISP流程：从传感器原始数据到视频编码就绪

---

## 目录

1. [ISP管线概览](#1-isp管线概览)
2. [RAW域处理阶段](#2-raw域处理阶段)
3. [RGB域处理阶段](#3-rgb域处理阶段)
4. [YUV域处理阶段](#4-yuv域处理阶段)
5. [各阶段色彩空间转换](#5-各阶段色彩空间转换)
6. [质量与性能权衡](#6-质量与性能权衡)
7. [典型ISP架构对比](#7-典型isp架构对比)

---

## 1. ISP管线概览

### 1.1 什么是ISP

**ISP（Image Signal Processor，图像信号处理器）**是将传感器RAW数据转换为可用图像的专用硬件/软件系统。

#### ISP在影像链路中的位置

```
完整影像处理链路：

光学镜头
    ↓
CMOS传感器 → RAW数据（12-16bit，单通道）
    ↓
┌─────────────────────────────────────────┐
│              ISP处理                     │
│  RAW → RGB线性 → RGB非线性 → YUV 4:2:0 │
└─────────────────────────────────────────┘
    ↓
视频编码器（H.264/HEVC/AV1）
    ↓
存储/传输
    ↓
显示设备
```

### 1.2 ISP处理流程总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           完整ISP管线                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │   RAW    │ →  │  Black   │ →  │  Linear  │ →  │  White   │              │
│  │  Input   │    │  Level   │    │ ization  │    │ Balance  │              │
│  │(12-16bit)│    │  Correct │    │          │    │          │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│       ↓                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Lens    │ →  │Demosaic │ →  │   CCM    │ →  │  Gamma   │              │
│  │ Shading │    │          │    │          │    │  Correct │              │
│  │ (LSC)   │    │(去马赛克)│    │色彩校正  │    │          │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│       ↓                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Tone    │ →  │  RGB→YUV │ →  │ Chroma   │ →  │  Edge    │              │
│  │  Mapping │    │  Convert │    │Subsample │    │ Enhance  │              │
│  │ (HDR)   │    │          │    │ (4:2:0)  │    │          │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│       ↓                                                                 │
│  ┌──────────┐    ┌──────────┐                                              │
│  │  Noise   │ →  │  YUV     │                                              │
│  │  Reduce  │    │  Output  │                                              │
│  │          │    │(8-10bit) │                                              │
│  └──────────┘    └──────────┘                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 位深变化

| 阶段 | 位深 | 说明 |
|------|------|------|
| RAW输入 | 12-16bit | 传感器原生位深 |
| 线性处理 | 12-16bit | 保持精度 |
| Demosaic | 12-16bit | 三通道线性RGB |
| Gamma后 | 8-10bit | 非线性压缩 |
| YUV输出 | 8-10bit | 编码器输入 |

---

## 2. RAW域处理阶段

### 2.1 黑电平校正（Black Level Correction）

#### 目的

传感器在无光照时仍有输出（暗电流），需要扣除黑电平以恢复真实信号。

#### 数学公式

$$
\text{Linear}_{out} = \frac{\text{RAW} - \text{Black Level}}{\text{White Level} - \text{Black Level}}
$$

#### 实现

```python
def black_level_correction(raw, black_level, white_level):
    """
    黑电平校正
    
    Args:
        raw: 输入RAW数据（12-14bit）
        black_level: 黑电平值（通常256@14bit或64@12bit）
        white_level: 白电平值（通常16383@14bit或4095@12bit）
    """
    # 扣除黑电平
    linear = raw.astype(np.float32) - black_level
    
    # 归一化到[0, 1]
    linear = linear / (white_level - black_level)
    
    # 裁剪负值（噪声可能导致）
    linear = np.maximum(linear, 0)
    
    return linear
```

### 2.2 线性化（Linearization）

#### 目的

某些传感器输出非线性响应，需要进行线性化校正。

#### LUT方法

```python
def linearize_with_lut(raw, lut):
    """
    使用查找表进行线性化
    
    Args:
        raw: 输入RAW数据
        lut: 线性化查找表
    """
    # 应用LUT
    linear = lut[raw]
    return linear
```

### 2.3 镜头阴影校正（Lens Shading Correction, LSC）

#### 问题描述

镜头边缘的光强衰减（渐晕）和颜色偏移：

```
光强分布：

      暗
  暗  亮  暗
      暗

原因：
1. 光学渐晕：镜头边缘光线角度大，透过率低
2. 几何渐晕：光线被镜筒遮挡
3. 像素响应：边缘像素感光角度不同
```

#### 校正方法

```python
def lens_shading_correction(raw, gain_table):
    """
    镜头阴影校正
    
    Args:
        raw: 输入RAW数据
        gain_table: 增益表（与RAW同尺寸，或下采样）
    """
    if gain_table.shape != raw.shape:
        # 上采样增益表
        gain_table = cv2.resize(gain_table, (raw.shape[1], raw.shape[0]), 
                                interpolation=cv2.INTER_LINEAR)
    
    # 应用增益
    corrected = raw * gain_table
    
    return corrected
```

#### 增益表标定

```
标定流程：

1. 拍摄均匀光源（积分球）
2. 找到中心区域的平均亮度
3. 计算每个像素需要的增益：
   gain[i,j] = center_brightness / brightness[i,j]
4. 存储增益表（可压缩存储）
```

### 2.4 坏点校正（Dead Pixel Correction, DPC）

#### 问题描述

传感器可能存在坏点（始终亮或始终暗的像素）。

#### 检测与校正

```python
def dead_pixel_correction(raw, threshold=50):
    """
    坏点校正（基于邻域中值）
    """
    height, width = raw.shape
    corrected = raw.copy()
    
    for y in range(1, height-1):
        for x in range(1, width-1):
            # 获取同颜色邻域
            neighbors = get_same_color_neighbors(raw, x, y)
            
            median = np.median(neighbors)
            current = raw[y, x]
            
            # 检测坏点
            if abs(current - median) > threshold:
                corrected[y, x] = median
    
    return corrected
```

---

## 3. RGB域处理阶段

### 3.1 Demosaic（去马赛克）

详见 [RAW域详细解析](./RAW域_详细解析.md) 第3节。

```
输入: 单通道Bayer RAW
输出: 三通道线性RGB（12-16bit）

关键算法：
- 双线性插值（快速，质量一般）
- 边缘感知（平衡）
- 深度学习（质量最好）
```

### 3.2 白平衡（White Balance）

#### 处理时机

通常在Demosaic之后立即进行，在线性空间操作。

```python
def apply_white_balance(rgb, gains):
    """
    应用白平衡增益
    
    Args:
        rgb: 线性RGB图像
        gains: [R_gain, G_gain, B_gain]
    """
    balanced = rgb.copy()
    balanced[:,:,0] *= gains[0]  # R
    balanced[:,:,1] *= gains[1]  # G
    balanced[:,:,2] *= gains[2]  # B
    
    return balanced
```

### 3.3 色彩校正矩阵（CCM）

#### 目的

将传感器RGB转换到标准色彩空间（如sRGB、Rec.709）。

```python
def apply_ccm(rgb, ccm):
    """
    应用色彩校正矩阵
    
    Args:
        rgb: 线性RGB图像（H×W×3）
        ccm: 3×3色彩校正矩阵
    """
    # 重塑为像素列表
    pixels = rgb.reshape(-1, 3)
    
    # 矩阵乘法
    corrected = np.dot(pixels, ccm.T)
    
    # 重塑回图像
    return corrected.reshape(rgb.shape)
```

#### 典型CCM

```
sRGB CCM示例：

┌                    ┐
│  1.20  -0.10  -0.10 │
│ -0.10   1.15  -0.05 │
│  0.00  -0.15   1.15 │
└                    ┘

约束：
- 每行之和 ≈ 1（保持中性灰）
- 对角线 > 0（保持通道方向）
```

### 3.4 Gamma校正

#### 目的

将线性光信号转换为非线性信号，匹配显示设备特性并优化编码效率。

#### sRGB Gamma

$$
V = \begin{cases}
12.92 \cdot L & L \leq 0.0031308 \\
1.055 \cdot L^{1/2.4} - 0.055 & L > 0.0031308
\end{cases}
$$

```python
def srgb_gamma_encode(linear):
    """
    sRGB Gamma编码
    """
    nonlinear = np.where(
        linear <= 0.0031308,
        12.92 * linear,
        1.055 * np.power(linear, 1/2.4) - 0.055
    )
    return np.clip(nonlinear, 0, 1)
```

### 3.5 色调映射（HDR场景）

#### 处理流程

```
HDR场景处理：

线性HDR RGB（16bit+）
    ↓
色调映射算法（如Reinhard、ACES）
    ↓
非线性SDR/HDR RGB（10-12bit）
    ↓
PQ/HLG编码（HDR输出）
    ↓
或sRGB Gamma（SDR输出）
```

详见 [色调映射算法_详细解析.md](./色调映射算法_详细解析.md)

---

## 4. YUV域处理阶段

### 4.1 RGB到YUV转换

#### 转换矩阵选择

| 应用场景 | 推荐标准 | 说明 |
|---------|---------|------|
| SD内容 | BT.601 | 历史兼容 |
| HD内容 | BT.709 | 主流标准 |
| UHD/HDR | BT.2020 | 广色域支持 |

```python
def rgb_to_yuv_bt709(rgb):
    """
    RGB转YCbCr（BT.709）
    """
    matrix = np.array([
        [0.2126, 0.7152, 0.0722],
        [-0.1146, -0.3854, 0.5000],
        [0.5000, -0.4542, -0.0458]
    ])
    
    yuv = np.dot(rgb, matrix.T)
    yuv[:,:,0] += 0           # Y: [0, 1]
    yuv[:,:,1] += 0.5         # Cb: [0, 1] → [-0.5, 0.5]
    yuv[:,:,2] += 0.5         # Cr: [0, 1] → [-0.5, 0.5]
    
    return np.clip(yuv, 0, 1)
```

### 4.2 色度子采样

#### 4:2:0实现

```python
def chroma_subsample_420(yuv):
    """
    YUV 4:4:4 转 4:2:0
    """
    y = yuv[:,:,0]
    cb = yuv[:,:,1]
    cr = yuv[:,:,2]
    
    height, width = y.shape
    
    # 2×2平均下采样Cb/Cr
    cb_420 = np.zeros((height//2, width//2), dtype=cb.dtype)
    cr_420 = np.zeros((height//2, width//2), dtype=cr.dtype)
    
    for y_idx in range(0, height, 2):
        for x_idx in range(0, width, 2):
            cb_420[y_idx//2, x_idx//2] = np.mean([
                cb[y_idx, x_idx],
                cb[y_idx, x_idx+1],
                cb[y_idx+1, x_idx],
                cb[y_idx+1, x_idx+1]
            ])
            cr_420[y_idx//2, x_idx//2] = np.mean([
                cr[y_idx, x_idx],
                cr[y_idx, x_idx+1],
                cr[y_idx+1, x_idx],
                cr[y_idx+1, x_idx+1]
            ])
    
    return y, cb_420, cr_420
```

### 4.3 边缘增强

#### 目的

补偿Demosaic和色度子采样导致的细节损失。

```python
def edge_enhancement(y_channel, strength=1.0):
    """
    亮度通道边缘增强（Unsharp Mask）
    """
    # 高斯模糊
    blurred = cv2.GaussianBlur(y_channel, (5, 5), 1.0)
    
    # 计算细节
    detail = y_channel - blurred
    
    # 增强
    enhanced = y_channel + strength * detail
    
    return np.clip(enhanced, 0, 1)
```

### 4.4 降噪

#### 时域降噪（视频）

```python
def temporal_denoise(current_frame, previous_frame, motion_threshold=0.05):
    """
    简单时域降噪
    """
    # 计算帧间差异
    diff = np.abs(current_frame - previous_frame)
    
    # 创建混合掩码
    blend_mask = diff < motion_threshold
    
    # 混合（静态区域使用历史帧，运动区域使用当前帧）
    denoised = np.where(blend_mask, 
                       0.7 * previous_frame + 0.3 * current_frame,
                       current_frame)
    
    return denoised
```

---

## 5. 各阶段色彩空间转换

### 5.1 转换链路总结

```
完整色彩空间转换链路：

1. RAW（传感器原生）
   ↓ 黑电平校正 + 线性化
   
2. 线性RAW（归一化）
   ↓ Demosaic
   
3. 线性RGB（传感器RGB）
   ↓ 白平衡 + CCM
   
4. 线性RGB（标准空间，如sRGB线性）
   ↓ Gamma校正
   
5. 非线性RGB（sRGB/Rec.709）
   ↓ RGB→YUV矩阵
   
6. YUV 4:4:4
   ↓ 色度子采样
   
7. YUV 4:2:0（最终输出）
```

### 5.2 关键转换节点详解

#### 节点1：RAW → 线性RGB（Demosaic）

```
输入: 单通道Bayer RAW（12-14bit）
输出: 三通道线性RGB（12-14bit）

关键考虑：
- 保持线性（光与电的线性关系）
- 避免引入伪影
- 保留高频细节
```

#### 节点2：线性RGB → 非线性RGB（Gamma）

```
输入: 线性RGB（12-14bit）
输出: 非线性RGB（8-10bit）

关键考虑：
- 选择正确的传递函数（sRGB/Rec.709/PQ/HLG）
- 位深截断的量化误差
- HDR场景的色调映射
```

#### 节点3：RGB → YUV（色彩空间转换）

```
输入: 非线性RGB（8-10bit）
输出: YUV 4:4:4（8-10bit）

关键考虑：
- 选择正确的转换矩阵（BT.601/709/2020）
- 范围映射（Full vs Limited）
- 量化精度
```

#### 节点4：YUV 4:4:4 → YUV 4:2:0（子采样）

```
输入: YUV 4:4:4
输出: YUV 4:2:0

关键考虑：
- 抗混叠滤波
- 相位对齐
- 上采样算法（解码端）
```

### 5.3 转换误差累积

```
误差来源分析：

1. 量化误差
   - 每bit转换引入±0.5 LSB误差
   - 多次转换累积

2. 矩阵运算误差
   - 浮点转定点
   - 系数精度限制

3. 子采样误差
   - 高频色度信息丢失
   - 重建误差

优化策略：
- 尽量减少转换步骤
- 使用更高位深中间表示
- 优化矩阵系数精度
```

---

## 6. 质量与性能权衡

### 6.1 算法复杂度vs质量

| 处理阶段 | 快速算法 | 质量算法 | 质量差异 |
|---------|---------|---------|---------|
| Demosaic | 双线性 | 深度学习 | 5-10dB |
| 降噪 | 空域均值 | BM3D | 3-5dB |
| 色调映射 | 简单压缩 | 局部自适应 | 主观显著 |
| 子采样 | 最近邻 | 双三次+滤波 | 1-2dB |

### 6.2 移动端优化策略

```
移动端ISP优化：

1. 算法简化
   - Demosaic：双线性 → 边缘感知（跳过ML）
   - 降噪：时域替代空域复杂算法
   - 色调映射：全局替代局部

2. 硬件加速
   - 专用ISP芯片
   - GPU Compute Shader
   - NPU/DSP

3. 流水线优化
   - 零拷贝内存
   - 异步处理
   - 分块处理（Tile-based）

4. 精度权衡
   - RAW 10bit替代14bit
   - 定点数替代浮点
   - 查找表替代实时计算
```

### 6.3 专业级优化策略

```
专业相机/电影机ISP：

1. 质量优先
   - 复杂Demosaic算法
   - 多帧合成降噪
   - 高级色调映射

2. 灵活性
   - 可调整的CCM
   - 自定义Gamma曲线
   - Log输出模式

3. 后期友好
   - 保留线性RAW选项
   - 宽色域输出（Rec.2020）
   - 高位深（12bit+）
```

---

## 7. 典型ISP架构对比

### 7.1 手机ISP

#### 特点

```
高通Spectra / 苹果ISP / 三星ISP：

- 集成在SoC中
- 实时处理（30-120fps）
- 多摄协同
- AI增强（场景识别、美颜）

典型管线：
RAW → 黑电平 → LSC → DPC → Demosaic → WB → CCM → Gamma → YUV → 编码
（硬件固化，部分可配置）
```

### 7.2 专业相机ISP

#### 特点

```
佳能DIGIC / 索尼BIONZ：

- 更高位深处理（14bit+）
- 复杂降噪算法
- 多种输出模式（RAW/JPEG/同时）

典型管线：
RAW → 预处理 → Demosaic → 多帧合成 → 高级降噪 → 色彩科学 → 输出
（更多可配置参数）
```

### 7.3 软件ISP

#### 特点

```
Adobe Camera Raw / dcraw / libraw：

- 灵活性最高
- 算法可更新
- 计算资源充足

典型管线：
RAW文件 → 解码 → 可配置处理链 → 多种输出格式
（完全可编程）
```

### 7.4 架构对比表

| 特性 | 手机ISP | 专业相机ISP | 软件ISP |
|------|--------|------------|--------|
| **处理速度** | 实时 | 准实时 | 离线 |
| **位深** | 10-12bit | 14bit+ | 16bit+ |
| **算法复杂度** | 中等 | 高 | 最高 |
| **灵活性** | 低 | 中 | 高 |
| **功耗** | 低 | 中 | 高 |
| **成本** | 集成成本低 | 中等 | 软件免费 |

---

## 总结

RAW到YUV的ISP管线是数字成像的核心，理解其流程对于：

1. **图像质量优化**：识别各阶段的关键参数
2. **算法开发**：在正确的阶段插入处理
3. **性能调优**：平衡质量与速度
4. **故障排查**：定位问题来源

核心要点：
- **线性vs非线性**：RAW和早期RGB是线性的，Gamma后是非线性的
- **色彩空间一致性**：每次转换都要明确源和目标空间
- **位深管理**：保持足够精度避免量化误差
- **硬件特性**：了解目标平台的处理能力

> 🔗 返回：[RAW_YUV域深度解析](./RAW_YUV域深度解析.md)

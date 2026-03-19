# YUV域详细解析

> 亮度-色度分离：数字视频与图像压缩的核心

---

## 目录

1. [YUV色彩空间基础](#1-yuv色彩空间基础)
2. [RGB与YUV转换](#2-rgb与yuv转换)
3. [色度子采样](#3-色度子采样)
4. [色彩范围与量化](#4-色彩范围与量化)
5. [标准演进对比](#5-标准演进对比)
6. [应用场景详解](#6-应用场景详解)
7. [工程实现要点](#7-工程实现要点)

---

## 1. YUV色彩空间基础

### 1.1 历史背景

YUV色彩空间起源于**模拟电视时代**的彩色电视广播兼容性问题：

```
历史演进：

1950s: 黑白电视普及
    ↓
需要向后兼容的彩色电视系统
    ↓
NTSC (美国) 采用 YIQ
PAL/SECAM (欧洲) 采用 YUV
    ↓
数字时代：YUV → YCbCr
```

#### 术语辨析

| 术语 | 定义 | 信号类型 | 应用场景 |
|------|------|---------|---------|
| **YUV** | 模拟色差信号 | 模拟 | 传统PAL/NTSC广播 |
| **YCbCr** | 数字色差信号 | 数字 | 数字视频、JPEG、MPEG |
| **YPbPr** | 模拟分量视频 | 模拟 | 模拟高清接口（已淘汰） |

> **注意**：现代语境中，"YUV"通常指代YCbCr数字格式

### 1.2 亮度-色度分离原理

#### 人眼视觉特性

YUV设计的核心依据是**人眼视觉系统（HVS）的特性**：

```
人眼视觉分辨率：

亮度通道（Y）：
- 高空间分辨率
- 高敏感度
- 对细节敏感

色度通道（U/V或Cb/Cr）：
- 低空间分辨率
- 低敏感度
- 对细节不敏感

生理原因：
- 视网膜上视杆细胞（亮度）数量 >> 视锥细胞（色度）
- 大脑皮层中亮度处理区域更大
```

#### 分离优势

| 优势 | 说明 | 效果 |
|------|------|------|
| **压缩效率** | 色度子采样减少数据量 | 4:2:0节省50%带宽 |
| **兼容性** | 黑白设备只解码Y | 向后兼容 |
| **处理效率** | 亮度处理可独立进行 | 简化算法 |
| **噪声鲁棒** | 色度噪声较不敏感 | 视觉质量更好 |

### 1.3 YUV分量定义

#### 数学定义

$$
\begin{aligned}
Y &= \text{亮度（Luma）} \\
U &= B - Y \quad \text{（蓝色色差）} \\
V &= R - Y \quad \text{（红色色差）}
\end{aligned}
$$

Cb/Cr是U/V的数字量化版本：

$$
\begin{aligned}
Cb &= \frac{B - Y}{2} \cdot \frac{255}{127} + 128 \\
Cr &= \frac{R - Y}{2} \cdot \frac{255}{127} + 128
\end{aligned}
$$

#### 几何解释

```
RGB立方体中的YUV：

       B
       │
       │    Y轴：沿(1,1,1)方向
       │    （亮度方向）
       │
       └────────G
      /
     /
    R

U/V平面：垂直于Y轴的平面
- 该平面上所有点的Y值相同
- U/V表示颜色在该平面上的位置
```

---

## 2. RGB与YUV转换

### 2.1 转换矩阵推导

#### 亮度方程

Y是RGB的加权平均，权重基于人眼对三原色的敏感度：

$$
Y = w_r \cdot R + w_g \cdot G + w_b \cdot B
$$

其中 $w_r + w_g + w_b = 1$

#### 色差方程

$$
\begin{aligned}
U &= B - Y = B - (w_r R + w_g G + w_b B) \\
  &= -w_r R - w_g G + (1-w_b) B \\
  &= -w_r R - w_g G + (w_r + w_g) B \\
  \\
V &= R - Y = R - (w_r R + w_g G + w_b B) \\
  &= (1-w_r) R - w_g G - w_b B \\
  &= (w_g + w_b) R - w_g G - w_b B
\end{aligned}
$$

### 2.2 BT.601标准（SDTV）

#### 权重系数

基于早期CRT荧光粉特性：

$$
w_r = 0.299, \quad w_g = 0.587, \quad w_b = 0.114
$$

#### 正向转换（RGB → YUV）

$$
\begin{bmatrix} Y \\ Cb \\ Cr \end{bmatrix} =
\begin{bmatrix} 0.299 & 0.587 & 0.114 \\ -0.169 & -0.331 & 0.500 \\ 0.500 & -0.419 & -0.081 \end{bmatrix} \cdot
\begin{bmatrix} R \\ G \\ B \end{bmatrix} +
\begin{bmatrix} 0 \\ 128 \\ 128 \end{bmatrix}
$$

#### 逆向转换（YUV → RGB）

$$
\begin{bmatrix} R \\ G \\ B \end{bmatrix} =
\begin{bmatrix} 1.000 & 0.000 & 1.403 \\ 1.000 & -0.344 & -0.714 \\ 1.000 & 1.773 & 0.000 \end{bmatrix} \cdot
\begin{bmatrix} Y - 16 \\ Cb - 128 \\ Cr - 128 \end{bmatrix}
$$

### 2.3 BT.709标准（HDTV）

#### 权重系数

基于现代显示器特性：

$$
w_r = 0.2126, \quad w_g = 0.7152, \quad w_b = 0.0722
$$

#### 正向转换

$$
\begin{bmatrix} Y \\ Cb \\ Cr \end{bmatrix} =
\begin{bmatrix} 0.2126 & 0.7152 & 0.0722 \\ -0.1146 & -0.3854 & 0.5000 \\ 0.5000 & -0.4542 & -0.0458 \end{bmatrix} \cdot
\begin{bmatrix} R \\ G \\ B \end{bmatrix} +
\begin{bmatrix} 0 \\ 128 \\ 128 \end{bmatrix}
$$

#### 逆向转换

$$
\begin{bmatrix} R \\ G \\ B \end{bmatrix} =
\begin{bmatrix} 1.0000 & 0.0000 & 1.5748 \\ 1.0000 & -0.1873 & -0.4681 \\ 1.0000 & 1.8556 & 0.0000 \end{bmatrix} \cdot
\begin{bmatrix} Y - 16 \\ Cb - 128 \\ Cr - 128 \end{bmatrix}
$$

### 2.4 BT.2020标准（UHDTV/HDR）

#### 权重系数

针对广色域显示：

$$
w_r = 0.2627, \quad w_g = 0.6780, \quad w_b = 0.0593
$$

#### 正向转换

$$
\begin{bmatrix} Y \\ Cb \\ Cr \end{bmatrix} =
\begin{bmatrix} 0.2627 & 0.6780 & 0.0593 \\ -0.1396 & -0.3604 & 0.5000 \\ 0.5000 & -0.4598 & -0.0402 \end{bmatrix} \cdot
\begin{bmatrix} R \\ G \\ B \end{bmatrix} +
\begin{bmatrix} 0 \\ 128 \\ 128 \end{bmatrix}
$$

### 2.5 转换矩阵对比

| 标准 | $w_r$ | $w_g$ | $w_b$ | 应用场景 |
|------|-------|-------|-------|---------|
| **BT.601** | 0.299 | 0.587 | 0.114 | SD视频（720×576/480） |
| **BT.709** | 0.2126 | 0.7152 | 0.0722 | HD视频（1920×1080） |
| **BT.2020** | 0.2627 | 0.6780 | 0.0593 | UHD/HDR（4K/8K） |
| **SMPTE 240M** | 0.212 | 0.701 | 0.087 | 早期HDTV（已废弃） |

#### 权重差异的影响

```
不同标准的Y计算差异：

场景：纯红色 (R=1, G=0, B=0)

BT.601: Y = 0.299
BT.709: Y = 0.2126
BT.2020: Y = 0.2627

结论：
- 相同RGB值在不同标准下亮度不同
- 跨标准转换时需要重新计算Y
- 混用标准会导致亮度/色彩偏移
```

### 2.6 实现代码示例

#### Python实现（BT.709）

```python
import numpy as np

def rgb_to_ycbcr_bt709(rgb):
    """
    RGB [0,255] 转 YCbCr [0,255]
    """
    # 转换矩阵
    matrix = np.array([
        [0.2126, 0.7152, 0.0722],
        [-0.1146, -0.3854, 0.5000],
        [0.5000, -0.4542, -0.0458]
    ])
    
    # 应用转换
    yuv = np.dot(rgb, matrix.T)
    
    # 添加偏移
    yuv[:,:,0] += 0          # Y: [0, 255]
    yuv[:,:,1] += 128        # Cb: [0, 255]
    yuv[:,:,2] += 128        # Cr: [0, 255]
    
    return np.clip(yuv, 0, 255).astype(np.uint8)

def ycbcr_to_rgb_bt709(ycbcr):
    """
    YCbCr [0,255] 转 RGB [0,255]
    """
    # 减去偏移
    yuv = ycbcr.astype(np.float32)
    yuv[:,:,0] -= 16         # Y: 先映射到[16,235]
    yuv[:,:,1] -= 128        # Cb
    yuv[:,:,2] -= 128        # Cr
    
    # 逆向矩阵
    matrix = np.array([
        [1.0000, 0.0000, 1.5748],
        [1.0000, -0.1873, -0.4681],
        [1.0000, 1.8556, 0.0000]
    ])
    
    # 应用转换
    rgb = np.dot(yuv, matrix.T)
    
    return np.clip(rgb, 0, 255).astype(np.uint8)
```

#### SIMD优化（C++伪代码）

```cpp
// SSE/AVX优化版本
void RGB_to_YUV_BT709_SSE(const uint8_t* rgb, uint8_t* yuv, int width, int height) {
    const int pixels = width * height;
    
    for (int i = 0; i < pixels; i += 16) {
        // 加载16个像素的RGB数据
        __m128i r = _mm_loadu_si128(...);
        __m128i g = _mm_loadu_si128(...);
        __m128i b = _mm_loadu_si128(...);
        
        // 转换为16bit精度
        __m256i r16 = _mm256_cvtepu8_epi16(r);
        __m256i g16 = _mm256_cvtepu8_epi16(g);
        __m256i b16 = _mm256_cvtepu8_epi16(b);
        
        // 计算 Y = 0.2126*R + 0.7152*G + 0.0722*B
        __m256i y = _mm256_add_epi16(
            _mm256_add_epi16(
                _mm256_mullo_epi16(r16, _mm256_set1_epi16(54)),  // 0.2126 * 256
                _mm256_mullo_epi16(g16, _mm256_set1_epi16(183))  // 0.7152 * 256
            ),
            _mm256_mullo_epi16(b16, _mm256_set1_epi16(18))       // 0.0722 * 256
        );
        y = _mm256_srli_epi16(y, 8);  // 除以256
        
        // 类似计算Cb, Cr...
        
        // 存储结果
        _mm_storeu_si128((__m128i*)yuv, _mm256_cvtepi16_epi8(y));
    }
}
```

---

## 3. 色度子采样

### 3.1 子采样原理

基于人眼对色度细节不敏感的特性，降低色度通道的分辨率：

```
采样格式命名规则：J:a:b

J: 水平采样参考（通常是4）
a: 第一行色度采样数
b: 第二行色度采样数
```

### 3.2 常见采样格式

#### 4:4:4（无子采样）

```
每个像素都有完整的Y、U、V：

像素:  0    1    2    3
Y:    [Y0] [Y1] [Y2] [Y3]
U:    [U0] [U1] [U2] [U3]
V:    [V0] [V1] [V2] [V3]

数据量: 100%
应用: 电影调色、医学影像、屏幕录制
```

#### 4:2:2（水平1/2采样）

```
色度水平分辨率减半：

像素:  0    1    2    3
Y:    [Y0] [Y1] [Y2] [Y3]
U:    [U0]      [U2]
V:    [V0]      [V2]

U0被像素0和1共享
U2被像素2和3共享

数据量: 67% (Y + 0.5U + 0.5V)
应用: 广播级视频、ProRes
```

#### 4:2:0（水平和垂直1/2采样）

```
色度水平和垂直分辨率都减半：

行0:
Y:    [Y0] [Y1] [Y2] [Y3]
U:    [U0]      [U2]
V:    [V0]      [V2]

行1:
Y:    [Y4] [Y5] [Y6] [Y7]
U:    (共享行0的U)
V:    (共享行0的V)

U0被像素(0,0), (1,0), (0,1), (1,1)共享

数据量: 50% (Y + 0.25U + 0.25V)
应用: H.264/HEVC/AV1、JPEG、流媒体
```

#### 4:1:1（水平1/4采样）

```
色度水平分辨率为1/4：

像素:  0    1    2    3
Y:    [Y0] [Y1] [Y2] [Y3]
U:    [U0]
V:    [V0]

数据量: 50%
应用: 早期DV格式（已较少使用）
```

#### 4:0:0（仅亮度）

```
只有Y通道，无色彩信息：

像素:  0    1    2    3
Y:    [Y0] [Y1] [Y2] [Y3]
U:    (无)
V:    (无)

数据量: 33%
应用: 灰度图像、预览缩略图
```

### 3.3 子采样算法实现

#### 下采样（4:4:4 → 4:2:0）

```python
def chroma_downsample_444_to_420(yuv_444):
    """
    4:4:4 下采样到 4:2:0
    """
    height, width = yuv_444.shape[:2]
    
    # Y保持原样
    y = yuv_444[:,:,0]
    
    # Cb/Cr 2×2平均下采样
    cb_full = yuv_444[:,:,1]
    cr_full = yuv_444[:,:,2]
    
    # 方法1：简单平均
    cb_420 = (cb_full[0::2, 0::2] + cb_full[0::2, 1::2] + 
              cb_full[1::2, 0::2] + cb_full[1::2, 1::2]) / 4
    cr_420 = (cr_full[0::2, 0::2] + cr_full[0::2, 1::2] + 
              cr_full[1::2, 0::2] + cr_full[1::2, 1::2]) / 4
    
    # 方法2：带抗混叠滤波（推荐）
    # 先应用低通滤波器，再下采样
    kernel = np.array([[1, 2, 1],
                       [2, 4, 2],
                       [1, 2, 1]]) / 16
    cb_filtered = convolve2d(cb_full, kernel, mode='same')
    cr_filtered = convolve2d(cr_full, kernel, mode='same')
    cb_420 = cb_filtered[0::2, 0::2]
    cr_420 = cr_filtered[0::2, 0::2]
    
    return y, cb_420, cr_420
```

#### 上采样（4:2:0 → 4:4:4）

```python
def chroma_upsample_420_to_444(y, cb_420, cr_420):
    """
    4:2:0 上采样到 4:4:4
    """
    height, width = y.shape
    
    # 方法1：最近邻（最快，质量差）
    cb_444 = np.repeat(np.repeat(cb_420, 2, axis=0), 2, axis=1)
    cr_444 = np.repeat(np.repeat(cr_420, 2, axis=0), 2, axis=1)
    
    # 方法2：双线性插值（平衡）
    from scipy.ndimage import zoom
    cb_444 = zoom(cb_420, 2, order=1)
    cr_444 = zoom(cr_420, 2, order=1)
    
    # 方法3：双三次插值（质量最好，最慢）
    cb_444 = zoom(cb_420, 2, order=3)
    cr_444 = zoom(cr_420, 2, order=3)
    
    # 裁剪到目标尺寸（处理奇数尺寸）
    cb_444 = cb_444[:height, :width]
    cr_444 = cr_444[:height, :width]
    
    return np.stack([y, cb_444, cr_444], axis=2)
```

### 3.4 子采样质量评估

#### 客观指标

| 采样格式 | CPSNR (dB) | SSIM | 文件大小 |
|---------|-----------|------|---------|
| 4:4:4 | ∞ | 1.0 | 100% |
| 4:2:2 | ~45 | ~0.98 | 67% |
| 4:2:0 | ~40 | ~0.95 | 50% |
| 4:1:1 | ~35 | ~0.90 | 50% |

#### 主观评估

```
视觉质量测试场景：

1. 红蓝细条纹（最难场景）
   4:2:0会出现明显的色彩渗透

2. 肤色渐变
   4:2:0通常可接受

3. 文字边缘
   4:2:0可能导致色彩边缘

4. 自然风景
   4:2:0几乎无感知差异
```

---

## 4. 色彩范围与量化

### 4.1 范围定义

#### Full Range（全范围）

```
Y:  [0, 255]（8bit）或 [0, 1023]（10bit）
Cb: [0, 255] 或 [0, 1023]
Cr: [0, 255] 或 [0, 1023]

应用：
- 计算机图形
- JPEG图像
- 部分视频编码
```

#### Limited Range（有限范围）

```
Y:  [16, 235]（8bit）或 [64, 940]（10bit）
Cb: [16, 240] 或 [64, 960]
Cr: [16, 240] 或 [64, 960]

保留头部和底部空间用于：
- 同步信号
- 过曝/欠曝保护

应用：
- 广播视频
- 大多数H.264/HEVC内容
```

### 4.2 范围转换

#### Full → Limited

```python
def full_to_limited(yuv_full, bit_depth=8):
    """
    全范围转有限范围
    """
    if bit_depth == 8:
        yuv_limited = yuv_full.copy()
        yuv_limited[:,:,0] = yuv_full[:,:,0] * 219/255 + 16   # Y
        yuv_limited[:,:,1] = yuv_full[:,:,1] * 224/255 + 16   # Cb
        yuv_limited[:,:,2] = yuv_full[:,:,2] * 224/255 + 16   # Cr
    else:  # 10bit
        yuv_limited = yuv_full.copy()
        yuv_limited[:,:,0] = yuv_full[:,:,0] * 876/1023 + 64
        yuv_limited[:,:,1] = yuv_full[:,:,1] * 896/1023 + 64
        yuv_limited[:,:,2] = yuv_full[:,:,2] * 896/1023 + 64
    
    return yuv_limited.astype(yuv_full.dtype)
```

#### Limited → Full

```python
def limited_to_full(yuv_limited, bit_depth=8):
    """
    有限范围转全范围
    """
    if bit_depth == 8:
        yuv_full = yuv_limited.copy()
        yuv_full[:,:,0] = (yuv_limited[:,:,0] - 16) * 255/219   # Y
        yuv_full[:,:,1] = (yuv_limited[:,:,1] - 16) * 255/224   # Cb
        yuv_full[:,:,2] = (yuv_limited[:,:,2] - 16) * 255/224   # Cr
    else:  # 10bit
        yuv_full = yuv_limited.copy()
        yuv_full[:,:,0] = (yuv_limited[:,:,0] - 64) * 1023/876
        yuv_full[:,:,1] = (yuv_limited[:,:,1] - 64) * 1023/896
        yuv_full[:,:,2] = (yuv_limited[:,:,2] - 64) * 1023/896
    
    return np.clip(yuv_full, 0, 2**bit_depth - 1).astype(yuv_limited.dtype)
```

### 4.3 范围混淆问题

```
常见问题：范围不匹配导致的色彩错误

场景：
播放器认为视频是Limited Range
但实际编码是Full Range

结果：
- 暗部细节丢失（被压缩到16以下）
- 亮部过曝（被压缩到235以上）
- 整体对比度降低

解决方案：
- 元数据标记（VUI信息）
- 播放器自动检测
- 手动设置
```

---

## 5. 标准演进对比

### 5.1 BT.601 vs BT.709 vs BT.2020

| 特性 | BT.601 | BT.709 | BT.2020 |
|------|--------|--------|---------|
| **发布年份** | 1982 | 1993 | 2012 |
| **分辨率** | SD (720×576/480) | HD (1920×1080) | UHD (3840×2160+) |
| **色域** | Rec. 601 | Rec. 709 | Rec. 2020 |
| **动态范围** | SDR | SDR | SDR/HDR |
| **位深** | 8bit | 8-10bit | 10-12bit |
| **$w_r$** | 0.299 | 0.2126 | 0.2627 |
| **$w_g$** | 0.587 | 0.7152 | 0.6780 |
| **$w_b$** | 0.114 | 0.0722 | 0.0593 |

### 5.2 标准选择指南

```
应用场景 → 推荐标准：

SD内容（DVD、老视频）
    ↓
BT.601

HD内容（蓝光、HDTV广播）
    ↓
BT.709

4K/HDR内容（UHD蓝光、流媒体）
    ↓
BT.2020

注意：
- 错误选择会导致色彩偏移
- 大多数现代内容使用BT.709
- HDR内容必须使用BT.2020
```

### 5.3 传递函数差异

| 标准 | 传递函数 | 说明 |
|------|---------|------|
| BT.601 | Gamma 2.2 | 早期模拟电视 |
| BT.709 | BT.709 OETF | 分段函数 |
| BT.2020 | PQ (ST 2084) | HDR感知量化 |
| BT.2020 | HLG | 混合对数伽马 |

---

## 6. 应用场景详解

### 6.1 视频编码

#### H.264/AVC

```
H.264中的YUV处理：

输入: YUV 4:2:0 8bit
    ↓
宏块划分（16×16）
    ↓
帧内/帧间预测
    ↓
DCT变换（4×4或8×8）
    ↓
量化
    ↓
熵编码（CAVLC/CABAC）
    ↓
输出: H.264码流

特点：
- 仅支持4:2:0（Baseline/Main）
- High Profile支持4:2:2/4:4:4
- 8bit为主，Hi10P支持10bit
```

#### H.265/HEVC

```
HEVC中的YUV处理：

改进：
- 支持4:2:0、4:2:2、4:4:4
- 支持8bit、10bit、12bit
- 更大的CTU（64×64）
- 更高效的色度预测

Main Profile: 4:2:0 8bit
Main 10 Profile: 4:2:0 10bit
Main 4:2:2 10 Profile: 4:2:2 10bit
Main 4:4:4 12 Profile: 4:4:4 12bit
```

#### AV1

```
AV1中的YUV处理：

特点：
- 仅支持4:2:0（当前版本）
- 支持8bit、10bit
- 专业版支持4:4:4（计划中）
- 更高效的色度预测模式

优势：
- 相同质量下比HEVC节省30%码率
- 免版税
```

### 6.2 图像压缩

#### JPEG

```
JPEG压缩流程：

RGB图像
    ↓
色彩空间转换（RGB → YCbCr）
    ↓
色度子采样（4:2:0或4:2:2）
    ↓
8×8 DCT变换
    ↓
量化（亮度/色度不同量化表）
    ↓
Zig-Zag扫描
    ↓
霍夫曼编码
    ↓
JPEG文件

关键：
- 使用BT.601矩阵（历史原因）
- 色度量化更激进（人眼不敏感）
```

#### WebP

```
WebP支持两种模式：

有损模式（基于VP8）：
- YUV 4:2:0
- 块预测 + DCT

无损模式：
- 直接压缩RGB
- 或压缩YUV（可选）
```

### 6.3 实时视频处理

#### GPU渲染管线

```
GPU中的YUV处理：

视频解码器
    ↓
NV12/NV21格式（GPU友好）
    ↓
纹理上传
    ↓
YUV → RGB 着色器转换
    ↓
渲染到屏幕

NV12格式：
YYYYYYYY
YYYYYYYY
UVUVUVUV
（Y平面 + 交错UV平面）
```

#### 零拷贝优化

```python
# 零拷贝YUV处理流程

# 1. 解码器直接输出到GPU内存
video_frame = decoder.decode_to_gpu()

# 2. 使用CUDA/OpenCL处理
processed = cuda_process(video_frame)

# 3. 直接渲染，无需CPU回读
render_to_screen(processed)

优势：
- 避免CPU-GPU数据传输
- 降低延迟
- 提高吞吐量
```

### 6.4 电视广播系统

#### 历史演进

```
模拟时代：
NTSC (美国/日本): YIQ
PAL (欧洲/中国): YUV
SECAM (法国/俄罗斯): YDbDr

数字时代：
全部统一为YCbCr
- SD: BT.601
- HD: BT.709
- UHD: BT.2020
```

#### 现代广播链

```
制作端：
4:4:4或4:2:2 10bit
    ↓
传输编码：
4:2:0 8bit（节省带宽）
    ↓
接收端：
上采样到4:2:2显示
```

---

## 7. 工程实现要点

### 7.1 内存布局

#### Planar格式

```
YUV Planar（I420/YV12）：

YYYYYYYY
YYYYYYYY
YYYYYYYY
YYYYYYYY
UUUU
UUUU
VVVV
VVVV

优点：
- 通道分离，便于处理
- 压缩友好

缺点：
- 非交错访问不连续
```

#### Semi-Planar格式

```
NV12/NV21（GPU友好）：

YYYYYYYY
YYYYYYYY
YYYYYYYY
YYYYYYYY
UVUVUVUV
UVUVUVUV

或（NV21）：
VUVUVUVU
VUVUVUVU

优点：
- UV交错，GPU采样高效
- 现代视频标准常用
```

#### Packed格式

```
UYVY（4:2:2 Packed）：
U0 Y0 V0 Y1 U2 Y2 V2 Y3 ...

YUYV/YUY2：
Y0 U0 Y1 V0 Y2 U2 Y3 V2 ...

优点：
- 内存连续
- 适合老设备

缺点：
- 处理复杂
- 现代少用
```

### 7.2 跨平台兼容性

#### 平台差异

| 平台 | 原生格式 | 注意事项 |
|------|---------|---------|
| **Windows** | NV12, YUY2 | DirectShow/MediaFoundation |
| **macOS/iOS** | 420v, 420f | CoreVideo像素格式 |
| **Android** | YUV_420_888 | ImageReader灵活格式 |
| **Linux** | I420, NV12 | V4L2标准 |
| **Web** | I420, NV12 | WebCodecs API |

#### 格式转换工具

```python
import cv2

def convert_yuv_format(yuv_data, src_fmt, dst_fmt, width, height):
    """
    YUV格式转换
    """
    # OpenCV支持多种YUV格式转换
    if src_fmt == 'I420' and dst_fmt == 'NV12':
        y = yuv_data[:width*height].reshape(height, width)
        u = yuv_data[width*height:width*height*5//4].reshape(height//2, width//2)
        v = yuv_data[width*height*5//4:].reshape(height//2, width//2)
        
        # 交错UV
        uv = np.empty((height//2, width), dtype=np.uint8)
        uv[:,0::2] = u
        uv[:,1::2] = v
        
        return np.concatenate([y.flatten(), uv.flatten()])
```

### 7.3 性能优化

#### SIMD优化要点

```cpp
// AVX2优化YUV→RGB转换
void YUV_to_RGB_AVX2(const uint8_t* yuv, uint8_t* rgb, int count) {
    const __m256i y_offset = _mm256_set1_epi16(16);
    const __m256i uv_offset = _mm256_set1_epi16(128);
    
    for (int i = 0; i < count; i += 32) {
        // 加载32个Y值
        __m256i y = _mm256_loadu_si256((__m256i*)(yuv + i));
        
        // 加载16个U和16个V值（4:2:0）
        // 并插值到32个
        __m256i u = load_and_upsample_uv(yuv + count + i/2);
        __m256i v = load_and_upsample_uv(yuv + count + count/4 + i/2);
        
        // 转换为16bit并减去偏移
        y = _mm256_sub_epi16(_mm256_cvtepu8_epi16(y), y_offset);
        u = _mm256_sub_epi16(u, uv_offset);
        v = _mm256_sub_epi16(v, uv_offset);
        
        // 计算R = Y + 1.402*V
        __m256i r = _mm256_add_epi16(y, _mm256_mulhrs_epi16(v, _mm256_set1_epi16(22970)));
        
        // 类似计算G和B...
        
        // 打包并存储
        _mm256_storeu_si256((__m256i*)(rgb + i*3), pack_rgb(r, g, b));
    }
}
```

#### GPU加速

```glsl
// GLSL YUV→RGB着色器
#version 330 core

uniform sampler2D y_texture;
uniform sampler2D uv_texture;

in vec2 tex_coord;
out vec4 frag_color;

void main() {
    float y = texture(y_texture, tex_coord).r;
    vec2 uv = texture(uv_texture, tex_coord).rg;
    
    // 减去偏移
    y = y - 0.0625;  // 16/256
    float u = uv.r - 0.5;
    float v = uv.g - 0.5;
    
    // BT.709矩阵
    float r = y + 1.5748 * v;
    float g = y - 0.1873 * u - 0.4681 * v;
    float b = y + 1.8556 * u;
    
    frag_color = vec4(r, g, b, 1.0);
}
```

### 7.4 调试与验证

#### 测试图案

```
标准测试图案：

1. 彩条（Color Bars）
   白 黄 青 绿 品 红 蓝 黑
   用于检查色彩还原

2. 灰阶（Grayscale）
   从黑到白的渐变
   用于检查亮度线性

3. 色度多波群（Chroma Multiburst）
   不同频率的色度信号
   用于检查色度带宽
```

#### 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 色彩偏移 | 矩阵错误 | 检查BT.601/709/2020 |
| 亮度异常 | 范围混淆 | 检查Full/Limited |
| 色度锯齿 | 上采样算法差 | 使用双线性/双三次 |
| 绿屏/粉屏 | UV通道交换 | 检查NV12/NV21 |
| 条纹伪影 | 对齐错误 | 检查stride/padding |

---

## 总结

YUV域是数字视频和图像压缩的核心，理解其原理对于：

1. **视频编码**：优化压缩效率和质量
2. **图像处理**：正确的色彩空间转换
3. **跨平台开发**：处理不同系统的格式差异
4. **性能优化**：利用硬件加速

核心技术要点：
- **转换矩阵**：BT.601/709/2020的区别
- **色度子采样**：4:2:0/4:2:2的权衡
- **色彩范围**：Full vs Limited的处理
- **内存布局**：Planar/Semi-Planar/Packed

> 🔗 返回：[RAW_YUV域深度解析](./RAW_YUV域深度解析.md)

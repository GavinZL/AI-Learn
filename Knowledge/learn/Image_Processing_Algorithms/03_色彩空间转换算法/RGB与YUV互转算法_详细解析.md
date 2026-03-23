# RGB与YUV互转算法详细解析

> 亮度-色度分离：视频编码与图像处理的核心色彩表示变换

---

## 目录

1. [亮度-色度分离的理论基础](#1-亮度-色度分离的理论基础)
2. [BT.601转换（标清）](#2-bt601转换标清)
3. [BT.709转换（高清）](#3-bt709转换高清)
4. [BT.2020转换（超高清/HDR）](#4-bt2020转换超高清hdr)
5. [色度子采样](#5-色度子采样)
6. [定点化与硬件实现](#6-定点化与硬件实现)
7. [跨平台差异](#7-跨平台差异)
8. [参考资源](#8-参考资源)

---

## 1. 亮度-色度分离的理论基础

### 1.1 人眼视觉特性

人类视觉系统对亮度和色度的敏感度存在显著差异，这是YUV编码的生物学基础：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        人眼视觉敏感度特性                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   视网膜感光细胞分布：                                                       │
│   ┌────────────────────────────────────────────────────────────┐            │
│   │     视杆细胞（Rod）          视锥细胞（Cone）              │            │
│   │     ~1.2亿个                 ~600万个                      │            │
│   │     感知亮度                 感知颜色                      │            │
│   │     高敏感度                 低敏感度                      │            │
│   │     低空间分辨率             高空间分辨率                  │            │
│   └────────────────────────────────────────────────────────────┘            │
│                                                                              │
│   空间频率响应对比（对比敏感度函数CSF）：                                     │
│                                                                              │
│   敏感度                                                                     │
│     ▲                                                                        │
│     │    ╱╲                                                                  │
│     │   ╱  ╲   亮度通道                                                     │
│     │  ╱    ╲                                                                │
│     │ ╱      ╲───────                                                       │
│     │╱   ╱╲   ╲                                                              │
│     │   ╱  ╲   色度通道                                                     │
│     │──╱────╲──────────                                                     │
│     └──────────────────────→ 空间频率 (cycles/degree)                       │
│                                                                              │
│   关键发现：                                                                 │
│   • 亮度通道：高频细节敏感，~8 cycles/degree峰值                            │
│   • 色度通道：低频敏感，高频细节几乎感知不到                                 │
│   • 色度信息可以大幅压缩而不影响主观质量                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 YUV分离的编码效率优势

将RGB转换为YUV带来的编码效率提升：

| 优势 | 说明 |
|------|------|
| **色度子采样** | Y保持全分辨率，UV可降采样至1/4（4:2:0），数据量减少50% |
| **能量集中** | 亮度Y承载大部分图像能量，便于压缩优化 |
| **去相关性** | RGB三通道强相关，YUV各通道相关性低，压缩效率高 |
| **兼容性** | 黑白显示设备只需Y通道即可显示 |

### 1.3 YUV家族术语辨析

```
┌─────────────────────────────────────────────────────────────────┐
│                    YUV相关术语对比                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   术语        全称                应用场景        值范围         │
│   ──────────────────────────────────────────────────────────    │
│   YUV        Y/U/V               模拟视频        连续值         │
│   YCbCr      Y/Cb/Cr             数字视频        离散值         │
│   YPbPr      Y/Pb/Pr             分量视频接口    模拟连续       │
│   Y'CbCr     Gamma校正后的YCbCr  实际使用        离散值         │
│                                                                  │
│   注意：                                                         │
│   • 数字视频中通常使用YCbCr，但习惯上仍称YUV                     │
│   • Y'表示经过Gamma校正的亮度（非线性）                          │
│   • 本文中YUV泛指数字视频的亮度-色度分离表示                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. BT.601转换（标清）

### 2.1 BT.601标准概述

ITU-R BT.601是标准清晰度电视（SDTV）的色彩编码标准：

- **发布年份**：1982年
- **适用分辨率**：480i/576i（NTSC/PAL）
- **色域**：基于CRT显示器特性

### 2.2 转换矩阵推导

#### 亮度Y的定义

基于人眼对RGB三原色的敏感度加权：

$$
Y = 0.299R + 0.587G + 0.114B
$$

系数来源：人眼对绿色最敏感（0.587），对蓝色最不敏感（0.114）。

#### 色差Cb/Cr的定义

$$
Cb = \frac{B - Y}{1.772} + 0.5 = -0.169R - 0.331G + 0.500B + 0.5
$$

$$
Cr = \frac{R - Y}{1.402} + 0.5 = 0.500R - 0.419G - 0.081B + 0.5
$$

#### 完整转换矩阵

**RGB → YCbCr (BT.601)**:

$$
\begin{bmatrix} Y \\ Cb \\ Cr \end{bmatrix} = 
\begin{bmatrix} 
0.299 & 0.587 & 0.114 \\
-0.169 & -0.331 & 0.500 \\
0.500 & -0.419 & -0.081
\end{bmatrix}
\begin{bmatrix} R \\ G \\ B \end{bmatrix}
+
\begin{bmatrix} 0 \\ 128 \\ 128 \end{bmatrix}
$$

**YCbCr → RGB (BT.601)**:

$$
\begin{bmatrix} R \\ G \\ B \end{bmatrix} = 
\begin{bmatrix} 
1.000 & 0.000 & 1.402 \\
1.000 & -0.344 & -0.714 \\
1.000 & 1.772 & 0.000
\end{bmatrix}
\begin{bmatrix} Y \\ Cb - 128 \\ Cr - 128 \end{bmatrix}
$$

### 2.3 Full Range vs Limited Range

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Full Range vs Limited Range                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   8bit数值范围对比：                                                         │
│                                                                              │
│   分量        Full Range       Limited Range      说明                      │
│   ──────────────────────────────────────────────────────────────────────    │
│   Y (亮度)    0 - 255          16 - 235           Limited预留超黑/超白      │
│   Cb (色差)   0 - 255          16 - 240           保护带防止溢出            │
│   Cr (色差)   0 - 255          16 - 240           与模拟视频兼容            │
│                                                                              │
│   转换公式差异（以Y为例）：                                                  │
│                                                                              │
│   Full Range:                                                                │
│   Y = 0.299R + 0.587G + 0.114B                                              │
│   (输入输出都是0-255)                                                        │
│                                                                              │
│   Limited Range:                                                             │
│   Y = 16 + 219 × (0.299R + 0.587G + 0.114B) / 255                           │
│   (输出映射到16-235)                                                         │
│                                                                              │
│   常见问题：                                                                 │
│   • 混用Range导致黑位偏灰、对比度下降                                        │
│   • 视频播放器需正确识别Range标志                                            │
│   • JPEG使用Full Range，视频通常使用Limited Range                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 定点化实现

```python
import numpy as np

def rgb_to_ycbcr_bt601_full(rgb):
    """
    BT.601 RGB到YCbCr转换 (Full Range)
    
    Args:
        rgb: RGB图像 (H, W, 3), uint8 [0-255]
    
    Returns:
        ycbcr: YCbCr图像 (H, W, 3), uint8 [0-255]
    """
    rgb = rgb.astype(np.float32)
    
    # 转换矩阵
    Y  = 0.299 * rgb[:,:,0] + 0.587 * rgb[:,:,1] + 0.114 * rgb[:,:,2]
    Cb = -0.169 * rgb[:,:,0] - 0.331 * rgb[:,:,1] + 0.500 * rgb[:,:,2] + 128
    Cr = 0.500 * rgb[:,:,0] - 0.419 * rgb[:,:,1] - 0.081 * rgb[:,:,2] + 128
    
    ycbcr = np.stack([Y, Cb, Cr], axis=-1)
    return np.clip(ycbcr, 0, 255).astype(np.uint8)

def ycbcr_to_rgb_bt601_full(ycbcr):
    """
    BT.601 YCbCr到RGB转换 (Full Range)
    """
    ycbcr = ycbcr.astype(np.float32)
    Y, Cb, Cr = ycbcr[:,:,0], ycbcr[:,:,1] - 128, ycbcr[:,:,2] - 128
    
    R = Y + 1.402 * Cr
    G = Y - 0.344 * Cb - 0.714 * Cr
    B = Y + 1.772 * Cb
    
    rgb = np.stack([R, G, B], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)

def rgb_to_ycbcr_bt601_limited(rgb):
    """
    BT.601 RGB到YCbCr转换 (Limited Range, 视频标准)
    """
    rgb = rgb.astype(np.float32)
    
    Y  = 16 + 65.481 * rgb[:,:,0]/255 + 128.553 * rgb[:,:,1]/255 + 24.966 * rgb[:,:,2]/255
    Cb = 128 - 37.797 * rgb[:,:,0]/255 - 74.203 * rgb[:,:,1]/255 + 112.0 * rgb[:,:,2]/255
    Cr = 128 + 112.0 * rgb[:,:,0]/255 - 93.786 * rgb[:,:,1]/255 - 18.214 * rgb[:,:,2]/255
    
    ycbcr = np.stack([Y, Cb, Cr], axis=-1)
    return np.clip(ycbcr, 0, 255).astype(np.uint8)
```

---

## 3. BT.709转换（高清）

### 3.1 BT.709标准概述

ITU-R BT.709是高清电视（HDTV）的国际标准：

- **发布年份**：1990年（多次修订）
- **适用分辨率**：720p/1080i/1080p
- **色域**：与sRGB色域重合

### 3.2 BT.709转换矩阵

由于HD内容的色域与亮度特性变化，BT.709采用不同的亮度系数：

$$
Y = 0.2126R + 0.7152G + 0.0722B
$$

**RGB → YCbCr (BT.709)**:

$$
\begin{bmatrix} Y \\ Cb \\ Cr \end{bmatrix} = 
\begin{bmatrix} 
0.2126 & 0.7152 & 0.0722 \\
-0.1146 & -0.3854 & 0.5000 \\
0.5000 & -0.4542 & -0.0458
\end{bmatrix}
\begin{bmatrix} R \\ G \\ B \end{bmatrix}
+
\begin{bmatrix} 0 \\ 128 \\ 128 \end{bmatrix}
$$

**YCbCr → RGB (BT.709)**:

$$
\begin{bmatrix} R \\ G \\ B \end{bmatrix} = 
\begin{bmatrix} 
1.0000 & 0.0000 & 1.5748 \\
1.0000 & -0.1873 & -0.4681 \\
1.0000 & 1.8556 & 0.0000
\end{bmatrix}
\begin{bmatrix} Y \\ Cb - 128 \\ Cr - 128 \end{bmatrix}
$$

### 3.3 BT.601与BT.709对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BT.601 vs BT.709 对比                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   参数                 BT.601             BT.709            差异原因        │
│   ────────────────────────────────────────────────────────────────────────  │
│   Y系数(R)             0.299              0.2126           绿色权重增加    │
│   Y系数(G)             0.587              0.7152           HD显示特性      │
│   Y系数(B)             0.114              0.0722           蓝色减少        │
│                                                                              │
│   色域                 SMPTE-C            sRGB/Rec.709     色域扩展        │
│   白点                 D65                D65              相同            │
│   典型分辨率           480i/576i          720p/1080p       清晰度提升      │
│                                                                              │
│   混用问题示例：                                                             │
│                                                                              │
│   ┌─────────────┐     错误转换      ┌─────────────┐                        │
│   │ HD视频      │ ───────────────→ │ 颜色偏移    │                        │
│   │ (BT.709)    │   用BT.601解码   │ 绿色偏黄    │                        │
│   └─────────────┘                   │ 肤色不准    │                        │
│                                      └─────────────┘                        │
│                                                                              │
│   正确做法：                                                                 │
│   • 根据视频元数据选择正确的转换矩阵                                         │
│   • H.264/H.265码流中有color_primaries/matrix_coefficients字段              │
│   • 默认：SD→BT.601, HD→BT.709, UHD→BT.2020                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 BT.709实现代码

```python
def rgb_to_ycbcr_bt709_full(rgb):
    """
    BT.709 RGB到YCbCr转换 (Full Range)
    """
    rgb = rgb.astype(np.float32)
    
    Y  = 0.2126 * rgb[:,:,0] + 0.7152 * rgb[:,:,1] + 0.0722 * rgb[:,:,2]
    Cb = -0.1146 * rgb[:,:,0] - 0.3854 * rgb[:,:,1] + 0.5000 * rgb[:,:,2] + 128
    Cr = 0.5000 * rgb[:,:,0] - 0.4542 * rgb[:,:,1] - 0.0458 * rgb[:,:,2] + 128
    
    ycbcr = np.stack([Y, Cb, Cr], axis=-1)
    return np.clip(ycbcr, 0, 255).astype(np.uint8)

def ycbcr_to_rgb_bt709_full(ycbcr):
    """
    BT.709 YCbCr到RGB转换 (Full Range)
    """
    ycbcr = ycbcr.astype(np.float32)
    Y, Cb, Cr = ycbcr[:,:,0], ycbcr[:,:,1] - 128, ycbcr[:,:,2] - 128
    
    R = Y + 1.5748 * Cr
    G = Y - 0.1873 * Cb - 0.4681 * Cr
    B = Y + 1.8556 * Cb
    
    rgb = np.stack([R, G, B], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)
```

---

## 4. BT.2020转换（超高清/HDR）

### 4.1 BT.2020标准概述

ITU-R BT.2020定义了超高清电视（UHDTV）的参数：

- **发布年份**：2012年
- **适用分辨率**：4K (3840×2160) / 8K (7680×4320)
- **色域**：宽色域（Wide Color Gamut），覆盖75.8%的CIE 1931色度图

### 4.2 BT.2020转换矩阵

$$
Y = 0.2627R + 0.6780G + 0.0593B
$$

**RGB → YCbCr (BT.2020)**:

$$
\begin{bmatrix} Y \\ Cb \\ Cr \end{bmatrix} = 
\begin{bmatrix} 
0.2627 & 0.6780 & 0.0593 \\
-0.1396 & -0.3604 & 0.5000 \\
0.5000 & -0.4598 & -0.0402
\end{bmatrix}
\begin{bmatrix} R \\ G \\ B \end{bmatrix}
+
\begin{bmatrix} 0 \\ 512 \\ 512 \end{bmatrix}_{10bit}
$$

### 4.3 高位深要求

BT.2020规定支持10bit和12bit位深：

```
┌─────────────────────────────────────────────────────────────────┐
│                   BT.2020 位深规格                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   位深        灰阶数        Y范围           CbCr范围            │
│   ────────────────────────────────────────────────────────────  │
│   10bit       1024         64-940          64-960              │
│   12bit       4096         256-3760        256-3840            │
│                                                                  │
│   为什么需要高位深？                                             │
│   • 宽色域表示需要更高精度                                       │
│   • HDR内容动态范围大，避免色带（banding）                       │
│   • 色度子采样后仍需保持足够精度                                 │
│                                                                  │
│   10bit vs 8bit对比：                                            │
│                                                                  │
│   8bit渐变：  ██████░░░░░░████████░░░░░░  (可见色带)             │
│   10bit渐变： ████████████████████████████ (平滑过渡)            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 BT.2020实现代码

```python
def rgb_to_ycbcr_bt2020_10bit(rgb):
    """
    BT.2020 RGB到YCbCr转换 (10bit Limited Range)
    
    Args:
        rgb: RGB图像 (H, W, 3), uint16 [0-1023]
    
    Returns:
        ycbcr: YCbCr图像 (H, W, 3), uint16 [64-940/64-960]
    """
    rgb = rgb.astype(np.float32)
    
    # 归一化到 [0, 1]
    rgb_norm = rgb / 1023.0
    
    # 转换矩阵
    Y_norm  = 0.2627 * rgb_norm[:,:,0] + 0.6780 * rgb_norm[:,:,1] + 0.0593 * rgb_norm[:,:,2]
    Cb_norm = -0.1396 * rgb_norm[:,:,0] - 0.3604 * rgb_norm[:,:,1] + 0.5000 * rgb_norm[:,:,2]
    Cr_norm = 0.5000 * rgb_norm[:,:,0] - 0.4598 * rgb_norm[:,:,1] - 0.0402 * rgb_norm[:,:,2]
    
    # Limited Range缩放
    Y  = 64 + Y_norm * 876  # 64-940
    Cb = 512 + Cb_norm * 896  # 64-960
    Cr = 512 + Cr_norm * 896  # 64-960
    
    ycbcr = np.stack([Y, Cb, Cr], axis=-1)
    return np.clip(ycbcr, 0, 1023).astype(np.uint16)

def ycbcr_to_rgb_bt2020_10bit(ycbcr):
    """
    BT.2020 YCbCr到RGB转换 (10bit Limited Range)
    """
    ycbcr = ycbcr.astype(np.float32)
    
    # Limited Range反归一化
    Y_norm  = (ycbcr[:,:,0] - 64) / 876
    Cb_norm = (ycbcr[:,:,1] - 512) / 896
    Cr_norm = (ycbcr[:,:,2] - 512) / 896
    
    # 逆转换矩阵
    R_norm = Y_norm + 1.4746 * Cr_norm
    G_norm = Y_norm - 0.1646 * Cb_norm - 0.5714 * Cr_norm
    B_norm = Y_norm + 1.8814 * Cb_norm
    
    rgb = np.stack([R_norm, G_norm, B_norm], axis=-1) * 1023
    return np.clip(rgb, 0, 1023).astype(np.uint16)
```

### 4.5 三代标准对比

| 标准 | BT.601 | BT.709 | BT.2020 |
|------|--------|--------|---------|
| **年代** | 1982 | 1990 | 2012 |
| **分辨率** | SD (480/576) | HD (720/1080) | UHD (4K/8K) |
| **Y(R)系数** | 0.299 | 0.2126 | 0.2627 |
| **Y(G)系数** | 0.587 | 0.7152 | 0.6780 |
| **Y(B)系数** | 0.114 | 0.0722 | 0.0593 |
| **位深** | 8bit | 8/10bit | 10/12bit |
| **色域覆盖** | ~35% CIE | ~35% CIE | ~75% CIE |

---

## 5. 色度子采样

### 5.1 子采样格式详解

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        色度子采样格式对比                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   4:4:4 (无子采样)                                                           │
│   ┌─────┬─────┬─────┬─────┐                                                 │
│   │Y Cb│Y Cb│Y Cb│Y Cb│   每个像素都有完整的Y、Cb、Cr                       │
│   │  Cr│  Cr│  Cr│  Cr│   数据量：100%                                      │
│   ├─────┼─────┼─────┼─────┤   应用：专业视频制作、图形渲染                   │
│   │Y Cb│Y Cb│Y Cb│Y Cb│                                                     │
│   │  Cr│  Cr│  Cr│  Cr│                                                     │
│   └─────┴─────┴─────┴─────┘                                                 │
│                                                                              │
│   4:2:2 (水平半采样)                                                         │
│   ┌─────┬─────┬─────┬─────┐                                                 │
│   │Y Cb│  Y  │Y Cb│  Y  │   水平方向每2个像素共享1组CbCr                     │
│   │  Cr│     │  Cr│     │   数据量：67%                                      │
│   ├─────┼─────┼─────┼─────┤   应用：广播级视频、专业摄像机                   │
│   │Y Cb│  Y  │Y Cb│  Y  │                                                     │
│   │  Cr│     │  Cr│     │                                                     │
│   └─────┴─────┴─────┴─────┘                                                 │
│                                                                              │
│   4:2:0 (水平+垂直半采样)                                                    │
│   ┌─────┬─────┬─────┬─────┐                                                 │
│   │Y Cb│  Y  │Y Cb│  Y  │   每2×2像素块共享1组CbCr                          │
│   │  Cr│     │  Cr│     │   数据量：50%                                      │
│   ├─────┼─────┼─────┼─────┤   应用：H.264/H.265、流媒体、蓝光               │
│   │  Y │  Y  │  Y │  Y  │                                                     │
│   │    │     │    │     │                                                     │
│   └─────┴─────┴─────┴─────┘                                                 │
│                                                                              │
│   4:1:1 (水平四分之一采样)                                                   │
│   ┌─────┬─────┬─────┬─────┐                                                 │
│   │Y Cb│  Y  │  Y  │  Y  │   水平方向每4个像素共享1组CbCr                    │
│   │  Cr│     │     │     │   数据量：50%（但水平色度更低）                   │
│   ├─────┼─────┼─────┼─────┤   应用：DV格式（已少用）                        │
│   │Y Cb│  Y  │  Y  │  Y  │                                                     │
│   │  Cr│     │     │     │                                                     │
│   └─────┴─────┴─────┴─────┘                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 下采样滤波器设计

#### MPEG-2风格采样位置

```
┌─────────────────────────────────────────────────────────────────┐
│              4:2:0 采样位置差异                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   MPEG-2 / H.264 (center位置)：                                 │
│   ┌───┬───┬───┬───┐                                             │
│   │ Y │ Y │ Y │ Y │    Y: 像素中心                              │
│   ├───┼───┼───┼───┤    C: 4个Y中心（垂直居中）                  │
│   │ Y │ C │ Y │ C │                                             │
│   ├───┼───┼───┼───┤                                             │
│   │ Y │ Y │ Y │ Y │                                             │
│   ├───┼───┼───┼───┤                                             │
│   │ Y │ C │ Y │ C │                                             │
│   └───┴───┴───┴───┘                                             │
│                                                                  │
│   MPEG-4 / H.264 (left位置，又称cosited)：                      │
│   ┌───┬───┬───┬───┐                                             │
│   │Y C│ Y │Y C│ Y │    C: 与左上Y同位置                         │
│   ├───┼───┼───┼───┤                                             │
│   │ Y │ Y │ Y │ Y │                                             │
│   ├───┼───┼───┼───┤                                             │
│   │Y C│ Y │Y C│ Y │                                             │
│   ├───┼───┼───┼───┤                                             │
│   │ Y │ Y │ Y │ Y │                                             │
│   └───┴───┴───┴───┘                                             │
│                                                                  │
│   采样位置影响：                                                 │
│   • 错误的位置假设导致色度偏移（边缘色晕）                       │
│   • H.264/H.265 VUI中有chroma_sample_loc_type字段               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 下采样滤波器实现

```python
def chroma_downsample_420(cb_444, cr_444, method='mpeg2'):
    """
    4:4:4到4:2:0色度下采样
    
    Args:
        cb_444, cr_444: 全分辨率色度 (H, W)
        method: 'mpeg2' (center) 或 'mpeg4' (cosited)
    
    Returns:
        cb_420, cr_420: 下采样色度 (H/2, W/2)
    """
    h, w = cb_444.shape
    
    if method == 'mpeg2':
        # MPEG-2: 垂直方向平均2行，水平方向平均2列
        # 相当于2x2 box滤波
        cb_420 = (cb_444[0::2, 0::2] + cb_444[0::2, 1::2] +
                  cb_444[1::2, 0::2] + cb_444[1::2, 1::2]) / 4
        cr_420 = (cr_444[0::2, 0::2] + cr_444[0::2, 1::2] +
                  cr_444[1::2, 0::2] + cr_444[1::2, 1::2]) / 4
    
    elif method == 'mpeg4':
        # MPEG-4 cosited: 取左上角像素（最简单实现）
        # 更好的实现应使用带偏移的滤波器
        cb_420 = cb_444[0::2, 0::2]
        cr_420 = cr_444[0::2, 0::2]
    
    return cb_420, cr_420

def chroma_downsample_422(cb_444, cr_444):
    """
    4:4:4到4:2:2色度下采样
    """
    # 水平方向平均2列
    cb_422 = (cb_444[:, 0::2] + cb_444[:, 1::2]) / 2
    cr_422 = (cr_444[:, 0::2] + cr_444[:, 1::2]) / 2
    return cb_422, cr_422
```

### 5.3 上采样重建方法

```python
def chroma_upsample_420_bilinear(cb_420, cr_420, target_h, target_w):
    """
    4:2:0到4:4:4色度上采样（双线性插值）
    """
    from scipy.ndimage import zoom
    
    scale_h = target_h / cb_420.shape[0]
    scale_w = target_w / cb_420.shape[1]
    
    cb_444 = zoom(cb_420, (scale_h, scale_w), order=1)  # 双线性
    cr_444 = zoom(cr_420, (scale_h, scale_w), order=1)
    
    return cb_444, cr_444

def chroma_upsample_420_nearest(cb_420, cr_420):
    """
    4:2:0到4:4:4色度上采样（最近邻，用于快速预览）
    """
    cb_444 = np.repeat(np.repeat(cb_420, 2, axis=0), 2, axis=1)
    cr_444 = np.repeat(np.repeat(cr_420, 2, axis=0), 2, axis=1)
    return cb_444, cr_444
```

### 5.4 子采样对图像质量的影响

| 格式 | 带宽/存储 | 色度分辨率 | 典型伪影 | 适用场景 |
|------|----------|-----------|---------|---------|
| **4:4:4** | 100% | 全分辨率 | 无 | 图形渲染、色键抠像 |
| **4:2:2** | 67% | 水平半分辨率 | 细微色晕 | 广播、专业制作 |
| **4:2:0** | 50% | 水平+垂直半 | 彩色边缘模糊 | 流媒体、消费视频 |
| **4:1:1** | 50% | 水平1/4 | 水平色带 | 遗留DV格式 |

---

## 6. 定点化与硬件实现

### 6.1 整数近似转换矩阵

浮点矩阵乘法在硬件实现中效率低，需要定点化：

```
┌─────────────────────────────────────────────────────────────────┐
│                  定点化转换矩阵                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   原理：用整数乘法 + 移位代替浮点乘法                            │
│                                                                  │
│   系数缩放公式：                                                 │
│   coef_int = round(coef_float × 2^N)                            │
│   result = (pixel × coef_int) >> N                              │
│                                                                  │
│   BT.601 8bit定点化示例（N=8, 缩放因子256）：                    │
│                                                                  │
│   浮点系数           整数系数                                    │
│   ──────────────────────────────────                            │
│   0.299   →   77 (0.300781)                                     │
│   0.587   →   150 (0.585938)                                    │
│   0.114   →   29 (0.113281)                                     │
│                                                                  │
│   Y = (77*R + 150*G + 29*B) >> 8                                │
│                                                                  │
│   精度分析：                                                     │
│   • 系数误差 < 0.5/256 ≈ 0.2%                                   │
│   • 最大累积误差 < 1 LSB (对于8bit输出)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 定点化实现代码

```python
def rgb_to_ycbcr_bt601_fixed(rgb):
    """
    BT.601定点化转换（8bit输入输出）
    使用16bit中间精度，8bit移位
    """
    rgb = rgb.astype(np.int32)
    R, G, B = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
    
    # 定点系数（×256）
    # Y = 0.299R + 0.587G + 0.114B
    Y = (77 * R + 150 * G + 29 * B + 128) >> 8
    
    # Cb = -0.169R - 0.331G + 0.500B + 128
    Cb = ((-43 * R - 85 * G + 128 * B + 128) >> 8) + 128
    
    # Cr = 0.500R - 0.419G - 0.081B + 128
    Cr = ((128 * R - 107 * G - 21 * B + 128) >> 8) + 128
    
    ycbcr = np.stack([Y, Cb, Cr], axis=-1)
    return np.clip(ycbcr, 0, 255).astype(np.uint8)

def ycbcr_to_rgb_bt601_fixed(ycbcr):
    """
    BT.601定点化逆转换
    """
    ycbcr = ycbcr.astype(np.int32)
    Y, Cb, Cr = ycbcr[:,:,0], ycbcr[:,:,1] - 128, ycbcr[:,:,2] - 128
    
    # 定点系数（×256）
    # R = Y + 1.402Cr
    R = Y + ((359 * Cr + 128) >> 8)
    
    # G = Y - 0.344Cb - 0.714Cr
    G = Y - ((88 * Cb + 183 * Cr + 128) >> 8)
    
    # B = Y + 1.772Cb
    B = Y + ((454 * Cb + 128) >> 8)
    
    rgb = np.stack([R, G, B], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)
```

### 6.3 精度误差分析

```python
def analyze_conversion_error(rgb_image, forward_func, inverse_func):
    """
    分析RGB→YCbCr→RGB转换的往返误差
    """
    # 正向转换
    ycbcr = forward_func(rgb_image)
    
    # 逆向转换
    rgb_reconstructed = inverse_func(ycbcr)
    
    # 误差计算
    error = rgb_image.astype(np.int32) - rgb_reconstructed.astype(np.int32)
    
    print(f"最大误差: {np.abs(error).max()}")
    print(f"平均误差: {np.abs(error).mean():.4f}")
    print(f"PSNR: {10 * np.log10(255**2 / np.mean(error**2)):.2f} dB")
    
    return error

# 典型结果：
# 浮点实现：最大误差0，PSNR无穷大
# 定点实现：最大误差1-2，PSNR > 50dB（可接受）
```

### 6.4 ISP硬件中的实现

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ISP硬件RGB↔YUV模块架构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │                    RGB → YCbCr 硬件模块                          │       │
│   │                                                                  │       │
│   │   R ──┬──[×77]──┐                                               │       │
│   │       │         │                                               │       │
│   │   G ──┼──[×150]─┼──[加法树]──[>>8]──[clip]── Y                 │       │
│   │       │         │                                               │       │
│   │   B ──┴──[×29]──┘                                               │       │
│   │                                                                  │       │
│   │   R ──┬──[×-43]─┐                                               │       │
│   │       │         │                                               │       │
│   │   G ──┼──[×-85]─┼──[加法树]──[>>8]──[+128]──[clip]── Cb        │       │
│   │       │         │                                               │       │
│   │   B ──┴──[×128]─┘                                               │       │
│   │                                                                  │       │
│   │   (Cr通道类似)                                                   │       │
│   │                                                                  │       │
│   │   特点：                                                         │       │
│   │   • 3个通道可并行计算                                            │       │
│   │   • 乘法器可用移位+加法实现（如×77 = 64+8+4+1）                  │       │
│   │   • 流水线设计，每时钟周期处理1像素                              │       │
│   │                                                                  │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│   典型延迟：2-3个时钟周期                                                    │
│   面积开销：~1000门（8bit实现）                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. 跨平台差异

### 7.1 Android MediaCodec颜色格式

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Android MediaCodec颜色格式                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   常见格式常量：                                                             │
│   ────────────────────────────────────────────────────────────────────────  │
│   COLOR_FormatYUV420Planar      (I420)    Y平面 + U平面 + V平面            │
│   COLOR_FormatYUV420SemiPlanar  (NV12)    Y平面 + UV交织平面               │
│   COLOR_FormatYUV420PackedPlanar         厂商特定打包格式                  │
│   COLOR_FormatYUV420Flexible             灵活格式（API 21+）               │
│                                                                              │
│   内存布局对比（以1920×1080为例）：                                          │
│                                                                              │
│   I420 (YUV420P)：                                                          │
│   ┌────────────────────────────────────────┐ offset 0                       │
│   │              Y平面                      │ size: 1920×1080               │
│   │            (1920×1080)                  │                               │
│   ├────────────────────────────────────────┤ offset 2073600                 │
│   │       U平面        │       V平面        │ size: 960×540 each            │
│   │     (960×540)      │     (960×540)      │                               │
│   └────────────────────────────────────────┘                                │
│                                                                              │
│   NV12 (YUV420SP)：                                                         │
│   ┌────────────────────────────────────────┐ offset 0                       │
│   │              Y平面                      │ size: 1920×1080               │
│   │            (1920×1080)                  │                               │
│   ├────────────────────────────────────────┤ offset 2073600                 │
│   │           UV交织平面                    │ size: 1920×540                │
│   │   U V U V U V U V ... (1920×540)       │ (UVUVUV...)                   │
│   └────────────────────────────────────────┘                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

```java
// Android MediaCodec使用示例
MediaFormat format = MediaFormat.createVideoFormat("video/avc", 1920, 1080);
format.setInteger(MediaFormat.KEY_COLOR_FORMAT,
    MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar);

// 检查支持的格式
MediaCodecInfo.CodecCapabilities caps = codecInfo.getCapabilitiesForType("video/avc");
for (int colorFormat : caps.colorFormats) {
    Log.d("Codec", "Supported format: " + colorFormat);
}
```

### 7.2 iOS CVPixelBuffer格式

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     iOS CVPixelBuffer格式                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   常见OSType常量：                                                           │
│   ────────────────────────────────────────────────────────────────────────  │
│   kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange   (NV12 Limited)         │
│   kCVPixelFormatType_420YpCbCr8BiPlanarFullRange    (NV12 Full)            │
│   kCVPixelFormatType_420YpCbCr8Planar               (I420)                 │
│   kCVPixelFormatType_32BGRA                         (BGRA 4:4:4)           │
│                                                                              │
│   VideoToolbox编码典型配置：                                                 │
│   • 摄像头输出：kCVPixelFormatType_420YpCbCr8BiPlanarFullRange             │
│   • H.264编码：kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

```swift
// iOS CVPixelBuffer访问示例
func processPixelBuffer(_ pixelBuffer: CVPixelBuffer) {
    CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }
    
    let formatType = CVPixelBufferGetPixelFormatType(pixelBuffer)
    
    if formatType == kCVPixelFormatType_420YpCbCr8BiPlanarFullRange {
        // NV12格式
        let yPlane = CVPixelBufferGetBaseAddressOfPlane(pixelBuffer, 0)
        let uvPlane = CVPixelBufferGetBaseAddressOfPlane(pixelBuffer, 1)
        let yStride = CVPixelBufferGetBytesPerRowOfPlane(pixelBuffer, 0)
        let uvStride = CVPixelBufferGetBytesPerRowOfPlane(pixelBuffer, 1)
        
        // 处理Y和UV数据...
    }
}
```

### 7.3 FFmpeg swscale

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FFmpeg swscale色彩空间转换                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   常用像素格式：                                                             │
│   ────────────────────────────────────────────────────────────────────────  │
│   AV_PIX_FMT_YUV420P       I420（最常用）                                   │
│   AV_PIX_FMT_NV12          NV12（硬件友好）                                 │
│   AV_PIX_FMT_YUV422P       4:2:2平面格式                                    │
│   AV_PIX_FMT_YUVJ420P      JPEG使用的Full Range 4:2:0                      │
│   AV_PIX_FMT_YUV420P10LE   10bit YUV420                                    │
│   AV_PIX_FMT_RGB24         RGB打包格式                                      │
│   AV_PIX_FMT_BGR24         BGR打包格式（OpenCV默认）                        │
│                                                                              │
│   swscale转换流程：                                                          │
│   1. sws_getContext() 创建转换上下文                                        │
│   2. sws_scale() 执行转换                                                   │
│   3. sws_freeContext() 释放资源                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

```c
// FFmpeg swscale使用示例
#include <libswscale/swscale.h>

// 创建RGB到YUV转换上下文
struct SwsContext *sws_ctx = sws_getContext(
    width, height, AV_PIX_FMT_RGB24,    // 输入
    width, height, AV_PIX_FMT_YUV420P,  // 输出
    SWS_BILINEAR,                        // 缩放算法（影响子采样滤波）
    NULL, NULL, NULL);

// 设置色彩空间参数（BT.709）
int src_range = 1;  // Full Range
int dst_range = 0;  // Limited Range
const int *inv_table = sws_getCoefficients(SWS_CS_ITU709);  // BT.709矩阵
const int *table = sws_getCoefficients(SWS_CS_ITU709);
int brightness = 0, contrast = 1 << 16, saturation = 1 << 16;

sws_setColorspaceDetails(sws_ctx, inv_table, src_range,
                         table, dst_range,
                         brightness, contrast, saturation);

// 执行转换
uint8_t *src_data[1] = {rgb_buffer};
int src_linesize[1] = {width * 3};
uint8_t *dst_data[3] = {y_plane, u_plane, v_plane};
int dst_linesize[3] = {width, width/2, width/2};

sws_scale(sws_ctx, src_data, src_linesize, 0, height,
          dst_data, dst_linesize);

// 释放
sws_freeContext(sws_ctx);
```

### 7.4 Python实现汇总

```python
import numpy as np
import cv2

class YUVConverter:
    """跨格式YUV转换器"""
    
    MATRIX_BT601 = {
        'kr': 0.299, 'kg': 0.587, 'kb': 0.114
    }
    MATRIX_BT709 = {
        'kr': 0.2126, 'kg': 0.7152, 'kb': 0.0722
    }
    MATRIX_BT2020 = {
        'kr': 0.2627, 'kg': 0.6780, 'kb': 0.0593
    }
    
    def __init__(self, standard='bt709', full_range=True):
        self.standard = standard
        self.full_range = full_range
        
        if standard == 'bt601':
            self.matrix = self.MATRIX_BT601
        elif standard == 'bt709':
            self.matrix = self.MATRIX_BT709
        elif standard == 'bt2020':
            self.matrix = self.MATRIX_BT2020
    
    def rgb_to_ycbcr(self, rgb):
        """RGB到YCbCr转换"""
        rgb = rgb.astype(np.float32) / 255.0
        kr, kg, kb = self.matrix['kr'], self.matrix['kg'], self.matrix['kb']
        
        Y = kr * rgb[:,:,0] + kg * rgb[:,:,1] + kb * rgb[:,:,2]
        Cb = (rgb[:,:,2] - Y) / (2 * (1 - kb))
        Cr = (rgb[:,:,0] - Y) / (2 * (1 - kr))
        
        if self.full_range:
            Y = Y * 255
            Cb = Cb * 255 + 128
            Cr = Cr * 255 + 128
        else:
            Y = Y * 219 + 16
            Cb = Cb * 224 + 128
            Cr = Cr * 224 + 128
        
        return np.stack([Y, Cb, Cr], axis=-1).astype(np.uint8)
    
    def ycbcr_to_rgb(self, ycbcr):
        """YCbCr到RGB转换"""
        ycbcr = ycbcr.astype(np.float32)
        kr, kg, kb = self.matrix['kr'], self.matrix['kg'], self.matrix['kb']
        
        if self.full_range:
            Y = ycbcr[:,:,0] / 255
            Cb = (ycbcr[:,:,1] - 128) / 255
            Cr = (ycbcr[:,:,2] - 128) / 255
        else:
            Y = (ycbcr[:,:,0] - 16) / 219
            Cb = (ycbcr[:,:,1] - 128) / 224
            Cr = (ycbcr[:,:,2] - 128) / 224
        
        R = Y + 2 * (1 - kr) * Cr
        G = Y - 2 * kb * (1 - kb) / kg * Cb - 2 * kr * (1 - kr) / kg * Cr
        B = Y + 2 * (1 - kb) * Cb
        
        rgb = np.stack([R, G, B], axis=-1) * 255
        return np.clip(rgb, 0, 255).astype(np.uint8)
    
    def subsample_420(self, ycbcr):
        """4:4:4到4:2:0子采样"""
        Y = ycbcr[:,:,0]
        Cb = cv2.resize(ycbcr[:,:,1], None, fx=0.5, fy=0.5, 
                        interpolation=cv2.INTER_AREA)
        Cr = cv2.resize(ycbcr[:,:,2], None, fx=0.5, fy=0.5,
                        interpolation=cv2.INTER_AREA)
        return Y, Cb, Cr
    
    def upsample_420(self, Y, Cb, Cr):
        """4:2:0到4:4:4上采样"""
        h, w = Y.shape
        Cb_up = cv2.resize(Cb, (w, h), interpolation=cv2.INTER_LINEAR)
        Cr_up = cv2.resize(Cr, (w, h), interpolation=cv2.INTER_LINEAR)
        return np.stack([Y, Cb_up, Cr_up], axis=-1)


# 使用示例
if __name__ == '__main__':
    # 读取RGB图像
    rgb = cv2.imread('test.jpg')
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
    
    # BT.709转换
    converter = YUVConverter(standard='bt709', full_range=True)
    ycbcr = converter.rgb_to_ycbcr(rgb)
    
    # 4:2:0子采样
    Y, Cb, Cr = converter.subsample_420(ycbcr)
    print(f"Y shape: {Y.shape}, Cb shape: {Cb.shape}")
    
    # 重建
    ycbcr_reconstructed = converter.upsample_420(Y, Cb, Cr)
    rgb_reconstructed = converter.ycbcr_to_rgb(ycbcr_reconstructed)
    
    # 计算误差
    error = np.abs(rgb.astype(np.float32) - rgb_reconstructed.astype(np.float32))
    print(f"Mean error: {error.mean():.2f}, Max error: {error.max()}")
```

---

## 8. 参考资源

### 标准规范

- **ITU-R BT.601**: 标清电视编码参数
- **ITU-R BT.709**: 高清电视编码参数
- **ITU-R BT.2020**: 超高清电视编码参数
- **ITU-T H.264/H.265**: 视频编码标准（含VUI色彩信息）

### 技术文档

- **Charles Poynton**: "Digital Video and HD: Algorithms and Interfaces"
- **Keith Jack**: "Video Demystified"
- **FFmpeg Documentation**: libswscale色彩空间转换

### 开源实现

- **FFmpeg**: libswscale色彩空间转换库
- **libyuv**: Google的YUV处理库（高度优化）
- **OpenCV**: cv2.cvtColor色彩空间转换

### 平台SDK

- **Android**: MediaCodec, ImageReader
- **iOS**: VideoToolbox, CVPixelBuffer
- **Windows**: Media Foundation, DirectShow

---

*本文档涵盖了RGB与YUV互转的核心算法、各代标准差异、色度子采样原理及跨平台实现细节。正确处理色彩空间转换是视频处理管线的基础。*

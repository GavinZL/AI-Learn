# RAW到RGB转换算法详细解析

> 从传感器原始信号到标准色彩空间：图像处理管线的核心转换链路

---

## 目录

1. [RAW到RGB的完整转换流程概述](#1-raw到rgb的完整转换流程概述)
2. [白平衡算法](#2-白平衡算法)
3. [色彩校正矩阵（CCM）](#3-色彩校正矩阵ccm)
4. [Gamma校正](#4-gamma校正)
5. [端到端示例](#5-端到端示例)
6. [参考资源](#6-参考资源)

---

## 1. RAW到RGB的完整转换流程概述

### 1.1 转换管线架构

从Bayer域RAW数据到最终可显示的sRGB图像，需要经过多个精密的处理步骤：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAW → RGB 完整转换管线                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │  Bayer   │   │   白平衡  │   │ Demosaic │   │   CCM    │   │  Gamma   │  │
│  │   RAW    │ → │   (WB)   │ → │  去马赛克 │ → │ 色彩校正 │ → │   校正   │  │
│  │  12-14b  │   │ 增益调整  │   │ 插值到RGB │   │ 3×3矩阵  │   │ 传递函数 │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│       ↓               ↓              ↓              ↓              ↓        │
│   单通道Bayer     温度校正       线性RGB        目标色域       非线性RGB    │
│   传感器色域      中性灰恢复     传感器色域      线性RGB        sRGB/P3等   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 各步骤的数学本质

| 处理阶段 | 输入 | 输出 | 数学操作 | 目的 |
|---------|------|------|---------|------|
| **黑电平校正** | RAW | RAW | $I' = I - BL$ | 消除传感器暗电流偏移 |
| **白平衡** | Bayer RAW | Bayer RAW | $I' = I \times Gain$ | 消除色温偏差 |
| **Demosaic** | Bayer单通道 | RGB三通道 | 插值重建 | 还原完整彩色图像 |
| **CCM** | 线性RGB | 线性RGB | $RGB_{out} = M \cdot RGB_{in}$ | 映射到目标色彩空间 |
| **Gamma** | 线性RGB | 非线性RGB | $V' = f(V)$ | 感知优化编码 |

### 1.3 线性域与非线性域

理解线性与非线性是掌握RAW处理的关键：

```
┌─────────────────────────────────────────────────────────────────┐
│                    线性域 vs 非线性域                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   物理光照强度（线性）                                            │
│   ──────────────────────────────────────────────────────────     │
│   0%      25%      50%      75%     100%   ← 实际光量            │
│   │       │        │        │        │                          │
│   ▼       ▼        ▼        ▼        ▼                          │
│   ●───────●────────●────────●────────●     ← RAW值（线性）       │
│   0      0.25     0.5      0.75     1.0                         │
│                                                                  │
│   Gamma编码后（非线性）                                           │
│   ──────────────────────────────────────────────────────────     │
│   ●───●────●─────●───────●                ← 编码值（γ=2.2）      │
│   0  0.5  0.73  0.88    1.0               ← 更多bit给暗部       │
│                                                                  │
│   关键原则：                                                      │
│   • 物理运算（WB、CCM）必须在线性域进行                            │
│   • Gamma编码是最后一步，用于存储和显示                            │
│   • 混淆线性/非线性会导致色彩错误                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 位深演变

整个管线中数据位深的变化：

```
RAW (12-14bit) → 黑电平校正 (12-14bit) → 白平衡 (16bit扩展) 
    → Demosaic (16bit) → CCM (16bit浮点) → Gamma (8/10/12bit)
```

**为什么需要高位深中间处理？**

- WB增益可能>1，需要额外headroom
- CCM矩阵运算可能产生溢出
- 避免累积量化误差

---

## 2. 白平衡算法

### 2.1 白平衡的物理意义

白平衡用于**补偿不同光源色温对图像颜色的影响**，使得在任何光源下拍摄的白色物体都呈现为白色。

```
┌───────────────────────────────────────────────────────────────┐
│                    色温与白平衡                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│   色温（K）   光源类型          RGB偏移           需要的校正   │
│   ─────────────────────────────────────────────────────────   │
│   2000K      烛光              强红色偏移        增强蓝色     │
│   2700K      白炽灯            红色偏移          略增蓝色     │
│   4000K      荧光灯            可能偏绿          增品红       │
│   5500K      日光（标准）      平衡              无需校正     │
│   6500K      阴天              蓝色偏移          增强红色     │
│   10000K+    蓝天反射光        强蓝色偏移        强增红色     │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 Gray World假设算法

#### 原理

Gray World假设：**场景中所有颜色的平均值应该是中性灰**。

$$
\bar{R} = \bar{G} = \bar{B} = \bar{Gray}
$$

#### 增益计算

```
目标：使三个通道的平均值相等

设原始通道平均值为 avg_R, avg_G, avg_B
以G通道为基准（因为Bayer中G最多）：

Gain_R = avg_G / avg_R
Gain_G = 1.0
Gain_B = avg_G / avg_B
```

#### 实现代码

```python
import numpy as np

def gray_world_wb(raw_bayer, pattern='RGGB'):
    """
    Gray World白平衡算法
    
    Args:
        raw_bayer: Bayer格式RAW数据 (H, W)
        pattern: Bayer排列模式
    
    Returns:
        wb_gains: [R_gain, G_gain, B_gain]
    """
    h, w = raw_bayer.shape
    
    # 根据Bayer pattern提取各通道
    if pattern == 'RGGB':
        R = raw_bayer[0::2, 0::2]   # 偶行偶列
        Gr = raw_bayer[0::2, 1::2]  # 偶行奇列
        Gb = raw_bayer[1::2, 0::2]  # 奇行偶列
        B = raw_bayer[1::2, 1::2]   # 奇行奇列
    
    # 计算各通道平均值
    avg_R = np.mean(R)
    avg_G = (np.mean(Gr) + np.mean(Gb)) / 2
    avg_B = np.mean(B)
    
    # 以G为基准计算增益
    gain_R = avg_G / avg_R
    gain_G = 1.0
    gain_B = avg_G / avg_B
    
    return np.array([gain_R, gain_G, gain_B])

def apply_wb_gains(raw_bayer, gains, pattern='RGGB'):
    """
    应用白平衡增益到Bayer域
    """
    result = raw_bayer.astype(np.float32).copy()
    
    if pattern == 'RGGB':
        result[0::2, 0::2] *= gains[0]  # R
        result[0::2, 1::2] *= gains[1]  # Gr
        result[1::2, 0::2] *= gains[1]  # Gb
        result[1::2, 1::2] *= gains[2]  # B
    
    return np.clip(result, 0, 65535)
```

#### Gray World的局限性

- **假设条件严格**：场景必须色彩丰富且分布均匀
- **对单一颜色场景失效**：如蓝天、绿草地
- **不处理非标准光源**：如荧光灯的绿色尖峰

### 2.3 完美反射体假设（Max RGB）

#### 原理

假设场景中存在**完美的白色反射体**，其RGB三通道应该达到最大值且相等。

$$
\max(R) = \max(G) = \max(B)
$$

#### 实现

```python
def max_rgb_wb(raw_bayer, pattern='RGGB', percentile=99):
    """
    Max RGB白平衡（使用百分位数避免过曝像素影响）
    """
    if pattern == 'RGGB':
        R = raw_bayer[0::2, 0::2]
        Gr = raw_bayer[0::2, 1::2]
        Gb = raw_bayer[1::2, 0::2]
        B = raw_bayer[1::2, 1::2]
    
    # 使用百分位数而非最大值（更鲁棒）
    max_R = np.percentile(R, percentile)
    max_G = (np.percentile(Gr, percentile) + np.percentile(Gb, percentile)) / 2
    max_B = np.percentile(B, percentile)
    
    # 以G为基准
    gain_R = max_G / max_R
    gain_G = 1.0
    gain_B = max_G / max_B
    
    return np.array([gain_R, gain_G, gain_B])
```

### 2.4 色温估计与增益计算

#### 从色温到增益的转换

已知目标色温，可以通过Planckian轨迹计算对应的RGB比例：

```python
def kelvin_to_rgb_gains(temperature):
    """
    将色温转换为RGB增益
    基于Planckian轨迹的近似公式
    """
    temp = temperature / 100
    
    # 计算Red
    if temp <= 66:
        red = 255
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)
    
    # 计算Green
    if temp <= 66:
        green = 99.4708025861 * np.log(temp) - 161.1195681661
    else:
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    
    # 计算Blue
    if temp >= 66:
        blue = 255
    elif temp <= 19:
        blue = 0
    else:
        blue = 138.5177312231 * np.log(temp - 10) - 305.0447927307
    
    # 归一化为增益
    red = np.clip(red, 0, 255) / 255
    green = np.clip(green, 0, 255) / 255
    blue = np.clip(blue, 0, 255) / 255
    
    # 以G为基准的增益
    max_val = max(red, green, blue)
    return np.array([max_val/red, max_val/green, max_val/blue])
```

#### 色温估计算法

从图像反推光源色温：

```python
def estimate_color_temperature(rgb_image):
    """
    从图像估计色温（简化算法）
    基于R/B比值的色温映射
    """
    r_mean = np.mean(rgb_image[:,:,0])
    b_mean = np.mean(rgb_image[:,:,2])
    
    # R/B比值与色温的关系（经验公式）
    ratio = r_mean / (b_mean + 1e-6)
    
    # 对数映射到色温范围
    # ratio高 = 色温低（暖色）, ratio低 = 色温高（冷色）
    estimated_temp = 6500 / ratio  # 简化映射
    
    return np.clip(estimated_temp, 2000, 12000)
```

### 2.5 多光源场景的自适应白平衡

真实场景常存在多种光源（如室内灯光+窗户日光），需要**局部自适应白平衡**：

```
┌─────────────────────────────────────────────────────────────────┐
│                    多光源白平衡策略                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  方法一：分区域处理                                               │
│  ┌──────────────────────────────────────┐                       │
│  │ ┌─────────┐     ┌─────────┐         │                       │
│  │ │ 窗户区域 │     │ 灯光区域 │         │                       │
│  │ │  6500K  │     │  2700K  │         │                       │
│  │ │  WB_1   │     │  WB_2   │         │                       │
│  │ └─────────┘     └─────────┘         │                       │
│  │           ↓ 渐变混合 ↓               │                       │
│  │        过渡区域：WB插值              │                       │
│  └──────────────────────────────────────┘                       │
│                                                                  │
│  方法二：选择性白平衡                                             │
│  • 检测主光源（面积最大/亮度最高）                                 │
│  • 对主光源做全局白平衡                                           │
│  • 允许次光源保留轻微色偏（更自然）                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.6 白平衡增益的Bayer域应用

**为什么在Bayer域而非RGB域应用白平衡？**

1. **减少Demosaic伪彩**：色彩平衡后的Bayer数据更利于插值
2. **避免溢出**：先白平衡再去马赛克，减少后续处理的动态范围需求
3. **硬件效率**：ISP通常在早期阶段完成WB

```
┌─────────────────────────────────────────────────────────────────┐
│                  Bayer域白平衡应用                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   原始Bayer：         应用WB增益后：                             │
│   ┌───┬───┬───┬───┐  ┌───┬───┬───┬───┐                         │
│   │ R │Gr │ R │Gr │  │R×g│Gr │R×g│Gr │   g = R_gain           │
│   ├───┼───┼───┼───┤  ├───┼───┼───┼───┤                         │
│   │Gb │ B │Gb │ B │  │Gb │B×b│Gb │B×b│   b = B_gain           │
│   ├───┼───┼───┼───┤  ├───┼───┼───┼───┤                         │
│   │ R │Gr │ R │Gr │  │R×g│Gr │R×g│Gr │   (G_gain通常=1)       │
│   ├───┼───┼───┼───┤  ├───┼───┼───┼───┤                         │
│   │Gb │ B │Gb │ B │  │Gb │B×b│Gb │B×b│                         │
│   └───┴───┴───┴───┘  └───┴───┴───┴───┘                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 色彩校正矩阵（CCM）

### 3.1 CCM的数学定义

色彩校正矩阵（Color Correction Matrix）是一个3×3线性变换矩阵，将传感器的原生色域映射到目标色彩空间：

$$
\begin{bmatrix} R_{out} \\ G_{out} \\ B_{out} \end{bmatrix} = 
\begin{bmatrix} 
c_{11} & c_{12} & c_{13} \\
c_{21} & c_{22} & c_{23} \\
c_{31} & c_{32} & c_{33}
\end{bmatrix}
\begin{bmatrix} R_{in} \\ G_{in} \\ B_{in} \end{bmatrix}
$$

简写为：$RGB_{out} = CCM \cdot RGB_{in}$

### 3.2 为什么需要CCM？

```
┌─────────────────────────────────────────────────────────────────┐
│                    传感器色域 vs 目标色域                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   问题根源：                                                     │
│   • 传感器的RGB滤光片光谱响应 ≠ 标准色彩空间的定义               │
│   • 不同传感器的滤光片特性各异                                   │
│   • 需要映射到统一的目标空间（sRGB、Adobe RGB等）                │
│                                                                  │
│   CIE xy色度图示意：                                             │
│        y                                                         │
│        ▲                                                         │
│        │    ╱ 光谱轨迹                                           │
│        │   ╱                                                     │
│        │  ●───────────●   ← 传感器原生RGB三原色                  │
│        │ ╱ ╲   ▲   ╱ ╲                                          │
│        │╱   ╲  │  ╱   ╲                                         │
│        ●─────╲─│─╱─────●  ← sRGB三原色                          │
│        │      ╲│╱                                                │
│        └───────●───────────→ x                                   │
│                                                                  │
│   CCM的作用：线性变换将传感器三角形映射到目标三角形              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 最小二乘法求解CCM

#### 问题建模

给定ColorChecker的标准色块值和传感器拍摄值，求解最优CCM：

$$
\min_{CCM} \|X_{target} - CCM \cdot X_{sensor}\|^2
$$

其中：
- $X_{target}$：ColorChecker色块的标准RGB值（3×N矩阵，N为色块数）
- $X_{sensor}$：传感器拍摄的RGB值（3×N矩阵）

#### 解析解

$$
CCM = X_{target} \cdot X_{sensor}^T \cdot (X_{sensor} \cdot X_{sensor}^T)^{-1}
$$

#### 实现代码

```python
import numpy as np

def compute_ccm(sensor_rgb, target_rgb):
    """
    最小二乘法计算CCM
    
    Args:
        sensor_rgb: 传感器测量值 (N, 3), N个色块
        target_rgb: 目标标准值 (N, 3)
    
    Returns:
        ccm: 3x3色彩校正矩阵
    """
    # 转置为 (3, N)
    X = sensor_rgb.T  # (3, N)
    Y = target_rgb.T  # (3, N)
    
    # 最小二乘解: CCM = Y * X^T * (X * X^T)^(-1)
    XXT = X @ X.T  # (3, 3)
    YXT = Y @ X.T  # (3, 3)
    
    ccm = YXT @ np.linalg.inv(XXT)
    
    return ccm

def apply_ccm(rgb_image, ccm):
    """
    应用CCM到图像
    """
    h, w, _ = rgb_image.shape
    rgb_flat = rgb_image.reshape(-1, 3).T  # (3, H*W)
    
    result_flat = ccm @ rgb_flat
    result = result_flat.T.reshape(h, w, 3)
    
    return np.clip(result, 0, 1)
```

### 3.4 多照明体CCM插值

不同光源下最优CCM不同，需要根据色温插值：

```python
def interpolate_ccm(ccm_dict, target_temp):
    """
    根据色温插值CCM
    
    Args:
        ccm_dict: {色温: CCM矩阵} 字典，如 {2856: ccm_A, 6504: ccm_D65}
        target_temp: 目标色温
    
    Returns:
        插值后的CCM
    """
    temps = sorted(ccm_dict.keys())
    
    # 边界情况
    if target_temp <= temps[0]:
        return ccm_dict[temps[0]]
    if target_temp >= temps[-1]:
        return ccm_dict[temps[-1]]
    
    # 找到插值区间
    for i in range(len(temps) - 1):
        if temps[i] <= target_temp <= temps[i+1]:
            t1, t2 = temps[i], temps[i+1]
            break
    
    # 线性插值
    alpha = (target_temp - t1) / (t2 - t1)
    ccm = (1 - alpha) * ccm_dict[t1] + alpha * ccm_dict[t2]
    
    return ccm

# 典型应用
ccm_illuminants = {
    2856: np.array([...]),   # 标准光源A (钨丝灯)
    4000: np.array([...]),   # CWF (冷白荧光灯)
    5000: np.array([...]),   # D50 (地平线日光)
    6504: np.array([...]),   # D65 (正午日光)
}

current_ccm = interpolate_ccm(ccm_illuminants, estimated_temp)
```

### 3.5 CCM标定流程

#### 使用Macbeth ColorChecker

```
┌─────────────────────────────────────────────────────────────────┐
│                  CCM标定流程                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 准备工作                                                     │
│     • X-Rite ColorChecker Classic (24色块)                      │
│     • 标准光源（D65灯箱或实际目标环境光）                         │
│     • 固定相机设置（手动曝光、固定ISO）                           │
│                                                                  │
│  2. 拍摄RAW图像                                                  │
│     ┌─────────────────────────────────┐                         │
│     │ ■ ■ ■ ■ ■ ■ │← 棕色系列        │                         │
│     │ ■ ■ ■ ■ ■ ■ │← 色相序列        │                         │
│     │ ■ ■ ■ ■ ■ ■ │← 原色与互补色    │                         │
│     │ ■ ■ ■ ■ ■ ■ │← 灰阶序列        │                         │
│     └─────────────────────────────────┘                         │
│                                                                  │
│  3. 提取色块RGB值                                                │
│     • 定位24个色块中心区域                                       │
│     • 计算每个色块的平均RGB                                      │
│     • 注意：使用线性RAW值（已黑电平校正、白平衡）                  │
│                                                                  │
│  4. 获取参考值                                                   │
│     • X-Rite提供的Lab/sRGB标准值                                │
│     • 或使用分光光度计实测                                       │
│                                                                  │
│  5. 最小二乘求解CCM                                              │
│                                                                  │
│  6. 验证与调优                                                   │
│     • 计算ΔE色差                                                │
│     • 平均ΔE < 3为可接受，< 1为优秀                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### ColorChecker标准值示例

```python
# Macbeth ColorChecker的sRGB参考值（D50光源下）
# 注意：这是Gamma编码后的sRGB值，需要先解码为线性
COLORCHECKER_SRGB = np.array([
    [115, 82, 68],    # Dark Skin
    [194, 150, 130],  # Light Skin
    [98, 122, 157],   # Blue Sky
    [87, 108, 67],    # Foliage
    [133, 128, 177],  # Blue Flower
    [103, 189, 170],  # Bluish Green
    [214, 126, 44],   # Orange
    [80, 91, 166],    # Purplish Blue
    [193, 90, 99],    # Moderate Red
    [94, 60, 108],    # Purple
    [157, 188, 64],   # Yellow Green
    [224, 163, 46],   # Orange Yellow
    [56, 61, 150],    # Blue
    [70, 148, 73],    # Green
    [175, 54, 60],    # Red
    [231, 199, 31],   # Yellow
    [187, 86, 149],   # Magenta
    [8, 133, 161],    # Cyan
    [243, 243, 242],  # White
    [200, 200, 200],  # Neutral 8
    [160, 160, 160],  # Neutral 6.5
    [122, 122, 121],  # Neutral 5
    [85, 85, 85],     # Neutral 3.5
    [52, 52, 52],     # Black
]) / 255.0

def srgb_to_linear(srgb):
    """将sRGB解码为线性RGB"""
    linear = np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + 0.055) / 1.055) ** 2.4
    )
    return linear
```

---

## 4. Gamma校正

### 4.1 为什么需要Gamma校正？

#### 线性光的存储问题

```
┌─────────────────────────────────────────────────────────────────┐
│                    线性编码的位深浪费                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   人眼感知亮度（Weber-Fechner定律）：                            │
│   感知亮度 ≈ log(物理亮度)                                       │
│                                                                  │
│   8bit线性编码的问题：                                           │
│                                                                  │
│   物理亮度    线性编码值    感知亮度                             │
│   ─────────────────────────────────────                         │
│   100%        255          最亮                                  │
│    50%        128          中等偏亮                              │
│    25%         64          中等                                  │
│    12.5%       32          中等偏暗                              │
│     1%          3          暗（仅3级灰阶！）                      │
│                                                                  │
│   → 大量bit浪费在高光区，暗部严重量化                            │
│                                                                  │
│   Gamma编码的解决方案：                                          │
│   • 对信号做γ次幂压缩                                            │
│   • 分配更多编码值给暗部                                         │
│   • 显示时反向解码                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 sRGB传递函数

sRGB标准定义的Gamma编码是**分段函数**（非简单幂函数）：

$$
V' = \begin{cases}
12.92 \times V & V \leq 0.0031308 \\
1.055 \times V^{1/2.4} - 0.055 & V > 0.0031308
\end{cases}
$$

反向解码（EOTF）：

$$
V = \begin{cases}
V' / 12.92 & V' \leq 0.04045 \\
\left( \frac{V' + 0.055}{1.055} \right)^{2.4} & V' > 0.04045
\end{cases}
$$

#### 实现代码

```python
def srgb_oetf(linear):
    """sRGB编码：线性 → sRGB（用于存储）"""
    return np.where(
        linear <= 0.0031308,
        12.92 * linear,
        1.055 * np.power(linear, 1/2.4) - 0.055
    )

def srgb_eotf(encoded):
    """sRGB解码：sRGB → 线性（用于处理）"""
    return np.where(
        encoded <= 0.04045,
        encoded / 12.92,
        np.power((encoded + 0.055) / 1.055, 2.4)
    )
```

### 4.3 BT.709传递函数

高清电视标准BT.709的传递函数（与sRGB类似但参数不同）：

$$
V' = \begin{cases}
4.5 \times V & V < 0.018 \\
1.099 \times V^{0.45} - 0.099 & V \geq 0.018
\end{cases}
$$

```python
def bt709_oetf(linear):
    """BT.709编码"""
    return np.where(
        linear < 0.018,
        4.5 * linear,
        1.099 * np.power(linear, 0.45) - 0.099
    )
```

### 4.4 PQ和HLG传递函数概述

#### PQ（Perceptual Quantizer）- HDR10

针对HDR设计，基于人眼Barten模型，可表示0-10000 nits亮度：

$$
V' = \left( \frac{c_1 + c_2 \cdot L^{m_1}}{1 + c_3 \cdot L^{m_1}} \right)^{m_2}
$$

其中 $L$ 是归一化到10000 nits的绝对亮度。

#### HLG（Hybrid Log-Gamma）- 广播HDR

为兼容SDR设计的HDR传递函数：

$$
V' = \begin{cases}
\sqrt{3 \cdot V} & 0 \leq V \leq 1/12 \\
a \cdot \ln(12V - b) + c & 1/12 < V \leq 1
\end{cases}
$$

```python
def pq_oetf(linear, L_max=10000):
    """PQ编码（简化实现）"""
    m1, m2 = 0.1593017578125, 78.84375
    c1, c2, c3 = 0.8359375, 18.8515625, 18.6875
    
    L = linear * L_max / 10000  # 归一化到10000 nits
    L_m1 = np.power(L, m1)
    
    return np.power((c1 + c2 * L_m1) / (1 + c3 * L_m1), m2)

def hlg_oetf(linear):
    """HLG编码"""
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    
    return np.where(
        linear <= 1/12,
        np.sqrt(3 * linear),
        a * np.log(12 * linear - b) + c
    )
```

### 4.5 传递函数对比

| 标准 | 应用场景 | 峰值亮度 | 主要特点 |
|------|---------|---------|---------|
| **sRGB** | 网络、普通显示器 | ~80 nits | 广泛兼容，SDR标准 |
| **BT.709** | 高清电视 | ~100 nits | 电视广播标准 |
| **PQ** | HDR10、Dolby Vision | 10000 nits | 绝对亮度映射 |
| **HLG** | 广播HDR | 相对亮度 | SDR兼容性好 |

---

## 5. 端到端示例

### 5.1 完整处理流程代码

```python
import numpy as np

class RAWtoRGBPipeline:
    """RAW到sRGB的完整转换管线"""
    
    def __init__(self, black_level=64, white_level=1023, bayer_pattern='RGGB'):
        self.black_level = black_level
        self.white_level = white_level
        self.bayer_pattern = bayer_pattern
        
    def black_level_correction(self, raw):
        """黑电平校正"""
        corrected = raw.astype(np.float32) - self.black_level
        corrected = np.clip(corrected, 0, self.white_level - self.black_level)
        # 归一化到 [0, 1]
        return corrected / (self.white_level - self.black_level)
    
    def white_balance(self, bayer, method='gray_world'):
        """白平衡"""
        if method == 'gray_world':
            gains = self._gray_world_gains(bayer)
        elif method == 'max_rgb':
            gains = self._max_rgb_gains(bayer)
        else:
            gains = np.array([1.0, 1.0, 1.0])
        
        return self._apply_bayer_gains(bayer, gains)
    
    def _gray_world_gains(self, bayer):
        """Gray World白平衡增益计算"""
        R = bayer[0::2, 0::2]
        Gr = bayer[0::2, 1::2]
        Gb = bayer[1::2, 0::2]
        B = bayer[1::2, 1::2]
        
        avg_R = np.mean(R)
        avg_G = (np.mean(Gr) + np.mean(Gb)) / 2
        avg_B = np.mean(B)
        
        return np.array([avg_G/avg_R, 1.0, avg_G/avg_B])
    
    def _max_rgb_gains(self, bayer):
        """Max RGB白平衡增益计算"""
        R = bayer[0::2, 0::2]
        Gr = bayer[0::2, 1::2]
        Gb = bayer[1::2, 0::2]
        B = bayer[1::2, 1::2]
        
        max_R = np.percentile(R, 99)
        max_G = (np.percentile(Gr, 99) + np.percentile(Gb, 99)) / 2
        max_B = np.percentile(B, 99)
        
        return np.array([max_G/max_R, 1.0, max_G/max_B])
    
    def _apply_bayer_gains(self, bayer, gains):
        """应用增益到Bayer域"""
        result = bayer.copy()
        result[0::2, 0::2] *= gains[0]  # R
        result[0::2, 1::2] *= gains[1]  # Gr
        result[1::2, 0::2] *= gains[1]  # Gb
        result[1::2, 1::2] *= gains[2]  # B
        return np.clip(result, 0, 1)
    
    def demosaic(self, bayer):
        """简单双线性去马赛克"""
        h, w = bayer.shape
        rgb = np.zeros((h, w, 3))
        
        # R通道
        rgb[0::2, 0::2, 0] = bayer[0::2, 0::2]
        rgb[0::2, 1::2, 0] = (bayer[0::2, 0::2][:, :-1] + bayer[0::2, 0::2][:, 1:]) / 2
        rgb[1::2, 0::2, 0] = (bayer[0::2, 0::2][:-1, :] + bayer[0::2, 0::2][1:, :]) / 2
        rgb[1::2, 1::2, 0] = (bayer[0::2, 0::2][:-1, :-1] + bayer[0::2, 0::2][:-1, 1:] +
                              bayer[0::2, 0::2][1:, :-1] + bayer[0::2, 0::2][1:, 1:]) / 4
        
        # G通道（简化处理）
        rgb[0::2, 0::2, 1] = (bayer[0::2, 1::2][:, :-1] + bayer[1::2, 0::2][:-1, :]) / 2
        rgb[0::2, 1::2, 1] = bayer[0::2, 1::2]
        rgb[1::2, 0::2, 1] = bayer[1::2, 0::2]
        rgb[1::2, 1::2, 1] = (bayer[0::2, 1::2][:-1, :] + bayer[1::2, 0::2][:, :-1]) / 2
        
        # B通道
        rgb[1::2, 1::2, 2] = bayer[1::2, 1::2]
        rgb[1::2, 0::2, 2] = (bayer[1::2, 1::2][:, :-1] + bayer[1::2, 1::2][:, 1:]) / 2
        rgb[0::2, 1::2, 2] = (bayer[1::2, 1::2][:-1, :] + bayer[1::2, 1::2][1:, :]) / 2
        rgb[0::2, 0::2, 2] = (bayer[1::2, 1::2][:-1, :-1] + bayer[1::2, 1::2][:-1, 1:] +
                              bayer[1::2, 1::2][1:, :-1] + bayer[1::2, 1::2][1:, 1:]) / 4
        
        return np.clip(rgb, 0, 1)
    
    def apply_ccm(self, rgb, ccm):
        """应用色彩校正矩阵"""
        h, w, _ = rgb.shape
        rgb_flat = rgb.reshape(-1, 3)
        result_flat = rgb_flat @ ccm.T
        return np.clip(result_flat.reshape(h, w, 3), 0, 1)
    
    def gamma_encode(self, linear, standard='srgb'):
        """Gamma编码"""
        if standard == 'srgb':
            return np.where(
                linear <= 0.0031308,
                12.92 * linear,
                1.055 * np.power(linear, 1/2.4) - 0.055
            )
        elif standard == 'bt709':
            return np.where(
                linear < 0.018,
                4.5 * linear,
                1.099 * np.power(linear, 0.45) - 0.099
            )
        else:
            return np.power(linear, 1/2.2)  # 简单Gamma 2.2
    
    def process(self, raw, ccm=None):
        """
        完整处理流程
        
        Args:
            raw: 原始Bayer RAW数据
            ccm: 色彩校正矩阵（可选）
        
        Returns:
            sRGB图像 (8bit, 0-255)
        """
        # 1. 黑电平校正
        bayer = self.black_level_correction(raw)
        
        # 2. 白平衡
        bayer_wb = self.white_balance(bayer, method='gray_world')
        
        # 3. 去马赛克
        linear_rgb = self.demosaic(bayer_wb)
        
        # 4. 色彩校正（如果提供CCM）
        if ccm is not None:
            linear_rgb = self.apply_ccm(linear_rgb, ccm)
        
        # 5. Gamma编码
        srgb = self.gamma_encode(linear_rgb, standard='srgb')
        
        # 6. 转换为8bit输出
        output = (srgb * 255).astype(np.uint8)
        
        return output


# 使用示例
if __name__ == '__main__':
    # 模拟10bit RAW数据
    raw = np.random.randint(64, 1024, (1080, 1920), dtype=np.uint16)
    
    # 示例CCM（单位矩阵，实际需要标定）
    ccm = np.array([
        [1.5, -0.3, -0.2],
        [-0.2, 1.4, -0.2],
        [-0.1, -0.3, 1.4]
    ])
    
    # 创建处理管线
    pipeline = RAWtoRGBPipeline(black_level=64, white_level=1023)
    
    # 处理
    srgb_output = pipeline.process(raw, ccm)
    
    print(f"输出尺寸: {srgb_output.shape}")
    print(f"输出范围: [{srgb_output.min()}, {srgb_output.max()}]")
```

### 5.2 处理流程可视化

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RAW → sRGB 端到端流程                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   输入RAW (10bit, 1920×1080)                                                │
│         ↓                                                                    │
│   ┌─────────────────┐                                                       │
│   │ 黑电平校正      │  raw' = (raw - 64) / (1023 - 64)                      │
│   │ [0,1] 归一化    │  → 消除暗电流，归一化到浮点                            │
│   └────────┬────────┘                                                       │
│            ↓                                                                 │
│   ┌─────────────────┐                                                       │
│   │ 白平衡 (Bayer)  │  R×1.2, G×1.0, B×1.5 （示例增益）                     │
│   │ Gray World     │  → 消除色温偏差                                        │
│   └────────┬────────┘                                                       │
│            ↓                                                                 │
│   ┌─────────────────┐                                                       │
│   │ Demosaic       │  Bayer (H×W×1) → RGB (H×W×3)                           │
│   │ 双线性插值      │  → 重建完整彩色图像                                    │
│   └────────┬────────┘                                                       │
│            ↓                                                                 │
│   ┌─────────────────┐                                                       │
│   │ CCM色彩校正     │  RGB_out = CCM × RGB_in                               │
│   │ 3×3矩阵        │  → 映射到sRGB色域                                      │
│   └────────┬────────┘                                                       │
│            ↓                                                                 │
│   ┌─────────────────┐                                                       │
│   │ sRGB Gamma     │  线性 → sRGB传递函数                                   │
│   │ 编码           │  → 感知优化编码                                        │
│   └────────┬────────┘                                                       │
│            ↓                                                                 │
│   输出sRGB (8bit, 1920×1080×3)                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 参考资源

### 学术文献

1. **Ramanath, R. et al.** (2005). "Color Image Processing Pipeline." *IEEE Signal Processing Magazine*
2. **Kasson, J. & Plouffe, W.** (1992). "An Analysis of Selected Computer Interchange Color Spaces." *ACM Transactions on Graphics*
3. **Finlayson, G. & Trezzi, E.** (2004). "Shades of Gray and Colour Constancy." *Color and Imaging Conference*

### 标准规范

- **IEC 61966-2-1**: sRGB色彩空间标准
- **ITU-R BT.709**: 高清电视标准
- **ITU-R BT.2100**: HDR电视标准（PQ/HLG）
- **SMPTE ST 2084**: PQ传递函数规范

### 开源实现

- **dcraw**: Dave Coffin的RAW解码器（C语言）
- **LibRaw**: 现代RAW处理库
- **rawpy**: Python的RAW处理绑定
- **darktable**: 开源RAW图像工作流

### 工具与资源

- **X-Rite ColorChecker**: 色彩标定色卡
- **Imatest**: 图像质量测试软件
- **Colour-Science for Python**: 色彩科学Python库

---

*本文档涵盖了RAW到RGB转换的核心算法与实现，从白平衡、色彩校正到Gamma编码的完整链路。实际ISP实现还需考虑降噪、锐化、色调映射等更多环节。*

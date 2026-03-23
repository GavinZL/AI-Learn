# HDR合成算法详细解析

> 从多曝光融合到Ghost去除：高动态范围图像生成的完整技术链路

---

## 目录

1. [HDR合成问题定义](#1-hdr合成问题定义)
2. [相机响应函数恢复](#2-相机响应函数恢复)
3. [曝光融合](#3-曝光融合)
4. [HDR合成算法](#4-hdr合成算法)
5. [Ghost去除](#5-ghost去除)
6. [帧对齐](#6-帧对齐)
7. [实际应用](#7-实际应用)
8. [参考资源](#8-参考资源)

---

## 1. HDR合成问题定义

### 1.1 从多张LDR曝光合成高动态范围图像

HDR合成的核心思想：**结合不同曝光的图像，获取场景完整的亮度信息**。

```
┌─────────────────────────────────────────────────────────────────┐
│                    HDR合成原理                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   短曝光 (1/1000s)       中曝光 (1/250s)        长曝光 (1/60s)  │
│   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐ │
│   │ ████        │        │ ████████    │        │ ████████████│ │
│   │ ██          │        │ ████████    │        │ ████████████│ │
│   │             │        │ ██████      │        │ ████████████│ │
│   │             │        │ ████        │        │ ████████████│ │
│   └─────────────┘        └─────────────┘        └─────────────┘ │
│   亮部有细节              中间调适中             暗部有细节      │
│   暗部欠曝                                       亮部过曝        │
│                                                                  │
│         │                    │                    │              │
│         └────────────────────┼────────────────────┘              │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │   HDR合成算法   │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│                             ▼                                    │
│                    ┌─────────────────┐                          │
│                    │ HDR辐照度图     │                          │
│                    │ (32bit float)   │                          │
│                    │ ████████████████│                          │
│                    │ ████████████████│ 全范围细节               │
│                    │ ████████████████│                          │
│                    │ ████████████████│                          │
│                    └─────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 成像模型与CRF

相机的成像过程可建模为：

$$
Z = f(E \cdot \Delta t)
$$

其中：
- $Z$ 是像素值（8/12/14bit）
- $E$ 是场景辐照度（irradiance）
- $\Delta t$ 是曝光时间
- $f(\cdot)$ 是**相机响应函数**（CRF, Camera Response Function）

```
┌─────────────────────────────────────────────────────────────────┐
│                  相机响应函数 (CRF)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   像素值 Z                                                       │
│       255 ┤                            ────────────             │
│           │                       ────                           │
│           │                  ────                                │
│       200 ┤              ───                                     │
│           │           ──                                         │
│           │         ─                                            │
│       150 ┤       ─        典型CRF                               │
│           │      ─         (S型非线性)                           │
│           │     ─                                                │
│       100 ┤    ─                                                 │
│           │   ─                                                  │
│           │  ─                                                   │
│        50 ┤ ─                                                    │
│           │─                                                     │
│           │                                                      │
│         0 ┼─────────────────────────────────────────────────→   │
│           0        E·Δt (曝光量，对数尺度)         高            │
│                                                                  │
│   理想CRF: 线性 (科学相机)                                       │
│   实际CRF: 非线性 (胶片特性、显示优化、Gamma等)                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 HDR合成的数学框架

已知多张不同曝光时间的图像，反推场景辐照度：

$$
E = \frac{f^{-1}(Z)}{\Delta t}
$$

多曝光加权融合：

$$
E(x,y) = \frac{\sum_{j=1}^{P} w(Z_j(x,y)) \cdot \frac{f^{-1}(Z_j(x,y))}{\Delta t_j}}{\sum_{j=1}^{P} w(Z_j(x,y))}
$$

其中 $w(Z)$ 是权重函数，用于降低过曝/欠曝像素的贡献。

---

## 2. 相机响应函数恢复

### 2.1 Debevec-Malik方法

经典的CRF恢复算法，将问题转化为线性优化：

$$
g(Z_{ij}) = \ln E_i + \ln \Delta t_j
$$

其中 $g = \ln f^{-1}$，通过最小化以下目标函数：

$$
\min_{g, E} \sum_{i,j} [g(Z_{ij}) - \ln E_i - \ln \Delta t_j]^2 + \lambda \sum_{z=1}^{254} g''(z)^2
$$

```
┌─────────────────────────────────────────────────────────────────┐
│               Debevec-Malik算法流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   输入: 多曝光图像序列 + 曝光时间                                │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  1. 采样像素位置                                         │   │
│   │     - 从图像中随机选取N个像素位置                        │   │
│   │     - 确保覆盖不同亮度区域                               │   │
│   │     - 典型N = 50-100                                     │   │
│   │                                                          │   │
│   │  2. 构建方程组 Ax = b                                    │   │
│   │     - 数据项: g(Zij) = ln(Ei) + ln(Δtj)                 │   │
│   │     - 平滑项: λ · g''(z) = 0                            │   │
│   │     - 约束: g(128) = 0 (中值归一化)                     │   │
│   │                                                          │   │
│   │  3. 最小二乘求解                                         │   │
│   │     - 超定方程组，使用SVD或QR分解                        │   │
│   │     - 得到g(z)曲线 (256个值)                            │   │
│   │                                                          │   │
│   │  4. 计算CRF                                              │   │
│   │     f⁻¹(z) = exp(g(z))                                  │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   输出: 相机响应函数曲线 f⁻¹(z)                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

```python
import numpy as np

def recover_crf_debevec(images, exposure_times, lambda_smooth=50, n_samples=100):
    """
    Debevec-Malik CRF恢复算法
    
    参数:
        images: list of LDR images [P, H, W]
        exposure_times: list of exposure times
        lambda_smooth: 平滑权重
        n_samples: 采样像素数
    返回:
        g: 响应曲线 g(z) = ln(f⁻¹(z)), shape [256]
    """
    n_exposures = len(images)
    z_min, z_max = 0, 255
    z_mid = 128
    
    # 像素采样
    h, w = images[0].shape
    indices = np.random.choice(h * w, n_samples, replace=False)
    
    # 收集采样点的像素值
    Z = np.zeros((n_samples, n_exposures), dtype=np.uint8)
    for j, img in enumerate(images):
        Z[:, j] = img.flatten()[indices]
    
    # 构建方程组
    n = 256  # 灰度级数
    n_equations = n_samples * n_exposures + n + 1
    n_unknowns = n + n_samples  # g(z) + ln(E_i)
    
    A = np.zeros((n_equations, n_unknowns))
    b = np.zeros(n_equations)
    
    # 权重函数 (三角形)
    def weight(z):
        if z <= z_mid:
            return z - z_min + 1
        else:
            return z_max - z + 1
    
    k = 0  # 方程索引
    
    # 数据拟合方程
    for i in range(n_samples):
        for j in range(n_exposures):
            z = Z[i, j]
            w = weight(z)
            A[k, z] = w
            A[k, n + i] = -w
            b[k] = w * np.log(exposure_times[j])
            k += 1
    
    # 约束 g(128) = 0
    A[k, z_mid] = 1
    k += 1
    
    # 平滑方程
    for z in range(1, n - 1):
        w = weight(z)
        A[k, z - 1] = lambda_smooth * w
        A[k, z] = -2 * lambda_smooth * w
        A[k, z + 1] = lambda_smooth * w
        k += 1
    
    # 最小二乘求解
    x, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    g = x[:n]
    
    return g

def apply_crf_inverse(image, g):
    """应用CRF逆函数"""
    return np.exp(g[image])
```

### 2.2 Robertson方法

Robertson方法采用**迭代优化**，更加稳健：

```python
def recover_crf_robertson(images, exposure_times, iterations=10):
    """
    Robertson迭代CRF恢复
    
    特点：
    - 不需要预先采样
    - 迭代优化E和f
    - 对噪声更鲁棒
    """
    n_exp = len(images)
    shape = images[0].shape
    
    # 初始化CRF为线性
    g = np.arange(256).astype(np.float32) / 255.0
    
    # 权重函数
    w = np.array([min(z, 255-z) for z in range(256)], dtype=np.float32)
    w = w / w.max()
    
    for iteration in range(iterations):
        # E-step: 固定g，估计E
        E = np.zeros(shape, dtype=np.float64)
        W = np.zeros(shape, dtype=np.float64)
        
        for j, (img, dt) in enumerate(zip(images, exposure_times)):
            weight_map = w[img]
            E += weight_map * g[img] / dt
            W += weight_map
        
        E = E / (W + 1e-10)
        
        # M-step: 固定E，更新g
        g_new = np.zeros(256, dtype=np.float64)
        g_count = np.zeros(256, dtype=np.float64)
        
        for j, (img, dt) in enumerate(zip(images, exposure_times)):
            expected = E * dt
            for z in range(256):
                mask = img == z
                if np.any(mask):
                    g_new[z] += np.sum(expected[mask] * w[z])
                    g_count[z] += np.sum(mask) * w[z]
        
        g = g_new / (g_count + 1e-10)
        g = g / g[128]  # 归一化
    
    return g
```

---

## 3. 曝光融合

### 3.1 Mertens算法

**曝光融合**（Exposure Fusion）直接融合LDR图像，无需计算HDR：

$$
R(x,y) = \sum_{j=1}^{P} W_j(x,y) \cdot I_j(x,y)
$$

权重由三个质量度量的乘积决定：

$$
W_j = (C_j)^{\omega_c} \cdot (S_j)^{\omega_s} \cdot (E_j)^{\omega_e}
$$

```
┌─────────────────────────────────────────────────────────────────┐
│               Mertens曝光融合权重                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. 对比度 (Contrast)                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  C = |Laplacian(I)|                                      │   │
│   │                                                          │   │
│   │  作用：选择局部细节丰富的像素                            │   │
│   │  高对比度区域获得更高权重                                │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   2. 饱和度 (Saturation)                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  S = std(R, G, B)                                        │   │
│   │                                                          │   │
│   │  作用：选择颜色鲜艳的像素                                │   │
│   │  避免过曝（白色）和欠曝（黑色）的去饱和区域              │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   3. 曝光度 (Well-Exposedness)                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  E = exp(-(I - 0.5)² / (2σ²))                           │   │
│   │                                                          │   │
│   │           1.0 ┤      ●───●                               │   │
│   │               │    ╱     ╲                               │   │
│   │               │   ╱       ╲                              │   │
│   │           0.5 ┤  ╱         ╲                             │   │
│   │               │ ╱           ╲                            │   │
│   │               │╱             ╲                           │   │
│   │           0.0 ┼───────────────→                          │   │
│   │               0  0.25  0.5  0.75  1.0  像素值           │   │
│   │                                                          │   │
│   │  作用：偏好中间调，避免极端曝光                          │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 拉普拉斯金字塔融合

为避免直接融合产生的伪影，使用**多尺度金字塔融合**：

```
┌─────────────────────────────────────────────────────────────────┐
│              拉普拉斯金字塔融合                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   图像1          图像2          权重1          权重2            │
│     │              │              │              │               │
│     ▼              ▼              ▼              ▼               │
│   ┌────┐        ┌────┐        ┌────┐        ┌────┐              │
│   │ L₀ │        │ L₀ │        │ G₀ │        │ G₀ │   高分辨率  │
│   ├────┤        ├────┤        ├────┤        ├────┤              │
│   │ L₁ │        │ L₁ │        │ G₁ │        │ G₁ │              │
│   ├────┤        ├────┤        ├────┤        ├────┤              │
│   │ L₂ │        │ L₂ │        │ G₂ │        │ G₂ │              │
│   ├────┤        ├────┤        ├────┤        ├────┤              │
│   │ L₃ │        │ L₃ │        │ G₃ │        │ G₃ │   低分辨率  │
│   └────┘        └────┘        └────┘        └────┘              │
│     │              │              │              │               │
│     └──────┬───────┘              └──────┬───────┘               │
│            │                             │                       │
│            ▼                             ▼                       │
│     在每层进行加权融合: L_fused[k] = W₁[k]·L₁[k] + W₂[k]·L₂[k] │
│                                                                  │
│            │                                                     │
│            ▼                                                     │
│     从金字塔重建最终图像                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

```python
import cv2
import numpy as np

def mertens_fusion(images, weights_contrast=1.0, weights_saturation=1.0, 
                   weights_exposedness=1.0, sigma=0.2):
    """
    Mertens曝光融合实现
    """
    n_images = len(images)
    
    # 计算权重
    weights = []
    for img in images:
        # 转为灰度
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        # 对比度 (Laplacian绝对值)
        contrast = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
        
        # 饱和度 (RGB标准差)
        saturation = img.astype(np.float32).std(axis=2) / 255.0
        
        # 曝光度 (高斯)
        img_norm = img.astype(np.float32) / 255.0
        exposedness = np.exp(-0.5 * ((img_norm - 0.5) ** 2).sum(axis=2) / (sigma ** 2))
        
        # 组合权重
        w = (contrast ** weights_contrast) * \
            (saturation ** weights_saturation) * \
            (exposedness ** weights_exposedness)
        
        weights.append(w + 1e-12)  # 避免除零
    
    # 归一化权重
    weight_sum = np.sum(weights, axis=0)
    weights = [w / weight_sum for w in weights]
    
    # 金字塔融合
    n_levels = int(np.log2(min(images[0].shape[:2]))) - 1
    
    # 构建拉普拉斯金字塔
    def build_laplacian_pyramid(img, levels):
        gaussian = [img]
        for _ in range(levels):
            img = cv2.pyrDown(img)
            gaussian.append(img)
        
        laplacian = []
        for i in range(levels):
            expanded = cv2.pyrUp(gaussian[i+1], dstsize=(gaussian[i].shape[1], gaussian[i].shape[0]))
            laplacian.append(gaussian[i].astype(np.float32) - expanded.astype(np.float32))
        laplacian.append(gaussian[-1].astype(np.float32))
        
        return laplacian
    
    # 构建高斯金字塔（权重）
    def build_gaussian_pyramid(img, levels):
        pyramid = [img]
        for _ in range(levels):
            img = cv2.pyrDown(img)
            pyramid.append(img)
        return pyramid
    
    # 融合
    fused_pyramid = None
    
    for img, w in zip(images, weights):
        lap_pyr = build_laplacian_pyramid(img, n_levels)
        gauss_pyr = build_gaussian_pyramid(w, n_levels)
        
        if fused_pyramid is None:
            fused_pyramid = [np.zeros_like(l) for l in lap_pyr]
        
        for level in range(len(lap_pyr)):
            w_3ch = np.stack([gauss_pyr[level]] * 3, axis=-1)
            fused_pyramid[level] += w_3ch * lap_pyr[level]
    
    # 重建
    result = fused_pyramid[-1]
    for i in range(len(fused_pyramid) - 2, -1, -1):
        result = cv2.pyrUp(result, dstsize=(fused_pyramid[i].shape[1], fused_pyramid[i].shape[0]))
        result = result + fused_pyramid[i]
    
    return np.clip(result, 0, 255).astype(np.uint8)
```

---

## 4. HDR合成算法

### 4.1 辐照度图重建

```python
def merge_hdr_debevec(images, exposure_times, response_curve):
    """
    使用Debevec方法合成HDR辐照度图
    
    参数:
        images: list of LDR images
        exposure_times: 曝光时间列表
        response_curve: CRF逆函数 g(z) = ln(f⁻¹(z))
    """
    # 权重函数
    def weight(z):
        z_min, z_max = 0, 255
        z_mid = (z_min + z_max) / 2
        if z <= z_mid:
            return z - z_min + 1
        else:
            return z_max - z + 1
    
    weights = np.array([weight(z) for z in range(256)])
    
    # 初始化HDR
    hdr = np.zeros(images[0].shape, dtype=np.float64)
    weight_sum = np.zeros(images[0].shape, dtype=np.float64)
    
    for img, dt in zip(images, exposure_times):
        w = weights[img]
        ln_E = response_curve[img] - np.log(dt)
        
        hdr += w * ln_E
        weight_sum += w
    
    # 避免除零
    mask = weight_sum > 0
    hdr[mask] = np.exp(hdr[mask] / weight_sum[mask])
    hdr[~mask] = 0
    
    return hdr.astype(np.float32)
```

### 4.2 权重函数设计

| 权重函数 | 公式 | 特点 |
|----------|------|------|
| 三角形 | $w(z) = \min(z, 255-z)$ | 简单有效 |
| 高斯 | $w(z) = \exp(-\frac{(z-128)^2}{2\sigma^2})$ | 平滑 |
| 帽子 | $w(z) = 1 - (2z/255 - 1)^{12}$ | 中值平坦 |
| Debevec | $w(z) = z + 1$ if $z < 128$ else $256 - z$ | 经典 |

```
┌─────────────────────────────────────────────────────────────────┐
│                    权重函数对比                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   权重                                                           │
│   1.0 ┤              ───────────────   帽子(Hat)               │
│       │           ╱─                 ─╲                          │
│       │         ╱  ────────────────── ╲  高斯(Gaussian)        │
│   0.8 ┤        ╱  ╱                  ╲ ╲                        │
│       │       ╱  ╱                    ╲ ╲                        │
│       │      ╱  ╱                      ╲ ╲                       │
│   0.6 ┤     ╱  ╱                        ╲ ╲                      │
│       │    ╱  ╱                          ╲ ╲                     │
│       │   ╱  ╱                            ╲ ╲                    │
│   0.4 ┤  ╱  ╱                              ╲ ╲                   │
│       │ ╱  ╱    三角形(Triangle)            ╲ ╲                  │
│       │╱  ╱                                  ╲ ╲                 │
│   0.2 ┤  ╱                                    ╲ ╲                │
│       │ ╱                                      ╲ ╲               │
│       │╱                                        ╲╲               │
│   0.0 ┼──────────────────────────────────────────────────→      │
│       0        64       128       192       255  像素值          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Ghost去除

### 5.1 运动检测方法

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ghost伪影问题                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   曝光1              曝光2              曝光3                    │
│   ┌─────────┐        ┌─────────┐        ┌─────────┐             │
│   │    🚶   │        │     🚶  │        │      🚶 │   人在移动  │
│   │         │        │         │        │         │             │
│   └─────────┘        └─────────┘        └─────────┘             │
│                                                                  │
│   直接HDR合成结果:                                               │
│   ┌─────────────────────────────┐                               │
│   │   👻  👻  👻               │   三个半透明人影               │
│   │                             │   = Ghost伪影                 │
│   └─────────────────────────────┘                               │
│                                                                  │
│   Ghost检测与去除后:                                             │
│   ┌─────────────────────────────┐                               │
│   │        🚶                   │   只保留参考帧的人            │
│   │                             │                               │
│   └─────────────────────────────┘                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 位图方法检测

```python
def detect_ghost_bitmap(images, reference_idx=None):
    """
    基于位图的Ghost检测
    
    思路：
    1. 选择参考帧（通常是中间曝光）
    2. 将所有图像二值化
    3. 比较二值图差异，差异大的区域为Ghost
    """
    if reference_idx is None:
        reference_idx = len(images) // 2
    
    h, w = images[0].shape[:2]
    ghost_masks = []
    
    # 计算中值阈值位图
    def compute_mtb(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        median = np.median(gray)
        return (gray > median).astype(np.uint8)
    
    ref_mtb = compute_mtb(images[reference_idx])
    
    for i, img in enumerate(images):
        if i == reference_idx:
            ghost_masks.append(np.ones((h, w), dtype=np.uint8))
            continue
        
        # 曝光补偿：调整亮度后再比较
        # 这里简化处理
        mtb = compute_mtb(img)
        
        # XOR检测差异
        diff = cv2.bitwise_xor(ref_mtb, mtb)
        
        # 形态学操作去除噪声
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        diff = cv2.morphologyEx(diff, cv2.MORPH_OPEN, kernel)
        diff = cv2.morphologyEx(diff, cv2.MORPH_CLOSE, kernel)
        
        # 反转：差异区域为0（不使用），一致区域为1（使用）
        ghost_mask = 1 - diff
        ghost_masks.append(ghost_mask)
    
    return ghost_masks
```

### 5.3 梯度方法检测

```python
def detect_ghost_gradient(images, reference_idx=None, threshold=0.1):
    """
    基于梯度一致性的Ghost检测
    
    思路：
    如果是静态场景，不同曝光图像的梯度方向应该一致
    """
    if reference_idx is None:
        reference_idx = len(images) // 2
    
    def compute_gradient(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        return gx, gy
    
    ref_gx, ref_gy = compute_gradient(images[reference_idx])
    ref_magnitude = np.sqrt(ref_gx**2 + ref_gy**2) + 1e-10
    
    ghost_masks = []
    
    for i, img in enumerate(images):
        if i == reference_idx:
            ghost_masks.append(np.ones(img.shape[:2], dtype=np.float32))
            continue
        
        gx, gy = compute_gradient(img)
        magnitude = np.sqrt(gx**2 + gy**2) + 1e-10
        
        # 归一化梯度
        ref_gx_norm = ref_gx / ref_magnitude
        ref_gy_norm = ref_gy / ref_magnitude
        gx_norm = gx / magnitude
        gy_norm = gy / magnitude
        
        # 梯度方向一致性（点积）
        consistency = ref_gx_norm * gx_norm + ref_gy_norm * gy_norm
        
        # 一致性高的区域为有效区域
        mask = (consistency > (1 - threshold)).astype(np.float32)
        
        # 平滑
        mask = cv2.GaussianBlur(mask, (15, 15), 5)
        
        ghost_masks.append(mask)
    
    return ghost_masks
```

### 5.4 去Ghost融合策略

```python
def merge_hdr_deghost(images, exposure_times, response_curve, ghost_masks):
    """
    带Ghost去除的HDR合成
    """
    weights = np.array([min(z, 255-z) + 1 for z in range(256)])
    
    hdr = np.zeros(images[0].shape, dtype=np.float64)
    weight_sum = np.zeros(images[0].shape, dtype=np.float64)
    
    for img, dt, ghost_mask in zip(images, exposure_times, ghost_masks):
        w = weights[img] * ghost_mask[:, :, np.newaxis]  # 加入Ghost掩码
        ln_E = response_curve[img] - np.log(dt)
        
        hdr += w * ln_E
        weight_sum += w
    
    mask = weight_sum > 0
    hdr[mask] = np.exp(hdr[mask] / weight_sum[mask])
    hdr[~mask] = 0
    
    return hdr.astype(np.float32)
```

---

## 6. 帧对齐

### 6.1 MTB快速对齐

**MTB**（Median Threshold Bitmap）是一种对曝光不变的对齐方法：

```
┌─────────────────────────────────────────────────────────────────┐
│                    MTB对齐算法                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   核心思想：                                                     │
│   中值阈值位图对曝光变化不敏感                                   │
│                                                                  │
│   原理:                                                          │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │                                                            │ │
│   │  亮图像          暗图像          MTB                       │ │
│   │  ┌────────┐      ┌────────┐      ┌────────┐               │ │
│   │  │████████│      │██      │      │████    │  中值以上=1   │ │
│   │  │████████│  →   │██████  │  →   │████    │  中值以下=0   │ │
│   │  │████    │      │████████│      │████    │               │ │
│   │  │██      │      │████████│      │████    │               │ │
│   │  └────────┘      └────────┘      └────────┘               │ │
│   │                                                            │ │
│   │  虽然整体亮度不同，但MTB结构相似                          │ │
│   │                                                            │ │
│   └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│   金字塔加速:                                                    │
│   1. 构建图像金字塔                                              │
│   2. 从最粗层开始，计算MTB XOR                                   │
│   3. 搜索最小XOR对应的偏移                                       │
│   4. 将偏移传递到下一层，细化搜索                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

```python
def align_mtb(images, max_shift=64):
    """
    MTB对齐算法
    
    返回对齐后的图像列表
    """
    def compute_mtb_and_mask(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        median = np.median(gray)
        
        # MTB
        mtb = (gray > median).astype(np.uint8)
        
        # 排除掩码（接近中值的像素不可靠）
        exclusion = np.abs(gray.astype(np.float32) - median) < 4
        
        return mtb, (~exclusion).astype(np.uint8)
    
    def get_shift(mtb1, mask1, mtb2, mask2, search_range=1):
        """在小范围内搜索最佳偏移"""
        best_shift = (0, 0)
        min_error = float('inf')
        
        for dy in range(-search_range, search_range + 1):
            for dx in range(-search_range, search_range + 1):
                # 平移
                M = np.float32([[1, 0, dx], [0, 1, dy]])
                shifted_mtb2 = cv2.warpAffine(mtb2, M, (mtb2.shape[1], mtb2.shape[0]))
                shifted_mask2 = cv2.warpAffine(mask2, M, (mask2.shape[1], mask2.shape[0]))
                
                # XOR误差
                combined_mask = mask1 & shifted_mask2
                diff = cv2.bitwise_xor(mtb1, shifted_mtb2) & combined_mask
                error = np.sum(diff)
                
                if error < min_error:
                    min_error = error
                    best_shift = (dx, dy)
        
        return best_shift
    
    # 参考帧
    ref_idx = len(images) // 2
    ref_image = images[ref_idx]
    
    # 计算偏移
    aligned = []
    for i, img in enumerate(images):
        if i == ref_idx:
            aligned.append(img.copy())
            continue
        
        # 金字塔层数
        n_levels = int(np.log2(max_shift))
        
        total_shift = [0, 0]
        
        # 从粗到细
        for level in range(n_levels - 1, -1, -1):
            scale = 2 ** level
            
            # 缩小
            ref_small = cv2.resize(ref_image, None, fx=1/scale, fy=1/scale)
            img_small = cv2.resize(img, None, fx=1/scale, fy=1/scale)
            
            # 计算MTB
            ref_mtb, ref_mask = compute_mtb_and_mask(ref_small)
            img_mtb, img_mask = compute_mtb_and_mask(img_small)
            
            # 应用累积偏移
            if total_shift != [0, 0]:
                M = np.float32([[1, 0, total_shift[0]], [0, 1, total_shift[1]]])
                img_mtb = cv2.warpAffine(img_mtb, M, (img_mtb.shape[1], img_mtb.shape[0]))
                img_mask = cv2.warpAffine(img_mask, M, (img_mask.shape[1], img_mask.shape[0]))
            
            # 搜索该层的偏移
            shift = get_shift(ref_mtb, ref_mask, img_mtb, img_mask)
            
            # 更新累积偏移
            total_shift[0] = total_shift[0] * 2 + shift[0]
            total_shift[1] = total_shift[1] * 2 + shift[1]
        
        # 应用最终偏移
        M = np.float32([[1, 0, total_shift[0]], [0, 1, total_shift[1]]])
        aligned_img = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
        aligned.append(aligned_img)
    
    return aligned
```

### 6.2 特征点对齐

对于有显著运动的场景，使用特征点匹配：

```python
def align_features(images, reference_idx=None):
    """
    基于ORB特征的图像对齐
    """
    if reference_idx is None:
        reference_idx = len(images) // 2
    
    ref = images[reference_idx]
    ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    
    # ORB检测器
    orb = cv2.ORB_create(nfeatures=5000)
    ref_kp, ref_desc = orb.detectAndCompute(ref_gray, None)
    
    # 匹配器
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    aligned = []
    for i, img in enumerate(images):
        if i == reference_idx:
            aligned.append(img.copy())
            continue
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kp, desc = orb.detectAndCompute(gray, None)
        
        # 匹配
        matches = bf.match(ref_desc, desc)
        matches = sorted(matches, key=lambda x: x.distance)[:100]
        
        # 提取匹配点
        src_pts = np.float32([ref_kp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # 计算单应性矩阵
        H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
        
        # 变换
        aligned_img = cv2.warpPerspective(img, H, (ref.shape[1], ref.shape[0]))
        aligned.append(aligned_img)
    
    return aligned
```

---

## 7. 实际应用

### 7.1 手机HDR拍照（Google HDR+）

```
┌─────────────────────────────────────────────────────────────────┐
│                 Google HDR+ 技术分析                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   核心创新：短曝光连拍 + 计算摄影                                │
│                                                                  │
│   传统HDR:          HDR+:                                        │
│   ┌─────┐           ┌─────┬─────┬─────┬─────┐                   │
│   │长曝光│           │短曝光│短曝光│短曝光│...│  连续拍摄         │
│   ├─────┤           └──┬──┴──┬──┴──┬──┴──┬──┘  同一曝光        │
│   │中曝光│              │     │     │     │                      │
│   ├─────┤              ▼     ▼     ▼     ▼                      │
│   │短曝光│           ┌─────────────────────────┐                │
│   └─────┘           │     对齐 + 融合         │                │
│                     └───────────┬─────────────┘                │
│   问题:                         │                               │
│   - 长曝光模糊                  ▼                               │
│   - 对齐困难              ┌───────────┐                         │
│   - Ghost明显             │  超分辨率  │                         │
│                           │  降噪合成  │                         │
│   HDR+优势:               └─────┬─────┘                         │
│   - 无运动模糊                  │                               │
│   - 更好对齐                    ▼                               │
│   - 低噪声                 最终HDR图像                          │
│                                                                  │
│   关键技术:                                                      │
│   1. 零快门延迟（ZSL）：预先缓存帧                               │
│   2. 鲁棒对齐：金字塔对齐 + 光流                                 │
│   3. 时域降噪：多帧融合                                          │
│   4. 局部色调映射：保留细节                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 实时HDR视频采集

```
┌─────────────────────────────────────────────────────────────────┐
│              实时HDR视频采集方案                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   方案1: 交替曝光 (Alternating Exposure)                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                          │   │
│   │  时间→                                                   │   │
│   │  ┌───┬───┬───┬───┬───┬───┬───┬───┐                      │   │
│   │  │短 │长 │短 │长 │短 │长 │短 │长 │  60fps→30fps HDR    │   │
│   │  └───┴───┴───┴───┴───┴───┴───┴───┘                      │   │
│   │    ↓   ↓                                                 │   │
│   │    └───┴──→ 合成1帧HDR                                  │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   方案2: 分割曝光传感器 (Split-Pixel)                           │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                          │   │
│   │  单像素内两个光电二极管                                  │   │
│   │  ┌─────────┐                                             │   │
│   │  │ 大PD │小PD │  大PD：长曝光，高灵敏度                 │   │
│   │  │ (高) │(低) │  小PD：短曝光，低灵敏度                 │   │
│   │  └─────────┘                                             │   │
│   │                                                          │   │
│   │  同时采集，无时间差，无Ghost                             │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   方案3: DOL-HDR (Digital Overlap)                              │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                          │   │
│   │  逐行曝光时间控制                                        │   │
│   │  行1: ─────────────────────  长曝光                     │   │
│   │  行2: ─────────────────────  长曝光                     │   │
│   │  行3: ─────────  短曝光                                  │   │
│   │  行4: ─────────  短曝光                                  │   │
│   │  ...                                                     │   │
│   │                                                          │   │
│   │  交织读出，最小时间差                                    │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 OpenCV HDR处理示例

```python
import cv2
import numpy as np

def complete_hdr_pipeline(image_paths, exposure_times):
    """
    完整的HDR处理流程
    """
    # 1. 读取图像
    images = [cv2.imread(p) for p in image_paths]
    times = np.array(exposure_times, dtype=np.float32)
    
    # 2. 对齐（可选）
    align_mtb = cv2.createAlignMTB()
    align_mtb.process(images, images)
    
    # 3. 恢复CRF
    calibrate = cv2.createCalibrateDebevec()
    response = calibrate.process(images, times)
    
    # 4. 合成HDR
    merge_debevec = cv2.createMergeDebevec()
    hdr = merge_debevec.process(images, times, response)
    
    # 5. 色调映射
    tonemap = cv2.createTonemap(gamma=2.2)
    ldr = tonemap.process(hdr)
    
    # 或者使用曝光融合（更快，无需CRF）
    merge_mertens = cv2.createMergeMertens()
    fusion = merge_mertens.process(images)
    
    # 6. 转换为8bit
    ldr_8bit = np.clip(ldr * 255, 0, 255).astype(np.uint8)
    fusion_8bit = np.clip(fusion * 255, 0, 255).astype(np.uint8)
    
    return hdr, ldr_8bit, fusion_8bit

# 使用示例
if __name__ == "__main__":
    images = ['exposure_1.jpg', 'exposure_2.jpg', 'exposure_3.jpg']
    times = [1/30, 1/125, 1/500]  # 曝光时间（秒）
    
    hdr, ldr, fusion = complete_hdr_pipeline(images, times)
    
    cv2.imwrite('output_hdr.hdr', hdr)
    cv2.imwrite('output_ldr.jpg', ldr)
    cv2.imwrite('output_fusion.jpg', fusion)
```

---

## 8. 参考资源

### 经典论文

1. Debevec, P. E., & Malik, J. (1997). "Recovering High Dynamic Range Radiance Maps from Photographs." *SIGGRAPH*.
2. Mertens, T., et al. (2007). "Exposure Fusion." *Pacific Graphics*.
3. Robertson, M. A., et al. (1999). "Estimation-Theoretic Approach to Dynamic Range Enhancement using Multiple Exposures." *Journal of Electronic Imaging*.
4. Ward, G. (2003). "Fast, Robust Image Registration for Compositing High Dynamic Range Photographs from Hand-Held Exposures." *JGT*.

### 技术博客

- [Google Research: HDR+](https://ai.googleblog.com/2014/10/hdr-low-light-and-high-dynamic-range.html)
- [Marc Levoy's Computational Photography](https://graphics.stanford.edu/courses/cs178/)

### 开源实现

| 项目 | 语言 | 特点 |
|------|------|------|
| [OpenCV HDR Module](https://docs.opencv.org/master/d2/df0/tutorial_py_hdr.html) | C++/Python | 完整HDR管线 |
| [Luminance HDR](https://github.com/LuminanceHDR/LuminanceHDR) | C++/Qt | GUI工具 |
| [HDRMerge](https://github.com/jcelaya/hdrmerge) | C++ | RAW HDR合成 |

### 标准

- **OpenEXR**: 工业标准HDR图像格式
- **Radiance RGBE**: 经典HDR格式
- **PFM**: 便携式浮点图格式

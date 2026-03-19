# RAW域详细解析

> 从传感器原始数据到线性RGB：数字成像的第一站

---

## 目录

1. [RAW数据基础](#1-raw数据基础)
2. [Bayer滤色阵列详解](#2-bayer滤色阵列详解)
3. [Demosaicing算法](#3-demosaicing算法)
4. [白平衡与色彩校正](#4-白平衡与色彩校正)
5. [噪点建模与去除](#5-噪点建模与去除)
6. [RAW格式与标准](#6-raw格式与标准)
7. [应用场景分析](#7-应用场景分析)

---

## 1. RAW数据基础

### 1.1 什么是RAW数据

RAW数据是图像传感器输出的**未经任何处理的原始数字信号**，直接反映了光电转换的结果。

#### 物理意义

```
光子 → 光电二极管 → 电荷积累 → ADC量化 → RAW数据

关键特性：
- 线性响应：输出与接收光子数成正比
- 单通道：每个像素仅记录一种颜色
- 高位深：通常12-16bit（对比JPEG的8bit）
- 传感器原生色域：未映射到任何标准色彩空间
```

#### RAW vs RGB对比

| 特性 | RAW数据 | RGB图像（如JPEG） |
|------|--------|------------------|
| **位深** | 12-16bit | 8bit |
| **通道数** | 1（Bayer） | 3（R,G,B） |
| **线性/非线性** | 线性光 | 非线性（Gamma编码） |
| **白平衡** | 未应用 | 已固化 |
| **色域** | 传感器原生 | sRGB/Adobe RGB等 |
| **压缩** | 通常无损/未压缩 | 有损压缩 |
| **文件大小** | 大（10-50MB） | 小（2-10MB） |

### 1.2 传感器工作原理

#### CMOS传感器架构

```
┌─────────────────────────────────────────────────────────────┐
│                      CMOS像素结构                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   微透镜      滤色片      光电二极管      读出电路            │
│      ↓          ↓            ↓              ↓               │
│   ┌─────┐    ┌─────┐     ┌───────┐     ┌────────┐          │
│   │     │    │  R  │     │       │     │  浮置  │          │
│   │  ◉  │ →  │ 或  │ →   │  P-N  │ →   │  扩散  │ → 电压   │
│   │     │    │  G  │     │  结   │     │  节点  │          │
│   │     │    │ 或  │     │       │     │        │          │
│   │     │    │  B  │     │       │     │        │          │
│   └─────┘    └─────┘     └───────┘     └────────┘          │
│                                                              │
│   光子收集 → 波长选择 → 电荷转换 → 电压读出 → ADC量化        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 光电转换特性

传感器输出与光照强度的关系：

$$
\text{Digital Output} = \text{Gain} \times (\text{Photon Count} \times \text{QE} + \text{Noise})
$$

其中：
- **QE（量子效率）**：光子转换为电子的效率
- **Gain**：模拟增益（ISO控制）
- **Noise**：包含读出噪声、暗电流噪声等

### 1.3 RAW数据的数值特性

#### 位深与动态范围

| 位深 | 灰阶数 | 理论动态范围 | 典型应用 |
|------|-------|-------------|---------|
| 10bit | 1,024 | ~60dB | 早期手机 |
| 12bit | 4,096 | ~72dB | 消费级相机 |
| 14bit | 16,384 | ~84dB | 专业相机 |
| 16bit | 65,536 | ~96dB | 科学成像 |

#### 黑电平（Black Level）

传感器在无光照时仍有输出（暗电流），需要扣除黑电平：

$$
\text{Linear Value} = \frac{\text{RAW Value} - \text{Black Level}}{\text{White Level} - \text{Black Level}}
$$

典型值：
- Black Level：256（14bit）/ 64（12bit）
- White Level：16383（14bit）/ 4095（12bit）

---

## 2. Bayer滤色阵列详解

### 2.1 标准Bayer排列

Bryce Bayer于1976年发明的滤色阵列，是数字成像的事实标准：

```
RGGB排列（最常见的Bayer变体）：

行0:  R  G  R  G  R  G ...
行1:  G  B  G  B  G  B ...
行2:  R  G  R  G  R  G ...
行3:  G  B  G  B  G  B ...

绿色占50%：人眼对绿色最敏感（亮度感知主要依赖绿光）
红色占25%：提供长波色度信息
蓝色占25%：提供短波色度信息
```

#### 其他排列变体

| 排列 | 模式 | 特点 | 应用 |
|------|------|------|------|
| **RGGB** | 标准 | 平衡设计 | 绝大多数相机 |
| **BGGR** | 旋转 | 与RGGB等效 | 部分传感器 |
| **GRBG** | 偏移 | 特定优化 | 专业相机 |
| **GBRG** | 偏移 | 特定优化 | 专业相机 |

### 2.2 非Bayer CFA设计

#### X-Trans（富士）

```
6×6随机排列，减少摩尔纹和伪色：

G G R G G B
R G G B G G
G B G G R G
G G R G G B
R G G B G G
G B G G R G

特点：
- 更均匀的颜色分布
- 减少高频混叠
- 需要专用Demosaic算法
```

#### Quad Bayer（索尼/三星）

```
2×2像素共享同色滤色片：

高分辨率模式（48MP）:
R G R G ...
G B G B ...
R G R G ...
G B G B ...

高灵敏度模式（12MP）:
4个R合并 → 1个R
4个G合并 → 1个G
4个B合并 → 1个B

优势：灵活切换分辨率与灵敏度
```

#### RYYB（华为）

```
用黄色替换绿色：

R Y R Y ...
Y B Y B ...
R Y R Y ...
Y B Y B ...

优势：
- 黄色滤光片透过更多光线（+40%进光量）
- 提升暗光性能

挑战：
- 黄色包含红+绿信息，分离更复杂
- 需要更复杂的AWB算法
```

### 2.3 CFA的光谱特性

不同CFA的光谱响应曲线：

```
透过率 ↑
   │
100%├──────────────────────┐
   │    ┌───┐              │
 75%│    │   │    ┌───┐    │
   │    │   │    │   │    │
 50%│────┘   └────┤   ├────┘
   │              │   │
 25%│              └───┘
   │
  0%└────┬───┬────┬───┬────→ 波长
       400   500  600   700nm

        蓝    绿    红

理想CFA：互不重叠的方波
实际CFA：有重叠、有过渡带
```

---

## 3. Demosaicing算法

### 3.1 问题定义

从单通道Bayer数据重建三通道RGB：

```
输入（Bayer）:              输出（RGB）:
┌───┬───┬───┐             ┌───────┬───────┬───────┐
│ R │ G │ R │             │R│G│B│ │R│G│B│ │R│G│B│
├───┼───┼───┤      →      ├───────┼───────┼───────┤
│ G │ B │ G │             │R│G│B│ │R│G│B│ │R│G│B│
├───┼───┼───┤             ├───────┼───────┼───────┤
│ R │ G │ R │             │R│G│B│ │R│G│B│ │R│G│B│
└───┴───┴───┘             └───────┴───────┴───────┘

每个像素需要插值出缺失的两个颜色通道
```

### 3.2 双线性插值（Baseline）

#### G通道插值

在R或B位置插值G值：

```
位置：R位置插值G

   G0
G1 R  G2
   G3

G_interpolated = (G0 + G1 + G2 + G3) / 4
```

#### R/B通道插值

在G位置插值R或B值（根据所在行选择方向）：

```
在G位置（R行）插值R：

R0 G R1
G  B  G
R2 G R3

R_interpolated = (R0 + R1) / 2  （水平方向）

在G位置（B行）插值B：

G  R  G
B0 G B1
G  R  G

B_interpolated = (B0 + B1) / 2  （水平方向）
```

#### 伪代码实现

```python
def demosaic_bilinear(raw_image, pattern='RGGB'):
    """
    双线性插值Demosaic
    """
    height, width = raw_image.shape
    rgb = np.zeros((height, width, 3), dtype=np.float32)
    
    # 获取Bayer掩码
    r_mask, g_mask, b_mask = get_bayer_masks(height, width, pattern)
    
    # 1. 直接复制已知值
    rgb[:,:,0] = raw_image * r_mask  # R
    rgb[:,:,1] = raw_image * g_mask  # G
    rgb[:,:,2] = raw_image * b_mask  # B
    
    # 2. 插值G通道
    kernel_g = np.array([[0, 1/4, 0],
                         [1/4, 0, 1/4],
                         [0, 1/4, 0]])
    g_interpolated = convolve2d(raw_image * (1 - g_mask), kernel_g, mode='same')
    rgb[:,:,1] += g_interpolated
    
    # 3. 插值R和B通道（简化版）
    kernel_rb = np.array([[1/4, 0, 1/4],
                          [0, 0, 0],
                          [1/4, 0, 1/4]])
    r_interpolated = convolve2d(raw_image * (1 - r_mask), kernel_rb, mode='same')
    b_interpolated = convolve2d(raw_image * (1 - b_mask), kernel_rb, mode='same')
    rgb[:,:,0] += r_interpolated
    rgb[:,:,2] += b_interpolated
    
    return rgb
```

#### 问题分析

| 问题 | 原因 | 表现 |
|------|------|------|
| **拉链伪影** | 跨越边缘插值 | 边缘出现锯齿状条纹 |
| **伪色** | 颜色混叠 | 高频区域出现彩色条纹 |
| **模糊** | 平均操作 | 细节丢失 |

### 3.3 边缘感知算法

#### 梯度自适应插值

核心思想：**沿边缘方向插值，而非跨越边缘**

```
判断边缘方向：

   N0
W0 G E0
   S0

水平梯度: |E0 - W0|
垂直梯度: |N0 - S0|

if 水平梯度 < 垂直梯度:
    沿水平方向插值（左右平均）
else:
    沿垂直方向插值（上下平均）
```

#### AHD（Adaptive Homogeneity-Directed）

```
AHD算法步骤：

1. 分别进行水平插值和垂直插值
   - 得到 G_h 和 G_v

2. 计算两个方向的色差
   - Δ_h = |G_h - 原始G|
   - Δ_v = |G_v - 原始G|

3. 选择误差较小的方向
   - 如果 Δ_h < Δ_v: 使用水平插值结果
   - 否则: 使用垂直插值结果

4. 后处理：中值滤波去除孤立错误
```

### 3.4 频域与迭代方法

#### 频域分析

Bayer采样可以看作对RGB三个通道进行不同模式的下采样：

```
频域特性：

R通道: 在水平和垂直方向都下采样2倍
       → 频谱限制在[-π/2, π/2]

G通道: 棋盘格采样
       → 频谱有特定结构

B通道: 同R通道

Demosaic本质：频谱重建问题
```

#### 迭代重建

```python
def iterative_demosaic(raw, iterations=5):
    """
    迭代优化Demosaic
    """
    # 初始化：双线性插值
    rgb = bilinear_demosaic(raw)
    
    for i in range(iterations):
        # 1. 计算当前估计的Bayer采样
        simulated_raw = apply_bayer_mask(rgb)
        
        # 2. 计算误差
        error = raw - simulated_raw
        
        # 3. 将误差反投影到RGB
        rgb_correction = distribute_error(error)
        
        # 4. 更新估计
        rgb += rgb_correction * step_size
        
        # 5. 施加平滑约束（正则化）
        rgb = apply_smoothness_constraint(rgb)
    
    return rgb
```

### 3.5 机器学习方法

#### 深度学习Demosaic

```
网络架构示例（DeepDemosaick）：

输入: Bayer RAW (H×W×1)
  ↓
[Conv 3×3, 64] → ReLU
  ↓
[ResBlock × 8]
  - Conv 3×3
  - ReLU
  - Conv 3×3
  - Skip Connection
  ↓
[Conv 3×3, 12]  # 上采样2×2
  ↓
PixelShuffle(2×)  # 分辨率恢复
  ↓
输出: RGB (2H×2W×3)
```

#### 传统vs深度学习方法对比

| 方法 | 速度 | 质量 | 内存 | 适用场景 |
|------|------|------|------|---------|
| 双线性 | 极快 | 差 | 极低 | 实时预览 |
| 边缘感知 | 快 | 中 | 低 | 通用处理 |
| 迭代优化 | 慢 | 良 | 中 | 静态图像 |
| 深度学习 | 中等* | 优 | 高 | 高质量输出 |

*注：使用专用NPU/GPU加速时

---

## 4. 白平衡与色彩校正

### 4.1 白平衡原理

#### 色温与光源

不同光源具有不同的光谱分布：

| 光源 | 色温（K） | 特点 |
|------|----------|------|
| 烛光 | 1,800 | 偏红/黄 |
| 白炽灯 | 2,700 | 偏暖 |
| 荧光灯 | 4,000 | 偏绿 |
| 日光 | 5,500 | 中性 |
| 阴天 | 6,500 | 偏冷 |
| 阴影 | 7,500 | 偏蓝 |

#### 白平衡数学模型

$$
\begin{bmatrix} R_{wb} \\ G_{wb} \\ B_{wb} \end{bmatrix} = 
\begin{bmatrix} g_r & 0 & 0 \\ 0 & g_g & 0 \\ 0 & 0 & g_b \end{bmatrix} \cdot
\begin{bmatrix} R_{raw} \\ G_{raw} \\ B_{raw} \end{bmatrix}
$$

其中增益系数满足：$g_r \cdot R_{gray} = g_g \cdot G_{gray} = g_b \cdot B_{gray}$

### 4.2 自动白平衡算法

#### 灰度世界假设（Gray World）

假设：场景的平均反射是中性灰

```python
def gray_world_wb(image):
    """
    灰度世界白平衡
    """
    mean_r = np.mean(image[:,:,0])
    mean_g = np.mean(image[:,:,1])
    mean_b = np.mean(image[:,:,2])
    
    # 计算增益（以G为基准）
    g_r = mean_g / mean_r
    g_g = 1.0
    g_b = mean_g / mean_b
    
    return apply_gains(image, [g_r, g_g, g_b])
```

**局限性**：大面积单色场景会失效

#### 白点检测（White Patch）

假设：图像最亮的区域是白色

```python
def white_patch_wb(image, percentile=99):
    """
    白点检测白平衡
    """
    # 找到亮度最高的区域
    luminance = 0.299 * image[:,:,0] + 0.587 * image[:,:,1] + 0.114 * image[:,:,2]
    threshold = np.percentile(luminance, percentile)
    
    # 在高亮区域计算平均颜色
    mask = luminance >= threshold
    white_r = np.mean(image[:,:,0][mask])
    white_g = np.mean(image[:,:,1][mask])
    white_b = np.mean(image[:,:,2][mask])
    
    # 计算增益
    g_r = 1.0 / white_r
    g_g = 1.0 / white_g
    g_b = 1.0 / white_b
    
    return apply_gains(image, [g_r, g_g, g_b])
```

#### 色温估计法

```
基于黑体辐射曲线：

1. 计算当前场景的色度坐标 (x, y)
2. 在黑体辐射轨迹上找到最近的色温
3. 根据色温计算标准白点
4. 计算从当前白点到标准白点的转换
```

### 4.3 色彩校正矩阵（CCM）

#### 为什么需要CCM

传感器RGB与标准RGB（如sRGB）存在差异：

```
传感器响应 ≠ 标准观察者响应

原因：
- CFA光谱响应与CIE颜色匹配函数不同
- 传感器间存在个体差异
- 需要校准到标准色彩空间
```

#### CCM数学推导

目标：找到矩阵 $M$ 使得

$$
\begin{bmatrix} R_{target} \\ G_{target} \\ B_{target} \end{bmatrix} = 
M \cdot \begin{bmatrix} R_{sensor} \\ G_{sensor} \\ B_{sensor} \end{bmatrix}
$$

使用ColorChecker标定：

```python
def calibrate_ccm(sensor_colors, target_colors):
    """
    最小二乘标定CCM
    
    sensor_colors: N×3 传感器测得的ColorChecker颜色
    target_colors: N×3 标准ColorChecker值
    """
    # 求解 M = target × pinv(sensor)
    M = np.linalg.lstsq(sensor_colors, target_colors, rcond=None)[0]
    
    # 约束：每行之和为1（保持中性色）
    M = M / np.sum(M, axis=1, keepdims=True)
    
    return M.T  # 转置为3×3矩阵
```

#### 典型CCM结构

```
典型CCM矩阵（3×3）：

┌                    ┐
│  1.2  -0.1  -0.1  │
│ -0.1   1.1  -0.0  │
│ -0.0  -0.2   1.2  │
└                    ┘

对角线元素 > 1：增强该通道
对角线元素 < 1：减弱该通道
非对角线元素：通道间串扰校正
```

---

## 5. 噪点建模与去除

### 5.1 RAW域噪点特性

#### 噪点来源

| 噪点类型 | 来源 | 特性 | 与信号关系 |
|---------|------|------|-----------|
| **光子散粒噪声** | 光的量子特性 | 泊松分布 | $\sigma \propto \sqrt{Signal}$ |
| **读出噪声** | 电路热噪声 | 高斯分布 | 与信号无关 |
| **暗电流噪声** | 热生载流子 | 泊松+固定模式 | 与曝光时间相关 |
| **固定模式噪声** | 像素间差异 | 空间固定 | 可通过校准消除 |

#### 噪点模型

RAW域噪点通常建模为：

$$
\sigma^2(y) = a \cdot y + b
$$

其中：
- $y$：信号值
- $a$：光子散粒噪声系数
- $b$：读出噪声方差

### 5.2 传统降噪算法

#### 空域滤波

```python
def bilateral_filter(image, sigma_s, sigma_r):
    """
    双边滤波：保持边缘的降噪
    
    sigma_s: 空间域标准差
    sigma_r: 值域标准差
    """
    result = np.zeros_like(image)
    
    for i in range(height):
        for j in range(width):
            window = image[max(0,i-r):min(h,i+r), max(0,j-r):min(w,j+r)]
            
            # 空间权重
            spatial_w = gaussian(distance, sigma_s)
            
            # 值域权重（相似像素权重更高）
            range_w = gaussian(image[i,j] - window, sigma_r)
            
            # 组合权重
            weight = spatial_w * range_w
            result[i,j] = np.sum(window * weight) / np.sum(weight)
    
    return result
```

#### 变换域滤波

```
小波降噪流程：

1. 小波变换 → 多尺度分解
   LL (低频) │ LH (水平细节)
   ──────────┼──────────
   HL (垂直细节)│ HH (对角细节)

2. 阈值处理高频系数
   - 软阈值：sign(x) * max(|x| - T, 0)
   - 硬阈值：x if |x| > T else 0

3. 逆小波变换重建
```

### 5.3 多帧降噪

#### 原理

通过对齐和平均多帧图像降低随机噪声：

$$
\text{SNR}_{\text{multi}} = \sqrt{N} \cdot \text{SNR}_{\text{single}}
$$

其中 $N$ 为帧数

#### 流程

```python
def multi_frame_denoise(raw_frames):
    """
    多帧RAW降噪
    """
    # 1. 运动估计与对齐
    aligned_frames = []
    reference = raw_frames[0]
    
    for frame in raw_frames[1:]:
        motion_vectors = estimate_motion(frame, reference)
        aligned = warp_image(frame, motion_vectors)
        aligned_frames.append(aligned)
    
    # 2. 时域滤波（考虑运动区域）
    result = np.zeros_like(reference)
    
    for i in range(height):
        for j in range(width):
            # 收集该位置在多帧中的值
            values = [reference[i,j]]
            for frame in aligned_frames:
                values.append(frame[i,j])
            
            # 异常值剔除（去除鬼影）
            values = reject_outliers(values)
            
            # 加权平均
            result[i,j] = np.mean(values)
    
    return result
```

### 5.4 基于深度学习的降噪

#### DnCNN架构

```
输入: 含噪图像
  ↓
Conv(3×3, 64) + ReLU
  ↓
[Conv(3×3, 64) + BN + ReLU] × 15
  ↓
Conv(3×3, 1)
  ↓
输出: 残差（噪点估计）

去噪结果 = 输入 - 残差
```

#### 盲降噪vs非盲降噪

| 类型 | 输入 | 优点 | 缺点 |
|------|------|------|------|
| **非盲** | 图像 + 噪声水平 | 针对性强 | 需要准确估计噪声 |
| **盲** | 仅图像 | 自适应 | 复杂场景可能失效 |

---

## 6. RAW格式与标准

### 6.1 主流RAW格式

| 格式 | 厂商 | 特点 | 兼容性 |
|------|------|------|-------|
| **DNG** | Adobe | 开放标准，元数据丰富 | 通用 |
| **CR2/CR3** | Canon | 高效压缩，支持C-RAW | 需专用软件 |
| **NEF** | Nikon | 保留完整信息 | 需专用软件 |
| **ARW** | Sony | 支持压缩RAW | 需专用软件 |
| **RAF** | Fujifilm | 支持X-Trans | 需专用软件 |

### 6.2 DNG格式详解

#### 文件结构

```
DNG文件结构：

┌─────────────────────────────────────┐
│ TIFF Header                         │
│ - 字节序（II/MM）                   │
│ - 魔数（42）                        │
│ - IFD偏移                           │
├─────────────────────────────────────┤
│ IFD0 (主图像描述)                   │
│ - 图像尺寸                          │
│ - 位深                              │
│ - CFA模式                           │
│ - 色彩矩阵                          │
├─────────────────────────────────────┤
│ SubIFD (可选预览图)                 │
├─────────────────────────────────────┤
│ DNG私有标签                         │
│ - DNG版本                           │
│ - 相机型号                          │
│ - 白平衡系数                        │
│ - 前照矩阵                          │
├─────────────────────────────────────┤
│ 图像数据                            │
│ - RAW像素数据                       │
│ - 可选：JPEG压缩预览                │
└─────────────────────────────────────┘
```

#### 关键元数据

```python
# DNG解析关键字段
DNG_TAGS = {
    50706: 'DNGVersion',           # DNG版本号
    50707: 'DNGBackwardVersion',   # 向后兼容版本
    50708: 'UniqueCameraModel',    # 相机型号
    50717: 'BlackLevel',           # 黑电平
    50718: 'WhiteLevel',           # 白电平
    50719: 'DefaultScale',         # 默认缩放
    50778: 'CalibrationIlluminant1', # 校准光源1
    50779: 'CalibrationIlluminant2', # 校准光源2
    50781: 'ColorMatrix1',         # 色彩矩阵1
    50782: 'ColorMatrix2',         # 色彩矩阵2
    50794: 'AsShotWhiteXY',        # 拍摄时白点
}
```

### 6.3 移动端RAW

#### Camera2 API RAW输出

```java
// Android Camera2 API 获取RAW
CameraCharacteristics characteristics = cameraManager.getCameraCharacteristics(cameraId);

// 检查RAW支持
boolean rawSupported = characteristics.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)
    .contains(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW);

// 配置RAW输出
ImageReader rawReader = ImageReader.newInstance(
    width, height, 
    ImageFormat.RAW_SENSOR,  // 或 RAW10, RAW12
    maxImages
);
```

#### iOS DNG输出

```swift
// iOS AVCapturePhotoOutput 获取DNG
let photoSettings = AVCapturePhotoSettings(rawPixelFormatType: kCVPixelFormatType_14Bayer_RGGB)

photoOutput.capturePhoto(with: photoSettings, delegate: self)

// 在回调中获取DNG数据
func photoOutput(_ output: AVCapturePhotoOutput, 
                 didFinishProcessingPhoto photo: AVCapturePhoto, 
                 error: Error?) {
    if let dngData = photo.fileDataRepresentation() {
        // 保存DNG文件
    }
}
```

---

## 7. 应用场景分析

### 7.1 专业摄影后期

#### 工作流程

```
专业摄影RAW工作流：

拍摄（RAW）
    ↓
导入Lightroom/Capture One
    ↓
RAW解码（Demosaic + WB + CCM）
    ↓
曝光/对比度调整（线性空间）
    ↓
色彩调整（HSL、分离色调）
    ↓
局部调整（渐变、径向滤镜）
    ↓
降噪与锐化
    ↓
输出（TIFF/PSD/JPEG）
```

#### 关键优势

- **曝光调整**：RAW提供±4EV调整空间
- **白平衡重算**：无损调整，无偏色
- **色彩深度**：16bit处理避免色带

### 7.2 计算摄影

#### HDR合成

```
多曝光RAW合成HDR：

RAW -2EV ──┐
           ├──→ 对齐 → 合并 → 色调映射 → HDR图像
RAW  0EV ──┤
           │
RAW +2EV ──┘

优势：
- 在线性空间合成更准确
- 避免JPEG压缩伪影
- 保留完整动态范围
```

#### 夜景模式

```
夜景RAW处理：

1. 捕获多帧RAW（通常8-16帧）
2. 对齐（考虑手持抖动）
3. 时域降噪
4. 提亮阴影
5. 色调映射
```

### 7.3 科学成像

#### 天文摄影

```
天文RAW处理特点：

- 长曝光（数分钟）
- 暗帧校准（Dark Frame Subtraction）
- 平场校准（Flat Field Correction）
- 偏置帧校准（Bias Subtraction）

校准公式：
Calibrated = (Raw - Dark - Bias) / (Flat - Bias)
```

#### 医学影像

| 应用 | RAW优势 | 特殊要求 |
|------|--------|---------|
| 内窥镜 | 色彩准确性 | 消毒环境 |
| 显微镜 | 定量分析 | 均匀照明 |
| 病理切片 | 细节保留 | 标准化流程 |

---

## 总结

RAW域是数字成像的基础，理解RAW处理的关键技术对于：

1. **图像质量优化**：从传感器获取最佳画质
2. **算法开发**：设计更好的ISP算法
3. **后期处理**：充分利用RAW的灵活性
4. **跨平台开发**：处理不同设备的RAW数据

核心技术要点：
- **Demosaic**：从单通道重建RGB，边缘感知是关键
- **白平衡**：校正光源色温，自动算法需要鲁棒性
- **CCM**：将传感器色彩映射到标准空间
- **降噪**：理解噪点模型，选择合适的算法

> 🔗 返回：[RAW_YUV域深度解析](./RAW_YUV域深度解析.md)

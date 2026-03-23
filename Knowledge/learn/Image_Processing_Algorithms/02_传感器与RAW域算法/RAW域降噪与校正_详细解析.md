# RAW域降噪与校正详细解析

> 在源头消除噪声与缺陷：传感器原始数据的预处理核心技术

---

## 目录

1. [传感器噪声模型](#1-传感器噪声模型)
2. [黑电平校正（OBC/BLC）](#2-黑电平校正obcblc)
3. [坏点校正（DPC）](#3-坏点校正dpc)
4. [RAW域降噪](#4-raw域降噪)
5. [绿色不均衡校正（GIC）](#5-绿色不均衡校正gic)
6. [RAW域处理顺序](#6-raw域处理顺序)
7. [参考资源](#7-参考资源)

---

## 1. 传感器噪声模型

### 1.1 噪声来源概述

图像传感器的噪声是影响成像质量的关键因素，理解噪声模型是进行有效降噪的基础。

```
传感器噪声来源分类：

┌─────────────────────────────────────────────────────────────────┐
│                      传感器噪声来源                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │  光子噪声   │    │  暗电流噪声  │    │  读出噪声   │        │
│   │  (Shot)     │    │  (Dark)     │    │  (Read)     │        │
│   │  信号相关   │    │  时间/温度  │    │  电路固有   │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│         ↓                  ↓                  ↓                 │
│   ┌─────────────────────────────────────────────────────┐      │
│   │              固定模式噪声 (FPN)                       │      │
│   │        像素间响应不一致（PRNU/DSNU）                  │      │
│   └─────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 光子散粒噪声（Shot Noise）

#### 物理本质

光子到达传感器是一个泊松随机过程，即使在恒定光照下，单位时间内到达的光子数也会波动。

$$
P(k) = \frac{\lambda^k e^{-\lambda}}{k!}
$$

其中 $\lambda$ 是平均光子数，$k$ 是实际计数。

#### 特性

- **信号依赖性**：噪声方差等于信号均值
  $$\sigma_{shot}^2 = \mu_{signal}$$
  
- **标准差与信号关系**：
  $$\sigma_{shot} = \sqrt{\mu_{signal}}$$

- **SNR（信噪比）**：
  $$SNR_{shot} = \frac{\mu}{\sigma} = \sqrt{\mu}$$

```
光子噪声的信号依赖性示意：

信号强度    噪声标准差    SNR
─────────────────────────────
   100         10         10
  1000         32         32
 10000        100        100
 
结论：高亮度区域SNR更高，暗部噪声相对更明显
```

### 1.3 读出噪声（Read Noise）

#### 来源

读出噪声产生于像素信号的读出和放大电路，是与信号无关的**加性高斯噪声**。

$$
n_{read} \sim \mathcal{N}(0, \sigma_{read}^2)
$$

#### 组成部分

| 来源 | 描述 | 特性 |
|------|------|------|
| **源跟随器噪声** | 像素内放大器热噪声 | 与温度相关 |
| **ADC量化噪声** | 模数转换离散化误差 | 均匀分布，$\sigma = LSB/\sqrt{12}$ |
| **列放大器噪声** | 列级放大电路噪声 | 列间差异 |
| **CDS残余** | 相关双采样后残留 | 与采样时序相关 |

#### 典型值

```
不同传感器的读出噪声水平（单位：e-）：

传感器类型          读出噪声(e-)
──────────────────────────────
手机传感器           2-5
消费级相机           3-8
专业相机             1-3
科学级CCD            <1
背照式BSI            1-3
```

### 1.4 暗电流噪声（Dark Current Noise）

#### 物理成因

即使在无光照条件下，由于热激发，电子会自发从价带跃迁到导带，产生暗电流。

$$
I_{dark} = A \cdot T^{1.5} \cdot e^{-\frac{E_g}{2kT}}
$$

其中：
- $A$：常数
- $T$：绝对温度
- $E_g$：硅的带隙能量（约1.12eV）
- $k$：玻尔兹曼常数

#### 温度依赖性

```
暗电流与温度的关系（经验法则）：

温度每升高8-10°C，暗电流约翻倍

温度(°C)    相对暗电流
─────────────────────
   0           1x
  10           2x
  20           4x
  30           8x
  40          16x
```

#### 暗电流噪声

暗电流本身也是泊松过程，因此：

$$
\sigma_{dark} = \sqrt{I_{dark} \cdot t_{exp}}
$$

### 1.5 固定模式噪声（FPN）

#### 分类

```
固定模式噪声类型：

┌────────────────────────────────────────────────────────┐
│                   固定模式噪声 (FPN)                    │
├────────────────────┬───────────────────────────────────┤
│                    │                                    │
│   DSNU             │         PRNU                      │
│   (Dark Signal     │    (Photo Response                │
│    Non-Uniformity) │     Non-Uniformity)               │
│                    │                                    │
│   - 暗场不均匀     │    - 光响应不均匀                 │
│   - 加性误差       │    - 乘性误差                     │
│   - 热像素         │    - 灵敏度差异                   │
│                    │                                    │
└────────────────────┴───────────────────────────────────┘
```

#### DSNU（暗信号不均匀性）

在无光照下，不同像素的输出值不同：

$$
D(x,y) = D_0 + d(x,y)
$$

其中 $d(x,y)$ 是像素 $(x,y)$ 的暗信号偏差。

#### PRNU（光响应不均匀性）

对同样的光照，不同像素的响应不同：

$$
S(x,y) = [1 + p(x,y)] \cdot L(x,y)
$$

其中 $p(x,y)$ 是像素 $(x,y)$ 的响应偏差（通常<2%）。

### 1.6 综合噪声模型

#### 完整信号模型

传感器输出可建模为：

$$
Y(x,y) = g \cdot \{[1 + p(x,y)] \cdot [\Phi(x,y) + D(x,y)] + n_{read}\} + q
$$

其中：
- $g$：系统增益（ISO）
- $p(x,y)$：PRNU
- $\Phi(x,y)$：光子信号
- $D(x,y)$：暗电流
- $n_{read}$：读出噪声
- $q$：量化噪声

#### 简化实用模型

对于大多数ISP应用，采用**异方差高斯模型**：

$$
Y = X + n, \quad n \sim \mathcal{N}(0, \sigma^2(X))
$$

$$
\sigma^2(X) = a \cdot X + b
$$

其中：
- $a$：与光子噪声相关（信号依赖项）
- $b$：与读出噪声相关（信号无关项）

---

## 2. 黑电平校正（OBC/BLC）

### 2.1 黑电平的物理来源

#### 什么是黑电平

黑电平（Black Level）是传感器在完全无光照条件下的输出值，主要来源于：

1. **暗电流积累**：曝光期间的热生成电荷
2. **ADC偏置**：模数转换器的零点偏移
3. **电路偏置**：读出电路的直流偏置

```
黑电平示意：

ADC输出
   ↑
   │                    ╱ 有效信号
   │                  ╱
   │                ╱
   │    ━━━━━━━━━━┳━━━━━━━━ 饱和电平
   │              │
   │              │
   │    ┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┄ 黑电平 (如：64 DN)
   │              │
   └──────────────┴────────→ 入射光强
   
   黑电平以下为负信号区域（clipping）
```

#### 黑电平的变化因素

| 因素 | 影响 | 变化幅度 |
|------|------|----------|
| **温度** | 暗电流增加 | 显著 |
| **曝光时间** | 暗电流积累 | 线性 |
| **ISO增益** | 放大偏置 | 近似线性 |
| **行/列位置** | 读出电路差异 | 行相关 |

### 2.2 OB区域检测与统计

#### 光学黑区（Optical Black, OB）

传感器设计时会预留一些**被遮光的像素行/列**，用于实时测量黑电平：

```
传感器像素布局：

┌──────────────────────────────────────────┐
│ OB行 ████████████████████████████████████│ ← 顶部OB（遮光）
├────┬─────────────────────────────────────┤
│ OB │                                     │
│ 列 │         有效像素区域                │ ← 左侧OB（遮光）
│    │         (Active Area)               │
│ ████                                     │
│ ████                                     │
├────┼─────────────────────────────────────┤
│ OB │█████████████████████████████████████│ ← 底部OB
└────┴─────────────────────────────────────┘
```

#### OB统计方法

```c
// OB区域统计黑电平
typedef struct {
    uint16_t ob_mean;       // OB均值
    uint16_t ob_median;     // OB中值（更稳健）
    uint16_t ob_std;        // OB标准差
    uint16_t ob_min;        // OB最小值
    uint16_t ob_max;        // OB最大值
} OB_Stats;

OB_Stats compute_ob_stats(uint16_t* raw, int W, int H, 
                          int ob_left, int ob_top, int ob_right, int ob_bottom) {
    OB_Stats stats;
    int count = 0;
    uint32_t sum = 0;
    uint16_t* ob_values = malloc(ob_left * H * sizeof(uint16_t));
    
    // 收集左侧OB列数据
    for (int y = ob_top; y < H - ob_bottom; y++) {
        for (int x = 0; x < ob_left; x++) {
            uint16_t val = raw[y * W + x];
            ob_values[count++] = val;
            sum += val;
        }
    }
    
    stats.ob_mean = sum / count;
    
    // 计算中值（排序后取中间值）
    qsort(ob_values, count, sizeof(uint16_t), compare_uint16);
    stats.ob_median = ob_values[count / 2];
    
    // 标准差计算
    uint64_t var_sum = 0;
    for (int i = 0; i < count; i++) {
        int diff = ob_values[i] - stats.ob_mean;
        var_sum += diff * diff;
    }
    stats.ob_std = sqrt(var_sum / count);
    
    free(ob_values);
    return stats;
}
```

### 2.3 动态黑电平校正算法

#### 逐帧动态校正

```c
void dynamic_blc(uint16_t* raw, int W, int H, int ob_cols, int ob_rows) {
    // 1. 计算当前帧OB统计
    OB_Stats stats = compute_ob_stats(raw, W, H, ob_cols, ob_rows, 0, 0);
    
    // 2. 时域滤波（IIR低通，避免抖动）
    static float blc_filtered = 64.0f;  // 初始值
    float alpha = 0.1f;  // 滤波系数
    blc_filtered = alpha * stats.ob_median + (1 - alpha) * blc_filtered;
    
    uint16_t blc = (uint16_t)(blc_filtered + 0.5f);
    
    // 3. 应用校正
    for (int y = ob_rows; y < H; y++) {
        for (int x = ob_cols; x < W; x++) {
            int idx = y * W + x;
            raw[idx] = (raw[idx] > blc) ? (raw[idx] - blc) : 0;
        }
    }
}
```

### 2.4 逐行/逐列校正

#### 行间黑电平差异

由于读出电路的差异，不同行可能有不同的黑电平偏移：

```c
void row_blc(uint16_t* raw, int W, int H, int ob_cols) {
    for (int y = 0; y < H; y++) {
        // 计算该行OB区域的中值
        uint16_t row_ob[64];  // 假设ob_cols <= 64
        for (int x = 0; x < ob_cols; x++) {
            row_ob[x] = raw[y * W + x];
        }
        
        // 排序取中值
        qsort(row_ob, ob_cols, sizeof(uint16_t), compare_uint16);
        uint16_t row_blc = row_ob[ob_cols / 2];
        
        // 对该行所有像素减去黑电平
        for (int x = ob_cols; x < W; x++) {
            int idx = y * W + x;
            raw[idx] = (raw[idx] > row_blc) ? (raw[idx] - row_blc) : 0;
        }
    }
}
```

#### 列黑电平校正

```c
void column_blc(uint16_t* raw, int W, int H, int ob_rows) {
    // 类似行校正，但沿列方向统计
    for (int x = 0; x < W; x++) {
        uint32_t col_sum = 0;
        for (int y = 0; y < ob_rows; y++) {
            col_sum += raw[y * W + x];
        }
        uint16_t col_blc = col_sum / ob_rows;
        
        for (int y = ob_rows; y < H; y++) {
            int idx = y * W + x;
            raw[idx] = (raw[idx] > col_blc) ? (raw[idx] - col_blc) : 0;
        }
    }
}
```

---

## 3. 坏点校正（DPC）

### 3.1 坏点类型

```
坏点分类：

┌─────────────────────────────────────────────────────────┐
│                        坏点类型                          │
├─────────────────┬────────────────┬──────────────────────┤
│    死点         │    热点        │    不稳定点          │
│  (Dead Pixel)   │  (Hot Pixel)   │  (Unstable Pixel)   │
├─────────────────┼────────────────┼──────────────────────┤
│ 输出恒定为0     │ 输出恒定为满   │ 输出随机波动         │
│ 或极低值        │ 或异常高值     │ 与信号无关           │
└─────────────────┴────────────────┴──────────────────────┘
```

### 3.2 静态坏点检测

#### 暗场/亮场标定

```
静态坏点标定流程：

1. 暗场标定（检测热点）：
   - 遮盖镜头，长曝光
   - 记录输出值异常高的像素
   
2. 亮场标定（检测死点）：
   - 均匀照明（如积分球）
   - 记录输出值异常低的像素
   
3. 生成坏点映射表（Defect Map）
```

#### 标定算法

```c
typedef struct {
    uint16_t x;
    uint16_t y;
    uint8_t  type;  // 0:dead, 1:hot, 2:unstable
} DefectPixel;

// 暗场标定
int calibrate_dark_field(uint16_t* dark_frame, int W, int H,
                         DefectPixel* defects, int max_defects) {
    int count = 0;
    
    // 计算全局统计
    uint32_t sum = 0;
    for (int i = 0; i < W * H; i++) {
        sum += dark_frame[i];
    }
    float mean = (float)sum / (W * H);
    
    // 计算标准差
    float var_sum = 0;
    for (int i = 0; i < W * H; i++) {
        float diff = dark_frame[i] - mean;
        var_sum += diff * diff;
    }
    float std = sqrt(var_sum / (W * H));
    
    // 检测热点：超过 mean + 5*std 的像素
    float threshold = mean + 5 * std;
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            if (dark_frame[y * W + x] > threshold && count < max_defects) {
                defects[count].x = x;
                defects[count].y = y;
                defects[count].type = 1;  // hot pixel
                count++;
            }
        }
    }
    
    return count;
}
```

### 3.3 动态坏点检测

#### 梯度阈值法

```c
bool is_dynamic_defect_gradient(uint16_t* raw, int x, int y, int W, int threshold) {
    uint16_t center = raw[y * W + x];
    
    // 同色邻域（Bayer模式下距离为2）
    uint16_t neighbors[4] = {
        raw[(y-2) * W + x],      // 上
        raw[(y+2) * W + x],      // 下
        raw[y * W + (x-2)],      // 左
        raw[y * W + (x+2)]       // 右
    };
    
    // 计算梯度
    int grad_sum = 0;
    for (int i = 0; i < 4; i++) {
        grad_sum += abs(center - neighbors[i]);
    }
    
    // 计算邻域均值
    uint32_t neighbor_sum = 0;
    for (int i = 0; i < 4; i++) {
        neighbor_sum += neighbors[i];
    }
    float neighbor_mean = neighbor_sum / 4.0f;
    
    // 判断：如果中心与所有邻域差异都很大，可能是坏点
    return (grad_sum > threshold * 4) && (abs(center - neighbor_mean) > threshold);
}
```

#### 中值阈值法

```c
bool is_dynamic_defect_median(uint16_t* raw, int x, int y, int W, float ratio_thresh) {
    // 收集5×5同色邻域（在Bayer中即3×3采样）
    uint16_t samples[9];
    int idx = 0;
    for (int dy = -2; dy <= 2; dy += 2) {
        for (int dx = -2; dx <= 2; dx += 2) {
            samples[idx++] = raw[(y + dy) * W + (x + dx)];
        }
    }
    
    // 排序求中值
    qsort(samples, 9, sizeof(uint16_t), compare_uint16);
    uint16_t median = samples[4];
    uint16_t center = samples[4];  // 中心值在排序后可能不在中间
    center = raw[y * W + x];       // 重新获取中心值
    
    // 计算比率
    float ratio = (median > 0) ? (float)center / median : 0;
    
    // 如果比率偏离1过多，判定为坏点
    return (ratio > (1 + ratio_thresh)) || (ratio < (1 - ratio_thresh));
}
```

### 3.4 坏点插值修复

#### 简单中值替换

```c
void correct_defect_median(uint16_t* raw, int x, int y, int W) {
    // 同色邻域中值替换
    uint16_t samples[8];
    int idx = 0;
    
    // 八邻域（同色）
    int offsets[8][2] = {{-2,0}, {2,0}, {0,-2}, {0,2},
                         {-2,-2}, {2,-2}, {-2,2}, {2,2}};
    
    for (int i = 0; i < 8; i++) {
        samples[idx++] = raw[(y + offsets[i][1]) * W + (x + offsets[i][0])];
    }
    
    qsort(samples, 8, sizeof(uint16_t), compare_uint16);
    raw[y * W + x] = (samples[3] + samples[4]) / 2;  // 中间两个值平均
}
```

#### 梯度加权插值

```c
void correct_defect_gradient(uint16_t* raw, int x, int y, int W) {
    // 计算四方向梯度
    uint16_t n = raw[(y-2) * W + x];
    uint16_t s = raw[(y+2) * W + x];
    uint16_t w = raw[y * W + (x-2)];
    uint16_t e = raw[y * W + (x+2)];
    
    float grad_ns = abs(n - s) + 1;  // +1避免除零
    float grad_we = abs(w - e) + 1;
    
    // 梯度小的方向权重大
    float w_ns = 1.0f / grad_ns;
    float w_we = 1.0f / grad_we;
    float w_total = w_ns + w_we;
    
    raw[y * W + x] = (uint16_t)(
        (w_ns * (n + s) / 2 + w_we * (w + e) / 2) / w_total
    );
}
```

---

## 4. RAW域降噪

### 4.1 RAW域降噪的优势与挑战

#### 优势

```
RAW域降噪优势：

1. 信号未经非线性处理
   - 噪声模型更准确（泊松+高斯）
   - 降噪参数更容易调优
   
2. 避免Demosaic放大噪声
   - 噪声不会被颜色插值扩散
   - 可更激进地降噪
   
3. 保留更多原始信息
   - 高位深数据
   - 未压缩信号
```

#### 挑战

```
RAW域降噪挑战：

1. Bayer马赛克结构
   - 不同颜色通道噪声特性不同
   - 空间相关性受CFA影响
   
2. 颜色通道间相关性利用困难
   - 颜色信息不完整
   - 难以利用跨通道先验
   
3. 计算复杂度高
   - 全分辨率处理
   - 实时性要求
```

### 4.2 通道分离降噪

#### 四通道分离

将Bayer图像分离为4个子图像：

```
原始Bayer:                   分离后：
┌───┬───┬───┬───┐           R通道:    Gr通道:   Gb通道:   B通道:
│ R │Gr │ R │Gr │           ┌───┬───┐ ┌───┬───┐ ┌───┬───┐ ┌───┬───┐
├───┼───┼───┼───┤           │R00│R02│ │G01│G03│ │G10│G12│ │B11│B13│
│Gb │ B │Gb │ B │    →      ├───┼───┤ ├───┼───┤ ├───┼───┤ ├───┼───┤
├───┼───┼───┼───┤           │R20│R22│ │G21│G23│ │G30│G32│ │B31│B33│
│ R │Gr │ R │Gr │           └───┴───┘ └───┴───┘ └───┴───┘ └───┴───┘
├───┼───┼───┼───┤
│Gb │ B │Gb │ B │           尺寸：原图 H/2 × W/2
└───┴───┴───┴───┘
```

#### 独立降噪

```c
void denoise_bayer_separated(uint16_t* raw, int W, int H, float sigma) {
    int half_W = W / 2;
    int half_H = H / 2;
    
    // 分配四个子通道
    float* ch_R  = malloc(half_W * half_H * sizeof(float));
    float* ch_Gr = malloc(half_W * half_H * sizeof(float));
    float* ch_Gb = malloc(half_W * half_H * sizeof(float));
    float* ch_B  = malloc(half_W * half_H * sizeof(float));
    
    // 分离通道
    separate_bayer(raw, W, H, ch_R, ch_Gr, ch_Gb, ch_B);
    
    // 对每个通道独立降噪（如高斯滤波、BM3D等）
    denoise_channel(ch_R,  half_W, half_H, sigma);
    denoise_channel(ch_Gr, half_W, half_H, sigma);
    denoise_channel(ch_Gb, half_W, half_H, sigma);
    denoise_channel(ch_B,  half_W, half_H, sigma);
    
    // 合并回Bayer格式
    merge_bayer(ch_R, ch_Gr, ch_Gb, ch_B, raw, W, H);
    
    // 清理
    free(ch_R); free(ch_Gr); free(ch_Gb); free(ch_B);
}
```

### 4.3 联合降噪

#### 跨通道相关性

虽然Bayer图像每个位置只有一个颜色，但相邻不同颜色像素之间存在相关性。

```c
// 利用绿色通道引导其他通道降噪
void guided_denoise_rb(uint16_t* raw, int W, int H) {
    // 先对绿色通道做高质量降噪（因为绿色采样率高）
    denoise_green_channel(raw, W, H);
    
    // 使用降噪后的绿色作为引导，联合降噪R/B
    for (int y = 1; y < H - 1; y++) {
        for (int x = 1; x < W - 1; x++) {
            if (is_red_or_blue(x, y)) {
                // 获取周围绿色像素的局部统计
                float local_green_var = compute_local_green_variance(raw, x, y, W);
                
                // 根据绿色通道的纹理强度调整降噪强度
                float denoise_strength = adaptive_strength(local_green_var);
                
                // 应用降噪
                raw[y * W + x] = bilateral_filter_single(raw, x, y, W, denoise_strength);
            }
        }
    }
}
```

### 4.4 噪声水平估计

#### Noise Profile

不同ISO和传感器有不同的噪声特性，需要建立噪声曲线：

```
噪声曲线（Noise Profile）：

σ²(I) = a·I + b

其中：
- I: 信号强度
- a: 光子噪声系数
- b: 读出噪声方差

     σ²
      ↑
      │              ╱
      │            ╱   ← 高ISO
      │          ╱
      │        ╱
      │      ╱
      │    ╱         ╱
      │  ╱         ╱   ← 低ISO
      │╱─────────╱─────────→ I
      b（读出噪声底限）
```

#### 估计算法

```c
typedef struct {
    float a;  // 光子噪声系数
    float b;  // 读出噪声方差
} NoiseProfile;

NoiseProfile estimate_noise_profile(uint16_t* raw, int W, int H) {
    // 在多个亮度级别统计噪声
    const int num_bins = 16;
    float mean_per_bin[16] = {0};
    float var_per_bin[16] = {0};
    int count_per_bin[16] = {0};
    
    // 分块统计（8×8块）
    for (int by = 0; by < H - 8; by += 8) {
        for (int bx = 0; bx < W - 8; bx += 8) {
            // 计算块均值和方差
            float block_mean, block_var;
            compute_block_stats(raw, bx, by, W, &block_mean, &block_var);
            
            // 只使用平坦区域（方差/均值比小）
            if (block_var / (block_mean + 1) < 0.1) {
                int bin = (int)(block_mean * num_bins / 65535);
                bin = (bin >= num_bins) ? num_bins - 1 : bin;
                
                mean_per_bin[bin] += block_mean;
                var_per_bin[bin] += block_var;
                count_per_bin[bin]++;
            }
        }
    }
    
    // 线性拟合：var = a*mean + b
    NoiseProfile profile;
    linear_regression(mean_per_bin, var_per_bin, count_per_bin, num_bins,
                      &profile.a, &profile.b);
    
    return profile;
}
```

---

## 5. 绿色不均衡校正（GIC）

### 5.1 Gr/Gb不一致的原因

Bayer阵列中有两种绿色像素（Gr和Gb），由于以下原因可能响应不一致：

```
┌───┬───┐
│ R │Gr │  Gr: 红行上的绿色像素
├───┼───┤
│Gb │ B │  Gb: 蓝行上的绿色像素
└───┴───┘

不一致原因：
1. 传感器制造差异：Gr/Gb滤光片特性微小差异
2. 串扰（Crosstalk）：与相邻不同颜色像素的光电串扰
3. 微透镜不对称：入射角响应差异
4. 读出电路差异：行相关的增益/偏置差异
```

### 5.2 检测方法

```c
// 检测Gr/Gb不均衡程度
float detect_gr_gb_imbalance(uint16_t* raw, int W, int H) {
    uint64_t sum_gr = 0, sum_gb = 0;
    int count = 0;
    
    for (int y = 2; y < H - 2; y++) {
        for (int x = 2; x < W - 2; x++) {
            if (is_green_at_red_row(x, y)) {  // Gr
                sum_gr += raw[y * W + x];
                count++;
            } else if (is_green_at_blue_row(x, y)) {  // Gb
                sum_gb += raw[y * W + x];
            }
        }
    }
    
    float mean_gr = (float)sum_gr / count;
    float mean_gb = (float)sum_gb / count;
    
    return mean_gr / mean_gb;  // 理想值为1.0
}
```

### 5.3 校正算法

#### 全局增益校正

```c
void gic_global_gain(uint16_t* raw, int W, int H, float ratio) {
    // 将Gb调整为与Gr一致
    float gb_gain = ratio;  // ratio = Gr_mean / Gb_mean
    
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            if (is_green_at_blue_row(x, y)) {
                raw[y * W + x] = (uint16_t)(raw[y * W + x] * gb_gain);
            }
        }
    }
}
```

#### 局部自适应校正

```c
void gic_local_adaptive(uint16_t* raw, int W, int H) {
    for (int y = 2; y < H - 2; y++) {
        for (int x = 2; x < W - 2; x++) {
            if (is_green_at_blue_row(x, y)) {  // Gb位置
                // 获取周围Gr像素
                uint16_t gr_neighbors[4] = {
                    raw[(y-1) * W + (x-1)],
                    raw[(y-1) * W + (x+1)],
                    raw[(y+1) * W + (x-1)],
                    raw[(y+1) * W + (x+1)]
                };
                
                // 获取周围Gb像素
                uint16_t gb_neighbors[4] = {
                    raw[y * W + (x-2)],
                    raw[y * W + (x+2)],
                    raw[(y-2) * W + x],
                    raw[(y+2) * W + x]
                };
                
                // 计算局部比率
                float gr_mean = (gr_neighbors[0] + gr_neighbors[1] + 
                                gr_neighbors[2] + gr_neighbors[3]) / 4.0f;
                float gb_mean = (gb_neighbors[0] + gb_neighbors[1] + 
                                gb_neighbors[2] + gb_neighbors[3]) / 4.0f;
                
                if (gb_mean > 0) {
                    float local_ratio = gr_mean / gb_mean;
                    // 限制校正范围（防止过校正）
                    local_ratio = fmaxf(0.95f, fminf(1.05f, local_ratio));
                    raw[y * W + x] = (uint16_t)(raw[y * W + x] * local_ratio);
                }
            }
        }
    }
}
```

---

## 6. RAW域处理顺序

### 6.1 推荐执行顺序

RAW域处理步骤之间存在依赖关系，正确的顺序至关重要：

```
RAW域处理流水线（推荐顺序）：

┌──────────────────────────────────────────────────────────────┐
│                    RAW域处理流水线                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────────┐                                            │
│   │ 1. 黑电平   │ ← 第一步：消除偏置                         │
│   │    校正     │                                            │
│   └──────┬──────┘                                            │
│          ↓                                                    │
│   ┌─────────────┐                                            │
│   │ 2. 线性化   │ ← 校正传感器非线性响应（如有）             │
│   │    校正     │                                            │
│   └──────┬──────┘                                            │
│          ↓                                                    │
│   ┌─────────────┐                                            │
│   │ 3. 坏点     │ ← 必须在降噪前：避免坏点被平滑保留         │
│   │    校正     │                                            │
│   └──────┬──────┘                                            │
│          ↓                                                    │
│   ┌─────────────┐                                            │
│   │ 4. 绿色     │ ← 在降噪前校正：避免影响噪声估计           │
│   │    不均衡   │                                            │
│   └──────┬──────┘                                            │
│          ↓                                                    │
│   ┌─────────────┐                                            │
│   │ 5. RAW域    │ ← 在线性域降噪效果最佳                     │
│   │    降噪     │                                            │
│   └──────┬──────┘                                            │
│          ↓                                                    │
│   ┌─────────────┐                                            │
│   │ 6. 镜头     │ ← 可以在降噪前或后                         │
│   │    阴影校正 │                                            │
│   └──────┬──────┘                                            │
│          ↓                                                    │
│   ┌─────────────┐                                            │
│   │ 7. Demosaic │ ← RAW域处理的最后一步                      │
│   │             │                                            │
│   └─────────────┘                                            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 依赖关系说明

| 步骤 | 依赖 | 原因 |
|------|------|------|
| 黑电平校正 | 无 | 最基础的偏置消除 |
| 线性化 | 黑电平 | 需要在正确零点基础上 |
| 坏点校正 | 黑电平 | 否则坏点阈值判断不准 |
| GIC | 坏点校正 | 坏点会影响Gr/Gb统计 |
| RAW降噪 | 上述所有 | 需要干净的输入信号 |
| LSC | 坏点校正 | 坏点会影响阴影拟合 |
| Demosaic | 所有RAW处理 | 颜色重建需要干净信号 |

### 6.3 处理顺序变体

```
变体A（降噪优先）：
BLC → DPC → GIC → Denoise → LSC → Demosaic
优点：降噪在最干净的信号上进行

变体B（LSC优先）：
BLC → DPC → LSC → GIC → Denoise → Demosaic
优点：阴影校正后亮度更均匀，有利于自适应降噪

变体C（联合处理）：
BLC → DPC → Joint(LSC + Denoise) → GIC → Demosaic
优点：可利用阴影信息指导降噪强度
```

---

## 7. 参考资源

### 学术论文

1. Healey, G.E., Kondepudy, R. (1994). "Radiometric CCD camera calibration and noise estimation." IEEE TPAMI
2. Foi, A., et al. (2008). "Practical Poissonian-Gaussian noise modeling and fitting for single-image raw-data." IEEE TIP
3. Liu, C., et al. (2008). "Automatic estimation and removal of noise from a single image." IEEE TPAMI
4. Dabov, K., et al. (2007). "Image denoising by sparse 3D transform-domain collaborative filtering." IEEE TIP (BM3D)

### 技术规范

- EMVA Standard 1288: Standard for Characterization of Image Sensors and Cameras
- DxOMark Sensor Analysis Methodology

### 开源实现

- **LibRaw**: https://www.libraw.org/
- **dcraw**: https://www.dechifro.org/dcraw/
- **RawTherapee**: https://rawtherapee.com/
- **darktable**: https://www.darktable.org/

### 传感器数据手册

- Sony IMX系列传感器技术文档
- Samsung ISOCELL技术白皮书
- OmniVision传感器规格书

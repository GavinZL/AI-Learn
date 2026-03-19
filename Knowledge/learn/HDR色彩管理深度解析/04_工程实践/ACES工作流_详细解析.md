# ACES工作流详解

> 深入理解学院色彩编码系统的架构、转换与应用

---

## 1. ACES概述

### 1.1 什么是ACES

ACES（Academy Color Encoding System，学院色彩编码系统）是由美国电影艺术与科学学院（AMPAS）开发的开放式色彩管理和图像交换标准。

**核心目标**：
1. **消除歧义**：统一影视制作各阶段的色彩表示
2. **保留信息**：使用超广色域确保颜色信息不丢失
3. **设备无关**：中间文件与具体设备解耦
4. **标准化流程**：从拍摄到放映的端到端一致性

### 1.2 ACES的历史

| 时间 | 里程碑 |
|------|--------|
| 2004 | 学院科学技术委员会启动ACES项目 |
| 2011 | ACES 1.0 预览版发布 |
| 2014 | ACES 1.0 正式版发布 |
| 2017 | ACES 1.1 发布，改进ODT |
| 2022 | ACES 2.0 发布，引入SSTS |

---

## 2. ACES颜色空间体系

### 2.1 ACES2065-1（AP0）

**定义**：
- **三原色**：AP0（ACES Primaries 0）
- **传递函数**：线性（Linear）
- **位深**：16-bit浮点（Half Float）

**AP0色度坐标**：

| 原色 | x | y |
|------|---|---|
| Red | 0.7347 | 0.2653 |
| Green | 0.0000 | 1.0000 |
| Blue | 0.0001 | -0.0770 |
| White | 0.32168 | 0.33767 |

**关键特性**：

1. **超广色域**：AP0三角形包含整个光谱轨迹
2. **全正值**：所有可见颜色可用正值表示
3. **设备无关**：不与任何物理设备绑定
4. **存储交换**：用于存档和跨系统交换

> ⚠️ **注意**：AP0包含"想象色"（Imaginary Colors），无法在物理世界中真实显示。

### 2.2 ACEScg（AP1）

**定义**：
- **三原色**：AP1（ACES Primaries 1）
- **传递函数**：线性
- **用途**：CG渲染、合成、VFX工作空间

**AP1色度坐标**：

| 原色 | x | y |
|------|---|---|
| Red | 0.713 | 0.293 |
| Green | 0.165 | 0.830 |
| Blue | 0.128 | 0.044 |
| White | 0.32168 | 0.33767 |

**与AP0的对比**：

| 特性 | AP0 | AP1 |
|------|-----|-----|
| 色域范围 | 包含所有可见色 | 接近Rec. 2020 |
| 物理可实现 | 否 | 是 |
| 渲染适用性 | 差（数值不稳定） | 优秀 |
| 主要用途 | 存档/交换 | 渲染/合成 |

**为什么选择AP1作为渲染空间？**

研究表明，渲染工作空间的色域会影响计算结果：

1. **光谱渲染Ground Truth**：使用波长采样计算最准确
2. **RGB渲染近似**：不同RGB空间结果不同
3. **AP1优势**：三原色接近光谱轨迹，渲染结果更接近光谱渲染

### 2.3 其他ACES颜色空间

| 空间 | 传递函数 | 用途 |
|------|---------|------|
| **ACEScc** | Log | 调色，类似Cineon Log |
| **ACEScct** | Log + Toe | 调色，暗部有线性段 |
| **ACESproxy** | Log | 10-bit/12-bit整型传输 |

---

## 3. ACES转换架构

### 3.1 转换流程概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ACES Processing Pipeline                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│   │  Input   │──▶│  Look    │──▶│Reference │──▶│ Output   │──▶│ Display  │  │
│   │Transform │   │Transform │   │Rendering│   │Transform │   │          │  │
│   │  (IDT)   │   │  (LMT)   │   │(RRT/SSTS)│   │  (ODT)   │   │          │  │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│                                                                              │
│   Scene-Referred  Scene-Referred  Output-Referred  Device-Specific          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Input Transform（IDT）

**功能**：将输入设备的原生数据转换到ACES2065-1（AP0）

**输入类型**：
- 摄影机RAW（ARRI、RED、Sony等）
- 扫描胶片
- sRGB/Rec.709图像
- CG渲染（直接生成ACEScg）

**IDT的组成**：

1. **线性化**：应用设备特定的EOTF
2. **白平衡**：调整到ACES白点（D60-like）
3. **矩阵转换**：从设备RGB转换到AP0

**示例：sRGB IDT**

```
sRGB图像 → sRGB EOTF → sRGB Linear → sRGB_to_AP0矩阵 → ACES2065-1
```

**重要说明**：
- IDT由设备制造商提供
- 不同摄影机型号有特定IDT
- 使用错误的IDT会导致颜色偏差

### 3.3 Look Transform（LMT）

**功能**：创意性的外观调整，输入输出都是Scene-Referred

**与调色的区别**：

| 特性 | LMT | 调色（Color Grading） |
|------|-----|---------------------|
| 应用阶段 | 渲染/输出之前 | 最终输出之后 |
| 调整范围 | 整体外观 | 局部区域 |
| 可逆性 | 通常可逆 | 通常不可逆 |
| 目的 | 建立基调 | 精细调整 |

**常见LMT**：
- **Blue Light Artifact Fix**：修正高亮蓝色过饱和
- **Print Film Emulation**：模拟胶片外观
- **Show LUT**：特定项目的整体风格

### 3.4 Reference Rendering Transform（RRT）

**功能**：将Scene-Referred图像转换为Output-Referred

**ACES 1.0 RRT组成**：

1. **Input Conversion**：从AP0转换到内部工作空间
2. **Gamut Compression**：压缩超出色域的颜色
3. **Tone Scale**：S曲线色调映射
4. **Output Conversion**：转换到输出空间

**Tone Scale曲线**：

使用分段B-spline曲线（segmented_spline_c5）：
- 暗部：提升对比度，保留细节
- 中灰：保持自然
- 高光：柔和压缩，避免硬裁切

### 3.5 Output Device Transform（ODT）

**功能**：将RRT输出转换到特定显示设备

**ODT的组成**：

1. **Gamut Mapping**：将宽色域映射到设备色域
2. **Tone Scale**：针对设备动态范围的调整
3. **Encoding**：应用设备的EOTF（Gamma/PQ/HLG）

**ACES 1.0 ODT类型**：

| ODT | 色域 | 峰值亮度 | 传递函数 |
|-----|------|---------|---------|
| sRGB | sRGB | 100 nit | sRGB |
| Rec.709 | Rec.709 | 100 nit | BT.1886 |
| DCI-P3 | P3 | 48/100 nit | Gamma 2.6 |
| Rec.2020 | Rec.2020 | 1000 nit | PQ |
| P3D60 | P3 | 1000 nit | PQ |

---

## 4. ACES 2.0改进

### 4.1 Single Stage Tone Scale（SSTS）

ACES 1.0的问题：
- RRT和ODT各有一次Tone Scale
- 概念复杂，实现困难
- HDR ODT标准不统一

ACES 2.0解决方案：
- 合并RRT和ODT的Tone Scale
- 统一的SSTS算法
- 简化的HDR ODT

**SSTS特性**：

```
输入（Scene-Referred，AP0）
    ↓
┌─────────────────┐
│   Gamut Mapping │  ← 处理超出色域的颜色
│  (AP0 → AP1)    │
└─────────────────┘
    ↓
┌─────────────────┐
│   SSTS Tone     │  ← 统一的色调映射
│   Scale         │
└─────────────────┘
    ↓
┌─────────────────┐
│   Device        │  ← 设备特定转换
│   Encoding      │
└─────────────────┘
    ↓
输出（Device-Specific）
```

### 4.2 新的Output Transform命名

ACES 2.0使用统一的命名规则：

```
OutputTransform.ACES.<TargetColorSpace>.<PeakBrightness>
```

示例：
- `OutputTransform.ACES.Rec709.100nit`
- `OutputTransform.ACES.P3D65.1000nit`
- `OutputTransform.ACES.Rec2020.4000nit`

---

## 5. 游戏引擎中的ACES实现

### 5.1 UE4的ACES管线

**核心文件**：`Engine/Shaders/Private/ACES.ush`

**管线流程**：

```
[场景渲染] ──▶ [后处理] ──▶ [生成CLUT] ──▶ [应用CLUT]
 sRGB Linear    HDR Linear     AP1空间        输出
```

**CLUT生成（CombineLUTs）**：

1. **解码输入**：
   - SDR：Log解码
   - HDR：PQ解码（ST2084ToLinear）

2. **White Balance**：色温调整

3. **颜色空间转换**：
   ```hlsl
   float3 ColorAP1 = mul(sRGB_2_AP1, BalancedColor);
   ```

4. **色域扩展（可选）**：
   ```hlsl
   // Expand bright saturated colors outside sRGB gamut
   float3 ColorExpand = mul(ExpandMat, ColorAP1);
   ColorAP1 = lerp(ColorAP1, ColorExpand, ExpandAmount);
   ```

5. **Color Grading**：色调、饱和度、对比度调整

6. **Tonemapping（SDR）**：
   ```hlsl
   // Blue Light Artifact Fix (LMT)
   ColorAP1 = lerp(ColorAP1, mul(BlueCorrectAP1, ColorAP1), BlueCorrection);
   
   // Filmic Tonemapping (RRT+ODT合并)
   ColorAP1 = FilmToneMap(ColorAP1);
   
   // 撤销Blue Correction
   ColorAP1 = lerp(ColorAP1, mul(BlueCorrectInvAP1, ColorAP1), BlueCorrection);
   ```

7. **输出编码**：
   - SDR：sRGB/Rec.709 OETF
   - HDR：PQ OETF

### 5.2 COD: WWII的ACES变体

**改进点**：

1. **保留RRT/ODT分离**：
   - Tone Curve（RRT等效）
   - Display Mapping（ODT等效）

2. **用户可调的HDR Range Reduction**：
   - 使用BT.2390 EETF
   - 可校准黑点/白点

3. **Universal CLUT**：
   - 包含：Color Grading + Tone Curve + Display Mapping
   - 每帧Async Compute生成

### 5.3 实现对比

| 特性 | UE4原生 | COD: WWII | 推荐方案 |
|------|---------|-----------|---------|
| RRT/ODT | 合并 | 分离 | 分离更清晰 |
| HDR Range Reduction | 固定 | 可调 | 可调更灵活 |
| Tone Curve | ACES Filmic | 自定义S曲线 | 项目特定 |
| UI处理 | Offscreen混合 | Backbuffer混合 | 视需求 |

---

## 6. DCC软件中的ACES

### 6.1 OpenColorIO（OCIO）

**什么是OCIO**：
- 索尼图像工作室开发的开源色彩管理系统
- 支持ACES的配置文件
- 跨软件一致性

**支持OCIO的软件**：
- Nuke
- Maya
- Houdini
- Blender
- Photoshop（通过插件）

### 6.2 配置OCIO

**基本配置**：

```yaml
ocio_profile_version: 2

search_path: luts
strictparsing: true
luma: [0.2126, 0.7152, 0.0722]

roles:
  scene_linear: ACES - ACEScg
  compositing_linear: ACES - ACEScg
  default: ACES - ACES2065-1
  
displays:
  sRGB:
    - !<View> {name: ACES 1.0 SDR-video, colorspace: Output - sRGB}
    - !<View> {name: Raw, colorspace: Raw}
  
  HDR:
    - !<View> {name: ACES 1.0 HDR-video, colorspace: Output - Rec.2020}
```

### 6.3 Substance Painter的ACES方案

Substance Painter不原生支持OCIO，但支持自定义LUT：

**解决方案**：
1. 在Nuke中生成sRGB Linear → ACES sRGB的LUT
2. 导出为Substance支持的格式
3. 在项目中加载LUT

---

## 7. ACES的局限与替代方案

### 7.1 ACES的批评

1. **"电影感"并非普适**：
   - ACES的S曲线针对影视优化
   - 某些游戏类型（二次元、卡通）可能不合适

2. **计算开销**：
   - 完整的ACES转换计算量较大
   - 移动端需要简化

3. **HDR游戏支持有限**：
   - 原生ACES HDR ODT较简单
   - 需要二次开发优化

### 7.2 替代方案

| 方案 | 特点 | 适用场景 |
|------|------|---------|
| **自定义Tonemapping** | 完全可控 | 风格化游戏 |
| **AgX** | Blender新方案，更自然 | 照片级真实 |
| **Filmic** | Blender旧方案 | 开源项目 |
| **Khronos PBR Neutral** | 中性色调映射 | 跨平台一致性 |

---

## 8. 调试与验证

### 8.1 ACES参考图像

ACES提供标准参考图像用于验证实现：

- **Still Life**：包含各种材质和颜色
- **Color Charts**：标准色卡
- **Ramps**：渐变测试

### 8.2 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 整体偏色 | 错误的IDT | 检查输入颜色空间 |
| 高光过曝 | Tone Scale问题 | 调整曝光或Tonemapping参数 |
| 暗部死黑 | Gamma/EOTF错误 | 检查传递函数实现 |
| 饱和度异常 | 色域转换错误 | 验证矩阵正确性 |
| 色带（Banding） | 位深不足 | 使用10-bit+或抖动 |

---

## 9. 总结

| 组件 | 功能 | 在游戏中的等效 |
|------|------|--------------|
| **IDT** | 输入设备转换 | 纹理解码（sRGB EOTF） |
| **LMT** | 外观调整 | 可选的风格化LUT |
| **RRT** | 场景到输出的色调映射 | Tonemapping核心 |
| **ODT** | 设备特定输出 | 显示器适配 + OETF |

---

## 参考

- [回到主文章](../HDR色彩管理深度解析.md)
- [ACES官方网站](https://acescentral.com/)
- [ACES GitHub](https://github.com/ampas/aces-dev)
- [OpenColorIO](https://opencolorio.org/)
- TB-2014-001: ACES System Version 1.0 Overview
- TB-2014-004: ACES Color Space Specification

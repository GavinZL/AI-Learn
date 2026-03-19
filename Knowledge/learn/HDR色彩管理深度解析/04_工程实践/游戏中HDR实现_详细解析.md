# 游戏中的HDR实现详解

> 从理论到实践：现代游戏引擎的HDR渲染管线

---

## 1. 游戏HDR概述

### 1.1 游戏HDR的独特挑战

相比影视制作，游戏HDR面临额外挑战：

| 挑战 | 影视 | 游戏 |
|------|------|------|
| **实时性** | 离线渲染，无限制 | 16-33ms帧时间限制 |
| **交互性** | 固定画面 | 动态场景，玩家控制 |
| **设备多样性** | 专业监视器 | 各种HDR/SDR显示器 |
| **一致性** | 单次输出 | 需同时支持SDR和HDR |
| **调试难度** | 可控环境 | 用户环境不可控 |

### 1.2 游戏HDR的发展

| 时间 | 里程碑 |
|------|--------|
| 2016 | PS4 Pro、Xbox One S支持HDR |
| 2017 | 《地平线：零之曙光》等首批HDR游戏 |
| 2018 | 《使命召唤：二战》技术分享 |
| 2019 | UE4原生HDR支持完善 |
| 2020+ | HDR成为3A游戏标配 |

---

## 2. HDR管线架构

### 2.1 整体流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          HDR Game Pipeline                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │  G-Buffer   │   │   Lighting  │   │  Post-Proc  │   │   Output    │       │
│  │   Pass      │──▶│    Pass     │──▶│    Pass     │──▶│    Pass     │       │
│  │             │   │             │   │             │   │             │       │
│  │ sRGB Linear │   │ HDR Linear  │   │ HDR Linear  │   │ Device      │       │
│  │  [0,1+]     │   │  [0,10000+] │   │  [0,10000+] │   │ Specific    │       │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘       │
│                                                               │               │
│                                          ┌────────────────────┘               │
│                                          ▼                                    │
│                              ┌─────────────────────┐                          │
│                              │   SDR Display       │                          │
│                              │   sRGB/Rec.709      │                          │
│                              │   100-300 nit       │                          │
│                              └─────────────────────┘                          │
│                                          │                                    │
│                              ┌─────────────────────┐                          │
│                              │   HDR Display       │                          │
│                              │   Rec.2020 + PQ     │                          │
│                              │   1000-10000 nit    │                          │
│                              └─────────────────────┘                          │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 关键设计决策

#### 工作空间选择

| 选项 | 优点 | 缺点 |
|------|------|------|
| **sRGB Linear** | 简单，兼容性好 | 色域窄，渲染精度受限 |
| **ACEScg (AP1)** | 广色域，渲染准确 | 需要额外转换 |
| **Rec.2020 Linear** | 直接对应HDR输出 | 计算开销大 |

**推荐**：ACEScg作为渲染工作空间

#### HDR元数据

HDR10（最常见）：
- 静态元数据（Static Metadata）
- MaxCLL（最大内容亮度）
- MaxFALL（最大平均帧亮度）
- 每帧相同

HDR10+ / Dolby Vision：
- 动态元数据（Dynamic Metadata）
- 每场景/每帧调整
- 更好的色调映射

---

## 3. 核心实现技术

### 3.1 CLUT（Color Lookup Table）

**为什么使用CLUT**：
- 将复杂的颜色转换预计算到3D纹理
- 运行时只需一次纹理采样
- 大幅提升性能

**CLUT的构建**：

```
输入坐标 (R,G,B) ──▶ 3D LUT ──▶ 输出颜色 (R',G',B')
   [0,1]^3           32^3或64^3      [0,1]^3
```

**UE4的CLUT生成**：

```hlsl
// PostProcessCombineLUTs.usf

float4 CombineLUTsCommon(float2 InUV, uint InLayerIndex)
{
    // 1. 构造中性颜色（LUT坐标）
    float3 Neutral = float3(InUV, InLayerIndex / LUTSize) * LUTSize / (LUTSize - 1);
    
    // 2. 解码到线性空间
    float3 LinearColor;
    if (GetOutputDevice() >= 3) // HDR
    {
        LinearColor = ST2084ToLinear(Neutral) * LinearToNitsScaleInverse;
    }
    else // SDR
    {
        LinearColor = LogToLin(Neutral) - LogToLin(0);
    }
    
    // 3. White Balance
    float3 BalancedColor = WhiteBalance(LinearColor);
    
    // 4. 转换到AP1
    float3 ColorAP1 = mul(sRGB_2_AP1, BalancedColor);
    
    // 5. 色域扩展（可选）
    if (ExpandGamut > 0)
    {
        ColorAP1 = ExpandGamutFunc(ColorAP1, ExpandGamut);
    }
    
    // 6. Color Grading
    ColorAP1 = ColorCorrectAll(ColorAP1);
    
    // 7. Output Transform（RRT + ODT）
    float3 OutputColor = OutputTransform(ColorAP1, GetOutputDevice());
    
    return float4(OutputColor, 0);
}
```

### 3.2 色调映射（Tonemapping）

#### SDR路径

**UE4 Filmic Tonemapping**：

```hlsl
float3 FilmToneMap(float3 Color)
{
    // 参数（可调）
    float Slope = 0.88;
    float Toe = 0.55;
    float Shoulder = 0.26;
    float BlackClip = 0.0;
    float WhiteClip = 0.04;
    
    // 应用S曲线
    float3 c = Color;
    c = (c * (Slope * c + Toe)) / (c * (Slope * c + Shoulder) + BlackClip) + WhiteClip;
    
    return c;
}
```

**COD的Tone Curve**：

```hlsl
// 基于log2亮度的S曲线
float ToneCurve(float x)
{
    // x: log2(亮度)
    // 输出: 映射后的log2(亮度)
    
    float shadow = -5.0;  // 暗部压缩点
    float highlight = 5.0; // 高光压缩点
    
    if (x < shadow)
        return lerp(x, shadow, smoothstep(shadow - 2.0, shadow, x));
    else if (x > highlight)
        return lerp(x, highlight, smoothstep(highlight, highlight + 2.0, x));
    
    return x;
}
```

#### HDR路径

**关键区别**：
- SDR：需要将HDR压缩到[0,1]范围
- HDR：保留高动态范围，仅做Range Reduction

**HDR Range Reduction**：

```hlsl
float3 HDRRangeReduction(float3 Color, float MaxDisplayNits)
{
    // 输入: 0-10000 nit的线性颜色
    // 输出: 适配显示器峰值亮度的颜色
    
    float luminance = Luminance(Color);
    
    // 使用BT.2390 EETF或自定义曲线
    float mappedLuminance = BT2390EETF(luminance, MaxDisplayNits);
    
    // 保持色度，调整亮度
    return Color * (mappedLuminance / max(luminance, 0.0001));
}
```

### 3.3 色域映射（Gamut Mapping）

当颜色超出目标色域时需要处理：

#### 简单裁切（Clipping）

```hlsl
float3 SimpleClip(float3 Color)
{
    return saturate(Color); // 硬裁切到[0,1]
}
```

问题：色相偏移，高饱和度颜色变灰

#### 感知色域映射

```hlsl
float3 PerceptualGamutMap(float3 Color, float3x3 FromToMatrix)
{
    // 1. 转换到目标空间
    float3 targetColor = mul(FromToMatrix, Color);
    
    // 2. 检查是否超出色域
    if (any(targetColor < 0) || any(targetColor > 1))
    {
        // 3. 降低饱和度直到在色域内
        float luminance = Luminance(Color);
        float3 desaturated = luminance;
        
        float t = 0.5; // 可调整的饱和度保持度
        targetColor = lerp(desaturated, targetColor, t);
    }
    
    return targetColor;
}
```

### 3.4 UI渲染

UI需要特殊处理以保持一致性：

#### 问题

- UI通常在sRGB空间设计
- HDR显示需要提升UI亮度
- 直接转换可能导致UI过亮

#### 解决方案

**UE4方案**：

```hlsl
// UI亮度限制在300 nit
float3 RenderUI(float3 UIColor)
{
    // 1. sRGB解码
    float3 linearUI = SRGBToLinear(UIColor);
    
    // 2. 限制最大亮度
    float maxUIBrightness = 300.0 / 10000.0; // PQ空间中的300 nit
    linearUI = min(linearUI, maxUIBrightness);
    
    // 3. 转换到BT.2020
    float3 ui2020 = mul(sRGB_2_BT2020, linearUI);
    
    // 4. PQ编码
    return LinearToPQ(ui2020);
}
```

**混合模式处理**：

- **Alpha Blend**：直接混合，注意Gamma校正
- **Additive**：在Linear空间计算，避免过曝

---

## 4. 平台特定实现

### 4.1 DirectX 12

**HDR Swapchain创建**：

```cpp
// 创建HDR交换链
DXGI_SWAP_CHAIN_DESC1 swapChainDesc = {};
swapChainDesc.Width = width;
swapChainDesc.Height = height;
swapChainDesc.Format = DXGI_FORMAT_R10G10B10A2_UNORM; // 或 FLOAT
swapChainDesc.SampleDesc.Count = 1;
swapChainDesc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
swapChainDesc.BufferCount = 2;
swapChainDesc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
swapChainDesc.Flags = DXGI_SWAP_CHAIN_FLAG_FRAME_LATENCY_WAITABLE_OBJECT;

// 设置HDR元数据
DXGI_HDR_METADATA_HDR10 hdrMetadata = {};
hdrMetadata.RedPrimary[0] = 34000;  // x = 0.708 * 50000
hdrMetadata.RedPrimary[1] = 14600;  // y = 0.292 * 50000
// ... 其他原色和白点
hdrMetadata.MaxMasteringLuminance = 1000; // nit
hdrMetadata.MinMasteringLuminance = 0;    // nit
hdrMetadata.MaxContentLightLevel = 1000;  // MaxCLL
hdrMetadata.MaxFrameAverageLightLevel = 400; // MaxFALL

swapChain->SetHDRMetaData(DXGI_HDR_METADATA_TYPE_HDR10, sizeof(hdrMetadata), &hdrMetadata);
```

### 4.2 PlayStation 5

**PS5 HDR特性**：
- 原生支持HDR10
- 自动色调映射
- 系统级HDR校准

**实现注意**：
- 使用SDK提供的HDR API
- 遵循平台HDR指南
- 利用系统HDR设置

### 4.3 Xbox Series X|S

**Auto HDR**：
- 系统自动将SDR游戏转换为HDR
- 开发者可覆盖默认行为
- 提供原生HDR可获得最佳效果

---

## 5. 调试与优化

### 5.1 HDR调试工具

#### 内部调试视图

```hlsl
// 显示亮度热力图
float3 DebugLuminance(float3 Color)
{
    float lum = Luminance(Color);
    
    // 颜色编码
    if (lum < 1.0) return float3(0, 0, 1);      // 蓝: SDR范围
    else if (lum < 100.0) return float3(0, 1, 0); // 绿: 低HDR
    else if (lum < 1000.0) return float3(1, 1, 0); // 黄: 中HDR
    else return float3(1, 0, 0);                    // 红: 高HDR
}

// 显示色域覆盖
float3 DebugGamut(float3 Color)
{
    // 转换到xy色度
    float3 xyY = RGBtoxyY(Color);
    
    // 检查是否在sRGB三角形内
    if (InsideSRGBGamut(xyY.xy))
        return Color; // 原色
    else
        return float3(1, 0, 1); // 品红: 广色域
}
```

#### 校准画面

- 灰阶渐变：检查色调映射
- 色卡：验证颜色准确性
- 亮度测试图：验证HDR范围

### 5.2 性能优化

| 技术 | 开销 | 优化方案 |
|------|------|---------|
| CLUT生成 | 每帧Compute Shader | 只在参数变化时更新 |
| PQ转换 | 多次pow | LUT预计算或近似 |
| 色域转换 | 矩阵乘法 | 合并到CLUT |
| UI渲染 | 额外Pass | 合并到主Pass |

---

## 6. 最佳实践

### 6.1 美术工作流

1. **在HDR显示器上创作**：
   - 确保美术看到真实的HDR效果
   - 定期在SDR显示器上检查

2. **使用参考图像**：
   - 建立项目的HDR参考标准
   - 与影视HDR内容对比

3. **曝光校准**：
   - 建立标准的曝光参考
   - 使用灰卡校准中灰

### 6.2 技术实现

1. **线性工作流**：
   - 所有光照计算在线性空间
   - 仅在最后应用OETF

2. **广色域中间空间**：
   - 使用ACEScg或Rec.2020
   - 避免sRGB空间计算

3. **一致的View Transform**：
   - 所有镜头使用相同的Tonemapping
   - 通过Color Grading调整风格

4. **用户校准**：
   - 提供HDR亮度校准
   - 保存用户偏好设置

### 6.3 质量验证

| 测试项 | 方法 | 通过标准 |
|--------|------|---------|
| SDR/HDR一致性 | 并排对比 | 视觉上接近 |
| 灰阶中性 | 灰阶图 | 无色偏 |
| 高光细节 | 高亮场景 | 可见细节 |
| 暗部细节 | 暗场景 | 无死黑 |
| 色带检查 | 渐变图 | 无明显色带 |

---

## 7. 常见问题

### Q: HDR游戏在SDR显示器上会怎样？

A: 需要色调映射到SDR范围。现代游戏引擎通常：
- 自动检测显示器类型
- 应用SDR Output Transform
- 保持视觉一致性

### Q: 如何处理不同HDR显示器的差异？

A: 推荐方案：
- 使用BT.2390 EETF进行Range Reduction
- 提供用户校准选项
- 默认1000 nit，支持到4000 nit

### Q: 移动端可以实现HDR吗？

A: 可以，但有限制：
- 部分高端手机支持HDR显示
- 需要简化计算（无CLUT或低分辨率CLUT）
- 考虑功耗影响

### Q: 网络流式传输的HDR游戏如何处理？

A: 考虑方案：
- 云端渲染HDR，客户端显示
- 或云端色调映射到SDR
- 取决于网络带宽和延迟

---

## 8. 参考实现

### UE4 HDR控制台命令

```
// 启用HDR输出
r.HDR.EnableHDROutput 1

// 设置输出设备
// 0=sRGB, 1=Rec709, 2=ExplicitGamma, 3=ACES1000nit, 4=ACES2000nit
r.HDR.Display.OutputDevice 3

// 设置色域
// 0=sRGB, 1=Rec709, 2=DCI-P3, 3=Rec2020, 4=ACES
r.HDR.Display.ColorGamut 3

// UI合成模式
r.HDR.UI.CompositeMode 1

// UI亮度级别
r.HDR.UI.Level 1.0
```

---

## 参考

- [回到主文章](../HDR色彩管理深度解析.md)
- [Digital Dragons 2018: HDR in Call of Duty](https://www.youtube.com/watch?v=5xCqCnB1mC0)
- [GDC 2019: Destiny 2 HDR](https://www.gdcvault.com/)
- [UE4 HDR Documentation](https://docs.unrealengine.com/)
- Microsoft DirectX HDR Samples

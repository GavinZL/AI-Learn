# SDR渲染管线详解

> 理解标准动态范围渲染的完整流程与关键技术

---

## 1. SDR渲染管线概述

### 1.1 管线的整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SDR Rendering Pipeline                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │  Asset   │   │  Decode  │   │  Render  │   │  Post-   │   │  Output  │  │
│  │  Input   │──▶│  Linear  │──▶│   Pass   │──▶│ Process  │──▶│  Encode  │  │
│  │          │   │  Space   │   │          │   │          │   │          │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│                                                                              │
│  sRGB textures     Linear sRGB      HDR Linear      SDR Range      sRGB    │
│  (gamma encoded)   (0-1+)          (unbounded)     (0-1)        (encoded)  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 关键问题

SDR渲染的核心挑战：

1. **动态范围限制**：最终输出必须限制在[0,1]范围
2. **Gamma校正**：线性与非线性空间的正确转换
3. **色调映射**：HDR场景值到SDR范围的映射
4. **一致性**：不同显示器上的显示一致性

---

## 2. 资产输入阶段

### 2.1 纹理的颜色空间

游戏资产通常在DCC工具中创建，需要注意：

| 纹理类型 | 颜色空间 | 传递函数 | 用途 |
|---------|---------|---------|------|
| **Albedo/Diffuse** | sRGB | sRGB OETF | 基础颜色 |
| **Normal Map** | Linear | None | 法线方向 |
| **Roughness/Metalness** | Linear | None | 材质参数 |
| **Ambient Occlusion** | Linear | None | 遮挡信息 |
| **Light Maps** | Linear | None | 烘焙光照 |
| **HDR Environment** | Scene-Referred | Linear | 环境光照 |

### 2.2 纹理导入设置

**正确配置示例（UE4）**：

```
纹理: T_Albedo_01
├── Compression Settings: Default (DXT1/5)
├── Mip Gen Settings: SimpleAverage
├── LOD Bias: 0
├── SRGB: ✓ (启用sRGB解码)
└── Never Stream: ☐

纹理: T_Roughness_01
├── Compression Settings: Default (DXT1)
├── Mip Gen Settings: SimpleAverage
├── LOD Bias: 0
├── SRGB: ☐ (线性纹理，不启用)
└── Never Stream: ☐
```

### 2.3 常见错误

| 错误 | 现象 | 修复 |
|------|------|------|
| 线性纹理标记为sRGB | 粗糙度/金属度看起来错误 | 取消sRGB标记 |
| sRGB纹理标记为线性 | 颜色过暗，对比度异常 | 启用sRGB标记 |
| 忽略Mip Map | 远处纹理闪烁或模糊 | 正确生成Mip Map |

---

## 3. 解码到线性空间

### 3.1 sRGB EOTF解码

在着色器中将sRGB纹理解码到线性空间：

```hlsl
float3 SRGBToLinear(float3 srgb)
{
    return srgb <= 0.04045 
        ? srgb / 12.92 
        : pow((srgb + 0.055) / 1.055, 2.4);
}
```

**硬件加速**：

现代GPU支持硬件sRGB解码：
- 纹理格式：`DXGI_FORMAT_R8G8B8A8_UNORM_SRGB`
- 采样时自动应用EOTF
- 无需着色器手动转换

### 3.2 线性工作空间

解码后进入**线性工作空间**：

```
sRGB纹理值 [0-1] 
    ↓ sRGB EOTF
线性颜色值 [0-1]（可能>1由于HDR光照）
    ↓ 光照计算
HDR场景值 [0-∞]
```

**为什么必须线性？**

光照计算基于物理：

$$
L_{out} = L_{light} \cdot f_{brdf}(\omega_i, \omega_o) \cdot \cos\theta_i
$$

这个公式假设所有输入都是线性的。如果在Gamma空间计算：

```
错误: (A^γ + B^γ)^(1/γ) ≠ A + B
正确: A + B = A + B
```

---

## 4. 渲染阶段

### 4.1 前向渲染 vs 延迟渲染

| 特性 | 前向渲染 | 延迟渲染 |
|------|---------|---------|
| **光照计算** | 每个像素每光源 | 在G-Buffer后统一计算 |
| **材质复杂度** | 受限 | 灵活 |
| **半透明** | 原生支持 | 需要额外Pass |
| **MSAA** | 原生支持 | 需要特殊处理 |
| **带宽** | 较低 | 较高 |

### 4.2 G-Buffer布局（延迟渲染）

```
RT0: RGB = Albedo (sRGB), A = Occlusion
RT1: RGB = Normal (XYZ), A = Roughness
RT2: RGB = Emissive, A = Metallic
RT3: RGB = World Position (可选), A = Specular
RT4: RGB = Base Color (Linear), A = Subsurface
```

**注意事项**：
- Albedo通常存储为sRGB，采样时解码
- Normal、Roughness等存储为线性
- 精度：Albedo 8-bit，Normal 10/16-bit

### 4.3 光照计算

标准PBR光照方程：

```hlsl
float3 DirectLighting(SurfaceData surface, LightData light)
{
    float3 F0 = lerp(0.04, surface.Albedo, surface.Metallic);
    
    // Cook-Torrance BRDF
    float3 F = FresnelSchlick(max(dot(H, V), 0.0), F0);
    float D = DistributionGGX(N, H, surface.Roughness);
    float G = GeometrySmith(N, V, L, surface.Roughness);
    
    float3 numerator = D * G * F;
    float denominator = 4.0 * max(dot(N, V), 0.0) * max(dot(N, L), 0.0) + 0.001;
    
    float3 specular = numerator / denominator;
    
    float3 kS = F;
    float3 kD = (1.0 - kS) * (1.0 - surface.Metallic);
    
    float NdotL = max(dot(N, L), 0.0);
    
    return (kD * surface.Albedo / PI + specular) * light.Color * light.Intensity * NdotL;
}
```

---

## 5. 后处理阶段

### 5.1 后处理管线顺序

```
1. Depth of Field
2. Motion Blur
3. Bloom
4. Tone Mapping
5. Color Grading
6. Anti-Aliasing (FXAA/TAA)
7. Vignette
8. Gamma Encoding
```

**关键原则**：
- 线性空间操作在Tone Mapping之前
- 非线性空间操作在Tone Mapping之后
- Bloom等效果需要HDR输入

### 5.2 Bloom效果

```hlsl
// Bloom提取（HDR阈值）
float3 BloomExtract(float3 color, float threshold)
{
    float luminance = dot(color, float3(0.2126, 0.7152, 0.0722));
    float contribution = max(0, luminance - threshold);
    return color * contribution / max(luminance, 0.0001);
}

// 高斯模糊（多次Downsample + Blur）
float3 GaussianBlur(Texture2D tex, float2 uv, float2 direction)
{
    float3 result = 0;
    float weights[5] = {0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216};
    
    for (int i = -4; i <= 4; i++)
    {
        float2 offset = direction * i * texelSize;
        result += tex.Sample(sampler, uv + offset) * weights[abs(i)];
    }
    
    return result;
}

// 合成
float3 CompositeBloom(float3 base, float3 bloom, float intensity)
{
    return base + bloom * intensity;
}
```

### 5.3 曝光（Exposure）

自动曝光计算：

```hlsl
float CalculateExposure(float avgLuminance, float targetLuminance)
{
    // EV100计算
    float EV100 = log2(avgLuminance * 100.0 / 12.5);
    
    // 曝光值
    float exposure = 1.0 / (1.2 * pow(2.0, EV100));
    
    // 限制范围
    return clamp(exposure, minExposure, maxExposure);
}

// 应用曝光
float3 ApplyExposure(float3 color, float exposure)
{
    return color * exposure;
}
```

---

## 6. 色调映射（Tone Mapping）

### 6.1 色调映射的必要性

渲染后的场景亮度可能达到数千甚至上万：

```
室内场景: 0.1 - 10
室外场景: 1 - 1000+
直视太阳: 10000+
```

SDR显示范围：0 - 1（相对）或 0.1 - 100 nit（绝对）

### 6.2 简单Reinhard

```hlsl
float3 Reinhard(float3 hdr)
{
    return hdr / (1.0 + hdr);
}
```

**问题**：
- 整体偏灰
- 暗部对比度损失

### 6.3 改进的Reinhard

```hlsl
float3 ReinhardExtended(float3 hdr, float maxWhite)
{
    float3 numerator = hdr * (1.0 + hdr / (maxWhite * maxWhite));
    return numerator / (1.0 + hdr);
}
```

### 6.4 ACES Filmic（推荐）

```hlsl
float3 ACESFilm(float3 x)
{
    float a = 2.51;
    float b = 0.03;
    float c = 2.43;
    float d = 0.59;
    float e = 0.14;
    
    return saturate((x * (a * x + b)) / (x * (c * x + d) + e));
}
```

**特性**：
- 自然的S曲线
- 保留暗部和高光细节
- 接近胶片响应

---

## 7. 颜色分级（Color Grading）

### 7.1 分级参数

| 参数 | 范围 | 效果 |
|------|------|------|
| **Saturation** | 0-2 | 整体饱和度 |
| **Contrast** | 0-2 | 对比度 |
| **Gamma** | 0.5-2 | 中间调亮度 |
| **Gain** | 0-2 | 高光调整 |
| **Lift** | -1-1 | 暗部调整 |

### 7.2 分级实现

```hlsl
float3 ColorGrading(float3 color, GradingParams params)
{
    // Lift/Gamma/Gain
    color = pow(color * params.Gain + params.Lift, params.Gamma);
    
    // 对比度
    color = (color - 0.5) * params.Contrast + 0.5;
    
    // 饱和度
    float luminance = dot(color, float3(0.2126, 0.7152, 0.0722));
    color = lerp(luminance, color, params.Saturation);
    
    return saturate(color);
}
```

### 7.3 使用LUT进行分级

```hlsl
// 32x32x32 3D LUT
Texture3D ColorGradingLUT;

float3 ApplyColorGradingLUT(float3 color)
{
    // 映射到LUT坐标
    float3 lutCoord = color * 31.0 / 32.0 + 0.5 / 32.0;
    
    return ColorGradingLUT.Sample(LinearSampler, lutCoord);
}
```

---

## 8. 输出编码

### 8.1 sRGB OETF编码

```hlsl
float3 LinearToSRGB(float3 linear)
{
    return linear <= 0.0031308 
        ? linear * 12.92 
        : 1.055 * pow(linear, 1.0 / 2.4) - 0.055;
}
```

### 8.2 抖动（Dithering）

避免8-bit输出的色带：

```hlsl
float3 Dither(float3 color, float2 screenPos)
{
    // Bayer抖动矩阵
    float bayer[16] = {
        0, 8, 2, 10,
        12, 4, 14, 6,
        3, 11, 1, 9,
        15, 7, 13, 5
    };
    
    int index = (int(screenPos.x) % 4) * 4 + (int(screenPos.y) % 4);
    float threshold = (bayer[index] / 16.0 - 0.5) / 255.0;
    
    return color + threshold;
}
```

---

## 9. 完整Shader示例

```hlsl
// SDR Post-Processing Shader

struct PSInput
{
    float4 position : SV_POSITION;
    float2 uv : TEXCOORD0;
};

cbuffer PostProcessParams
{
    float Exposure;
    float BloomIntensity;
    float Saturation;
    float Contrast;
    float3 Lift;
    float3 Gamma;
    float3 Gain;
};

Texture2D SceneTexture;
Texture2D BloomTexture;
Texture3D ColorGradingLUT;

float4 PSMain(PSInput input) : SV_TARGET
{
    // 1. 采样场景颜色（HDR Linear）
    float3 color = SceneTexture.Sample(LinearSampler, input.uv).rgb;
    
    // 2. 应用曝光
    color *= Exposure;
    
    // 3. 添加Bloom
    float3 bloom = BloomTexture.Sample(LinearSampler, input.uv).rgb;
    color += bloom * BloomIntensity;
    
    // 4. 色调映射（HDR -> SDR）
    color = ACESFilm(color);
    
    // 5. 颜色分级（使用LUT）
    float3 lutCoord = color * 31.0 / 32.0 + 0.5 / 32.0;
    color = ColorGradingLUT.Sample(LinearSampler, lutCoord).rgb;
    
    // 6. 手动颜色调整
    color = pow(color * Gain + Lift, Gamma);
    color = (color - 0.5) * Contrast + 0.5;
    float luminance = dot(color, float3(0.2126, 0.7152, 0.0722));
    color = lerp(luminance, color, Saturation);
    
    // 7. 抖动
    color = Dither(color, input.position.xy);
    
    // 8. sRGB编码
    color = LinearToSRGB(saturate(color));
    
    return float4(color, 1.0);
}
```

---

## 10. 常见问题与调试

### 10.1 画面过暗

**可能原因**：
- 曝光值过低
- Tone Mapping曲线过于压缩
- sRGB编码/解码错误

**调试方法**：
- 检查中间渲染结果亮度
- 验证sRGB转换正确性
- 调整Tone Mapping参数

### 10.2 高光裁切

**现象**：亮部细节丢失，出现纯白色块

**解决方案**：
- 降低曝光值
- 调整Tone Mapping的shoulder参数
- 使用更柔和的Tone Mapping曲线

### 10.3 色带（Banding）

**现象**：渐变区域出现明显色阶

**解决方案**：
- 启用抖动（Dithering）
- 使用10-bit输出（如果支持）
- 增加LUT精度

---

## 参考

- [回到主文章](../HDR色彩管理深度解析.md)
- Real-Time Rendering, 4th Edition
- Physically Based Rendering, 3rd Edition
- UE4 Documentation: Post Process Effects

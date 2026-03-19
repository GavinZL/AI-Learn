# HDR显示标准详解

> 深入理解HDR10、Dolby Vision、HLG等主流HDR标准

---

## 1. HDR标准概览

### 1.1 主要HDR标准

| 标准 | 制定组织 | 传递函数 | 元数据 | 主要应用 |
|------|---------|---------|--------|---------|
| **HDR10** | CTA | PQ | 静态 | 流媒体、游戏、UHD蓝光 |
| **HDR10+** | Samsung | PQ | 动态 | 流媒体、部分UHD蓝光 |
| **Dolby Vision** | Dolby | PQ | 动态 | 影院、高端流媒体 |
| **HLG** | BBC/NHK | HLG | 无 | 广播电视、直播 |
| **Advanced HDR** | Technicolor | PQ/HLG | 动态 | 部分流媒体 |

### 1.2 标准选择决策

```
                    应用场景
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    影视制作       流媒体/游戏      广播电视
        │              │              │
        ▼              ▼              ▼
   Dolby Vision      HDR10+          HLG
   (最高质量)      (开放标准)      (兼容性)
        │              │              │
        └──────────────┴──────────────┘
                       │
                    HDR10
                 (基础兼容)
```

---

## 2. HDR10标准

### 2.1 技术规格

**核心参数**：

| 参数 | 规格 |
|------|------|
| **EOTF** | SMPTE ST 2084 (PQ) |
| **色域** | ITU-R BT.2020 |
| **位深** | 10-bit/通道（最小） |
| **峰值亮度** | 1000-10000 nit（内容） |
| **元数据** | 静态（Static Metadata） |

### 2.2 静态元数据

HDR10使用HDR10元数据结构：

```c
typedef struct {
    uint16_t display_primaries_x[3];  // RGB x坐标 (0.16 fixed point)
    uint16_t display_primaries_y[3];  // RGB y坐标 (0.16 fixed point)
    uint16_t white_point_x;           // 白点x
    uint16_t white_point_y;           // 白点y
    uint32_t max_display_mastering_luminance;  // 母版最大亮度 (nit)
    uint32_t min_display_mastering_luminance;  // 母版最小亮度 (nit)
    uint16_t max_content_light_level;          // MaxCLL (nit)
    uint16_t max_frame_average_light_level;    // MaxFALL (nit)
} HDR10Metadata;
```

**关键字段解释**：

| 字段 | 说明 | 典型值 |
|------|------|--------|
| **Display Primaries** | 母版显示器的色域 | Rec.2020或DCI-P3 |
| **White Point** | D65 (0.3127, 0.3290) | D65 |
| **Max Mastering Luminance** | 母版峰值亮度 | 1000-4000 nit |
| **Min Mastering Luminance** | 母版黑电平 | 0.0001-0.005 nit |
| **MaxCLL** | 内容最大亮度 | 1000-10000 nit |
| **MaxFALL** | 最大平均帧亮度 | 200-400 nit |

### 2.3 HDR10的局限

1. **静态元数据**：
   - 整个视频使用同一套元数据
   - 无法针对场景优化
   - 明暗场景切换时效果不佳

2. **色调映射依赖**：
   - 显示器的色调映射质量参差不齐
   - 同一内容在不同显示器上效果差异大

3. **亮度限制**：
   - 实际内容通常限制在1000-4000 nit
   - 10000 nit极少使用

---

## 3. HDR10+标准

### 3.1 改进点

HDR10+是HDR10的扩展，主要改进：

| 特性 | HDR10 | HDR10+ |
|------|-------|--------|
| 元数据 | 静态 | **动态** |
| 色调映射 | 显示器决定 | **内容创作者控制** |
| 兼容性 | 广泛 | 需支持HDR10+的设备 |

### 3.2 动态元数据

HDR10+使用SMPTE ST 2094-40标准：

**元数据内容（每场景/每帧）**：

```
- 场景平均亮度
- 场景最大亮度
- 色调映射曲线参数
- 色域映射参数
- 饱和度调整
```

**优势**：
- 创作者精确控制每场景的显示效果
- 避免显示器色调映射的差异
- 更好的暗/亮场景处理

### 3.3 实现方式

HDR10+元数据可以：
- 嵌入视频流（SEI消息）
- 单独文件（JSON格式）

---

## 4. Dolby Vision

### 4.1 技术特点

Dolby Vision是最全面的HDR解决方案：

| 特性 | 规格 |
|------|------|
| **位深** | 12-bit（内部处理） |
| **峰值亮度** | 10000 nit |
| **元数据** | 动态，每帧 |
| **色调映射** | Dolby专有算法 |
| **向后兼容** | 可生成SDR/HDR10版本 |

### 4.2 内容制作流程

```
原始拍摄素材
      │
      ▼
┌─────────────┐
│ Dolby Vision│  ← 专业调色
│   母版制作   │
└─────────────┘
      │
      ├──▶ Dolby Vision Profile 5 (流媒体)
      ├──▶ Dolby Vision Profile 7 (UHD蓝光)
      ├──▶ HDR10 (兼容版本)
      └──▶ SDR (兼容版本)
```

### 4.3 Profile版本

| Profile | 应用 | 特点 |
|---------|------|------|
| **Profile 4** | 影院 | 最高质量 |
| **Profile 5** | 流媒体 | 单流，10-bit |
| **Profile 7** | UHD蓝光 | 双层，增强层 |
| **Profile 8** | 游戏 | 低延迟 |

### 4.4 Dolby Vision vs HDR10+

| 对比项 | Dolby Vision | HDR10+ |
|--------|-------------|--------|
| 授权费用 | 有 | 无（开放标准） |
| 设备支持 | 较广 | 较少 |
| 内容库 | 丰富 | 较少 |
| 质量 | 略优 | 接近 |
| 向后兼容 | 优秀 | 良好 |

---

## 5. HLG（Hybrid Log-Gamma）

### 5.1 设计哲学

HLG的设计目标是**向后兼容性**：

- 同一信号可在SDR和HDR显示器上显示
- 无需元数据
- 适合直播场景

### 5.2 技术原理

HLG使用双曲线设计：

```
信号值
  1.0 │                    ╭──────
      │                 ╭──╯
 0.75 │              ╭──╯        ← HDR显示使用
      │           ╭──╯
 0.50 │──────────╯               ← SDR显示使用
      │      ╭──╯
      │   ╭──╯
  0.0 │╭──╯
      └────────────────────────▶ 场景亮度
      0    0.2   0.5   1   2   5
```

- **0-50%信号**：Gamma-like曲线，SDR显示器直接显示
- **50-100%信号**：Log曲线，HDR显示器恢复高亮

### 5.3 系统Gamma

HLG使用系统Gamma适应不同环境：

$$
\gamma_{system} = 1.2 + 0.42 \cdot \log_{10}(L_{W} / 1000)
$$

其中 $L_W$ 是显示白点亮度（nit）。

**典型值**：

| 环境 | 显示器亮度 | 系统Gamma |
|------|-----------|----------|
| 影院 | 48 nit | 1.2 |
| 家庭暗室 | 100 nit | 1.4 |
| 家庭客厅 | 300 nit | 1.6 |
| 明亮房间 | 1000 nit | 1.8 |

### 5.4 HLG的应用场景

| 场景 | 优势 |
|------|------|
| **广播电视** | 无需双路信号 |
| **体育赛事直播** | 实时处理，无延迟 |
| **安全监控** | SDR/HDR同时可用 |
| **移动设备** | 自适应显示 |

---

## 6. 游戏HDR实现

### 6.1 游戏HDR标准选择

| 平台 | 推荐标准 | 原因 |
|------|---------|------|
| **PC** | HDR10 | 最广泛支持 |
| **PS5** | HDR10 | 系统原生支持 |
| **Xbox Series X\|S** | Auto HDR / HDR10 | 系统优化 |
| **Nintendo Switch** | 不支持HDR | 硬件限制 |

### 6.2 游戏HDR元数据

游戏通常使用简化元数据：

```cpp
struct GameHDRMetadata {
    // 静态参数
    uint32_t maxContentLightLevel;      // 内容最大亮度
    uint32_t maxFrameAverageLightLevel; // 平均亮度
    
    // 动态调整（可选）
    float currentSceneMaxLuminance;     // 当前场景最大亮度
    float currentSceneAverageLuminance; // 当前场景平均亮度
};
```

### 6.3 平台特定API

#### DirectX 12

```cpp
// 设置HDR元数据
DXGI_HDR_METADATA_HDR10 hdr10Metadata = {};
hdr10Metadata.RedPrimary[0] = 34000;  // x * 50000
hdr10Metadata.RedPrimary[1] = 14600;  // y * 50000
// ... 其他原色
hdr10Metadata.WhitePoint[0] = 15635;  // 0.3127 * 50000
hdr10Metadata.WhitePoint[1] = 16450;  // 0.3290 * 50000
hdr10Metadata.MaxMasteringLuminance = 1000;
hdr10Metadata.MinMasteringLuminance = 0;
hdr10Metadata.MaxContentLightLevel = maxCLL;
hdr10Metadata.MaxFrameAverageLightLevel = maxFALL;

swapChain->SetHDRMetaData(
    DXGI_HDR_METADATA_TYPE_HDR10,
    sizeof(hdr10Metadata),
    &hdr10Metadata
);
```

#### Vulkan

```cpp
// 使用VK_EXT_hdr_metadata扩展
VkHdrMetadataEXT hdrMetadata = {};
hdrMetadata.sType = VK_STRUCTURE_TYPE_HDR_METADATA_EXT;
hdrMetadata.displayPrimaryRed = {0.708, 0.292};
hdrMetadata.displayPrimaryGreen = {0.170, 0.797};
hdrMetadata.displayPrimaryBlue = {0.131, 0.046};
hdrMetadata.whitePoint = {0.3127, 0.3290};
hdrMetadata.maxLuminance = 1000.0f;
hdrMetadata.minLuminance = 0.001f;
hdrMetadata.maxContentLightLevel = maxCLL;
hdrMetadata.maxFrameAverageLightLevel = maxFALL;

vkSetHdrMetadataEXT(device, swapchainCount, swapchains, &hdrMetadata);
```

---

## 7. HDR显示器校准

### 7.1 校准参数

| 参数 | 典型值 | 说明 |
|------|--------|------|
| **峰值亮度** | 600-2000 nit | 显示器最大亮度 |
| **黑电平** | 0.01-0.1 nit | 最小可显示亮度 |
| **色域覆盖** | 90%+ DCI-P3 | 色彩范围 |
| **EOTF精度** | < 2 dE | PQ曲线匹配度 |

### 7.2 用户校准

游戏应提供HDR校准界面：

```
┌─────────────────────────────────────┐
│         HDR 校准向导                 │
├─────────────────────────────────────┤
│                                      │
│  1. 调整直到Logo刚好可见            │
│                                      │
│     ┌─────────────────┐             │
│     │  ░░░░░░░░░░░░░  │  ← 拖动    │
│     │  ░░░░░░░░░░░░░  │             │
│     └─────────────────┘             │
│                                      │
│  2. 调整直到Logo不再过曝            │
│                                      │
│     ┌─────────────────┐             │
│     │  ▓▓▓▓▓▓▓▓▓▓▓▓▓  │  ← 拖动    │
│     │  ▓▓▓▓▓▓▓▓▓▓▓▓▓  │             │
│     └─────────────────┘             │
│                                      │
│  [完成]  [重置为默认值]              │
└─────────────────────────────────────┘
```

---

## 8. HDR内容制作规范

### 8.1 母版制作标准

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| **母版显示器** | 1000-4000 nit | 峰值亮度 |
| **母版色域** | Rec.2020 | 或DCI-P3 |
| **位深** | 12-bit | 最小10-bit |
| **白点** | D65 | (0.3127, 0.3290) |
| **Gamma** | PQ | ST 2084 |

### 8.2 内容分级

| 级别 | 峰值亮度 | 应用场景 |
|------|---------|---------|
| **Level 1** | 1000 nit | 基础HDR |
| **Level 2** | 2000 nit | 高质量HDR |
| **Level 3** | 4000 nit | 专业HDR |
| **Level 4** | 10000 nit | 未来标准 |

---

## 9. 常见问题

### Q: 为什么HDR10内容在SDR显示器上显示异常？

A: HDR10信号需要色调映射才能在SDR显示器上正确显示。如果直接显示：
- PQ编码的信号会被错误解释
- 画面整体偏暗或偏亮
- 颜色严重失真

解决方案：播放器或显示器需要进行色调映射。

### Q: 如何判断显示器是否真正支持HDR？

A: 真正的HDR显示器应具备：
- 峰值亮度 ≥ 600 nit
- 支持10-bit色深
- 广色域（90%+ DCI-P3）
- 局部调光（Local Dimming）

仅支持HDR信号解码但不满足上述硬件要求的显示器为"伪HDR"。

### Q: HDR会增加多少带宽？

A: 相比SDR：
- HDR10（10-bit）：约25%增加
- Dolby Vision（12-bit）：约50%增加
- HLG（10-bit）：与SDR相近（向后兼容）

---

## 参考

- [回到主文章](../HDR色彩管理深度解析.md)
- CTA-861-G: A DTV Profile for Uncompressed High Speed Digital Interfaces
- SMPTE ST 2084: High Dynamic Range Electro-Optical Transfer Function
- SMPTE ST 2094: Dynamic Metadata for Color Volume Transforms
- ITU-R BT.2100: Image parameter values for high dynamic range television
- Dolby Vision White Paper

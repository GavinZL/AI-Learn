# DASH 与 MPEG-DASH 详细解析

> 国际标准的自适应流媒体协议——供应商中立、编解码器无关的大规模分发方案

---

## 核心结论（TL;DR）

**DASH（Dynamic Adaptive Streaming over HTTP），也称 MPEG-DASH（ISO/IEC 23009-1），是国际标准化组织制定的基于 HTTP 的自适应流媒体协议。** 与 Apple 私有的 HLS 不同，DASH 是供应商中立的开放标准，支持任意编解码器和 DRM 系统。它使用 XML 格式的 MPD（Media Presentation Description）文件描述媒体信息，采用 fMP4 作为默认分片格式。

**与 HLS 的核心区别**：HLS 是 Apple 的"事实标准"，DASH 是 ISO 的"法定标准"。技术上两者非常相似（都是 HTTP 分片 + 自适应码率），主要差异在于描述文件格式（M3U8 vs MPD）、DRM 生态（FairPlay vs Widevine/PlayReady）和标准化程度。

**类比**：如果 HLS 是"Apple Store 里的官方快递服务"，DASH 就是"联合国制定的国际邮政标准"——更通用、更灵活，但在 Apple 设备上不如 HLS 原生支持好。

---

## 目录

1. [设计背景与标准化历程](#1-设计背景与标准化历程)
2. [DASH 架构与核心概念](#2-dash-架构与核心概念)
3. [MPD 文件格式详解](#3-mpd-文件格式详解)
4. [Segment 结构与寻址](#4-segment-结构与寻址)
5. [自适应码率算法](#5-自适应码率算法)
6. [DRM 与 CENC](#6-drm-与-cenc)
7. [Low-Latency DASH (LL-DASH)](#7-low-latency-dash-ll-dash)
8. [CMAF：统一 HLS 与 DASH](#8-cmaf统一-hls-与-dash)
9. [适用场景与优缺点](#9-适用场景与优缺点)
10. [性能指标](#10-性能指标)
11. [与 HLS 详细对比](#11-与-hls-详细对比)
12. [FFmpeg 实践示例](#12-ffmpeg-实践示例)

---

## 1. 设计背景与标准化历程

### 1.1 为什么需要 DASH

2010 年前后，各厂商各自为政：
- Apple → HLS
- Microsoft → Smooth Streaming
- Adobe → HDS (HTTP Dynamic Streaming)

每种方案都需要单独的编码、存储和分发流程，内容提供商负担极重。业界需要一个统一的标准。

### 1.2 标准化时间线

```
2009 ── 3GPP 启动 DASH 标准化工作
2011 ── MPEG-DASH 第一版完成（ISO/IEC 23009-1:2012）
2014 ── 第二版，支持更多特性
2017 ── 第三版，增加低延迟支持
2019 ── 第四版，CMAF 整合
2022 ── 第五版，增强低延迟和 IPTV 支持
```

### 1.3 DASH 的设计原则

| 原则 | 说明 |
|------|------|
| **编解码器无关** | 支持 H.264、H.265、VP9、AV1 等任意编解码器 |
| **DRM 无关** | 支持 Widevine、PlayReady、FairPlay 等任意 DRM |
| **供应商中立** | ISO 国际标准，无单一厂商控制 |
| **HTTP 兼容** | 使用标准 HTTP，兼容所有 CDN |
| **可扩展** | 通过 Profile 和 Extension 支持不同场景 |

---

## 2. DASH 架构与核心概念

### 2.1 内容模型层次

DASH 使用严格的层次化内容模型：

```
Media Presentation (MPD)
  └── Period（时间段，如：广告段、正片段）
        └── Adaptation Set（自适应集，如：视频、音频、字幕）
              └── Representation（表示，如：1080p、720p、480p）
                    └── Segment（分片，实际的媒体文件）
```

**类比理解**：
- **Period** = 电视节目的不同段落（节目 → 广告 → 节目）
- **Adaptation Set** = 不同类型的轨道（视频轨、音频轨、字幕轨）
- **Representation** = 同一轨道的不同质量版本（高清、标清）
- **Segment** = 每个版本切割的小片段（每段几秒）

### 2.2 工作流程

```
1. 客户端请求 MPD 文件
   GET /content/manifest.mpd

2. 解析 MPD，获取可用的 Adaptation Set 和 Representation
   视频：1080p(5Mbps), 720p(2.5Mbps), 480p(1Mbps)
   音频：AAC(128kbps), AAC(64kbps)

3. 根据初始带宽估计，选择合适的 Representation

4. 下载初始化段（Initialization Segment）
   GET /content/video/1080p/init.mp4

5. 按序下载媒体段（Media Segment）
   GET /content/video/1080p/seg_001.m4s
   GET /content/video/1080p/seg_002.m4s

6. 持续监控带宽，动态切换 Representation
   带宽下降 → 切换到 720p
   GET /content/video/720p/seg_005.m4s
```

---

## 3. MPD 文件格式详解

### 3.1 MPD 结构（XML）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"
     type="dynamic"
     minimumUpdatePeriod="PT2S"
     availabilityStartTime="2026-03-19T10:00:00Z"
     minBufferTime="PT2S"
     profiles="urn:mpeg:dash:profile:isoff-live:2011">

  <Period id="1" start="PT0S">
    <!-- 视频 Adaptation Set -->
    <AdaptationSet mimeType="video/mp4" segmentAlignment="true"
                   startWithSAP="1">
      <!-- 1080p -->
      <Representation id="v1" width="1920" height="1080"
                      bandwidth="5000000" codecs="avc1.640028">
        <SegmentTemplate
          initialization="video/1080p/init.mp4"
          media="video/1080p/seg_$Number$.m4s"
          startNumber="1" duration="6000" timescale="1000"/>
      </Representation>

      <!-- 720p -->
      <Representation id="v2" width="1280" height="720"
                      bandwidth="2500000" codecs="avc1.64001f">
        <SegmentTemplate
          initialization="video/720p/init.mp4"
          media="video/720p/seg_$Number$.m4s"
          startNumber="1" duration="6000" timescale="1000"/>
      </Representation>

      <!-- 480p -->
      <Representation id="v3" width="854" height="480"
                      bandwidth="1000000" codecs="avc1.64001e">
        <SegmentTemplate
          initialization="video/480p/init.mp4"
          media="video/480p/seg_$Number$.m4s"
          startNumber="1" duration="6000" timescale="1000"/>
      </Representation>
    </AdaptationSet>

    <!-- 音频 Adaptation Set -->
    <AdaptationSet mimeType="audio/mp4" lang="zh">
      <Representation id="a1" bandwidth="128000"
                      codecs="mp4a.40.2" audioSamplingRate="48000">
        <SegmentTemplate
          initialization="audio/init.mp4"
          media="audio/seg_$Number$.m4s"
          startNumber="1" duration="6000" timescale="1000"/>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
```

### 3.2 MPD 关键属性

| 属性 | 说明 |
|------|------|
| `type` | `static`（点播）或 `dynamic`（直播） |
| `minimumUpdatePeriod` | 客户端刷新 MPD 的最小间隔 |
| `availabilityStartTime` | 直播开始时间 |
| `minBufferTime` | 客户端最小缓冲时长 |
| `profiles` | DASH Profile 标识 |
| `bandwidth` | Representation 的峰值码率（bps） |
| `codecs` | RFC 6381 格式的编解码器字符串 |

### 3.3 Segment 寻址方式

DASH 支持三种分片寻址方式：

**SegmentTemplate + Number**：
```xml
<SegmentTemplate media="seg_$Number$.m4s" startNumber="1" duration="6000" timescale="1000"/>
<!-- 生成：seg_1.m4s, seg_2.m4s, seg_3.m4s, ... -->
```

**SegmentTemplate + Timeline**：
```xml
<SegmentTemplate media="seg_$Time$.m4s">
  <SegmentTimeline>
    <S t="0" d="6006" r="99"/>  <!-- 100 个 6.006s 的分片 -->
  </SegmentTimeline>
</SegmentTemplate>
```

**SegmentList**：
```xml
<SegmentList duration="6">
  <Initialization sourceURL="init.mp4"/>
  <SegmentURL media="seg_001.m4s"/>
  <SegmentURL media="seg_002.m4s"/>
</SegmentList>
```

---

## 4. Segment 结构与寻址

### 4.1 Initialization Segment

初始化段包含解码器配置信息：

```
init.mp4:
  [ftyp] - 文件类型声明
  [moov] - 元数据容器
    [mvhd] - 影片头
    [trak] - 轨道信息
      [tkhd] - 轨道头
      [mdia] - 媒体信息
        [mdhd] - 媒体头（时间刻度）
        [hdlr] - 处理器类型（video/audio）
        [minf] - 媒体信息
          [stbl] - Sample 表（空，数据在 Media Segment 中）
    [mvex] - 扩展头（表示这是 fragmented MP4）
      [trex] - 默认 Sample 属性
```

### 4.2 Media Segment

媒体段包含实际的音视频数据：

```
seg_001.m4s:
  [styp] - 段类型
  [moof] - Movie Fragment
    [mfhd] - Fragment 头（序列号）
    [traf] - Track Fragment
      [tfhd] - Track Fragment 头
      [tfdt] - Track Fragment 解码时间
      [trun] - Track Run（每个 Sample 的大小、时长、偏移）
  [mdat] - 实际媒体数据
```

---

## 5. 自适应码率算法

### 5.1 BOLA（Buffer Occupancy based Lyapunov Algorithm）

BOLA 是 DASH 领域最知名的 ABR 算法之一：

```
核心思想：
  - 将 ABR 问题建模为在线优化问题
  - 使用 Lyapunov 优化理论推导出闭式解
  - 仅基于缓冲区水位做决策，不直接测量带宽

决策函数：
  quality = argmax { V × utility(q) + buffer_level × weight(q) }
  
  V：控制质量和缓冲之间权衡的参数
  utility(q)：码率 q 对应的质量效用（通常用 log(bitrate)）
  
优点：
  - 理论保证：有严格的数学证明
  - 稳定性好：不会频繁切换
  
缺点：
  - 启动阶段表现差（缓冲为空时无法做好决策）
  - 无法利用带宽测量信息
```

### 5.2 MPC（Model Predictive Control）

```
核心思想：
  - 预测未来 K 步的网络带宽（基于历史）
  - 选择使未来 K 步总效用最大化的码率序列
  - 效用函数：质量 + 平滑性 - 重缓冲惩罚

优点：综合性最好
缺点：计算复杂度较高
```

---

## 6. DRM 与 CENC

### 6.1 CENC（Common Encryption）

CENC（ISO/IEC 23001-7）定义了统一的加密格式，使同一套加密内容可以被不同的 DRM 系统解密：

```
加密方案：
  AES-128-CTR（计数器模式）
  AES-128-CBC（密码块链接模式）

内容加密一次 → 多个 DRM 系统可解密
```

### 6.2 Multi-DRM 架构

```
                    ┌─── Widevine License Server ─── Android/Chrome
编码 → CENC 加密 ───┤
                    ├─── PlayReady License Server ── Windows/Edge
                    │
                    └─── FairPlay License Server ─── iOS/Safari
                    
同一份加密内容，三套 DRM 密钥服务器
```

### 6.3 MPD 中的 DRM 声明

```xml
<AdaptationSet>
  <!-- Widevine -->
  <ContentProtection
    schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
    value="Widevine">
    <cenc:pssh>base64_encoded_pssh_data</cenc:pssh>
  </ContentProtection>
  
  <!-- PlayReady -->
  <ContentProtection
    schemeIdUri="urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95"
    value="PlayReady">
    <mspr:pro>base64_encoded_pro_data</mspr:pro>
  </ContentProtection>
</AdaptationSet>
```

---

## 7. Low-Latency DASH (LL-DASH)

### 7.1 核心机制

LL-DASH 使用 CMAF Chunk 实现低延迟：

```
传统 DASH：一个 Segment = 一个完整的 moof+mdat
LL-DASH：一个 Segment 由多个 CMAF Chunk 组成

Segment (2s):
  [Chunk 1 (200ms)][Chunk 2 (200ms)]...[Chunk 10 (200ms)]
  
每个 Chunk 独立可解码，编码器可以逐个 Chunk 推送
```

### 7.2 HTTP Chunked Transfer

LL-DASH 利用 HTTP Chunked Transfer Encoding：

```
服务器在生成第一个 Chunk 后立即开始 HTTP 响应
客户端边接收边解码，无需等待整个 Segment 完成

GET /seg_001.m4s → 200 OK, Transfer-Encoding: chunked
  [Chunk 1 data]  ← 立即可解码
  [Chunk 2 data]  ← 200ms 后到达
  ...
```

### 7.3 延迟对比

| 模式 | 分片时长 | 端到端延迟 |
|------|---------|-----------|
| 传统 DASH | 6s | 15-30s |
| 传统 DASH | 2s | 6-10s |
| LL-DASH (CMAF Chunk) | 200ms Chunk | 2-4s |

---

## 8. CMAF：统一 HLS 与 DASH

### 8.1 CMAF 的价值

CMAF（Common Media Application Format，ISO/IEC 23000-19）：

```
传统方式（需要两套内容）：
  编码 → TS 分片 → HLS M3U8 → Apple 设备
  编码 → fMP4 分片 → DASH MPD → 其他设备
  存储成本 × 2，CDN 缓存效率低

CMAF 方式（一套内容）：
  编码 → CMAF fMP4 分片 ──→ HLS M3U8 → Apple 设备
                          └──→ DASH MPD → 其他设备
  只需要不同的 Manifest 文件，媒体分片共享
```

### 8.2 CMAF 技术要求

- 分片格式：Fragmented ISO BMFF（fMP4）
- 编解码器：需要 HLS 和 DASH 都支持（如 H.264+AAC）
- 加密：CENC cbcs 模式（HLS 和 DASH 均支持）
- 分片对齐：关键帧对齐

---

## 9. 适用场景与优缺点

### 9.1 优点

| 优点 | 说明 |
|------|------|
| **国际标准** | ISO 标准，无厂商锁定 |
| **编解码器自由** | 支持任意编解码器 |
| **Multi-DRM** | 原生支持 CENC 多 DRM |
| **CDN 兼容** | 基于 HTTP |
| **灵活的内容模型** | Period/AdaptationSet 精细控制 |

### 9.2 缺点

| 缺点 | 说明 |
|------|------|
| **iOS 不原生支持** | Safari 只支持 HLS，需第三方播放器 |
| **MPD 复杂** | XML 格式比 M3U8 更复杂 |
| **实现碎片化** | 不同播放器实现差异较大 |
| **生态不如 HLS** | 在移动端普及度略低 |

---

## 10. 性能指标

| 指标 | 传统 DASH | LL-DASH |
|------|----------|---------|
| 端到端延迟 | 6-30s | 2-4s |
| 首帧时间 | 2-5s | 1-2s |
| 码率切换粒度 | 分片级别 | Chunk 级别 |
| CDN 缓存效率 | 极高 | 高 |

---

## 11. 与 HLS 详细对比

| 维度 | DASH | HLS |
|------|------|-----|
| **标准** | ISO/IEC 23009 | Apple 私有 / IETF 草案 |
| **描述格式** | MPD (XML) | M3U8 (文本) |
| **默认分片** | fMP4 | TS (传统) / fMP4 (新) |
| **编解码器** | 任意 | 传统限 H.264/AAC（扩展支持更多） |
| **DRM** | CENC (Widevine/PlayReady) | FairPlay |
| **iOS 原生** | ❌ | ✅ |
| **Android 原生** | ✅ (ExoPlayer) | ✅ (ExoPlayer) |
| **Web 支持** | dash.js, Shaka Player | hls.js, 原生 Safari |
| **低延迟** | LL-DASH (CMAF Chunk) | LL-HLS (Partial Segment) |
| **复杂度** | 较高 | 中等 |
| **实际采用** | YouTube, Netflix(部分) | Apple, 大多数直播平台 |

**实际选型建议**：
- 面向全平台 → CMAF + 双 Manifest（HLS + DASH）
- 面向 Apple 生态 → HLS
- 面向 Android/Web → DASH
- 需要 Multi-DRM → DASH + CENC

---

## 12. FFmpeg 实践示例

### 12.1 生成 DASH 流

```bash
# 基础 DASH 切片
ffmpeg -re -i input.mp4 \
  -c:v libx264 -b:v 4000k -preset veryfast \
  -c:a aac -b:a 128k \
  -f dash \
  -seg_duration 6 \
  -use_template 1 \
  -use_timeline 1 \
  -init_seg_name "init_\$RepresentationID\$.mp4" \
  -media_seg_name "seg_\$RepresentationID\$_\$Number\$.m4s" \
  output/manifest.mpd

# 多码率 DASH
ffmpeg -re -i input.mp4 \
  -map 0:v -b:v:0 5000k -s:v:0 1920x1080 \
  -map 0:v -b:v:1 2500k -s:v:1 1280x720 \
  -map 0:v -b:v:2 1000k -s:v:2 854x480 \
  -map 0:a -c:a aac -b:a 128k \
  -c:v libx264 -preset veryfast \
  -f dash \
  -seg_duration 4 \
  -adaptation_sets "id=0,streams=v id=1,streams=a" \
  output/manifest.mpd
```

### 12.2 DASH 播放测试

```bash
# 使用 ffplay 播放（需要支持 DASH 的构建）
ffplay output/manifest.mpd

# 使用 mpv（原生支持 DASH）
mpv output/manifest.mpd

# 使用 Web 播放器（推荐）
# dash.js: https://reference.dashif.org/dash.js/
# Shaka Player: https://shaka-player-demo.appspot.com/
```

### 12.3 CMAF 输出（同时兼容 HLS 和 DASH）

```bash
# 使用 Shaka Packager 生成 CMAF
# packager 同时生成 HLS 和 DASH manifest
packager \
  in=video_1080p.mp4,stream=video,output=video_1080p.mp4 \
  in=video_720p.mp4,stream=video,output=video_720p.mp4 \
  in=audio.mp4,stream=audio,output=audio.mp4 \
  --mpd_output manifest.mpd \
  --hls_master_playlist_output master.m3u8 \
  --segment_duration 6
```

---

## 与其他文档的关联

- **对比协议**：← [HLS_详细解析](./HLS_详细解析.md)
- **封装格式**：→ [封装与解封装原理](../../Video_Codec_Principles/05_封装与解封装/封装与解封装原理_详细解析.md)
- **协议选型**：→ [协议性能对比_详细解析](../05_协议对比与选型/协议性能对比_详细解析.md)
- **总览导航**：→ [AudioVideo_Transmission_Protocols 深度解析](../AudioVideo_Transmission_Protocols_深度解析.md)

---

> DASH 的价值不仅在于技术本身，更在于它代表的"开放标准对抗厂商锁定"的理念。在 CMAF 的推动下，HLS 和 DASH 正在走向融合——未来可能只需要一套媒体文件，两种 Manifest。

# HLS 详细解析

> Apple 定义的 HTTP 分片流协议——用 Web 基础设施承载大规模音视频分发

---

## 核心结论（TL;DR）

**HLS（HTTP Live Streaming）是 Apple 于 2009 年推出的基于 HTTP 的自适应码率流媒体协议。它将音视频切割为短小的 TS 或 fMP4 分片文件，通过 M3U8 播放列表描述分片信息，利用标准的 HTTP/CDN 基础设施实现大规模分发。** HLS 是目前全球覆盖最广的流媒体分发协议，几乎所有设备和浏览器都原生支持。

**类比**：如果 RTMP 是"一条专用的水管"持续输送水流，HLS 就是"把水装进一个个瓶子，放在超市货架上让顾客自取"——HTTP 服务器就是超市，CDN 就是连锁超市网络，M3U8 播放列表就是货架上的目录牌。

---

## 目录

1. [设计背景与第一性原理](#1-设计背景与第一性原理)
2. [HLS 架构与工作流程](#2-hls-架构与工作流程)
3. [M3U8 播放列表格式](#3-m3u8-播放列表格式)
4. [分片格式：TS vs fMP4](#4-分片格式ts-vs-fmp4)
5. [自适应码率（ABR）机制](#5-自适应码率abr机制)
6. [加密与 DRM](#6-加密与-drm)
7. [Low-Latency HLS (LL-HLS)](#7-low-latency-hls-ll-hls)
8. [适用场景与优缺点](#8-适用场景与优缺点)
9. [性能指标与延迟分析](#9-性能指标与延迟分析)
10. [与其他协议对比](#10-与其他协议对比)
11. [FFmpeg 实践示例](#11-ffmpeg-实践示例)

---

## 1. 设计背景与第一性原理

### 1.1 核心问题

2009 年，iPhone 不支持 Flash，但用户需要在手机上观看视频流。Apple 需要一种：
- 不依赖任何插件的流媒体方案
- 能利用现有的 HTTP/CDN 基础设施
- 能自适应不同的网络条件
- 能支持内容加密（DRM）

### 1.2 设计决策的推导

**推导过程**：
1. 不用插件 → 必须基于浏览器原生能力 → HTTP 是唯一选择
2. HTTP 是请求-响应模式 → 无法做到持续推送 → 必须将流切割为分片
3. 分片 → 需要一个索引来描述分片列表 → M3U8 播放列表
4. 网络变化 → 需要多种码率 → 多个分片流 + Master Playlist
5. CDN 缓存友好 → 分片是静态文件，天然可缓存 → 极致扩展性

**核心取舍**：用延迟换扩展性。每个分片通常 2-10 秒，加上下载和缓冲时间，总延迟在 6-30 秒——这对直播来说很高，但对 CDN 分发来说，这是最优解。

---

## 2. HLS 架构与工作流程

### 2.1 整体架构

```
┌────────┐    ┌───────────┐    ┌─────────┐    ┌────────┐
│ 编码器  │──→│ 分片器     │──→│ 源站     │──→│  CDN   │──→ 播放器
│(H.264/ │    │(Segmenter)│    │(Origin) │    │(Edge)  │
│ H.265) │    │           │    │         │    │        │
└────────┘    └───────────┘    └─────────┘    └────────┘
                   │
              生成 .ts/.m4s 分片
              生成 .m3u8 播放列表
```

### 2.2 工作流程

```
1. 编码器持续编码音视频流

2. 分片器将编码流切割为等时长的分片：
   segment_001.ts (6s)
   segment_002.ts (6s)
   segment_003.ts (6s)
   ...

3. 同时更新 M3U8 播放列表：
   #EXTM3U
   #EXT-X-TARGETDURATION:6
   #EXTINF:6.0,
   segment_001.ts
   #EXTINF:6.0,
   segment_002.ts
   #EXTINF:6.0,
   segment_003.ts

4. 播放器：
   a. 下载 Master Playlist → 获取可用码率列表
   b. 选择一个码率 → 下载对应的 Media Playlist
   c. 下载最新的分片 → 解码播放
   d. 周期性重新下载 Playlist → 获取新分片信息
   e. 根据网络状况 → 切换到不同码率
```

---

## 3. M3U8 播放列表格式

### 3.1 Master Playlist（多码率索引）

```m3u8
#EXTM3U
#EXT-X-VERSION:6

#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=30
1080p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720,CODECS="avc1.64001f,mp4a.40.2",FRAME-RATE=30
720p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=854x480,CODECS="avc1.64001e,mp4a.40.2",FRAME-RATE=30
480p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,CODECS="avc1.640015,mp4a.40.2",FRAME-RATE=30
360p/playlist.m3u8

# 纯音频备选
#EXT-X-STREAM-INF:BANDWIDTH=128000,CODECS="mp4a.40.2"
audio_only/playlist.m3u8
```

### 3.2 Media Playlist（分片索引）

**直播模式**（滑动窗口）：
```m3u8
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:1001

#EXTINF:6.006,
segment_1001.ts
#EXTINF:5.994,
segment_1002.ts
#EXTINF:6.006,
segment_1003.ts
```

**点播模式**（完整列表）：
```m3u8
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-PLAYLIST-TYPE:VOD

#EXTINF:6.006,
segment_001.ts
#EXTINF:6.006,
segment_002.ts
...
#EXTINF:4.238,
segment_150.ts

#EXT-X-ENDLIST
```

### 3.3 关键标签说明

| 标签 | 说明 |
|------|------|
| `#EXT-X-VERSION` | HLS 版本号 |
| `#EXT-X-TARGETDURATION` | 分片的最大时长（秒） |
| `#EXT-X-MEDIA-SEQUENCE` | 第一个分片的序列号 |
| `#EXTINF` | 分片的实际时长 |
| `#EXT-X-STREAM-INF` | 多码率流的描述 |
| `#EXT-X-KEY` | 加密信息 |
| `#EXT-X-MAP` | 初始化段（fMP4 用） |
| `#EXT-X-ENDLIST` | 标记点播列表结束 |
| `#EXT-X-DISCONTINUITY` | 标记编码参数变化点 |

---

## 4. 分片格式：TS vs fMP4

### 4.1 MPEG-TS 分片

传统 HLS 使用 MPEG Transport Stream 格式：

```
TS 文件结构：
  [TS Packet 188B][TS Packet 188B][TS Packet 188B]...
  
  每个 TS Packet：
    Sync Byte (0x47) | PID | Payload
    
  携带：
    PAT (Program Association Table) → PID 映射
    PMT (Program Map Table) → 流类型描述
    PES (Packetized Elementary Stream) → 音视频数据
```

**特点**：
- 每个 TS 分片独立可解码（包含 PAT/PMT/I帧）
- 188 字节固定包大小
- 开销较大（PAT/PMT/Adaptation Field 等头部）

### 4.2 fMP4 分片

从 HLS v7 开始支持 Fragmented MP4：

```
fMP4 结构：
  初始化段（init.mp4）：
    [ftyp][moov] → 编解码器参数、轨道信息
    
  媒体段（segment_001.m4s）：
    [moof][mdat] → 帧数据和时间信息
```

**fMP4 vs TS 对比**：

| 维度 | TS | fMP4 |
|------|-----|------|
| **头部开销** | 较大（每包 4B + PAT/PMT） | 较小 |
| **兼容性** | 极好（所有 HLS 播放器） | 需要 HLS v7+ |
| **与 DASH 兼容** | ❌ | ✅（CMAF） |
| **DRM 支持** | 有限 | 完善（CENC） |
| **分片粒度** | 以 TS 包为单位 | 以 Sample 为单位 |

### 4.3 CMAF（Common Media Application Format）

CMAF 统一了 HLS 和 DASH 的分片格式：

```
同一套 fMP4 分片 ──→ HLS M3U8 播放列表 ──→ Apple 设备
                └──→ DASH MPD 描述文件 ──→ Android/PC
                
减少了内容提供商需要编码和存储的份数
```

---

## 5. 自适应码率（ABR）机制

### 5.1 ABR 工作原理

```
播放器持续监控：
  - 下载速度（throughput）
  - 缓冲区水位（buffer level）
  - 历史切换记录

决策逻辑：
  if 下载速度 > 当前码率 × 1.5 且 缓冲充足
    → 尝试切换到更高码率
  elif 下载速度 < 当前码率 × 0.8 或 缓冲不足
    → 切换到更低码率
  else
    → 保持当前码率
```

### 5.2 ABR 算法分类

| 算法 | 策略 | 代表 | 优缺点 |
|------|------|------|--------|
| **基于带宽** | 估算网络吞吐量 | 简单吞吐量估计 | 简单但反应滞后 |
| **基于缓冲** | 根据缓冲区水位决策 | BBA, BOLA | 稳定但启动慢 |
| **混合** | 综合带宽和缓冲 | MPC | 效果好但复杂 |
| **基于学习** | 强化学习 | Pensieve, Comyco | 最优但需训练 |

### 5.3 码率切换策略

**关键帧对齐**：码率切换只能发生在 I 帧边界（即分片边界），否则会出现解码错误。

```
播放时间线：
  低码率：[====seg1====][====seg2====][====seg3====]
                                       ↑ 切换点
  高码率：                             [====seg4====][====seg5====]
  
切换在分片边界发生，对用户来说是无缝的
```

---

## 6. 加密与 DRM

### 6.1 AES-128 加密

HLS 原生支持 AES-128-CBC 加密：

```m3u8
#EXT-X-KEY:METHOD=AES-128,URI="https://key-server.com/key/123",IV=0x000102030405060708090a0b0c0d0e0f
#EXTINF:6.0,
segment_001.ts
```

- 播放器先请求密钥 URI 获取 16 字节 AES 密钥
- 用密钥 + IV 解密 TS 分片
- 支持密钥轮转（不同分片使用不同密钥）

### 6.2 Sample-AES

只加密媒体 Sample（帧数据），不加密容器头部：

```
优点：CDN 可以看到容器结构（帮助缓存优化）
      解密开销更小
缺点：安全性略低于全分片加密
```

### 6.3 FairPlay DRM

Apple 的 DRM 系统，配合 fMP4 分片使用 CENC（Common Encryption）标准。

---

## 7. Low-Latency HLS (LL-HLS)

### 7.1 传统 HLS 延迟分析

```
传统 HLS 延迟 = 编码延迟 + 分片时长 × 3 + 下载延迟

典型值（6s 分片）：
  编码：50ms
  等待分片生成：0-6s（平均 3s）
  Playlist 刷新等待：0-6s（平均 3s）
  安全缓冲（3个分片）：18s
  下载：~1s
  ──────────────────
  总计：约 15-30s
```

### 7.2 LL-HLS 的优化策略

Apple 在 2020 年推出 LL-HLS（RFC 8216bis），目标延迟 2-4 秒：

**策略一：部分分片（Partial Segments）**

```
传统：一个完整分片 6s，必须等 6s 才能下载
LL-HLS：分片被拆分为 200ms-2s 的 Part

#EXT-X-PART:DURATION=0.33334,URI="part001.0.m4s"
#EXT-X-PART:DURATION=0.33334,URI="part001.1.m4s"
...
#EXTINF:2.0,
segment_001.m4s
```

**策略二：Playlist Delta Update**

```
不用每次下载完整 Playlist，只获取增量更新：
GET /playlist.m3u8?_HLS_msn=1001&_HLS_part=3&_HLS_skip=YES
```

**策略三：阻塞式 Playlist 请求**

```
播放器请求尚未存在的分片序号：
GET /playlist.m3u8?_HLS_msn=1002

服务器阻塞请求，直到该分片就绪后立即响应
→ 避免了轮询延迟
```

**策略四：预加载提示（Preload Hints）**

```m3u8
#EXT-X-PRELOAD-HINT:TYPE=PART,URI="part002.0.m4s"
播放器可以提前建立连接，分片一就绪就开始下载
```

### 7.3 LL-HLS 延迟分析

```
LL-HLS 延迟：
  Part 时长：0.33s
  缓冲 Parts 数：3-6 个
  ──────────────────
  理论最低：约 1-2s
  实际典型：约 2-4s
```

---

## 8. 适用场景与优缺点

### 8.1 优点

| 优点 | 说明 |
|------|------|
| **CDN 完美兼容** | 基于 HTTP，所有 CDN 原生支持 |
| **极致扩展性** | 百万级并发无压力 |
| **设备兼容性** | iOS/Android/Web/SmartTV 全覆盖 |
| **自适应码率** | 多码率流 + ABR 算法 |
| **加密/DRM** | 完善的内容保护方案 |

### 8.2 缺点

| 缺点 | 说明 |
|------|------|
| **高延迟** | 传统 HLS 6-30s（LL-HLS 2-4s） |
| **不支持双向** | 纯拉流协议 |
| **Apple 主导** | 标准由 Apple 控制 |
| **分片开销** | 大量小文件对存储和 CDN 有压力 |

---

## 9. 性能指标与延迟分析

| 指标 | 传统 HLS | LL-HLS |
|------|---------|--------|
| 端到端延迟 | 10-30s | 2-4s |
| 首帧时间 | 2-5s | 1-2s |
| 码率切换时间 | 一个分片时长 | 一个 Part 时长 |
| CDN 缓存效率 | 极高 | 高 |

---

## 10. 与其他协议对比

| 维度 | HLS | DASH | RTMP | WebRTC |
|------|-----|------|------|--------|
| **标准** | Apple 私有(RFC草案) | ISO 国际标准 | Adobe 私有 | IETF RFC |
| **延迟** | 6-30s / 2-4s(LL) | 3-30s / 2-4s(LL) | 1-3s | < 0.5s |
| **CDN 支持** | 极好 | 极好 | 好 | 有限 |
| **DRM** | FairPlay | Widevine/PlayReady | 有限 | 无 |
| **iOS 原生** | ✅ | 需第三方 | ❌ | ✅ |
| **Android 原生** | ✅(ExoPlayer) | ✅(ExoPlayer) | ❌ | ✅ |

---

## 11. FFmpeg 实践示例

### 11.1 生成 HLS 流

```bash
# 基础 HLS 切片
ffmpeg -re -i input.mp4 \
  -c:v libx264 -preset veryfast -b:v 4000k \
  -c:a aac -b:a 128k \
  -f hls \
  -hls_time 6 \
  -hls_list_size 10 \
  -hls_flags delete_segments \
  output/stream.m3u8

# 多码率 HLS（生成 Master Playlist）
ffmpeg -re -i input.mp4 \
  -filter_complex "[0:v]split=3[v1][v2][v3]; \
    [v1]scale=1920:1080[v1out]; \
    [v2]scale=1280:720[v2out]; \
    [v3]scale=854:480[v3out]" \
  -map "[v1out]" -c:v:0 libx264 -b:v:0 5000k \
  -map "[v2out]" -c:v:1 libx264 -b:v:1 2500k \
  -map "[v3out]" -c:v:2 libx264 -b:v:2 1000k \
  -map a -c:a aac -b:a 128k \
  -f hls \
  -hls_time 6 \
  -master_pl_name master.m3u8 \
  -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2" \
  output/stream_%v.m3u8
```

### 11.2 HLS 加密

```bash
# AES-128 加密 HLS
ffmpeg -re -i input.mp4 \
  -c:v libx264 -c:a aac \
  -f hls \
  -hls_time 6 \
  -hls_key_info_file enc.keyinfo \
  output/encrypted.m3u8

# enc.keyinfo 文件内容：
# https://key-server.com/key/123
# /path/to/encryption.key
# 0123456789abcdef0123456789abcdef
```

### 11.3 LL-HLS 配置

```bash
# 低延迟 HLS
ffmpeg -re -i input.mp4 \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -c:a aac \
  -f hls \
  -hls_time 2 \
  -hls_flags low_latency \
  -hls_fmp4_init_filename init.mp4 \
  -hls_segment_type fmp4 \
  output/llhls.m3u8
```

---

## 与其他文档的关联

- **协议基础**：← [网络传输基础_详细解析](../01_传输基础与协议栈/网络传输基础_详细解析.md)
- **对比协议**：→ [DASH与MPEG_DASH_详细解析](./DASH与MPEG_DASH_详细解析.md)
- **推流源**：← [RTMP_详细解析](../02_实时推流协议/RTMP_详细解析.md)
- **封装格式**：→ [封装与解封装原理](../../Video_Codec_Principles/05_封装与解封装/封装与解封装原理_详细解析.md)
- **总览导航**：→ [AudioVideo_Transmission_Protocols 深度解析](../AudioVideo_Transmission_Protocols_深度解析.md)

---

> HLS 的成功证明了一个深刻的工程智慧：不要发明新的基础设施，而是在现有基础设施（HTTP/CDN）之上构建新能力。用延迟换扩展性，这个取舍在大规模分发场景下是最优解。

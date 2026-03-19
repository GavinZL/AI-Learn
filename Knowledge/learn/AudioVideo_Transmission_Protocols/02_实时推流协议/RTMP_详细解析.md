# RTMP 详细解析

> Flash 时代的遗产，至今仍是直播推流的事实标准——理解 RTMP 的握手、分块和消息机制

---

## 核心结论（TL;DR）

**RTMP（Real Time Messaging Protocol）是 Adobe 设计的基于 TCP 的流媒体传输协议，通过 Chunk 分块机制实现多路流的复用传输，以 1-3 秒的延迟为代价换取可靠的传输保证。** 尽管 Flash 已退出历史舞台，RTMP 仍然是直播推流（主播端到服务器）的事实标准，几乎所有 CDN 都支持 RTMP 推流。

**类比**：RTMP 像是一条"有专人押送的铁路运输线"——速度不是最快的（不如空运/UDP），但每一件货物都有编号、有清单、保证送达，适合从工厂（主播端）到仓库（服务器）的稳定运输。

---

## 目录

1. [历史背景与设计动机](#1-历史背景与设计动机)
2. [RTMP 握手流程](#2-rtmp-握手流程)
3. [Chunk 分块机制](#3-chunk-分块机制)
4. [消息类型体系](#4-消息类型体系)
5. [AMF 编码格式](#5-amf-编码格式)
6. [连接与推流命令流程](#6-连接与推流命令流程)
7. [RTMP 变种协议](#7-rtmp-变种协议)
8. [适用场景与优缺点](#8-适用场景与优缺点)
9. [性能指标与延迟分析](#9-性能指标与延迟分析)
10. [与其他协议对比](#10-与其他协议对比)
11. [FFmpeg 实践示例](#11-ffmpeg-实践示例)

---

## 1. 历史背景与设计动机

### 1.1 为什么需要 RTMP

2002 年，Macromedia（后被 Adobe 收购）面临的问题：**如何让浏览器中的 Flash 播放器高效地播放实时音视频流？**

当时的选择：
- HTTP：不支持实时推流，延迟太高
- RTP/RTSP：复杂，需要 UDP（穿透 NAT 困难），浏览器不原生支持
- 自研协议：基于 TCP（防火墙友好），针对 Flash 优化

**设计决策**：
1. **基于 TCP**：穿透防火墙/NAT 无障碍，可靠传输
2. **Chunk 机制**：将大消息拆分为小块，避免大帧阻塞小帧
3. **多路复用**：音频、视频、控制消息在同一个 TCP 连接上传输
4. **低开销头部**：Chunk 头部支持压缩，减少重复信息

### 1.2 RTMP 的生态地位

```
2003 ─── RTMP 随 Flash Media Server 发布
2009 ─── Adobe 公开 RTMP 规范
2012 ─── OBS、FFmpeg 等开源工具全面支持
2017 ─── Flash 宣布退役，但 RTMP 推流仍不可替代
2024 ─── Enhanced RTMP 支持 H.265/AV1/VP9
今天 ─── CDN 推流标准，被 SRT/WHIP 逐步挑战
```

---

## 2. RTMP 握手流程

### 2.1 三次握手

RTMP 握手在 TCP 连接建立之后进行，共交换 3 对数据包（C0-C2 / S0-S2）：

```
客户端                          服务端
  │                               │
  │──── C0 (1 byte) ────→        │  版本号
  │──── C1 (1536 bytes) ──→     │  时间戳 + 随机数据
  │                               │
  │       ←── S0 (1 byte) ──────│  版本号
  │       ←── S1 (1536 bytes) ──│  时间戳 + 随机数据
  │       ←── S2 (1536 bytes) ──│  C1 的回显
  │                               │
  │──── C2 (1536 bytes) ──→     │  S1 的回显
  │                               │
  │     握手完成，开始消息交换      │
```

### 2.2 各阶段详解

**C0/S0（Version）**：1 字节
- 值为 3 表示 RTMP 版本 3
- 值为 6 表示加密版本（RTMPE）

**C1/S1**：1536 字节
```
| Time (4 bytes) | Zero (4 bytes) | Random Data (1528 bytes) |
```

**C2/S2**：1536 字节（对方 C1/S1 的回显）
```
| Time (4 bytes) | Time2 (4 bytes) | Random Echo (1528 bytes) |
```

**握手延迟**：至少 1.5 个 RTT（TCP 握手 1 RTT + RTMP 握手 0.5 RTT），这是 RTMP 首帧延迟的主要来源之一。

---

## 3. Chunk 分块机制

### 3.1 设计原理

**核心问题**：TCP 是字节流协议，没有消息边界的概念。同时，视频 I 帧可能有数十 KB，而音频帧只有几百字节。如果按消息顺序传输，大的 I 帧会阻塞后续的音频帧。

**解决方案**：将消息拆分为固定大小的 Chunk（默认 128 字节），不同消息的 Chunk 可以交错传输。

```
消息级别：
  Video Message (50KB) ──→ [V1][V2][V3]...[V400]
  Audio Message (200B)  ──→ [A1][A2]

传输级别（Chunk 交错）：
  [V1][V2][V3][A1][V4][V5][A2][V6]...
  
效果：音频帧不需要等待整个视频帧传输完毕
```

### 3.2 Chunk 格式

每个 Chunk 由 **Chunk Header** 和 **Chunk Data** 组成：

```
+--------------+----------------+
| Chunk Header | Chunk Data     |
| (1-18 bytes) | (≤chunk size)  |
+--------------+----------------+
```

**Chunk Header** 包含：

```
+-+-+-+-+-+-+-+-+
|fmt|  cs id    |  Basic Header (1-3 bytes)
+-+-+-+-+-+-+-+-+
|  timestamp    |
+---------------+  Message Header (0/3/7/11 bytes, 取决于 fmt)
|  msg length   |
+---------------+
| msg type id   |
+---------------+
| msg stream id |
+---------------+
```

### 3.3 Chunk 头部压缩（fmt 字段）

RTMP 通过 4 种 fmt 类型实现头部压缩：

| fmt | 头部大小 | 包含字段 | 适用场景 |
|-----|---------|---------|---------|
| **0** | 11 字节 | 全部字段 | Chunk Stream 的第一个消息 |
| **1** | 7 字节 | 省略 stream id | 与前一消息相同 stream id |
| **2** | 3 字节 | 仅 timestamp delta | 大小和类型都相同 |
| **3** | 0 字节 | 无额外字段 | 连续 chunk（同一消息的后续分片） |

**这是 RTMP 减少带宽开销的关键机制**。对于连续的音频帧（大小、类型、stream id 都相同），大部分 chunk 只需要 1 字节的 Basic Header。

### 3.4 Chunk Size 协商

默认 Chunk Size 为 128 字节，但可以通过 `Set Chunk Size` 控制消息调整（通常增大到 4096-65536 字节）：

```
更大的 Chunk Size：
  优点：减少头部开销比例，提高传输效率
  缺点：增加交错粒度，音视频交错不够精细
  
推荐值：4096 字节（平衡效率和交错性）
```

---

## 4. 消息类型体系

### 4.1 协议控制消息（Type ID 1-6）

| Type ID | 名称 | 说明 |
|---------|------|------|
| 1 | Set Chunk Size | 设置 Chunk 大小 |
| 2 | Abort Message | 中止某个 Chunk Stream |
| 3 | Acknowledgement | 确认已接收的字节数 |
| 4 | User Control Message | 流控制事件 |
| 5 | Window Acknowledgement Size | 设置确认窗口大小 |
| 6 | Set Peer Bandwidth | 设置对端带宽 |

### 4.2 命令消息（Type ID 20/17）

使用 AMF0（Type 20）或 AMF3（Type 17）编码的命令：

| 命令 | 方向 | 说明 |
|------|------|------|
| connect | C→S | 建立连接到应用 |
| createStream | C→S | 创建消息流 |
| publish | C→S | 开始推流 |
| play | C→S | 开始拉流 |
| deleteStream | C→S | 删除消息流 |
| onStatus | S→C | 状态通知 |

### 4.3 数据消息

| Type ID | 名称 | 说明 |
|---------|------|------|
| 8 | Audio Message | 音频数据 |
| 9 | Video Message | 视频数据 |
| 18/15 | Data Message | 元数据（AMF0/AMF3） |

---

## 5. AMF 编码格式

### 5.1 AMF0 数据类型

AMF（Action Message Format）是 RTMP 命令和元数据的序列化格式：

| 类型标记 | 类型 | 说明 |
|---------|------|------|
| 0x00 | Number | 8 字节 IEEE 754 双精度浮点 |
| 0x01 | Boolean | 1 字节 |
| 0x02 | String | 2 字节长度 + UTF-8 字符串 |
| 0x03 | Object | 键值对集合 |
| 0x05 | Null | 空值 |
| 0x08 | ECMA Array | 关联数组 |
| 0x09 | Object End | 对象结束标记（0x000009） |

### 5.2 元数据示例

```
onMetaData {
  duration: 0,
  width: 1920,
  height: 1080,
  videodatarate: 4000,    // kbps
  framerate: 30,
  videocodecid: 7,        // H.264
  audiodatarate: 128,     // kbps
  audiosamplerate: 44100,
  audiosamplesize: 16,
  audiocodecid: 10,       // AAC
  stereo: true
}
```

---

## 6. 连接与推流命令流程

### 6.1 完整推流流程

```
客户端                                          服务端
  │                                               │
  │──── TCP 连接 ───→                             │
  │──── RTMP 握手 ───→                            │
  │                                               │
  │──── connect("live") ───→                      │
  │       ←── Window Ack Size ──────────────────│
  │       ←── Set Peer Bandwidth ───────────────│
  │       ←── Set Chunk Size ───────────────────│
  │       ←── _result(connect success) ─────────│
  │                                               │
  │──── releaseStream("stream_key") ───→         │
  │──── FCPublish("stream_key") ───→             │
  │──── createStream() ───→                      │
  │       ←── _result(stream_id=1) ─────────────│
  │                                               │
  │──── publish("stream_key", "live") ───→       │
  │       ←── onStatus("NetStream.Publish.Start")│
  │                                               │
  │──── Audio/Video Data ───→                    │  持续推流
  │──── Audio/Video Data ───→                    │
  │          .......                              │
```

### 6.2 RTMP URL 格式

```
rtmp://host[:port]/app[/instance]/stream_key

示例：
rtmp://live.example.com:1935/live/abc123

其中：
  host = live.example.com
  port = 1935（默认）
  app = live
  stream_key = abc123
```

---

## 7. RTMP 变种协议

| 变种 | 底层 | 加密 | 端口 | 说明 |
|------|------|------|------|------|
| **RTMP** | TCP | 无 | 1935 | 原始版本 |
| **RTMPS** | TLS/TCP | TLS | 443 | RTMP over TLS，安全传输 |
| **RTMPE** | TCP | 自有加密 | 1935 | Adobe 私有加密（已不推荐） |
| **RTMPT** | HTTP/TCP | 无 | 80/443 | RTMP over HTTP，穿透严格防火墙 |
| **RTMFP** | UDP | 是 | 1935 | P2P 模式（已废弃） |

**Enhanced RTMP（2023+）**：
- 支持 H.265 (HEVC)、VP9、AV1 编解码器
- 支持 HDR 元数据传输
- 由 OBS、FFmpeg、主流 CDN 联合推动
- 兼容原有 RTMP 基础设施

---

## 8. 适用场景与优缺点

### 8.1 优点

| 优点 | 说明 |
|------|------|
| **生态成熟** | 几乎所有 CDN、编码器、服务器都支持 |
| **穿透性好** | 基于 TCP，防火墙友好 |
| **延迟适中** | 1-3 秒，适合大多数直播场景 |
| **实现简单** | 协议文档公开，开源实现丰富 |
| **多路复用** | 音视频在同一连接上传输 |

### 8.2 缺点

| 缺点 | 说明 |
|------|------|
| **队头阻塞** | 基于 TCP，丢包时延迟飙升 |
| **加密薄弱** | 原生不支持加密（需用 RTMPS） |
| **不支持 P2P** | 纯客户端-服务器模式 |
| **编解码限制** | 原版仅支持 H.264/AAC（Enhanced RTMP 已扩展） |
| **不适合拉流分发** | 大规模分发需转为 HLS/DASH |

### 8.3 适用 vs 不适用

| ✅ 适用场景 | ❌ 不适用场景 |
|-----------|-------------|
| 主播端推流到服务器 | 大规模观众端拉流 |
| CDN 源站推流 | 超低延迟通信（< 500ms） |
| 游戏直播、电商直播推流 | P2P 实时对话 |
| 编码器到媒体服务器传输 | 移动弱网环境 |

---

## 9. 性能指标与延迟分析

### 9.1 延迟构成

```
RTMP 端到端延迟分解：

TCP 握手           ~1 RTT     (50-100ms)
RTMP 握手          ~0.5 RTT   (25-50ms)
connect + publish  ~2 RTT     (100-200ms)
编码延迟           ~50-200ms
网络传输           ~50-200ms
服务器处理         ~10-50ms
CDN 转发           ~100-500ms
─────────────────────────────
总计推流延迟：约 400ms - 1.5s

如果加上拉流端（转为 HLS/FLV）：
拉流协议延迟       ~1-10s
解码 + 渲染        ~30-100ms
─────────────────────────────
总计端到端：约 1.5s - 12s
```

### 9.2 吞吐量分析

RTMP 基于 TCP，吞吐量受 TCP 拥塞窗口限制：

```
理论最大吞吐量 ≈ 窗口大小 / RTT

示例：窗口 = 64KB, RTT = 50ms
吞吐量 ≈ 64 × 1024 × 8 / 0.05 ≈ 10.5 Mbps

对于 4Mbps 的 1080p 推流通常足够，
但在高 RTT 网络（跨洲际）下可能成为瓶颈。
```

---

## 10. 与其他协议对比

| 维度 | RTMP | SRT | WebRTC | HLS |
|------|------|-----|--------|-----|
| **底层协议** | TCP | UDP | UDP | HTTP/TCP |
| **延迟** | 1-3s | 0.2-2s | < 0.5s | 6-30s |
| **可靠性** | TCP 保证 | ARQ+FEC | NACK+FEC | TCP 保证 |
| **加密** | 可选(TLS) | AES 内置 | DTLS 强制 | 可选(TLS) |
| **CDN 支持** | 极好 | 增长中 | 有限 | 极好 |
| **主要用途** | 推流 | 专业传输 | P2P 通信 | 大规模分发 |
| **弱网表现** | 差（TCP阻塞） | 好 | 好 | 中 |
| **开源实现** | nginx-rtmp, SRS | libsrt | libwebrtc | 通用 HTTP |

---

## 11. FFmpeg 实践示例

### 11.1 RTMP 推流

```bash
# 推流到 RTMP 服务器（如 nginx-rtmp, SRS）
ffmpeg -re -i input.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -b:v 4000k -maxrate 4500k -bufsize 8000k \
  -c:a aac -b:a 128k -ar 44100 \
  -f flv rtmp://localhost/live/stream_key

# 推流摄像头（macOS）
ffmpeg -f avfoundation -i "0:0" \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -b:v 2500k \
  -c:a aac -b:a 128k \
  -f flv rtmp://localhost/live/webcam
```

### 11.2 RTMP 拉流

```bash
# 拉流并播放
ffplay rtmp://localhost/live/stream_key

# 拉流并录制为 MP4
ffmpeg -i rtmp://localhost/live/stream_key \
  -c copy output.mp4

# 拉流并转推到另一个服务器
ffmpeg -i rtmp://server1/live/stream \
  -c copy -f flv rtmp://server2/live/stream
```

### 11.3 nginx-rtmp 基础配置

```nginx
rtmp {
    server {
        listen 1935;
        
        application live {
            live on;
            
            # 转 HLS
            hls on;
            hls_path /tmp/hls;
            hls_fragment 3;
            hls_playlist_length 60;
            
            # 录制
            record all;
            record_path /tmp/rec;
        }
    }
}
```

---

## 与其他文档的关联

- **传输基础**：← [网络传输基础_详细解析](../01_传输基础与协议栈/网络传输基础_详细解析.md)
- **替代方案**：→ [SRT_详细解析](./SRT_详细解析.md)
- **分发协议**：→ [HLS_详细解析](../04_自适应流媒体协议/HLS_详细解析.md)
- **总览导航**：→ [AudioVideo_Transmission_Protocols 深度解析](../AudioVideo_Transmission_Protocols_深度解析.md)

---

> RTMP 虽然"老"，但它的 Chunk 分块和多路复用思想至今仍有价值。在可预见的未来，RTMP 推流仍将是直播基础设施的重要组成部分——直到 SRT/WHIP 完全成熟。

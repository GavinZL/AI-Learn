# WebRTC 详细解析

> 浏览器原生的实时通信引擎——从 ICE 打洞到 SRTP 加密的全链路剖析

---

## 核心结论（TL;DR）

**WebRTC（Web Real-Time Communication）是一套开放标准和开源框架，使浏览器和移动应用无需安装插件即可实现 P2P 的实时音视频通信和数据传输。** 其核心价值在于将原本需要专业设备和专有软件才能实现的实时通信能力，变成了一个浏览器 API 调用。

WebRTC 的延迟可以低至 **100-300ms**（端到端），是目前延迟最低的主流音视频传输方案。代价是架构复杂度高——它不是一个单一协议，而是一个协议簇的集合，涉及 **ICE/STUN/TURN（连接建立）、SDP（媒体协商）、DTLS-SRTP（加密传输）、RTP/RTCP（媒体传输）、SCTP（数据通道）** 等十多个协议的协同工作。

**类比**：WebRTC 像是一个"自带 GPS 导航、自动避障、全程加密"的智能快递无人机——功能极其强大，但内部结构也极其复杂。

---

## 目录

1. [设计背景与第一性原理](#1-设计背景与第一性原理)
2. [WebRTC 协议栈全景](#2-webrtc-协议栈全景)
3. [信令与 SDP 协商](#3-信令与-sdp-协商)
4. [ICE 连接建立](#4-ice-连接建立)
5. [DTLS-SRTP 安全传输](#5-dtls-srtp-安全传输)
6. [媒体传输与处理](#6-媒体传输与处理)
7. [拥塞控制（GCC/TWC）](#7-拥塞控制gcctcc)
8. [DataChannel](#8-datachannel)
9. [架构模式：P2P/SFU/MCU](#9-架构模式p2psfumcu)
10. [适用场景与优缺点](#10-适用场景与优缺点)
11. [性能指标](#11-性能指标)
12. [与其他协议对比](#12-与其他协议对比)
13. [代码示例](#13-代码示例)

---

## 1. 设计背景与第一性原理

### 1.1 核心问题

2010 年之前，在浏览器中实现实时视频通话需要：Flash 插件、Java Applet 或 ActiveX 控件。这不仅用户体验差，还存在安全隐患。

**Google 的目标**：让实时通信变成浏览器的原生能力，像打开网页一样简单。

### 1.2 从第一性原理推导设计决策

**需求**：两个浏览器之间实时传输音视频

**推导**：
1. **低延迟** → 必须用 UDP，不能用 TCP（队头阻塞）
2. **P2P 直连** → 减少中间节点，延迟最低 → 但需要解决 NAT 穿透
3. **NAT 穿透** → 需要 STUN 获取公网地址 + ICE 框架协调连接
4. **安全** → 浏览器场景必须加密（DTLS + SRTP）
5. **媒体协商** → 双方需要知道对方支持什么编解码器 → SDP
6. **SDP 交换** → 需要一个信令通道 → WebRTC 故意不定义信令协议（留给应用层）
7. **质量控制** → 需要自适应码率 → RTCP 反馈 + GCC 拥塞控制

---

## 2. WebRTC 协议栈全景

```
┌──────────────────────────────────────────────────┐
│                  Web API / 应用层                  │
│    getUserMedia │ RTCPeerConnection │ DataChannel  │
├──────────────────────────────────────────────────┤
│              信令层（WebRTC 不定义）                │
│         WebSocket / HTTP / SIP / 自定义           │
├──────────────┬───────────────────────────────────┤
│   媒体引擎    │        传输层                      │
│  ┌─────────┐ │ ┌──────────┬──────────┐          │
│  │音频处理  │ │ │  SRTP    │  SCTP    │          │
│  │(Opus/G711)│ │ (媒体加密) │(DataCh) │          │
│  ├─────────┤ │ ├──────────┴──────────┤          │
│  │视频处理  │ │ │       DTLS          │          │
│  │(VP8/H264)│ │ │   (密钥协商+加密)    │          │
│  └─────────┘ │ ├─────────────────────┤          │
│              │ │    ICE / STUN / TURN  │          │
│              │ ├─────────────────────┤          │
│              │ │        UDP           │          │
├──────────────┴─┴─────────────────────┴──────────┤
│                     IP                           │
└──────────────────────────────────────────────────┘
```

### 2.1 协议职责分工

| 协议 | 职责 | RFC |
|------|------|-----|
| **ICE** | NAT 穿透、连接候选收集和检查 | RFC 8445 |
| **STUN** | 获取 NAT 映射的公网地址 | RFC 5389 |
| **TURN** | 当 P2P 不通时提供中继 | RFC 5766 |
| **DTLS** | UDP 上的 TLS，密钥协商 | RFC 6347 |
| **SRTP** | RTP 数据包加密 | RFC 3711 |
| **SCTP** | 可靠/不可靠的数据通道 | RFC 4960 |
| **SDP** | 媒体能力描述和协商 | RFC 4566 |
| **RTP/RTCP** | 媒体数据传输和质量反馈 | RFC 3550 |

---

## 3. 信令与 SDP 协商

### 3.1 Offer/Answer 模型

WebRTC 使用 SDP（Session Description Protocol）进行媒体能力协商：

```
发起方(Alice)                              接收方(Bob)
     │                                        │
     │─── 创建 RTCPeerConnection ──          │
     │─── getUserMedia（获取摄像头/麦克风）──  │
     │                                        │
     │─── createOffer() ──→ SDP Offer        │
     │                        │               │
     │──── 通过信令服务器传递 ────→           │
     │                        │               │
     │                  setRemoteDescription   │
     │                  createAnswer()         │
     │                        │               │
     │       ←──── SDP Answer ──────────────│
     │                                        │
     │    setRemoteDescription                │
     │                                        │
     │ ←───── ICE Candidate 交换 ──────→     │
     │                                        │
     │ ←════ P2P 媒体流传输 ════→            │
```

### 3.2 SDP 示例解析

```
v=0
o=- 1234567890 2 IN IP4 127.0.0.1
s=-
t=0 0
m=audio 9 UDP/TLS/RTP/SAVPF 111 103 104
c=IN IP4 0.0.0.0
a=rtcp-mux
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
a=rtpmap:103 ISAC/16000
a=rtpmap:104 ISAC/32000
a=ice-ufrag:someUfrag
a=ice-pwd:somePassword
a=fingerprint:sha-256 AA:BB:CC:...
a=setup:actpass

m=video 9 UDP/TLS/RTP/SAVPF 96 97 98
a=rtcp-mux
a=rtpmap:96 VP8/90000
a=rtpmap:97 H264/90000
a=fmtp:97 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f
a=rtpmap:98 VP9/90000
a=rtcp-fb:96 nack
a=rtcp-fb:96 nack pli
a=rtcp-fb:96 goog-remb
a=rtcp-fb:96 transport-cc
```

关键字段解读：
- `m=audio/video`：媒体行，定义媒体类型和支持的编解码
- `a=rtpmap`：编解码器映射（PT → 编码器名称/时钟频率）
- `a=ice-ufrag/ice-pwd`：ICE 认证凭据
- `a=fingerprint`：DTLS 证书指纹（安全验证）
- `a=rtcp-fb`：支持的 RTCP 反馈类型

---

## 4. ICE 连接建立

### 4.1 候选地址收集

```
ICE Agent 收集三类候选地址：

1. Host Candidate（本地地址）
   192.168.1.100:50000（直接可用，无需穿透）

2. Server Reflexive Candidate（STUN 反射地址）
   向 STUN 服务器发 Binding Request → 获知公网地址
   1.2.3.4:12345（NAT 映射的公网地址）

3. Relay Candidate（TURN 中继地址）
   向 TURN 服务器请求分配地址
   5.6.7.8:54321（TURN 服务器上的中继地址）
```

### 4.2 连接检查流程

```
Alice 的候选:                    Bob 的候选:
  host: 192.168.1.100:50000       host: 10.0.0.50:60000
  srflx: 1.2.3.4:12345           srflx: 5.6.7.8:54321
  relay: 9.9.9.9:11111           relay: 8.8.8.8:22222

候选对（按优先级排序）:
  1. host-host     (最优，但跨网不通)
  2. host-srflx    (NAT 穿透尝试)
  3. srflx-srflx   (双 NAT 穿透)
  4. relay-srflx   (单侧中继)
  5. relay-relay   (双侧中继，必定成功但延迟最大)

ICE 逐对进行 STUN Binding 检查，选择能通的最高优先级对。
```

### 4.3 ICE 状态机

```
        new
         │
    gathering  ←──→  候选收集中
         │
    checking   ←──→  连接检查中
         │
    connected  ←──→  至少一对成功
         │
    completed  ←──→  最优对确认
         │
     closed
```

### 4.4 Trickle ICE

传统 ICE 需要等所有候选收集完才开始协商，Trickle ICE 允许边收集边发送：

```
传统 ICE：收集全部候选 → 生成 SDP → 发送 → 等待应答 → 开始检查
Trickle ICE：生成 SDP → 发送 → 同时逐个发送新发现的候选 → 尽早开始检查

效果：连接建立时间从 ~5s 降低到 ~1-2s
```

---

## 5. DTLS-SRTP 安全传输

### 5.1 为什么需要 DTLS-SRTP

WebRTC 强制加密所有媒体传输，机制是：
1. **DTLS**（Datagram TLS）：在 UDP 上完成密钥协商
2. **SRTP**：使用 DTLS 协商的密钥加密 RTP 包

```
ICE 连接建立成功
        │
        ▼
DTLS 握手（交换证书、协商密钥）
        │
        ▼
SRTP 密钥导出
        │
        ▼
所有 RTP 包使用 SRTP 加密传输
```

### 5.2 安全验证

SDP 中的 `fingerprint` 字段包含 DTLS 证书的哈希值。信令服务器（虽然可能不安全）传递了对方的证书指纹后，DTLS 握手时会验证对方证书是否匹配——这确保了即使信令被篡改，媒体也无法被窃听。

---

## 6. 媒体传输与处理

### 6.1 支持的编解码器

| 类型 | 必须支持 | 常用 | 说明 |
|------|---------|------|------|
| **音频** | Opus | G.711, G.722 | Opus 是 WebRTC 的默认音频编解码器 |
| **视频** | VP8 或 H.264 | VP9, AV1 | H.264 需要硬件加速时优先 |

### 6.2 Simulcast 与 SVC

**Simulcast（同步多流）**：
```
编码器同时产出多个分辨率的流：
  高质量：1080p @ 2.5Mbps
  中质量：720p @ 1Mbps
  低质量：360p @ 300kbps

SFU 根据每个接收端的网络状况选择转发哪一路
```

**SVC（可伸缩视频编码）**：
```
编码器产出分层的单一码流：
  基础层：360p（必须解码）
  增强层1：+720p（可选解码）
  增强层2：+1080p（可选解码）

SFU 可以根据带宽丢弃增强层，无需重新编码
```

### 6.3 丢包恢复策略

WebRTC 使用多重丢包恢复策略：

| 策略 | 机制 | 延迟代价 |
|------|------|---------|
| **NACK** | 请求重传丢失的包 | +1 RTT |
| **FEC (ULPFEC/FlexFEC)** | 前向纠错冗余包 | 0 |
| **PLI/FIR** | 请求关键帧 | +编码延迟 |
| **丢帧/冻结** | 跳过丢失帧 | 视觉降级 |

---

## 7. 拥塞控制（GCC/TCC）

### 7.1 GCC（Google Congestion Control）

GCC 是 WebRTC 的默认拥塞控制算法，基于两个维度估计带宽：

**基于延迟的估计器**：
```
测量包的到达间隔变化（delay gradient）
  如果延迟持续增加 → 网络拥塞 → 降低码率
  如果延迟稳定或减少 → 网络空闲 → 逐步增加码率
```

**基于丢包的估计器**：
```
丢包率 > 10% → 大幅降低码率
丢包率 2-10% → 保持当前码率
丢包率 < 2% → 可以增加码率
```

### 7.2 Transport-wide Congestion Control（TCC）

TCC 是 GCC 的改进版本：
- 接收端为每个包记录精确的到达时间
- 通过 RTCP Transport Feedback 包批量反馈给发送端
- 发送端拥有完整的传输统计信息，做出更精确的码率决策

---

## 8. DataChannel

### 8.1 架构

DataChannel 使用 SCTP over DTLS over UDP 实现：

```
DataChannel API
      │
    SCTP（支持可靠/不可靠、有序/无序）
      │
    DTLS（加密）
      │
    ICE/UDP
```

### 8.2 配置选项

| 选项 | 说明 |
|------|------|
| `ordered` | 是否保证顺序（默认 true） |
| `maxRetransmits` | 最大重传次数（设为 0 = 不可靠） |
| `maxPacketLifeTime` | 包的最大生存时间 |
| `protocol` | 子协议标识 |

---

## 9. 架构模式：P2P/SFU/MCU

### 9.1 三种架构对比

**P2P（Peer-to-Peer）**
```
A ←──→ B

优点：最低延迟，无服务器成本
缺点：N 人通话需要 N×(N-1)/2 条连接，带宽 = N-1 倍上行
适用：1v1 通话
```

**SFU（Selective Forwarding Unit）**
```
A ──→ SFU ──→ B
B ──→ SFU ──→ A
C ──→ SFU ──→ A, B

优点：每人只需 1 路上行，服务器不解码（CPU 低）
缺点：需要服务器，每人下行 = N-1 路
适用：小型会议（5-50人）——主流方案
```

**MCU（Multipoint Control Unit）**
```
A ──→ MCU ──→ 混合后的画面 ──→ A, B, C
B ──→ MCU
C ──→ MCU

优点：每人上下行各 1 路（带宽最省）
缺点：服务器需要解码+混流+重编码（CPU 极高）
适用：大规模会议、兼容传统终端
```

### 9.2 架构选择决策

| 参与人数 | 推荐架构 | 理由 |
|---------|---------|------|
| 2 人 | P2P | 最简单，延迟最低 |
| 3-20 人 | SFU | 性能和质量的最佳平衡 |
| 20-100 人 | SFU + Simulcast | 多流适配不同网络 |
| 100+ 人 | SFU/MCU + HLS 旁路 | 超大规模需要 CDN 兜底 |

---

## 10. 适用场景与优缺点

### 10.1 优点

| 优点 | 说明 |
|------|------|
| **超低延迟** | 端到端 100-500ms |
| **浏览器原生** | 无需安装插件 |
| **强制加密** | DTLS-SRTP，安全有保障 |
| **P2P 能力** | 减少服务器成本 |
| **开源成熟** | libwebrtc 被 Chrome/Firefox/Safari 使用 |

### 10.2 缺点

| 缺点 | 说明 |
|------|------|
| **架构复杂** | 涉及十多个协议的协同 |
| **扩展性有限** | 大规模场景需要 SFU/MCU |
| **信令未标准化** | 需要自行实现信令服务器 |
| **CDN 不友好** | 不能直接通过传统 CDN 分发 |
| **移动端耗电** | 持续的编解码和网络保活 |

---

## 11. 性能指标

### 11.1 延迟特征

```
WebRTC 端到端延迟分解：
  媒体采集：~20ms
  编码：~30-50ms（硬件编码）
  RTP 打包：~1ms
  网络传输：~10-100ms（取决于距离）
  Jitter Buffer：~20-100ms
  解码：~10-30ms
  渲染：~16ms（60fps）
  ──────────────────
  总计：约 100-350ms
```

### 11.2 关键性能数据

| 指标 | 典型值 |
|------|--------|
| 端到端延迟（局域网） | 50-150ms |
| 端到端延迟（同城公网） | 100-300ms |
| 端到端延迟（跨洲际） | 200-500ms |
| NAT 穿透成功率（STUN） | ~80% |
| NAT 穿透成功率（TURN 兜底） | ~100% |
| 丢包容忍度 | < 5%（配合 NACK+FEC） |

---

## 12. 与其他协议对比

| 维度 | WebRTC | RTMP | SRT | HLS |
|------|--------|------|-----|-----|
| **延迟** | < 500ms | 1-3s | 0.2-2s | 6-30s |
| **传输层** | UDP(DTLS) | TCP | UDP | HTTP/TCP |
| **加密** | 强制 | 可选 | 内置 | 可选 |
| **P2P** | ✅ | ❌ | ❌ | ❌ |
| **浏览器原生** | ✅ | ❌ | ❌ | ✅ |
| **大规模分发** | 需SFU | 需CDN | 不适合 | CDN 原生 |
| **双向通信** | ✅ | 单向 | 单向 | 单向 |

---

## 13. 代码示例

### 13.1 基础 WebRTC 连接（JavaScript）

```javascript
// 创建 PeerConnection
const pc = new RTCPeerConnection({
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'turn:turn.example.com', username: 'user', credential: 'pass' }
  ]
});

// 获取本地媒体流
const stream = await navigator.mediaDevices.getUserMedia({
  video: { width: 1280, height: 720 },
  audio: true
});

// 添加轨道
stream.getTracks().forEach(track => pc.addTrack(track, stream));

// 监听 ICE 候选
pc.onicecandidate = event => {
  if (event.candidate) {
    signaling.send({ type: 'candidate', candidate: event.candidate });
  }
};

// 创建 Offer
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);
signaling.send({ type: 'offer', sdp: offer });
```

### 13.2 FFmpeg WebRTC 推流（WHIP）

```bash
# 通过 WHIP 协议推流到 WebRTC 服务器
ffmpeg -re -i input.mp4 \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -b:v 2000k \
  -c:a libopus -b:a 64k \
  -f whip "http://server:8080/whip/stream"
```

---

## 与其他文档的关联

- **RTP/RTCP 基础**：← [UDP_RTP_RTCP协议栈_详细解析](../01_传输基础与协议栈/UDP_RTP_RTCP协议栈_详细解析.md)
- **RTP/RTCP 深入**：→ [RTP与RTCP_详细解析](./RTP与RTCP_详细解析.md)
- **协议选型**：→ [协议选择决策树_详细解析](../05_协议对比与选型/协议选择决策树_详细解析.md)
- **总览导航**：→ [AudioVideo_Transmission_Protocols 深度解析](../AudioVideo_Transmission_Protocols_深度解析.md)

---

> WebRTC 代表了"将实时通信能力民主化"的理念。它的复杂性恰恰反映了实时通信问题本身的复杂性——NAT 穿透、安全加密、拥塞控制、媒体处理，每一个都是独立的技术领域。

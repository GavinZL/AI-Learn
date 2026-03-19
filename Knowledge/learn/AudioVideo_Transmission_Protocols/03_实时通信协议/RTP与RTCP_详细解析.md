# RTP 与 RTCP 详细解析

> 深入 RTP/RTCP 的高级机制：从基础传输到 WebRTC 中的扩展反馈，掌握实时媒体传输的核心细节

---

## 核心结论（TL;DR）

**RTP 和 RTCP 是实时媒体传输的基石协议。RTP 提供时间戳、序列号和载荷类型标识，使接收端能够正确地重组和播放媒体流；RTCP 提供双向质量反馈通道，使发送端能够根据网络状况动态调整编码参数。** 本文在协议栈总览的基础上，深入探讨 RTP/RTCP 在实际工程中的高级机制：RTCP 扩展反馈（NACK/PLI/FIR/REMB/TCC）、RTP 扩展头、SRTP 安全传输、以及 RTP 在不同编解码器下的打包策略。

---

## 目录

1. [RTP 高级机制](#1-rtp-高级机制)
2. [RTCP 扩展反馈深入](#2-rtcp-扩展反馈深入)
3. [SRTP/SRTCP 安全传输](#3-srtpsrtcp-安全传输)
4. [RTP 载荷打包策略详解](#4-rtp-载荷打包策略详解)
5. [Jitter Buffer 设计](#5-jitter-buffer-设计)
6. [RTP Multiplexing 与 BUNDLE](#6-rtp-multiplexing-与-bundle)
7. [RTP 在不同场景中的应用](#7-rtp-在不同场景中的应用)
8. [常见问题与调试](#8-常见问题与调试)

---

## 1. RTP 高级机制

### 1.1 序列号回绕处理

RTP 序列号是 16 位，范围 0-65535。在高帧率视频流中，约 36 分钟就会回绕一次（30fps × 60s × 36min ≈ 65000）。

接收端必须正确处理回绕：

```
场景：当前包序列号 = 5，上一个包序列号 = 65530

判断逻辑：
  差值 = 5 - 65530 = -65525
  由于差值 < -32768（半窗口），判断为正向回绕
  实际差值 = 65536 - 65525 = 11
  → 包 5 是包 65530 之后第 11 个包（正常递增）
```

### 1.2 RTP 时间戳的高级用法

**帧内多包的时间戳处理**：

同一视频帧的所有 RTP 包共享相同的时间戳：

```
视频帧 #100（大小 80KB，拆分为 55 个 RTP 包）：
  RTP SEQ=1000, TS=9000000, M=0  ← 第 1 个包
  RTP SEQ=1001, TS=9000000, M=0  ← 第 2 个包
  ...
  RTP SEQ=1054, TS=9000000, M=1  ← 最后一个包（M=1 标记帧结束）

视频帧 #101：
  RTP SEQ=1055, TS=9003000, M=0  ← 新帧，TS 增加 3000（90000/30fps）
```

**不同时钟频率的含义**：

| 媒体类型 | 典型时钟频率 | 每帧 TS 增量 | 说明 |
|---------|------------|-------------|------|
| 视频 | 90000 Hz | 3000 (30fps) | MPEG-2 TS 历史约定 |
| Opus 音频 | 48000 Hz | 960 (20ms帧) | 采样率 |
| G.711 音频 | 8000 Hz | 160 (20ms帧) | 采样率 |
| H.264 视频 | 90000 Hz | 3600 (25fps) | 同视频约定 |

### 1.3 CSRC 与混音器

CSRC（Contributing Source）用于混音器场景：

```
用户A (SSRC=1001) ──→ 
                       混音器 (SSRC=9999) ──→ 混合后的音频
用户B (SSRC=1002) ──→        CC=2, CSRC=[1001, 1002]

接收端通过 CSRC 知道混合音频中包含哪些说话人的声音
```

---

## 2. RTCP 扩展反馈深入

### 2.1 NACK（Negative Acknowledgement）

**报文格式**（RFC 4585）：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|V=2|P|  FMT=1  |   PT=205      |          Length               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  SSRC of packet sender                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  SSRC of media source                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            PID                |             BLP               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **PID**（Packet ID）：第一个丢失的包序列号
- **BLP**（Bitmask of Lost Packets）：PID 之后 16 个包的丢失位图

```
示例：PID=100, BLP=0b0000000000000101
表示丢失的包：100, 101, 103
（BLP 的 bit0 = PID+1, bit1 = PID+2, ...）
```

**一个 NACK 最多报告 17 个连续范围内的丢包**（PID + 16位 BLP），高效紧凑。

### 2.2 PLI（Picture Loss Indication）

当接收端检测到视频帧无法完整解码（参考帧丢失）时发送 PLI：

```
接收端状态：
  帧 100 (I帧) → 解码成功 ✅
  帧 101 (P帧) → 丢包，解码失败 ❌
  帧 102 (P帧) → 参考帧 101 缺失，无法解码 ❌
  帧 103 (P帧) → 同上 ❌
  
→ 发送 PLI → 发送端在下一个机会编码一个 I 帧
→ 帧 105 (I帧) → 解码成功 ✅ → 恢复正常
```

PLI 的效果比 NACK 重传快（不需要等待每个丢失包的重传），但代价是 I 帧较大，会产生瞬时的带宽尖峰。

### 2.3 FIR（Full Intra Request）

FIR 与 PLI 类似，但语义更强：

| 对比 | PLI | FIR |
|------|-----|-----|
| **含义** | "我丢了一些包，请发 I 帧" | "请立即发送完整的 I 帧" |
| **场景** | 丢包导致解码失败 | 新参与者加入、录制开始 |
| **频率** | 可以频繁发送 | 应该谨慎使用 |

### 2.4 REMB（Receiver Estimated Maximum Bitrate）

接收端估计的最大可用带宽，用于指导发送端的码率控制：

```
REMB 报文内容：
  SSRC: 接收端标识
  BR Exp + BR Mantissa: 估计的最大码率
  
示例：REMB = 2,500,000 bps
发送端收到后：
  if (当前码率 > REMB) → 降低编码码率到 REMB
  if (当前码率 < REMB) → 可以逐步增加码率
```

**注意**：REMB 已被 Transport-CC（TCC）逐步替代，因为 TCC 在发送端做带宽估计，能做出更精确的决策。

### 2.5 Transport-wide Congestion Control（TCC）

TCC 是 WebRTC 中最先进的拥塞控制反馈机制：

```
发送端：
  为每个 RTP 包分配 transport-wide 序列号
  [1: T=0ms] [2: T=2ms] [3: T=5ms] [4: T=7ms]

接收端：
  记录每个包的到达时间
  [1: R=10ms] [2: R=15ms] [3: R=丢失] [4: R=22ms]
  
  打包为 Transport Feedback 报告：
  {base_seq: 1, receive_deltas: [10ms, 5ms, 丢失, 7ms]}

发送端：
  用发送时间和到达时间计算：
  - 单向延迟变化（delay gradient）
  - 丢包模式
  - 可用带宽估计
  → 调整编码码率
```

---

## 3. SRTP/SRTCP 安全传输

### 3.1 SRTP 加密机制

SRTP（Secure RTP，RFC 3711）对 RTP 包的载荷进行加密，但保留头部不加密：

```
原始 RTP 包：
|RTP Header (不加密)| Payload (明文) |

SRTP 包：
|RTP Header (不加密)| Payload (密文) | Auth Tag |
                                       ↑
                                 HMAC-SHA1 认证标签
```

**为什么不加密 RTP 头部？**
- 中间节点（如 SFU）需要读取 SSRC、PT、序列号来做路由决策
- 只要载荷加密，中间节点无法获取媒体内容

### 3.2 密钥派生

SRTP 使用 Master Key + 密钥派生函数生成实际的加密密钥和认证密钥：

```
Master Key (来自 DTLS 握手)
    │
    ├── KDF → SRTP Encryption Key
    ├── KDF → SRTP Authentication Key
    ├── KDF → SRTP Salt
    ├── KDF → SRTCP Encryption Key
    ├── KDF → SRTCP Authentication Key
    └── KDF → SRTCP Salt
```

### 3.3 加密算法

| 算法 | 说明 | 使用场景 |
|------|------|---------|
| AES-128-CM | AES 计数器模式 | 默认加密算法 |
| AES-256-CM | 256位 AES | 高安全性场景 |
| HMAC-SHA1-80 | 80位认证标签 | 默认认证 |
| HMAC-SHA1-32 | 32位认证标签 | 节省带宽 |

---

## 4. RTP 载荷打包策略详解

### 4.1 H.264 打包详解（RFC 6184）

**NAL 单元类型决定打包方式**：

| NAL Type | 含义 | 典型大小 | 打包方式 |
|----------|------|---------|---------|
| 1-5 | Coded Slice (非IDR/IDR) | 数百B - 数十KB | FU-A 分片 |
| 6 | SEI | 数十B | STAP-A 聚合 |
| 7 | SPS | ~50B | STAP-A 聚合 |
| 8 | PPS | ~10B | STAP-A 聚合 |
| 24 | STAP-A（聚合包） | - | 多 NAL 合并 |
| 28 | FU-A（分片包） | - | 大 NAL 拆分 |

**FU-A 分片详细结构**：

```
原始 NAL (8000 bytes, Type=5 IDR):
  [NAL Header(1B)][NAL Data(7999B)]

分片为 6 个 RTP 包（每个最大 1400B 载荷）：
  RTP#1: [RTP Hdr][FU Ind][FU Hdr(S=1,E=0,T=5)][Data 1-1398]
  RTP#2: [RTP Hdr][FU Ind][FU Hdr(S=0,E=0,T=5)][Data 1399-2797]
  RTP#3: [RTP Hdr][FU Ind][FU Hdr(S=0,E=0,T=5)][Data 2798-4196]
  RTP#4: [RTP Hdr][FU Ind][FU Hdr(S=0,E=0,T=5)][Data 4197-5595]
  RTP#5: [RTP Hdr][FU Ind][FU Hdr(S=0,E=0,T=5)][Data 5596-6994]
  RTP#6: [RTP Hdr][FU Ind][FU Hdr(S=0,E=1,T=5)][Data 6995-7999] M=1

S=Start, E=End, T=NAL Type, M=RTP Marker bit
```

### 4.2 VP8 打包（RFC 7741）

VP8 的 RTP 打包使用 VP8 Payload Descriptor：

```
 0 1 2 3 4 5 6 7
+-+-+-+-+-+-+-+-+
|X|R|N|S|R| PID |  (必选)
+-+-+-+-+-+-+-+-+
|I|L|T|K| RSV   |  (X=1 时存在，扩展字段)
+-+-+-+-+-+-+-+-+

X: 扩展标志
N: 非参考帧标志
S: 分片的起始标志
PID: 分区 ID
I: 有 PictureID
L: 有 TL0PICIDX
T: 有 TID（时间层 ID）
K: 有 KEYIDX
```

### 4.3 Opus 打包（RFC 7587）

Opus 的 RTP 打包极其简单：

```
|RTP Header| Opus TOC Byte | Opus Frame Data |

TOC (Table of Contents) Byte:
  config (5 bits): 编码模式和带宽
  s (1 bit): 立体声标志
  c (2 bits): 帧数代码（0=1帧, 1=2帧, 2=任意帧, 3=VBR）
```

---

## 5. Jitter Buffer 设计

### 5.1 静态 vs 自适应 Jitter Buffer

**静态 Jitter Buffer**：
```
固定缓冲深度（如 100ms）
  优点：实现简单
  缺点：网络好时浪费延迟，网络差时不够用
```

**自适应 Jitter Buffer**：
```
根据实际网络抖动动态调整缓冲深度

算法核心：
  jitter = smoothed_jitter * 0.9 + current_jitter * 0.1
  buffer_depth = jitter * safety_factor（通常 2-3 倍）
  
  网络平稳期：buffer_depth ≈ 20-40ms
  网络波动期：buffer_depth ≈ 100-200ms
  
  调整策略：
    增大：立即生效（跳帧或插入静音）
    减小：逐步减小（加速播放 5-10%）
```

### 5.2 WebRTC 的 NetEQ

WebRTC 的音频 Jitter Buffer（NetEQ）是业界最复杂的实现之一：

| 功能 | 说明 |
|------|------|
| **自适应缓冲** | 根据网络抖动动态调整 |
| **丢包隐藏（PLC）** | 基于上一帧预测丢失帧的内容 |
| **加速/减速播放** | WSOLA 算法，不改变音调的时间拉伸 |
| **舒适噪声生成（CNG）** | 静音期间生成背景噪声 |
| **混合策略** | 融合正常播放、加速、减速、PLC 的决策 |

---

## 6. RTP Multiplexing 与 BUNDLE

### 6.1 传统模式 vs BUNDLE

**传统模式**：每种媒体使用独立的端口对

```
音频 RTP: port 5000, RTCP: port 5001
视频 RTP: port 5002, RTCP: port 5003
→ 需要穿透 4 个 NAT 映射
```

**RTCP-mux（RFC 5761）**：RTP 和 RTCP 复用同一端口

```
音频 RTP+RTCP: port 5000
视频 RTP+RTCP: port 5002
→ 需要穿透 2 个 NAT 映射
```

**BUNDLE（RFC 8843）**：所有媒体复用同一端口

```
音频+视频 RTP+RTCP: port 5000
→ 只需穿透 1 个 NAT 映射

通过 SSRC 区分不同的媒体流
通过 MID (Media Identification) RTP 扩展头标识属于哪个 m= 行
```

### 6.2 区分复用的包

当所有内容都在同一端口时，如何区分包的类型？

```
接收到 UDP 包后：
  读取第一个字节的高 2 位：
    [0-3]   → STUN 消息（ICE 连接检查）
    [20-63] → DTLS 消息（密钥协商）
    [128-191] → RTP/RTCP（媒体数据）
    
  如果是 RTP/RTCP，再检查 Payload Type：
    PT 72-76 → RTCP（SR/RR/SDES/BYE/APP）
    其他 PT → RTP 数据包
    
  如果是 RTP，通过 SSRC 确定属于哪个媒体流
```

---

## 7. RTP 在不同场景中的应用

### 7.1 直播场景

```
编码器 → RTP 推流 → 媒体服务器 → 转码/转封装 → CDN 分发
                         │
                    RTCP 反馈（码率建议）
```

### 7.2 视频会议场景

```
参与者A → RTP → SFU ← RTP ← 参与者B
                  │
            RTCP Feedback (NACK/PLI/REMB/TCC)
            路由决策（基于 Simulcast 层选择）
```

### 7.3 监控场景

```
摄像机 → RTP/RTSP → NVR（录像机）→ 回放/查看
                          │
              RTCP 用于保活和质量监控
```

---

## 8. 常见问题与调试

### 8.1 常见问题排查

| 现象 | 可能原因 | 排查方法 |
|------|---------|---------|
| 视频花屏 | 丢包导致参考帧缺失 | 检查 RTCP RR 丢包率 |
| 音视频不同步 | NTP 时间戳不准 | 检查 SR 中 NTP/RTP TS 映射 |
| 单向无声/无画面 | ICE 或 SRTP 问题 | 检查 ICE 状态、DTLS 握手 |
| 延迟逐渐增大 | Jitter Buffer 膨胀 | 检查接收端缓冲统计 |
| 码率异常波动 | 拥塞控制过度反应 | 检查 REMB/TCC 反馈值 |

### 8.2 Wireshark 分析技巧

```
过滤 RTP 流：
  rtp

查看 RTP 流统计：
  Telephony → RTP → RTP Streams

查看丢包和抖动：
  Telephony → RTP → Stream Analysis

过滤特定 SSRC：
  rtp.ssrc == 0x12345678

过滤 RTCP 反馈：
  rtcp.pt == 205（RTPFB，包含 NACK）
  rtcp.pt == 206（PSFB，包含 PLI/FIR）
```

---

## 与其他文档的关联

- **协议栈概览**：← [UDP_RTP_RTCP协议栈_详细解析](../01_传输基础与协议栈/UDP_RTP_RTCP协议栈_详细解析.md)
- **WebRTC 应用**：← [WebRTC_详细解析](./WebRTC_详细解析.md)
- **编解码关联**：→ [Video_Codec_Principles](../../Video_Codec_Principles/Video_Codec_Principles_深度解析.md)
- **总览导航**：→ [AudioVideo_Transmission_Protocols 深度解析](../AudioVideo_Transmission_Protocols_深度解析.md)

---

> RTP/RTCP 的设计精髓在于"最小化协议层的职责，最大化应用层的灵活性"。它不替你做决策，而是给你足够的信息（时间戳、序列号、质量反馈）来做出最适合你场景的决策。

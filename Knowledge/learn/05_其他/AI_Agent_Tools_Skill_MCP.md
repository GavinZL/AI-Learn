# AI Agent 中的 Tools、Skill、MCP 概念辨析

> 首次学习：2026-03-10
> 最近更新：2026-03-10（第2次合并）
> 使用场景：AI Agent 架构设计
> 掌握水平：概念理解 → 架构决策

<!-- 更新日志 -->
<!-- [2026-03-10] 首次创建：核心概念对比 / 分层架构设计 / 常见误区 -->
<!-- [2026-03-10] 第2次合并：新增 MCP Server 实现 / 授权架构设计 / 代码示例 -->

---

## 一句话理解（费曼版）

**Tools 是"能做什么"，Skill 是"怎么做任务"，MCP 是"怎么标准化接入"**——三者构成 AI Agent 从原子能力到任务封装再到协议标准的完整技术栈。

---

## 知识框架

1. **概念本质对比** —— 三者的定义与核心区别
2. **分层架构设计** —— 选择"基于 MCP 构建 Skill"时的设计方法
3. **实际应用场景** —— 用一个例子串起来理解
4. **常见误区与避坑** —— 设计时容易犯的错误
5. **MCP Server 实现指南** —— 如何从零开始实现一个 Server
6. **授权架构设计** —— 用户授权在 MCP 中的最佳实践

---

## 核心概念

### Tool（工具）
AI Agent 能调用的**原子级功能**，通常是一个函数或 API 调用。粒度最细，职责单一。

**例子**：`search_google()`、`read_file()`、`call_calculator()`

### Skill（技能）
把**多个 Tools + Prompt 模板 + 业务逻辑**封装成的可复用任务模块。粒度中等，面向具体业务场景。

**例子**：`market_research()`（搜索+分析+生成报告）、`write_blog_post()`（选题+大纲+写作+润色）

### MCP（Model Context Protocol）
Anthropic 推出的**开放协议标准**，定义了 AI 模型如何与外部工具/数据源交互的规范。包括 Tool 描述格式（JSON Schema）、调用方式、返回结构等。

**核心价值**：让不同来源的 Tools/Skills 能用同一套接口规范接入，实现生态互通。

---

## 比喻 & 例子

### 比喻：餐厅后厨

| 概念 | 比喻 | 说明 |
|------|------|------|
| **Tool** | 单个厨具（刀、锅、铲子） | 每个只做一件事，但做得专业 |
| **Skill** | 一道菜的完整做法（宫保鸡丁 SOP） | 规定了先炒什么、后放什么、火候如何 |
| **MCP** | 厨房标准化操作手册 | 不管哪个厨师来，都按这套规范操作 |

### 工作例子：写行业分析报告

**场景**：让 AI 帮你"写一篇关于 AI 的行业分析报告"

1. **Tools 层**：需要 `search_google()` 搜资料、`fetch_webpage()` 抓取网页、`generate_text()` 生成文本
2. **Skill 层**：把这三个 Tools 加上特定的 Prompt 模板，封装成一个 `industry_report_skill`
3. **MCP 层**：你的 Skill 可能用 OpenAI 的 GPT-4，也可能用 Claude，还可能调用本地 Python 脚本——MCP 协议让这些不同的"后端"能用同一套接口规范接入你的 Agent

---

## 边界 & 反例

### 什么情况下这个区分不重要？
- 做简单 Demo 或原型时，可以直接用 Tools，不需要封装 Skill
- 使用单一模型生态（如只用 OpenAI）时，MCP 的优势不明显

### 什么情况下容易出错？
- **过度设计**：简单任务硬要拆成"原子 Tool + 组合 Skill"，反而增加复杂度
- **协议迷信**：为了用 MCP 而把所有逻辑下沉到 Server，导致 Agent 层变成"透传层"

---

## 常见误区

| 误区 | 正确理解 |
|------|----------|
| "Tools、Skill、MCP 是同一个东西的不同叫法" | 三者是**递进层级**：Tools 是原子能力，Skill 是任务封装，MCP 是协议标准 |
| "有了 MCP 就不需要 Skill 了" | MCP 解决"接口标准化"，Skill 解决"业务逻辑封装"——**管道标准化了，但水流还是要设计** |
| "选择 B 路径（基于 MCP）就要把所有逻辑下沉到 MCP Server" | 应该设计**分层 MCP 架构**：底层原子 Tools + 上层组合 Skills，Agent 层保留编排能力 |
| "MCP Server 越丰富越好" | Server 过多会增加管理复杂度，建议按业务域组织，而非按功能原子拆分 |

---

## 分层架构设计（选择 B 路径时）

### 架构图

```
┌─────────────────────────────────────────┐
│           Agent 核心层                   │
│  (决策、规划、Skill 编排、上下文管理)      │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────────┐
│Skill MCP│   │Skill MCP│   │ 原子 Tool   │
│ Server  │   │ Server  │   │ MCP Server  │
│(业务级) │   │(业务级) │   │  (基础能力)  │
│- 写报告  │   │- 数据分析│   │ - 搜索      │
│- 做调研  │   │- 代码生成│   │ - 读文件    │
└─────────┘   └─────────┘   │ - 调用API   │
                            └─────────────┘
```

### 关键设计原则

| 层级 | 职责 | 实现方式 |
|------|------|---------|
| **原子 Tool MCP** | 提供基础能力，无业务逻辑 | 独立 Server，社区共享 |
| **组合 Skill MCP** | 封装特定任务流程 | 可独立 Server，也可在 Agent 层编排 |
| **Agent 核心层** | 决策用哪个 Skill、如何组合、异常处理 | 框架核心代码 |

---

## 自测题

1. **Tools 和 Skill 的本质区别是什么？**
   > 答：Tools 是原子级功能（如搜索、读文件），Skill 是任务级封装（如市场调研、写博客），Skill 通常由多个 Tools + 业务逻辑组合而成。

2. **MCP 解决了什么问题？**
   > 答：MCP 是一个开放协议标准，让不同来源的 Tools/Skills 能用统一的接口规范接入 AI Agent，实现生态互通（一个 MCP Server 可被 Claude、Cursor、Cline 等多个客户端使用）。

3. **选择"完全基于 MCP"路径时，最大的设计陷阱是什么？**
   > 答：把本来应该在 Agent 层做的决策逻辑硬塞进 MCP Server，导致 Server 臃肿、Agent 弱智。正确做法是分层设计：底层原子 Tools 和上层组合 Skills 都用 MCP 协议暴露，但保留 Agent 层的编排和决策能力。

---

## 5. MCP Server 实现指南

### 5.1 核心实现步骤

1. **选择传输方式**：stdio（本地进程）或 SSE（远程服务）
2. **使用官方 SDK**：Python 或 TypeScript SDK 封装协议细节
3. **定义工具**：用装饰器注册工具，SDK 自动生成 JSON Schema
4. **处理生命周期**：initialize → tools/list → tools/call

### 5.2 代码示例（Python）

```python
# server.py
from mcp.server import Server
import os

mcp = Server("my-mcp-server")

@mcp.tool()
def search_web(query: str) -> str:
    """
    搜索网页并返回结果
    
    Args:
        query: 搜索关键词
    """
    # 实际实现：调用搜索引擎 API
    return f"搜索结果: {query}"

@mcp.tool()
def read_file(path: str) -> str:
    """读取文件内容"""
    with open(path, 'r') as f:
        return f.read()

if __name__ == "__main__":
    mcp.run(transport='stdio')
```

### 5.3 客户端配置（Claude Desktop）

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

---

## 6. 授权架构设计

### 6.1 推荐方案：客户端管理 Token + Server 验证

**架构图**：
```
┌─────────────────┐     1. 获取 Token      ┌─────────────────┐
│   授权服务       │ ◄───────────────────── │     客户端       │
│ (OAuth/SSO/Key) │                        │ (Claude/Cursor) │
└─────────────────┘                        └────────┬────────┘
                                                    │
                              2. Token 通过环境变量/参数传递
                                                    ▼
┌─────────────────┐     3. 验证 Token        ┌─────────────────┐
│   业务服务       │ ◄───────────────────── │   MCP Server    │
│  (私有数据 API)  │                        │  (验证后调用)    │
└─────────────────┘                        └─────────────────┘
```

### 6.2 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Server 层全权处理** | 客户端简单 | 违背无状态设计；stdio 难实现回调 | ⭐⭐ |
| **客户端管理 Token** | 符合 MCP 理念；灵活对接多种授权源 | 需确保 Token 传递安全 | ⭐⭐⭐⭐⭐ |
| **外部授权服务** | 职责分离彻底 | 架构复杂；引入额外依赖 | ⭐⭐⭐⭐ |

### 6.3 代码示例（带授权验证）

```python
# private_data_server.py
from mcp.server import Server
import os
import requests

mcp = Server("private-data-server")

def validate_token(token: str) -> bool:
    """验证 Token 有效性"""
    response = requests.post(
        "https://auth.example.com/validate",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.status_code == 200

@mcp.tool()
def query_user_data(query: str) -> str:
    """查询用户私有数据"""
    token = os.environ.get("API_TOKEN")
    if not token:
        return "错误：未提供 API_TOKEN"
    
    if not validate_token(token):
        return "错误：Token 无效或已过期"
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        "https://api.example.com/data",
        headers=headers,
        params={"q": query}
    )
    return response.text

if __name__ == "__main__":
    mcp.run(transport='stdio')
```

### 6.4 安全注意事项

| 风险 | 防护措施 |
|------|---------|
| Token 泄露 | 使用环境变量而非命令行参数；避免日志打印 Token |
| Token 过期 | Server 返回明确错误，客户端引导重新授权 |
| 权限过大 | Token 按最小权限原则申请（Scope 限制） |
| 中间人攻击 | 使用 HTTPS；验证服务端证书 |

---

## 延伸阅读 / 关联知识

1. **MCP 官方文档**：https://modelcontextprotocol.io/ —— 了解协议规范、SDK 使用、官方示例
2. **Function Calling vs Tool Use**：不同 LLM 厂商对"模型调用外部工具"的实现差异，MCP 正在尝试统一这些差异
3. **Agent 架构模式**：ReAct、Plan-and-Solve、Multi-Agent 等模式与 Tools/Skills 设计的结合
4. **OAuth 2.0 for MCP**：https://spec.modelcontextprotocol.io/specification/authorization/ —— 官方授权规范

---

## 关键决策检查清单

当你在设计 AI Agent 架构时，问自己：

### 概念设计
- [ ] 这个能力是原子级的（Tool）还是任务级的（Skill）？
- [ ] 这个 Skill 是否需要被多个 Agent 复用？
- [ ] 这个逻辑放在 MCP Server 里还是 Agent 层？（判断标准：是否需要动态决策）
- [ ] 是否遵循了"MCP 是管道，Skill 是水流，Agent 是调度员"的分层原则？

### Server 实现
- [ ] 选择 stdio 还是 SSE 传输方式？（本地工具 vs 远程服务）
- [ ] 工具描述是否清晰？（LLM 能否理解何时使用该工具）
- [ ] 错误处理是否完善？（返回标准错误格式而非抛异常）

### 授权设计
- [ ] Token 由客户端还是 Server 管理？（推荐：客户端管理，Server 验证）
- [ ] Token 如何安全传递？（环境变量 > 命令行参数）
- [ ] Token 过期如何处理？（Server 返回明确错误码）

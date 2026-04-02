# Spec Coding 与 Harness Engineering 概述

## 什么是 Spec Coding？

**Spec Coding**（Specification-Driven Development / SDD，规约驱动开发）是一种以结构化规范（Spec）为核心开发工件的方法论。它将传统的 "Prompt → Code" 转变为 "Idea → Spec → Code → Validation" 的完整流程。

### 核心哲学

1. **Spec 是源代码**: 代码是 Spec 的输出，Spec 是唯一的真相来源（Single Source of Truth）
2. **行为在实现前定义**: API 合约、数据模式、验收标准在写第一行代码前已锁定
3. **Spec 即测试框架**: 自动化测试从 Spec 生成或与 Spec 验证

### 开发模式对比

```
传统开发:        Idea → Code → (Maybe) Docs
                实现定义行为，后期补文档

AI 辅助开发:     Prompt → Code → Patch bugs → Explain later
                快速生成但缺乏结构，后期维护困难

Spec Coding:     Idea → Spec → Design → Tasks → Code → Tests
                规范先行，可追溯，可验证
```

### Spec Coding 解决的问题

| 问题 | 传统方式 | Spec Coding 方式 |
|------|---------|-----------------|
| 需求模糊 | 口头沟通、Slack 片段 | 结构化 GWT 规范 |
| 接口不一致 | 代码即文档 | OpenAPI/TypeSpec 先定义 |
| 测试滞后 | 开发后补测试 | 从 Spec 生成测试 |
| 追溯困难 | 翻 Git 历史 | 需求 ID 贯穿始终 |
| AI 输出失控 | Prompt 工程 | Spec 作为上下文约束 |

---

## 什么是 Harness Engineering？

**Harness Engineering**（马具工程）是构建使 AI Agent 在生产环境中可靠的"马具"（Harness）的学科。它不是在优化模型或提示词，而是构建围绕模型的完整基础设施层。

> 类比：就像马的缰绳和马鞍（Harness）控制强大的动物一样，Harness Engineering 控制 AI Agent 的行为。

### 五个核心组件

#### 1. 上下文工程 (Context Engineering)

**定义**: 组装 AI 在每个步骤需要的精确信息

**关键问题**:
- AI 知道什么？（What does the agent know?）
- 上下文是否太多或太少？
- 信息是否相关？

**最佳实践**:
```yaml
context:
  include_files:
    - specs/openapi.yaml      # API 规范
    - specs/adr/*.md          # 架构决策
    - src/types/*.h           # 类型定义
  exclude_patterns:
    - "*_test.cpp"            # 排除测试文件
    - "build/"                # 排除构建产物
  max_tokens: 8000            # 限制上下文大小
```

**案例**: Vercel 将 Agent 可用工具从 15 个减至 2 个，准确性从 80% → 100%

#### 2. 工具编排 (Tool Orchestration)

**定义**: 管理外部系统交互、输入验证、错误处理

**关键问题**:
- 工具调用失败怎么办？（API 500 错误、超时）
- 参数验证谁来做？
- 如何防止错误传播？

**核心功能**:
- 输入验证（参数类型、范围检查）
- 输出解析（格式验证、字段检查）
- 错误处理（重试、降级、熔断）
- 超时管理（避免无限等待）

**代码示例**:
```cpp
class ToolOrchestrator {
public:
    template<typename Tool, typename... Args>
    auto call_with_retry(Tool& tool, Args&&... args) {
        for (int attempt = 0; attempt < max_retries_; ++attempt) {
            try {
                auto result = tool.call(std::forward<Args>(args)...);
                if (validate_output(result)) {
                    return result;
                }
            } catch (const TimeoutException& e) {
                if (attempt == max_retries_ - 1) throw;
                std::this_thread::sleep_for(backoff_delay(attempt));
            }
        }
    }
};
```

#### 3. 验证循环 (Verification Loops)

**定义**: 每一步检查输出后再继续

**这是最高 ROI 的组件！**

**验证类型**:
| 类型 | 延迟 | 用途 | 示例 |
|------|------|------|------|
| Schema 验证 | 50-150μs | 检查数据格式 | JSON Schema 验证 |
| 语义验证 | 1 LLM call | 检查逻辑正确性 | 代码审查 Agent |
| 测试验证 | 可变 | 功能正确性 | 单元测试、集成测试 |

**效果**: LangChain 添加验证循环后，任务完成率从 52.8% → 66.5%（模型未改变）

**实现模式**:
```python
def run_agent_with_verification(task, tools):
    while not task.is_complete():
        action = agent.plan(context, tools)
        result = execute_tool(action)
        
        # 验证循环
        verification = verify_output(result, action.expected_schema)
        if not verification.passed:
            if verification.retry_recommended:
                result = retry_with_backoff(action)
            else:
                return TaskResult(status="failed", reason=verification.reason)
        
        context = update_context(context, result)
```

#### 4. 成本封套 (Cost Envelope)

**定义**: 每任务预算上限，防止失控

**为什么重要**:
- 防止无限重试导致的 API 费用爆炸
- 异常行为的早期信号
- 资源使用的可预测性

**配置示例**:
```yaml
cost:
  max_tokens_per_task: 100000
  max_api_calls_per_task: 50
  alert_threshold: 0.8  # 80% 时警告
  
  # 不同任务类型不同预算
  budgets:
    simple_refactor:
      max_tokens: 10000
    complex_feature:
      max_tokens: 50000
```

**案例**: 某团队无成本控制的 Agent 一夜之间产生 $2,400 账单（正常 $180/天）

#### 5. 可观测性 (Observability)

**定义**: 结构化执行轨迹和持续评估

**核心要素**:

**执行轨迹 (Traces)**:
```json
{
  "trace_id": "uuid",
  "timestamp": "2024-03-15T10:30:00Z",
  "steps": [
    {
      "step": 1,
      "action": "read_file",
      "input": "src/main.cpp",
      "output": "...",
      "tokens_used": 1500,
      "duration_ms": 120,
      "verification": "passed"
    }
  ],
  "total_tokens": 5000,
  "total_duration_ms": 2000,
  "status": "completed"
}
```

**持续评估**:
```python
class EvaluationPipeline:
    def run_daily(self):
        metrics = {
            'task_completion_rate': run_test_suite(),
            'avg_cost_per_task': calculate_cost(),
            'latency_p99': measure_latency(),
            'error_rate': count_errors()
        }
        
        # 检查回归
        if metrics['task_completion_rate'] < baseline * 0.95:
            alert("Performance regression detected!")
```

---

## Spec Coding + Harness Engineering 的关系

```
┌─────────────────────────────────────────────────────────────┐
│                      Spec Coding                            │
│                  回答"构建什么"                              │
│                                                             │
│  • 需求定义 (GWT)                                           │
│  • 架构设计 (ADR)                                           │
│  • 接口规范 (OpenAPI)                                       │
│  • 任务分解 (Tasks)                                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Harness Engineering                       │
│                 回答"如何可靠构建"                          │
│                                                             │
│  • 上下文工程 (Context)                                     │
│  • 工具编排 (Tools)                                         │
│  • 验证循环 (Verification)                                  │
│  • 成本控制 (Cost)                                          │
│  • 可观测性 (Observability)                                 │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                        输出                                 │
│                                                             │
│              可靠、可维护、可验证的软件                     │
└─────────────────────────────────────────────────────────────┘
```

**简单来说**:
- **Spec Coding** = 蓝图和施工规范
- **Harness Engineering** = 施工安全设施和质量检查流程

---

## 工程落地案例

### OpenAI Codex
- 3 名工程师在 5 个月内生成 100 万+ 行代码
- **关键**: 沙盒环境 + 验证循环 + 结构化工具访问
- **启示**: Harness 设计是 80% 因素，模型本身只有 20%

### Stripe Minions
- 每周合并 1,000+ PR，零人工编写代码
- **关键**: Spec 定义 → 代码生成 → 自动测试 → PR 合并完整链路
- **启示**: 全自动化的 Spec-Driven 流程

### Vercel
- 将 Agent 工具从 15 个减至 2 个
- 准确性: 80% → 100%
- Token 消耗: -37%
- 速度: 3.5x 提升
- **启示**: 精简工具，精确上下文

### LangChain
- Harness 工程改进使任务完成率: 52.8% → 66.5%
- **关键**: 模型未改变，仅改进 Harness
- **启示**: Harness > Model

### Ministry of Programming (MOP)
- 采用 SDD 标准后：30-50% 的后期缺陷减少
- QA 周期显著缩短
- **关键**: `/mop:generate-spec` 和 `/mop:implement-spec` 标准命令
- **启示**: 标准化流程比工具更重要

### GitHub Spec Kit
- 开源工具包支持 Spec-Driven Development
- 命令流: `/constitution` → `/tasks` → `/implement`
- **案例**: 一个航班时间构建完整 Next.js 播客网站
- **启示**: Spec 可以极大地加速开发

---

## 为什么现在需要这套方法论？

### AI 编程的痛点

1. **"Vibe Coding" 问题**
   - 快速但不稳定
   - 看起来像完成但边界情况未处理
   - 缺乏架构一致性

2. **上下文漂移**
   - AI 在多轮对话中丢失关键约束
   - 早期决策被遗忘
   - 实现偏离原始意图

3. **验证缺失**
   - AI 生成的代码未经测试
   - 错误静默传播
   - 生产环境才暴露问题

4. **成本失控**
   - Token 消耗不可预测
   - 无限重试导致账单爆炸
   - 效率无法度量

### Spec Coding + Harness Engineering 的解决之道

| 痛点 | 解决方案 |
|------|---------|
| Vibe Coding | Spec 先行，约束 AI 输出空间 |
| 上下文漂移 | 结构化的 Spec 作为持久上下文 |
| 验证缺失 | Harness 验证循环强制检查 |
| 成本失控 | Cost Envelope 硬性限制 |

---

## 下一章

接下来，我们将详细介绍 **Spec Coding 方法论框架**，包括：
- 金字塔三层结构
- Four Pillars（四大支柱）
- MECE 五阶段方法论

→ [继续阅读: 02-framework](../02-framework/README.md)

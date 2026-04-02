# 多Agent Spec Coding 框架设计

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Multi-Agent Spec Coding Framework                     │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────────────┤
│ Agent 1  │ Agent 2  │ Agent 3  │ Agent 4  │ Agent 5  │         Agent 6          │
│ 需求澄清  │ 框架设计  │ Spec撰写 │ Harness  │ 并行编码  │        自证测试           │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────────────────────┤
│ 交互式访谈│ 系统架构  │ FR/NFR   │ 验证流程  │ Code Gen │      测试生成+执行        │
│ 概念建模  │ 模块划分  │ ADR详细  │ CI/CD   │ 代码审查  │      覆盖率检查          │
│ 可行性评估│ 接口设计  │ 任务分解  │ 工具链   │ 可追溯   │      回归测试           │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────────────┘
     │           │           │           │           │              │
     ▼           ▼           ▼           ▼           ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              统一状态管理 (State Store)                           │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐         │
│  │ Idea   │  │Framework│  │ Specs  │  │Harness │  │ Code   │  │ Test   │         │
│  │ 原始想法 │  │ 框架设计 │  │ 规范文档 │  │ 配置   │  │ 代码   │  │ 测试结果 │         │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               人机交互检查点 (Human-in-the-loop)                 │
│                   [确认]      [确认]      [确认]      [确认]      [确认]         │
│                      ●─────────●─────────●─────────●─────────●                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 流程说明

```
用户输入 ──► Agent 1: 需求澄清 ──► [人工确认] 
                                         │
                                         ▼
Agent 2: 框架设计 ──► [人工确认]
    │                    │
    │ (高层面架构)       │ (确认模块划分)
    │                    ▼
    │              Agent 3: Spec撰写 ──► [人工确认]
    │                    │
    │                    │ (详细规范)
    │                    ▼
    └────────────► Agent 4: Harness配置 ──► [人工确认]
                              │
                              ▼
                        Agent 5: 并行编码 ──► [人工监督]
                              │
                              ▼
                        Agent 6: 自证测试 ──► [人工确认]
                              │
                              ▼
                          项目完成
```

---

## Agent 1: 需求澄清智能体 (Requirement Clarification Agent)

### 职责
- 通过交互式对话澄清用户需求
- 构建领域模型和概念图
- 识别技术约束和业务约束
- 评估技术可行性

### 工作流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   用户输入    │────►│  需求澄清Agent │────►│  结构化需求   │
│  (模糊想法)   │     │              │     │  (明确需求)   │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  交互式提问  │
                    │  - 是什么？  │
                    │  - 为什么？  │
                    │  - 谁使用？  │
                    │  - 何时用？  │
                    │  - 如何做？  │
                    └──────────────┘
```

### Prompt 模板

```yaml
# agent-1-clarify.prompt
role: |
  你是一位资深需求分析师，擅长通过系统化提问澄清模糊需求。
  你的目标是将用户的初步想法转化为结构化的需求理解。

workflow:
  - step: 理解业务场景
    questions:
      - "这个系统/功能的业务背景是什么？"
      - "解决了什么痛点？"
      - "没有它的时候用户如何解决这个问题？"
  
  - step: 识别利益相关者
    questions:
      - "谁将使用这个系统？"
      - "他们的技术背景如何？"
      - "谁是最终决策者？"
  
  - step: 功能范围界定
    questions:
      - "核心功能是什么？"
      - "必须有的功能（Must have）有哪些？"
      - "可有可无的功能（Nice to have）有哪些？"
      - "明确不包含的功能有哪些？"
  
  - step: 约束条件识别
    questions:
      - "有什么技术约束？（语言、框架、平台）"
      - "有什么性能要求？"
      - "有什么安全/合规要求？"
      - "时间和资源约束是什么？"
  
  - step: 验收标准
    questions:
      - "如何定义'完成'？"
      - "如何验证功能正确性？"
      - "有什么具体的数字指标？"

output_format: |
  ## Clarified Requirements
  
  ### 1. Business Context
  - Background: [业务背景]
  - Problem: [要解决的问题]
  - Value: [带来的价值]
  
  ### 2. Stakeholders
  - Primary Users: [主要用户]
  - Secondary Users: [次要用户]
  - Decision Makers: [决策者]
  
  ### 3. Functional Requirements
  - Core Features: [核心功能列表]
  - Must Have: [必须有]
  - Nice to Have: [可以有]
  - Out of Scope: [明确不做]
  
  ### 4. Constraints
  - Technical: [技术约束]
  - Performance: [性能要求]
  - Security: [安全要求]
  - Resources: [资源约束]
  
  ### 5. Acceptance Criteria
  - Success Metrics: [成功指标]
  - Verification Method: [验证方法]
```

### 输出示例

```markdown
## Clarified Requirements: TaskQueue System

### 1. Business Context
- Background: 需要类似 iOS GCD 的 C++ 任务队列系统
- Problem: 现有线程池库不够灵活，缺乏队列类型区分
- Value: 提供高效、易用的并发编程抽象

### 2. Stakeholders
- Primary Users: C++ 游戏/多媒体开发者
- Secondary Users: 后端服务开发者
- Decision Makers: 技术主管

### 3. Functional Requirements
- Core Features:
  1. 三种队列类型（Serial/Concurrent/Parallel）
  2. 同步/异步/延时任务执行
  3. 任务组管理
- Must Have: 线程安全、异常安全、可配置线程数
- Nice to Have: 任务优先级、取消机制
- Out of Scope: 跨进程通信、持久化任务

### 4. Constraints
- Technical: C++17, Header-only 或静态库
- Performance: P99 延迟 < 10μs
- Security: 不需要（库级别）
- Resources: 单项目维护

### 5. Acceptance Criteria
- Success Metrics: 100万 tasks/sec 吞吐
- Verification: 单元测试覆盖率 > 80%
```

---

## Agent 2: 框架设计智能体 (Framework Design Agent)

### 职责
- 设计系统整体架构和模块组成
- 确定模块间接口和依赖关系
- 进行技术选型
- 绘制架构图和模块关系图
- 与用户沟通确认框架设计

### 为什么需要框架设计Agent？

在需求澄清和详细Spec之间插入框架设计环节，可以避免：
1. **过早细化**：在没有确定整体架构前就陷入实现细节
2. **返工风险**：高层架构问题在详细设计阶段才发现
3. **模块不一致**：各模块设计者在缺乏统一框架下各自为战
4. **技术债务**：关键技术选型未经充分评估

### 工作流

```
┌──────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  结构化需求   │────►│  框架设计Agent   │────►│   框架设计文档   │
│ (Clarified)  │     │                 │     │  (高层面架构)   │
└──────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                    ┌─────────────────────────┐
                    │      框架设计流水线       │
                    │  1. 系统架构图            │
                    │  2. 模块划分              │
                    │  3. 模块间接口定义         │
                    │  4. 技术选型              │
                    │  5. 架构决策初稿          │
                    └─────────────────────────┘
```

### Prompt 模板

```yaml
# agent-2-framework.prompt
role: |
  你是一位资深系统架构师，擅长将需求转化为清晰的系统架构设计。
  你的任务是在不陷入实现细节的情况下，定义系统的整体结构、模块划分和技术方向。
  你需要与用户进行多轮沟通，确保架构设计符合业务需求和技术约束。

input: |
  ## Clarified Requirements
  [来自 Agent 1 的输出]

workflow:
  - step: 系统架构设计
    actions:
      - 确定架构风格（分层/微服务/事件驱动/管道等）
      - 绘制系统整体架构图
      - 识别核心组件和边界
      - 定义数据流向
    
    output: |
      ## System Architecture
      
      ### Architecture Style
      [选择的架构风格及理由]
      
      ### Architecture Diagram
      ```plantuml
      [PlantUML 架构图]
      ```
      
      ### Core Components
      | Component | Responsibility | Notes |
      |-----------|----------------|-------|
      | [组件名] | [职责] | [备注] |
      
      ### Data Flow
      [描述数据如何在组件间流动]
  
  - step: 模块划分
    actions:
      - 根据功能内聚性划分子模块
      - 定义模块间依赖关系
      - 识别共享模块和公共接口
      - 确定模块的优先级
    
    output: |
      ## Module Design
      
      ### Module Hierarchy
      ```
      System/
      ├── Module A/
      │   ├── Submodule A1
      │   └── Submodule A2
      ├── Module B/
      └── Shared/
          └── Common Utils
      ```
      
      ### Module Dependencies
      ```plantuml
      [PlantUML 依赖图]
      ```
      
      ### Module Interfaces
      | Module | Provided Interfaces | Required Interfaces |
      |--------|--------------------|--------------------|
      | [模块] | [提供的接口] | [依赖的接口] |
  
  - step: 技术选型
    actions:
      - 编程语言和版本
      - 核心框架和库
      - 数据存储方案
      - 通信机制
      - 部署架构
    
    output: |
      ## Technology Stack
      
      ### Core Technologies
      | Layer | Technology | Version | Rationale |
      |-------|------------|---------|-----------|
      | Language | [语言] | [版本] | [选择理由] |
      | Framework | [框架] | [版本] | [选择理由] |
      | Storage | [存储] | [版本] | [选择理由] |
      
      ### Key Libraries
      - [库名]: [用途] ([是否必需])
      
      ### Deployment Architecture
      [单机/分布式/云原生等]
  
  - step: 架构决策初稿
    actions:
      - 识别关键架构决策点
      - 对每个决策提供2-3个备选方案
      - 初步推荐方案（待详细ADR细化）
    
    output: |
      ## Key Architectural Decisions (Draft)
      
      ### Decision 1: [决策主题]
      **Context**: [背景]
      **Options**:
      1. [方案A]: [描述] - Pros: [优点] Cons: [缺点]
      2. [方案B]: [描述] - Pros: [优点] Cons: [缺点]
      3. [方案C]: [描述] - Pros: [优点] Cons: [缺点]
      **Preliminary Recommendation**: [初步推荐]
      **Open Questions**: [待确认问题]

interaction_protocol: |
  ## 与用户交互流程
  
  Round 1: Present initial framework design
    - 展示系统架构图
    - 解释模块划分逻辑
    - 说明技术选型理由
    - 提出开放性问题
  
  Round 2: Address user feedback
    - 根据用户反馈调整架构
    - 澄清用户的疑虑
    - 确认或修改技术选型
  
  Round 3: Final confirmation
    - 展示修订后的设计
    - 获得用户最终确认
    - 标记确认的设计为基线

output_structure: |
  framework/
  ├── README.md                    # 框架设计总览
  ├── system-architecture.md       # 系统架构
  ├── module-design.md             # 模块设计
  ├── technology-stack.md          # 技术选型
  ├── architecture-decisions-draft.md  # 架构决策初稿
  └── diagrams/
      ├── system-overview.png      # 系统架构图
      ├── module-dependencies.png  # 模块依赖图
      └── data-flow.png            # 数据流图
```

### 输出示例

```markdown
# TaskQueue Framework Design

## System Architecture

### Architecture Style
**分层架构 + 策略模式**
- 选择理由：清晰的关注点分离，易于测试和扩展

### Architecture Diagram
```plantuml
@startuml
package "Frontend Layer" {
  [TaskQueue] 
  [TaskGroup]
}

package "Operator Layer" {
  [TaskOperator]
  [TaskBarrierOperator]
  [TaskDelayOperator]
}

package "Backend Layer" {
  [IQueueImpl]
  [SerialQueueImpl]
  [ConcurrentQueueImpl]
}

package "ThreadPool Layer" {
  [IThreadPool]
  [ConcurrencyThreadPool]
  [WorkThread]
}

Frontend Layer ..> Operator Layer
Operator Layer ..> Backend Layer
Backend Layer ..> ThreadPool Layer
@enduml
```

### Core Components

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| TaskQueue | 对外API接口 | 支持三种队列类型 |
| TaskOperator | 操作抽象 | 支持Barrier、Delay等 |
| IQueueImpl | 队列实现接口 | 策略模式 |
| IThreadPool | 线程池管理 | 支持动态调整 |

## Module Design

### Module Hierarchy
```
taskqueue/
├── frontend/          # 对外API
│   ├── TaskQueue
│   └── TaskGroup
├── operator/          # 操作符
│   ├── TaskOperator
│   ├── TaskBarrierOperator
│   └── TaskDelayOperator
├── backend/           # 队列实现
│   ├── IQueueImpl
│   ├── SerialQueueImpl
│   └── ConcurrentQueueImpl
└── threadpool/        # 线程池
    ├── IThreadPool
    ├── ConcurrencyThreadPool
    └── WorkThread
```

### Module Dependencies
- frontend → operator → backend → threadpool
- 不允许反向依赖
- shared/ 模块可被所有层依赖

## Technology Stack

### Core Technologies
| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| Language | C++ | 17 | 现代C++特性，广泛支持 |
| Build | CMake | 3.14+ | 跨平台标准 |
| Test | Google Test | 1.10+ | 成熟生态 |

### Key Libraries
- 标准库 `<thread>`, `<future>`, `<chrono>`
- 无第三方依赖（核心库）

## Key Architectural Decisions (Draft)

### Decision 1: 队列实现策略
**Context**: 需要支持三种不同的队列行为
**Options**:
1. 继承模式：基类IQueueImpl，派生具体实现 - Pros: 多态灵活 Cons: 虚函数开销
2. 模板策略：编译时确定策略 - Pros: 零开销 Cons: 代码膨胀，二进制大
3. 组合模式：队列包含策略对象 - Pros: 灵活组合 Cons: 稍微复杂

**Preliminary Recommendation**: 继承模式（方案1）
- 理由：虚函数开销在微秒级可接受，灵活性更重要

### Decision 2: 线程池共享策略
**Context**: SerialQueue需要独占线程，Concurrent需要共享
**Options**:
1. 统一线程池：所有队列共享 - Pros: 资源高效 Cons: Serial难以保证
2. 分离线程池：Serial独立，Concurrent共享 - Pros: 语义清晰 Cons: 资源可能浪费
3. 混合模式：Serial初始独立，可退化为共享 - Pros: 平衡 Cons: 复杂

**Preliminary Recommendation**: 分离线程池（方案2）

## Open Questions

1. 是否需要支持跨平台（Windows/Linux/macOS）？
2. 是否Header-only还是编译为库？
3. 异常处理策略：终止vs传播？
```

---

## Agent 3: Spec 撰写智能体 (Spec Authoring Agent)

### 职责
- 根据澄清后的需求生成标准 Spec 文档
- 创建 FR（功能需求）、NFR（非功能需求）
- 编写 ADR（架构决策记录）
- 设计接口规范（OpenAPI/TypeSpec）
- 分解任务并生成依赖图

### 工作流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  结构化需求   │────►│  Spec撰写Agent│────►│   Spec文档   │
│  (Clarified) │     │              │     │   (标准格式)  │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │     Spec 生成流水线      │
              │  1. FR-XXX 功能需求文档   │
              │  2. NFR-XXX 非功能需求    │
              │  3. ADR-XXX 架构决策     │
              │  4. Interface 接口规范   │
              │  5. Tasks 任务分解       │
              └─────────────────────────┘
```

### Prompt 模板

```yaml
# agent-2-spec.prompt
role: |
  你是一位技术架构师和规格说明专家。
  你的任务是将澄清的需求转化为符合 SDD（Spec-Driven Development）
  方法论的标准规范文档。

input: |
  ## Clarified Requirements
  [来自 Agent 1 的输出]

workflow:
  - step: 生成功能需求 (FR)
    template: |
      # FR-{XXX}: [功能标题]
      
      ## Metadata
      - ID: FR-{DOMAIN}-{NUMBER}
      - Type: Functional Requirement
      - Priority: P0/P1/P2/P3
      
      ## Description
      [一句话描述]
      
      ## GWT Specifications
      ### Scenario 1: [正向场景]
      ```gherkin
      Given [前置条件]
      When [动作]
      Then [预期结果]
      ```
      
      ### Scenario 2: [边界场景]
      ...
      
      ## Interface Requirements
      [接口方法定义]
      
      ## Constraints
      [约束条件]
      
      ## Traceability
      [追溯信息]
    
  - step: 生成架构决策 (ADR)
    template: |
      # ADR-{XXX}: [决策标题]
      
      ## Status
      - Proposed / Accepted / Deprecated
      
      ## Context
      [背景信息]
      
      ## Decision
      [做出的决策]
      
      ## Consequences
      ### Positive
      - [好处]
      ### Negative
      - [代价]
      
      ## Alternatives Considered
      ### Alternative 1
      - Pros: [优点]
      - Cons: [缺点]
      - Why Rejected: [拒绝原因]
    
  - step: 生成接口规范
    template: |
      # Interface Specification
      
      ## Types
      [类型定义]
      
      ## Classes
      ### ClassName
      [类定义]
      
      ## Methods
      ### method_name
      [方法签名、参数、返回值]
    
  - step: 任务分解
    template: |
      # Task Decomposition
      
      tasks:
        - id: T-001
          title: [任务标题]
          requirement_ref: [FR-XXX]
          dependencies: [T-XXX]
          estimated_hours: [工时]
          acceptance_criteria: [验收标准]

output_structure: |
  specs/
  ├── requirements/
  │   ├── FR-001-*.md
  │   ├── FR-002-*.md
  │   └── NFR-001-*.md
  ├── architecture/
  │   ├── ADR-001-*.md
  │   └── ADR-002-*.md
  ├── interface/
  │   └── *.openapi.yaml
  └── tasks/
      └── task-breakdown.yaml
```

### 关键能力

1. **ID 自动生成**: 根据需求类型和域自动生成唯一 ID
2. **GWT 场景生成**: 自动补充正向、边界、异常场景
3. **ADR 备选方案**: 每个 ADR 至少提供 2 个备选方案
4. **依赖分析**: 识别任务间的依赖关系
5. **一致性检查**: 确保 Spec 间相互引用正确

---

## Agent 4: Harness 配置智能体 (Harness Configuration Agent)

### 职责
- 根据 Spec 设计验证流程
- 生成 harness.yaml 配置
- 配置 CI/CD 流水线
- 设置代码质量检查规则
- 配置成本控制和可观测性

### 工作流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Spec文档    │────►│ Harness配置Agent│────►│  配置文件    │
│  (已确认)     │     │              │     │  (可执行)    │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │    Harness 配置流水线    │
              │  1. 验证步骤设计          │
              │  2. 工具选择             │
              │  3. 成本预算             │
              │  4. 监控指标             │
              │  5. CI/CD 配置           │
              └─────────────────────────┘
```

### Prompt 模板

```yaml
# agent-3-harness.prompt
role: |
  你是一位 DevOps 和 Harness Engineering 专家。
  你的任务是为项目设计完整的验证和质量保障体系。

input: |
  ## Spec Documents
  [来自 Agent 2 的 Spec 文档]
  
  ## Technology Stack
  [技术栈信息]

workflow:
  - step: 分析验证需求
    actions:
      - 阅读所有 FR 和 NFR
      - 识别关键验收标准
      - 确定必须通过的检查点
  
  - step: 设计验证步骤
    questions:
      - "需要哪些编译检查？"
      - "需要哪些静态分析？"
      - "需要哪些测试？（单元/集成/性能）"
      - "需要哪些代码质量检查？"
      - "需要可追溯性检查吗？"
  
  - step: 配置工具链
    decisions:
      - 编译器: [gcc/clang/msvc]
      - 构建系统: [cmake/bazel/make]
      - 测试框架: [gtest/catch2/doctest]
      - 静态分析: [clang-tidy/cppcheck]
      - 代码格式: [clang-format]
      - 覆盖率: [gcovr/lcov]
  
  - step: 设计成本控制
    config:
      max_tokens_per_task: [预算]
      max_api_calls_per_task: [预算]
      alert_threshold: [0.8]
  
  - step: 配置可观测性
    metrics:
      - task_completion_rate
      - verification_pass_rate
      - tokens_used
      - duration_ms

output_files:
  - harness.yaml:
      description: "主 Harness 配置"
  - .github/workflows/ci.yml:
      description: "CI/CD 配置"
  - scripts/check_requirement_tags.py:
      description: "可追溯性检查脚本"
  - scripts/validate_spec.py:
      description: "Spec 验证脚本"
```

### 输出示例

```yaml
# harness.yaml
harness:
  name: taskqueue-project
  version: 1.0.0
  
  context:
    max_tokens: 10000
    include_files:
      - specs/requirements/*.md
      - specs/architecture/*.md
    exclude_patterns:
      - "*_test.cpp"
      - "build/"
  
  verification:
    steps:
      - name: compile
        command: "cmake --build build"
        must_pass: true
        
      - name: unit_tests
        command: "cd build && ctest"
        must_pass: true
        min_coverage: 80
        
      - name: traceability_check
        command: "python scripts/check_requirement_tags.py src/"
        must_pass: true
  
  cost:
    max_tokens_per_task: 50000
    alert_threshold: 0.8
  
  observability:
    log_level: debug
    metrics:
      - tokens_used
      - verification_pass_rate
```

---

## Agent 5: 多Agent并行编码智能体 (Parallel Coding Agents)

### 职责
- 多个 Agent 并行执行不同任务
- 每个 Agent 负责特定模块的实现
- 遵守 Harness 验证规则
- 保持代码可追溯性
- 模块间协作和接口对齐

### 架构

```
                           ┌──────────────┐
                           │  任务调度器   │
                           │  (Orchestrator)│
                           └──────┬───────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
       ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
       │  Coding Agent │   │  Coding Agent │   │  Coding Agent │
       │     #1       │   │     #2       │   │     #3       │
       │ Frontend API │   │  Backend Impl │   │ Thread Pool  │
       └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                                  ▼
                           ┌──────────────┐
                           │  代码审查Agent │
                           │  (Reviewer)   │
                           └──────────────┘
```

### Agent 类型

#### 4.1 功能实现 Agent

```yaml
# agent-4a-implement.prompt
role: |
  你是一位专业的 C++ 开发工程师。
  你的任务是根据 Spec 实现特定功能模块。

input:
  spec: [相关 FR 文档]
  adr: [相关 ADR 文档]
  harness: [Harness 配置]
  task: [具体任务]

workflow:
  - step: 理解需求
    read:
      - 相关 FR 文档
      - 相关 ADR 文档
      - 接口规范
  
  - step: 生成测试
    action: "先生成单元测试，定义期望行为"
  
  - step: 实现代码
    action: "实现功能代码，确保通过测试"
    requirements:
      - 添加 @require 标签
      - 添加 @adr 标签
      - 完整的文档注释
      - 异常安全
      - 线程安全（如需要）
  
  - step: 本地验证
    run:
      - compile
      - unit_tests
      - lint
  
  - step: 提交代码
    format: |
      {type}({scope}): {subject}
      
      {body}
      
      Refs: {FR-XXX}, {ADR-XXX}
```

#### 4.2 代码审查 Agent

```yaml
# agent-4b-review.prompt
role: |
  你是一位严格的代码审查员。
  你的任务是检查代码是否符合 Spec 和 Harness 要求。

checklist:
  traceability:
    - "是否有 @require 标签？"
    - "是否有 @adr 标签？"
    - "提交信息是否引用需求？"
  
  quality:
    - "代码是否编译无警告？"
    - "是否通过所有测试？"
    - "代码覆盖率是否达标？"
    - "是否符合代码风格？"
  
  architecture:
    - "是否遵循 ADR 的架构决策？"
    - "接口设计是否合理？"
    - "模块间依赖是否正确？"
  
  robustness:
    - "异常处理是否完整？"
    - "边界情况是否处理？"
    - "资源管理是否正确？"

decision:
  - if: "所有检查通过"
    action: "Approve"
  - elif: "有轻微问题"
    action: "Comment with suggestions"
  - else:
    action: "Request changes"
```

#### 4.3 集成协调 Agent

```yaml
# agent-4c-integrate.prompt
role: |
  你是一位系统集成专家。
  你的任务是协调多个 Agent 的工作，确保模块间接口一致。

tasks:
  - 检查模块间接口兼容性
  - 解决命名冲突
  - 统一错误处理方式
  - 确保头文件依赖正确
  - 生成集成测试
```

### 并行执行策略

```python
# 伪代码示例
class ParallelCodingOrchestrator:
    def __init__(self, tasks, agents):
        self.tasks = tasks
        self.agents = agents
        self.results = {}
    
    async def execute_parallel(self):
        # 1. 分析任务依赖
        dependency_graph = build_dependency_graph(self.tasks)
        
        # 2. 按波次执行
        for wave in topological_sort_by_depth(dependency_graph):
            # 同一波次的任务并行执行
            wave_tasks = [t for t in self.tasks if t.id in wave]
            
            results = await asyncio.gather(*[
                self.assign_to_agent(task) 
                for task in wave_tasks
            ])
            
            # 3. 验证本波次结果
            for result in results:
                if not self.harness.verify(result):
                    # 验证失败，让 Agent 修复
                    result = await self.agent_fix(result)
            
            self.results.update(dict(zip(wave, results)))
        
        return self.results
    
    async def assign_to_agent(self, task):
        # 根据任务类型选择 Agent
        agent = select_agent_by_expertise(task.type)
        
        # 准备上下文
        context = {
            'spec': load_spec(task.requirement_ref),
            'adr': load_adr(task.adr_ref),
            'dependencies': [
                self.results[dep] 
                for dep in task.dependencies
            ]
        }
        
        # 执行编码任务
        return await agent.code(task, context)
```

---

## Agent 6: 自证测试智能体 (Self-Certification Agent)

### 职责
- 根据 Spec 生成测试用例
- 执行全面的测试套件
- 生成测试报告
- 验证覆盖率
- 执行回归测试

### 工作流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   完整代码    │────►│  自证测试Agent │────►│  测试报告    │
│   + Spec     │     │              │     │  (通过/失败)  │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │    测试执行流水线        │
              │  1. 生成测试用例          │
              │  2. 执行单元测试          │
              │  3. 执行集成测试          │
              │  4. 执行性能测试          │
              │  5. 覆盖率检查            │
              │  6. 可追溯性验证          │
              └─────────────────────────┘
```

### Prompt 模板

```yaml
# agent-5-test.prompt
role: |
  你是一位测试专家和 QA 工程师。
  你的任务是确保代码完全符合 Spec 要求，通过全面的测试验证。

input:
  specs: [所有 FR/NFR 文档]
  code: [实现代码]
  harness: [Harness 配置]

workflow:
  - step: 生成测试用例
    method: |
      对每个 FR 文档：
        - 提取 GWT 场景
        - 生成对应的测试用例
        - 覆盖正向、边界、异常场景
  
  - step: 执行测试
    phases:
      - name: Unit Tests
        command: "./build/run_unit_tests"
        required: true
        
      - name: Integration Tests
        command: "./build/run_integration_tests"
        required: true
        
      - name: Performance Tests
        command: "./build/run_benchmarks"
        required: false
        
      - name: Stress Tests
        command: "./build/run_stress_tests"
        required: false
  
  - step: 覆盖率检查
    tools:
      - gcovr
      - llvm-cov
    threshold:
      line: 80%
      branch: 70%
      function: 90%
  
  - step: 可追溯性验证
    checks:
      - "每个 FR 都有对应的测试"
      - "每个测试都可追溯到 FR"
      - "代码中的 @require 标签有效"
  
  - step: 生成报告
    format: |
      # Test Certification Report
      
      ## Summary
      - Status: [PASS/FAIL]
      - Date: [timestamp]
      - Code Version: [git commit]
      
      ## Test Results
      | Category | Passed | Failed | Skipped | Coverage |
      |----------|--------|--------|---------|----------|
      | Unit     | X      | Y      | Z       | A%       |
      | Integration | X   | Y      | Z       | N/A      |
      | Performance | X   | Y      | Z       | N/A      |
      
      ## Traceability Matrix
      | FR ID | Test Cases | Status |
      |-------|------------|--------|
      | FR-001 | test_a, test_b | ✅ |
      
      ## Issues Found
      [如果有失败的测试，列出详情]
```

### 关键能力

1. **测试生成**: 从 GWT 场景自动生成测试代码
2. **变异测试**: 验证测试的有效性（mutation testing）
3. **模糊测试**: 发现边界情况问题
4. **性能基准**: 验证是否满足 NFR 要求
5. **可追溯矩阵**: 生成 FR ↔ Test 的映射表

---

## 统一状态管理

### 状态存储设计

```yaml
# state-store.yaml
project:
  id: "uuid"
  name: "TaskQueue System"
  created_at: "2024-03-15T10:00:00Z"
  status: "in_progress"  # in_progress | review | completed

  phases:
  clarify:
    status: "completed"
    output:
      clarified_requirements: "phases/01-clarify/requirements.md"
    reviewed_by: "user"
    reviewed_at: "2024-03-15T11:00:00Z"
  
  framework:
    status: "completed"
    output:
      framework_design_dir: "phases/02-framework/"
      system_architecture: "phases/02-framework/system-architecture.md"
      module_design: "phases/02-framework/module-design.md"
      technology_stack: "phases/02-framework/technology-stack.md"
      architecture_decisions_draft: "phases/02-framework/architecture-decisions-draft.md"
    reviewed_by: "user"
    reviewed_at: "2024-03-15T12:30:00Z"
    revisions:
      - version: 1
        changes: "Initial design"
      - version: 2
        changes: "Adjusted module boundaries based on user feedback"
  
  spec:
    status: "completed"
    output:
      requirements_dir: "specs/requirements/"
      architecture_dir: "specs/architecture/"
      interface_dir: "specs/interface/"
      tasks_file: "specs/tasks/breakdown.yaml"
    reviewed_by: "user"
    reviewed_at: "2024-03-15T14:00:00Z"
    based_on_framework: "phases/02-framework/"  # 追溯链接
  
  harness:
    status: "completed"
    output:
      harness_config: "harness.yaml"
      ci_config: ".github/workflows/ci.yml"
      scripts_dir: "scripts/"
    reviewed_by: "user"
    reviewed_at: "2024-03-15T15:00:00Z"
  
  develop:
    status: "in_progress"
    agents:
      - id: "agent-4a"
        name: "Frontend API Agent"
        task: "T-001"
        status: "coding"
        progress: 60
      - id: "agent-4b"
        name: "Backend Impl Agent"
        task: "T-002"
        status: "reviewing"
        progress: 90
    
  certify:
    status: "pending"
    test_results: null

codebase:
  src_dir: "src/"
  test_dir: "tests/"
  last_commit: "abc123"
  coverage: 75%

metrics:
  tokens_used: 45000
  api_calls: 25
  duration_minutes: 120
```

---

## Shared Architecture Context（共享架构上下文）

为了解决多Agent协作中的**架构一致性和模块连接**问题，我们引入共享架构上下文机制。

### 为什么需要共享架构上下文？

在多Agent并行工作时：
- Agent 2 设计的架构需要被后续所有Agent遵守
- Agent 5 的多个子Agent需要实时同步模块间的依赖关系
- 接口变更需要自动通知到所有相关Agent
- 需要自动检测架构违规（如层间非法依赖）

### 三层Context架构

```yaml
shared_architecture_context:
  # Layer 1: Master Framework (只读基线)
  # 由 Agent 2 创建，作为整个系统的架构契约
  master_framework:
    layers:
      frontend:
        responsibility: "对外API"
        scope:
          allowed: ["参数验证", "错误转换"]
          forbidden: ["直接操作线程"]
      backend:
        responsibility: "队列实现"
        interfaces:
          exports: ["IQueueImpl"]
    
  # Layer 2: Global State (实时状态)
  # 所有Agent实时更新和读取
  global_state:
    modules:
      frontend:
        status: "implementing"
        progress: 60
        assigned_agent: "Agent-5a"
      backend:
        status: "testing"
        progress: 90
    
  # Layer 3: Event Bus (跨Agent通信)
  # 支持事件驱动的松耦合协作
  event_bus:
    subscriptions:
      - event: "interface_changed"
        subscribers: ["Agent-4", "Agent-5", "Agent-6"]
      - event: "dependency_conflict"
        subscribers: ["Agent-3", "Agent-7"]
```

### Context Provider 设计

为所有Agent提供统一的上下文访问接口：

```cpp
class ContextProvider {
public:
    // 读取 Master Framework（只读）
    MasterFramework getMasterFramework() const;
    LayerDefinition getLayer(const std::string& name) const;
    bool isDependencyAllowed(const std::string& consumer, const std::string& provider) const;
    
    // 读写 Global State
    ModuleState getModuleState(const std::string& module) const;
    void updateModuleState(const std::string& module, const ModuleState& state);
    
    // Event Bus 操作
    void publishEvent(const Event& event);
    void subscribeEvent(const std::string& event_type, EventHandler handler);
    
    // 一致性检查
    std::vector<ConsistencyViolation> checkConsistency(const CodeArtifact& artifact) const;
};
```

### 集成到Agent工作流

```
Agent 2 (框架设计)
    │
    └──► 创建 Master Framework ──► 写入 Context ──► 设为只读
    │
Agent 3 (任务分解)
    │
    └──► 读取 Context 中的层定义 ──► 分解任务 ──► 注册依赖关系
    │
Agent 4 (Spec撰写)
    │
    └──► 验证接口符合架构约束 ──► 如有变更，发布 interface_changed 事件
    │
Agent 5 (并行编码) - 多个子Agent
    │
    ├── Agent-5a: 读取 frontend 层定义 → 检查职责边界 → 更新进度到 Context
    ├── Agent-5b: 读取 backend 层定义 → 监听依赖接口变化 → 自动适配
    └── Agent-5c: 订阅事件 → 当 IQueueImpl 变更时调整实现
    │
Agent 6 (测试)
    │
    └──► 验证所有模块遵守系统契约
```

### 详细设计文档

完整的共享架构上下文设计方案见：
📄 **[shared-architecture-context-design.md](./shared-architecture-context-design.md)**

包含：
- 完整的Context Schema定义
- Context Provider 接口设计
- Agent使用Context的代码示例
- 一致性规则引擎
- 同步机制设计
- 实施路径建议

---

## 人机交互检查点

### 检查点设计

```
[用户] ──► [Agent 1: 需求澄清] ──► [人工确认] 
                                        │
                                        ▼
[用户] ◄── [Agent 3: Spec撰写] ◄── [触发执行]
   │
   ▼ (Review)
[用户确认] ──► [Agent 4: Harness配置] ──► [人工确认]
                                                 │
                                                 ▼
[用户] ◄── [Agent 5: 并行编码] ◄── [触发执行]
   │
   ▼ (Monitor)
[用户监督] ──► [Agent 6: 自证测试] ──► [人工确认]
                                                │
                                                ▼
                                          [项目完成]
```

### 交互界面设计

每个检查点提供：
1. **概览**: 当前阶段产出摘要
2. **详情**: 完整的文档/代码/配置
3. **对比**: 与上一阶段的变更
4. **操作**: 
   - ✅ Approve (确认并继续)
   - 📝 Request Changes (要求修改，附带反馈)
   - ⏸️ Pause (暂停，稍后继续)
   - ❌ Abort (中止项目)

---

## 实现路线图

### Phase 1: 基础框架 (2周)
- [ ] 实现 Agent 1 (需求澄清)
- [ ] 实现 Agent 2 (框架设计)
- [ ] 实现状态管理系统
- [ ] 实现人机交互界面

### Phase 2: Spec与Harness (2周)
- [ ] 实现 Agent 3 (Spec撰写)
- [ ] 实现 Agent 4 (Harness配置)
- [ ] 实现框架到Spec的转换逻辑
- [ ] 实现Spec验证逻辑

### Phase 3: 执行框架 (2周)
- [ ] 实现 Agent 5 (并行编码)
- [ ] 实现任务调度器
- [ ] 实现代码审查流程
- [ ] 实现模块间协调机制

### Phase 4: 验证框架 (1周)
- [ ] 实现 Agent 6 (自证测试)
- [ ] 实现测试生成器
- [ ] 实现覆盖率检查
- [ ] 实现可追溯性验证

### Phase 4: 集成优化 (1周)
- [ ] 端到端测试
- [ ] 性能优化
- [ ] 用户体验优化
- [ ] 文档完善

---

## 技术栈建议

### 后端
- **语言**: Python 3.9+ (AI Agent) + Go/Rust (高性能组件)
- **框架**: FastAPI (API 服务)
- **数据库**: PostgreSQL (状态存储) + Redis (缓存)
- **消息队列**: Redis/RabbitMQ (Agent 间通信)
- **工作流**: Temporal/Cadence (复杂流程编排)

### AI/ML
- **LLM**: Claude/GPT-4 (主 Agent)
- **Embedding**: text-embedding-3 (语义搜索)
- **Vector DB**: Pinecone/Weaviate (Spec 检索)

### 前端
- **框架**: React/Vue
- **组件**: 自定义 Review 界面
- **实时通信**: WebSocket

### DevOps
- **容器**: Docker + Kubernetes
- **CI/CD**: GitHub Actions/GitLab CI
- **监控**: Prometheus + Grafana

---

## 下一步行动

### 方案A: 完整流程验证 (推荐)
1. **优先实现 Agent 1 + Agent 2 + Agent 3**：验证从需求→框架→详细Spec的完整流程
2. **使用 TaskQueue 项目作为试点**：已有完整 Spec 可供对比验证
3. **重点验证框架设计Agent的价值**：测试是否减少后续返工

### 方案B: 快速原型
1. **仅实现 Agent 1 (需求澄清)**：先验证需求澄清的效果
2. **与人工框架设计对比**：评估 Agent 2 的自动化程度
3. **逐步扩展**：确认价值后再添加后续 Agent

### 方案C: 已有Spec的逆向测试
1. **使用现有的 TaskQueue Spec**
2. **先实现 Agent 3 (Spec撰写)**：测试从框架到详细Spec的转换
3. **反向验证**：让 Agent 生成框架，与现有设计对比

### 关键问题待验证
- 框架设计 Agent 是否能有效减少返工？
- 用户是否愿意在框架层面多花一轮 Review 时间？
- 框架设计到详细 Spec 的自动化程度有多高？

需要我详细展开某个 Agent 的具体实现，或者先创建 **Agent 1 + Agent 2** 的原型来验证核心流程？

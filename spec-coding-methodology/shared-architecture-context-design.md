# 共享架构上下文（Shared Architecture Context）设计

## 核心理念

将架构治理从"独立的Agent"转变为**所有Agent共享的上下文基础设施**，通过统一的Context Provider为整个多Agent系统提供：
- 主框架定义（只读基线）
- 实时全局状态
- 跨Agent通信机制
- 一致性规则引擎

```
┌─────────────────────────────────────────────────────────────┐
│                  Shared Architecture Context                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Master       │  │ Global       │  │ Cross-Agent  │      │
│  │ Framework    │  │ State        │  │ Communication│      │
│  │ (只读基线)    │  │ (实时状态)    │  │ (事件总线)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ Agent 1 │◄────►│ Agent 2 │◄────►│ Agent 3 │
    │ 需求澄清 │      │ 框架设计 │      │ 任务分解 │
    └─────────┘      └─────────┘      └─────────┘
         │                 │                 │
         │    (通过Context同步)              │
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ Agent 4 │◄────►│ Agent 5 │◄────►│ Agent 6 │
    │ Spec撰写 │      │ Harness  │      │ 并行编码 │
    └─────────┘      └─────────┘      └─────────┘
```

---

## 一、Context 架构

### 1.1 三层Context结构

```yaml
# shared-context.yaml
shared_architecture_context:
  # ========== Layer 1: Master Framework (主框架定义) ==========
  # 由 Agent 2 创建，之后只读，作为整个系统的基线
  master_framework:
    version: "1.0.0"
    created_by: "Agent-2"
    created_at: "2024-03-15T12:00:00Z"
    
    # 系统级元数据
    system:
      name: "TaskQueueSystem"
      type: "library"  # library | service | application
      architecture_style: "layered"
      
    # 层定义（职责边界，所有Agent必须遵守）
    layers:
      frontend:
        order: 1
        responsibility: "对外API，业务逻辑编排"
        scope:
          allowed:
            - "提供用户友好的API"
            - "参数验证"
            - "错误转换"
          forbidden:
            - "直接操作线程"
            - "直接操作队列"
            - "了解具体队列实现"
        interfaces:
          exports:
            - name: "TaskQueue"
              stability: "stable"
            - name: "TaskGroup"
              stability: "stable"
          imports_from:
            - layer: "operator"
              contract: "TaskOperator abstraction"
            - layer: "backend"
              contract: "IQueueImpl interface"
              
      operator:
        order: 2
        responsibility: "任务操作抽象，支持扩展"
        scope:
          allowed:
            - "定义TaskOperator基类"
            - "实现各种操作符（Barrier/Delay）"
            - "组合模式支持"
          forbidden:
            - "了解队列实现细节"
            - "直接调度线程"
        interfaces:
          exports:
            - name: "TaskOperator"
            - name: "TaskBarrierOperator"
            - name: "TaskDelayOperator"
          imports_from:
            - layer: "shared"
              contract: "common utilities"
              
      backend:
        order: 3
        responsibility: "队列实现，任务调度"
        scope:
          allowed:
            - "实现IQueueImpl接口"
            - "管理任务队列"
            - "调用线程池"
          forbidden:
            - "暴露给用户"
            - "包含业务逻辑"
        interfaces:
          exports:
            - name: "IQueueImpl"
            - name: "SerialQueueImpl"
            - name: "ConcurrentQueueImpl"
          imports_from:
            - layer: "threadpool"
              contract: "IThreadPool interface"
              
      threadpool:
        order: 4
        responsibility: "线程生命周期管理"
        scope:
          allowed:
            - "管理线程池"
            - "执行任务"
            - "资源回收"
          forbidden:
            - "了解任务内容"
            - "了解业务逻辑"
        interfaces:
          exports:
            - name: "IThreadPool"
            - name: "ConcurrencyThreadPool"
            - name: "WorkThread"
            
      shared:
        order: 0  # 基础层，被所有层依赖
        responsibility: "共享基础设施"
        scope:
          allowed:
            - "定义通用工具"
            - "定义错误码"
            - "定义日志接口"
        interfaces:
          exports:
            - name: "ErrorCode"
            - name: "ILogger"
            - name: "common_utils"
    
    # 系统级契约（所有模块必须遵守）
    system_contracts:
      error_handling:
        pattern: "exception_based"
        base_exception: "QueueException"
        requirement: "所有错误必须包装为QueueException或其子类"
        
      memory_management:
        pattern: "smart_pointer"
        requirement: "使用std::unique_ptr进行所有权转移，禁止裸指针"
        
      thread_safety:
        requirement: "公共API必须线程安全，内部实现文档化线程安全级别"
        
      logging:
        format: "structured"
        requirement: "所有模块使用统一的ILogger接口"
        
    # 模块间通信契约
    inter_layer_communication:
      frontend_to_backend:
        pattern: "interface_injection"
        data_flow: "unidirectional"
        coupling: "loose"
        
      backend_to_threadpool:
        pattern: "callback"
        data_flow: "bidirectional"
        coupling: "loose"

  # ========== Layer 2: Global State (实时全局状态) ==========
  # 所有Agent实时读写，反映当前系统状态
  global_state:
    version: "auto_increment"
    last_updated: "2024-03-15T16:00:00Z"
    updated_by: "Agent-5a"
    
    # 模块状态跟踪
    modules:
      frontend:
        status: "implementing"  # design | implementing | testing | stable | deprecated
        version: "0.1.0"
        assigned_agent: "Agent-5a"
        progress_percentage: 60
        last_activity: "2024-03-15T15:30:00Z"
        
        # 当前正在处理的任务
        current_tasks:
          - task_id: "T-001"
            title: "实现 TaskQueue 核心类"
            status: "coding"
            
        # 已完成的任务
        completed_tasks:
          - task_id: "T-000"
            title: "设计 TaskQueue 接口"
            
        # 待处理的问题
        pending_issues:
          - issue_id: "ISS-001"
            description: "async 返回值类型需要确认"
            blocking: true
            
      backend:
        status: "testing"
        version: "0.1.0"
        assigned_agent: "Agent-5b"
        progress_percentage: 90
        
      threadpool:
        status: "stable"
        version: "1.0.0"
        assigned_agent: "Agent-5c"
        progress_percentage: 100
    
    # 依赖状态实时跟踪
    dependencies:
      - id: "dep-001"
        consumer: "frontend"
        provider: "backend"
        interface: "IQueueImpl"
        consumer_version: "0.1.0"
        provider_version: "0.1.0"
        status: "compatible"  # compatible | breaking_change | deprecated | not_implemented
        last_verified: "2024-03-15T15:00:00Z"
        
      - id: "dep-002"
        consumer: "backend"
        provider: "threadpool"
        interface: "IThreadPool"
        status: "compatible"
        
    # 接口兼容性矩阵
    compatibility_matrix:
      IQueueImpl:
        versions:
          "1.0.0":
            consumers:
              frontend: ["1.0.0", "1.0.1"]
          "1.0.1":
            consumers:
              frontend: ["1.0.1"]
            breaking_changes:
              - "移除废弃的submit_sync方法"
              
    # 资源分配
    resources:
      active_agents: 4
      task_queue_depth: 12
      estimated_completion: "2024-03-20"

  # ========== Layer 3: Cross-Agent Communication (跨Agent通信) ==========
  # 事件驱动，支持Agent间的松耦合协作
  event_bus:
    # 事件订阅表
    subscriptions:
      - event: "interface_changed"
        subscribers:
          - agent: "Agent-4"  # Spec撰写Agent需要更新文档
            priority: high
          - agent: "Agent-6"  # 编码Agent需要调整实现
            priority: high
          - agent: "Agent-7"  # 测试Agent需要更新测试
            priority: medium
            
      - event: "new_module_registered"
        subscribers:
          - agent: "all"
            action: "update_dependency_graph"
            
      - event: "dependency_conflict"
        subscribers:
          - agent: "Agent-3"  # 任务分解Agent需要调整
          - agent: "Agent-7"  # 架构治理Agent需要介入
            
      - event: "coding_blocked"
        subscribers:
          - agent: "Agent-5"  # Spec撰写Agent需要提供澄清
            
      - event: "test_failure"
        subscribers:
          - agent: "responsible_coding_agent"
          - agent: "Agent-7"  # 测试Agent分析失败原因
            
    # 事件历史（用于追踪和审计）
    event_history:
      - timestamp: "2024-03-15T10:00:00Z"
        event: "master_framework_created"
        by: "Agent-2"
        payload:
          version: "1.0.0"
          
      - timestamp: "2024-03-15T14:30:00Z"
        event: "interface_changed"
        by: "Agent-4"
        payload:
          layer: "frontend"
          interface: "TaskQueue"
          change_type: "method_added"
          method: "notify()"
          
      - timestamp: "2024-03-15T15:00:00Z"
        event: "dependency_conflict_detected"
        by: "Agent-6a"
        payload:
          conflict_type: "version_mismatch"
          consumer: "frontend"
          expected: "backend@1.0.0"
          actual: "backend@1.0.1"

  # ========== Layer 4: Consistency Rules Engine (一致性规则引擎) ==========
  # 自动验证所有Agent的输出是否符合架构约束
  consistency_rules:
    # 命名规范
    naming_conventions:
      - rule: "class_name"
        pattern: "PascalCase"
        applies_to: ["class", "struct"]
        
      - rule: "method_name"
        pattern: "camelCase"
        applies_to: ["method", "function"]
        
      - rule: "private_member"
        pattern: "trailing_underscore_"
        applies_to: ["private_field"]
    
    # 架构约束
    architectural_constraints:
      - rule: "layer_dependency"
        description: "高层不能依赖低层实现，只能依赖接口"
        check: |
          frontend.imports 必须只包含 operator.* 和 backend.IQueueImpl
          不能包含 backend.SerialQueueImpl 等具体实现
          
      - rule: "interface_stability"
        description: "stable接口不能在没有版本升级的情况下修改"
        check: |
          如果 interface.stability == "stable":
            禁止删除方法
            禁止修改方法签名
            允许添加带有默认实现的新方法
            
      - rule: "error_handling"
        description: "所有错误必须使用统一的错误体系"
        check: |
          所有抛出的异常必须继承自 QueueException
          错误码必须在 ErrorCode 枚举中定义
          
    # 自动修复建议
    auto_fixes:
      - trigger: "naming_violation"
        action: "suggest_rename"
        
      - trigger: "missing_include_guard"
        action: "add_pragma_once"

---

## 二、Context Provider 实现

### 2.1 Context Provider 接口

```cpp
// shared/context_provider.h
#pragma once

#include <string>
#include <functional>
#include <optional>

namespace taskqueue {
namespace shared {

/**
 * @brief 共享架构上下文提供者
 * @context_layer shared
 * 
 * 为所有Agent提供统一的架构上下文访问接口。
 * 实现为单例模式，确保全局状态一致性。
 */
class ContextProvider {
public:
    static ContextProvider& instance();
    
    // ========== Master Framework 访问（只读） ==========
    
    /**
     * @brief 获取主框架定义
     * @require FR-XXX
     * @context_read master_framework
     */
    MasterFramework getMasterFramework() const;
    
    /**
     * @brief 获取指定层的定义
     * @param layer_name 层名称
     * @return 层定义，如果不存在返回nullopt
     */
    std::optional<LayerDefinition> getLayer(const std::string& layer_name) const;
    
    /**
     * @brief 检查模块间依赖是否合法
     * @param consumer 消费层
     * @param provider 提供层
     * @return 是否允许依赖
     */
    bool isDependencyAllowed(const std::string& consumer, 
                            const std::string& provider) const;
    
    // ========== Global State 访问（读写） ==========
    
    /**
     * @brief 获取模块当前状态
     * @context_read_write global_state.modules
     */
    ModuleState getModuleState(const std::string& module_name) const;
    
    /**
     * @brief 更新模块状态
     * @context_read_write global_state.modules
     */
    void updateModuleState(const std::string& module_name, 
                          const ModuleState& state);
    
    /**
     * @brief 获取依赖状态
     * @context_read global_state.dependencies
     */
    std::vector<DependencyState> getDependencyStates() const;
    
    /**
     * @brief 注册新的依赖关系
     * @context_write global_state.dependencies
     */
    void registerDependency(const DependencyState& dependency);
    
    // ========== Event Bus 操作 ==========
    
    /**
     * @brief 发布事件
     * @context_write event_bus
     */
    void publishEvent(const Event& event);
    
    /**
     * @brief 订阅事件
     * @context_read event_bus.subscriptions
     */
    void subscribeEvent(const std::string& event_type, 
                       EventHandler handler);
    
    // ========== Consistency Check ==========
    
    /**
     * @brief 验证代码是否符合架构约束
     * @context_read consistency_rules
     */
    std::vector<ConsistencyViolation> checkConsistency(
        const CodeArtifact& artifact) const;
    
    /**
     * @brief 获取自动修复建议
     */
    std::vector<AutoFixSuggestion> getAutoFixes(
        const ConsistencyViolation& violation) const;

private:
    ContextProvider();
    ~ContextProvider() = default;
    
    // 禁用拷贝
    ContextProvider(const ContextProvider&) = delete;
    ContextProvider& operator=(const ContextProvider&) = delete;
    
    class Impl;
    std::unique_ptr<Impl> pImpl_;
};

} // namespace shared
} // namespace taskqueue
```

### 2.2 Agent 使用 Context 的示例

```cpp
// Agent 2: 框架设计 Agent 创建 Master Framework
void FrameworkDesignAgent::execute() {
    auto& context = ContextProvider::instance();
    
    // 创建主框架定义
    MasterFramework framework;
    framework.version = "1.0.0";
    
    // 定义层
    LayerDefinition frontend;
    frontend.name = "frontend";
    frontend.order = 1;
    frontend.responsibility = "对外API，业务逻辑编排";
    frontend.scope.allowed = {"提供用户友好的API", "参数验证"};
    frontend.scope.forbidden = {"直接操作线程", "直接操作队列"};
    
    // ... 定义其他层
    
    // 写入 Master Framework（初始化后变为只读）
    context.initializeMasterFramework(framework);
    
    // 发布事件通知其他Agent
    Event event;
    event.type = "master_framework_created";
    event.payload = framework;
    context.publishEvent(event);
}

// Agent 5: 编码 Agent 读取 Context 进行开发
void CodingAgent::implementTask(const Task& task) {
    auto& context = ContextProvider::instance();
    
    // 读取 Master Framework 了解职责边界
    auto layer = context.getLayer(task.module);
    if (!layer) {
        throw std::runtime_error("Unknown module: " + task.module);
    }
    
    // 检查职责边界
    for (const auto& action : task.planned_actions) {
        if (!layer->isActionAllowed(action)) {
            // 违反了架构约束！
            ConsistencyViolation violation;
            violation.rule = "layer_responsibility";
            violation.description = action + " not allowed in " + task.module;
            
            // 发布阻塞事件
            Event blocked_event;
            blocked_event.type = "coding_blocked";
            blocked_event.payload = violation;
            context.publishEvent(blocked_event);
            
            return;
        }
    }
    
    // 检查依赖的接口是否可用
    for (const auto& dep : task.dependencies) {
        auto dep_state = context.getDependencyStatus(dep.provider, dep.interface);
        if (dep_state.status != "compatible") {
            // 依赖不兼容，需要协调
            Event conflict_event;
            conflict_event.type = "dependency_conflict";
            conflict_event.payload = dep;
            context.publishEvent(conflict_event);
        }
    }
    
    // 执行编码...
    
    // 更新模块状态
    ModuleState state;
    state.status = "implementing";
    state.progress_percentage = 50;
    state.current_task = task.id;
    context.updateModuleState(task.module, state);
}

// Agent 6: 另一个编码 Agent 监听事件并响应
void AnotherCodingAgent::setup() {
    auto& context = ContextProvider::instance();
    
    // 订阅接口变更事件
    context.subscribeEvent("interface_changed", 
        [this](const Event& event) {
            const auto& payload = event.payload;
            if (payload.layer == "backend" && 
                payload.interface == "IQueueImpl") {
                // 我依赖的接口变了，需要调整实现
                this->adaptToInterfaceChange(payload);
            }
        });
}
```

---

## 三、上下文同步机制

### 3.1 同步策略

```yaml
# 上下文同步配置
context_sync:
  # Master Framework: 强一致性，写后只读
  master_framework:
    consistency: "strong"
    replication: "all_agents"
    persistence: "git_committed"  # 作为代码提交
    
  # Global State: 最终一致性，允许临时不一致
  global_state:
    consistency: "eventual"
    replication: "all_agents"
    persistence: "real_time_sync"
    conflict_resolution: "last_write_wins_with_timestamp"
    
  # Event Bus: 至少一次交付
  event_bus:
    delivery_guarantee: "at_least_once"
    ordering: "partial"  # 同一Agent的事件有序
    persistence: "in_memory_with_log"

---

## 四、一致性验证示例

### 4.1 自动检测架构违规

```python
# context/consistency_checker.py

class ConsistencyChecker:
    def __init__(self, context_provider):
        self.context = context_provider
        
    def check_code_artifact(self, artifact):
        """检查代码是否符合架构约束"""
        violations = []
        
        # 检查1: 层依赖是否合法
        for dependency in artifact.dependencies:
            if not self.context.is_dependency_allowed(
                artifact.layer, 
                dependency.layer
            ):
                violations.append({
                    'rule': 'layer_dependency',
                    'severity': 'error',
                    'message': f"{artifact.layer} cannot depend on {dependency.layer}",
                    'location': artifact.location,
                    'suggestion': f"Use interface from {dependency.layer} instead"
                })
        
        # 检查2: 是否访问了禁止的API
        layer_def = self.context.get_layer(artifact.layer)
        for api_call in artifact.api_calls:
            if api_call in layer_def.scope.forbidden:
                violations.append({
                    'rule': 'scope_violation',
                    'severity': 'error',
                    'message': f"{api_call} is forbidden in {artifact.layer}",
                    'suggestion': layer_def.get_alternative(api_call)
                })
        
        # 检查3: 接口稳定性
        for interface_change in artifact.interface_changes:
            interface_def = self.context.get_interface(interface_change.name)
            if interface_def.stability == 'stable' and interface_change.is_breaking:
                violations.append({
                    'rule': 'interface_stability',
                    'severity': 'warning',
                    'message': f"Breaking change to stable interface {interface_change.name}",
                    'suggestion': "Bump major version or use deprecation cycle"
                })
        
        return violations
```

### 4.2 实时冲突检测

```
场景：两个Agent同时修改同一个接口

时间线:
T1: Agent-5a 读取 IQueueImpl v1.0.0
T2: Agent-5b 读取 IQueueImpl v1.0.0
T3: Agent-5a 添加方法 submit_async() → 提交到 Context
T4: Agent-5b 添加方法 submit_sync() → 提交到 Context
T5: Context 检测到并发修改
T6: Context 合并两个修改（如果没有冲突）
T7: Context 发布 interface_changed 事件
T8: Agent-5c 收到通知，更新其实现
```

---

## 五、与现有Agent框架集成

### 5.1 更新后的Agent流程

```
Agent 1: 需求澄清
    │
    ▼
Agent 2: 框架设计
    │ ──► 创建 Master Framework，写入 Context
    │ ──► 发布 master_framework_created 事件
    ▼
Agent 3: 任务分解
    │ ──► 读取 Master Framework
    │ ──► 根据层边界分解任务
    │ ──► 注册任务依赖关系到 Context
    ▼
Agent 4: Spec撰写
    │ ──► 读取层定义和职责边界
    │ ──► 验证接口设计符合架构约束
    │ ──► 如有变更，发布 interface_changed 事件
    ▼
Agent 5: 并行编码（多个子Agent）
    │ ──► 每个子Agent读取Context
    │ ──► 实时检查职责边界
    │ ──► 监听依赖模块的事件
    │ ──► 更新模块进度到Context
    ▼
Agent 6: 测试
    │ ──► 验证所有模块遵守系统契约
    │ ──► 检查接口兼容性
    ▼
完成
```

### 5.2 人机交互检查点更新

```
检查点1: 需求澄清完成
    └─► 用户确认 Clarified Requirements

检查点2: 框架设计完成  ⭐ 关键检查点
    ├─► Context 中 Master Framework 只读化
    ├─► 用户确认系统架构
    └─► 所有Agent订阅相关事件

检查点3: 任务分解完成
    ├─► 用户确认任务粒度和依赖关系
    └─► 任务依赖关系写入 Context

检查点4: Spec撰写完成
    ├─► 自动验证符合 Master Framework
    ├─► 用户确认详细规范
    └─► 如有接口变更，自动通知相关Agent

检查点5: Harness配置完成
    └─► 用户确认验证流程

检查点6: 编码监控（持续）
    ├─► 实时显示各模块进度
    ├─► 自动检测架构违规并警告
    ├─► 依赖冲突时自动协调
    └─► 用户可干预调整

检查点7: 测试完成
    ├─► 自动验证追溯性
    ├─► 用户确认质量达标
    └─► 项目完成
```

---

## 六、实施建议

### 6.1 渐进式实施路径

**Phase 1: 基础Context（1周）**
- 实现 Master Framework 层（只读）
- Agent 2 创建，其他Agent读取
- 基本的层边界检查

**Phase 2: 全局状态（1周）**
- 添加 Global State 层
- 实现模块进度跟踪
- 依赖关系可视化

**Phase 3: 事件驱动（1周）**
- 添加 Event Bus
- 实现 Agent 间通信
- 接口变更通知

**Phase 4: 一致性引擎（1周）**
- 添加规则引擎
- 自动架构检查
- 自动修复建议

### 6.2 技术选型

```yaml
implementation:
  storage:
    master_framework: "Git + YAML"  # 版本控制
    global_state: "Redis"          # 实时同步
    event_bus: "Redis Pub/Sub"     # 消息传递
    
  language:
    context_provider: "C++17"      # 与项目一致
    consistency_checker: "Python"  # 灵活性
    
  sync_protocol:
    type: "WebSocket"
    fallback: "HTTP Polling"
    
  persistence:
    master_framework: "Git repository"
    global_state: "Redis RDB + AOF"
    event_history: "Time-series DB (InfluxDB)"
```

---

这个方案的核心优势是：**架构治理不再是瓶颈，而是流动的血液，贯穿整个多Agent系统。所有Agent都在同一个架构上下文中协作，确保最终产出的一致性。**

需要我详细展开某个部分，或者开始为 TaskQueue 项目创建具体的 Context 实现吗？
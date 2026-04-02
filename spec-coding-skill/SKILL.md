---
name: spec-coding-multi-agent
description: |
  Multi-Agent Spec-Driven Development workflow automation. 
  Triggers a complete 7-agent pipeline for requirement clarification, 
  framework design, task decomposition, spec authoring, harness configuration, 
  parallel coding, and self-certification testing.
  
  Use when:
  - Starting a new software project with clear requirements
  - Need comprehensive spec documentation before coding
  - Want AI-assisted architecture design and code generation
  - Require traceability from requirements to tests
  - Working with complex multi-module systems
---

# Spec Coding Multi-Agent Skill

## Quick Start

### Option 1: Using Skill Command (Recommended)

```bash
# Start the complete workflow
/spec-coding init --project-name "MyProject" --language cpp

# Or with options
/spec-coding init \
  --project-name "TaskQueue" \
  --language cpp \
  --complexity complex \
  --output ./my-project
```

### Option 2: Using Agent Directly

```bash
# Call the orchestrator agent directly
Agent spec-coding-orchestrator --input '{
  "project_name": "TaskQueue",
  "description": "A C++ task queue library",
  "language": "cpp",
  "project_path": "./TaskQueue"
}'
```

### Option 3: Step-by-Step Execution

Run each phase individually for more control:

```bash
# Phase 1: Clarify requirements
Agent agent-1-clarify --input '{
  "project_name": "TaskQueue",
  "description": "A C++ task queue library",
  "language": "cpp",
  "project_path": "./TaskQueue"
}'

# Phase 2: Design framework (after reviewing Phase 1 output)
Agent agent-2-framework --input '{
  "project_name": "TaskQueue",
  "project_path": "./TaskQueue",
  "context_snapshot": {...}
}'

# Continue with phases 3-7...
```

## Overview

This skill orchestrates 7 specialized agents to deliver a complete, production-ready software project:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPEC CODING WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                             │
│  │   Skill Entry   │  /spec-coding init --project-name "X"       │
│  │   Point         │                                             │
│  └────────┬────────┘                                             │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                             │
│  │  Orchestrator   │  Coordinates 7-phase workflow               │
│  │    Agent        │  Manages shared context                     │
│  └────────┬────────┘                                             │
│           │                                                      │
│    ┌──────┴──────┬────────┬────────┬────────┬────────┬────────┐ │
│    ▼             ▼        ▼        ▼        ▼        ▼        ▼ │
│ ┌─────┐    ┌────────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ │
│ │Agent│───▶│ Agent  │▶│Agent│▶│Agent│▶│Agent│▶│Agent│▶│Agent│ │
│ │  1  │    │   2    │ │  3  │ │  4  │ │  5  │ │  6  │ │  7  │ │
│ └─────┘    └────────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ │
│ Clarify    Framework  Decomp  Spec   Harness  Coding  Certify  │
│    │           │        │      │       │       │       │      │
│    └───────────┴────────┴──────┴───────┴───────┴───────┘      │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                           │
│              │   Shared Context    │  state.yaml               │
│              │   (state, progress) │  requirements/            │
│              └─────────────────────┘  framework/               │
│                                       specs/                   │
│                                       src/                     │
│                                       tests/                   │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture

The system uses a **hierarchical multi-agent architecture**:

1. **Skill Layer**: Entry point via `/spec-coding` command
2. **Orchestrator Layer**: `spec-coding-orchestrator.agent` manages the workflow
3. **Phase Layer**: 7 specialized agents execute specific phases
4. **Sub-Agent Layer**: Phase 6 spawns multiple coding sub-agents

### Agent Definitions

All agents are defined in the `agents/` directory:

| Agent File | Purpose | Input | Output |
|------------|---------|-------|--------|
| `spec-coding-orchestrator.agent` | Workflow orchestration | Project config | Complete project |
| `agent-1-clarify.agent` | Requirement clarification | Description | clarified.md |
| `agent-2-framework.agent` | Architecture design | Requirements | framework/*.md |
| `agent-3-decompose.agent` | Task decomposition | Framework | decomposition.yaml |
| `agent-4-spec.agent` | Spec authoring | Tasks | specs/**/*.md |
| `agent-5-harness.agent` | Test harness setup | Specs | harness.yaml |
| `agent-6-coding.agent` | Code implementation | Specs + Harness | src/ |
| `agent-7-certify.agent` | Certification | Code + Specs | CERTIFICATION_REPORT.md |

Each agent produces artifacts that are stored in a **Shared Architecture Context**, ensuring consistency and traceability throughout the pipeline.

## Agent Architecture

### How It Works

```
User Request
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│  1. SKILL LAYER                                               │
│     - Parse command line arguments                           │
│     - Validate inputs                                        │
│     - Create project structure                               │
│     - Invoke Orchestrator Agent                              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  2. ORCHESTRATOR LAYER                                        │
│     spec-coding-orchestrator.agent                           │
│     - Plans 7-phase execution (sequential thinking)          │
│     - Manages shared context (state.yaml)                    │
│     - Calls Phase Agents in sequence                         │
│     - Handles human checkpoints                              │
└────────────────────────┬─────────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
┌───────────────┐ ┌──────────┐ ┌──────────────┐
│ Phase Agent 1 │ │   ...    │ │ Phase Agent 7│
│ (Clarify)     │ │          │ │ (Certify)    │
└───────┬───────┘ └──────────┘ └──────┬───────┘
        │                             │
        │    ┌──────────────────┐     │
        └───▶│  Shared Context  │◀────┘
             │  (state.yaml)    │
             └──────────────────┘
```

### Agent Communication

Agents communicate through the **Shared Architecture Context**:

1. **Input**: Each agent receives:
   - `project_name`, `project_path`, `language`
   - `context_snapshot`: Full state.yaml content
   - Phase-specific inputs (e.g., previous phase outputs)

2. **Output**: Each agent produces:
   - Artifacts (files in project directory)
   - JSON return with status and artifact list
   - Updated context entries

3. **State Management**:
   ```yaml
   # context/state.yaml
   project:
     name: "TaskQueue"
     current_phase: "coding"
   phases:
     clarify: {status: "completed", output: {...}}
     framework: {status: "completed", output: {...}}
     coding: {status: "in_progress", output: {...}}
   ```

### Calling Convention

#### From Skill to Orchestrator:
```json
{
  "project_name": "TaskQueue",
  "description": "A C++ task queue library",
  "language": "cpp",
  "project_path": "./TaskQueue",
  "features": "async, sync, thread pool",
  "constraints": "C++17, header-only option"
}
```

#### From Orchestrator to Phase Agent:
```json
{
  "phase": "framework",
  "project_name": "TaskQueue",
  "project_path": "./TaskQueue",
  "language": "cpp",
  "context_snapshot": { /* full state.yaml */ },
  "previous_outputs": {
    "clarify": { /* Phase 1 output */ }
  }
}
```

### Tool Usage

Each agent has access to specific tools:

| Tool | Usage |
|------|-------|
| `read_file` | Read specs, context, source code |
| `create_file` | Write output artifacts |
| `search_replace` | Update existing files |
| `Agent` | Spawn sub-agents (Phase 6) |
| `run_in_terminal` | Execute build/test commands |
| `ask_user_question` | Human-in-the-loop (Phase 1) |
| `todo_write` | Track multi-step tasks |
| `mcp_sequential-thinking_sequentialthinking` | Plan complex work |

## Workflow Details

### Phase 1: Requirement Clarification (Agent 1)
**Purpose**: Transform vague ideas into structured requirements

**Input**: User's initial project description
**Output**: `context/requirements/clarified.md`

**Process**:
1. Conduct interactive interview with user
2. Identify stakeholders and constraints
3. Define functional and non-functional requirements
4. Establish acceptance criteria

**Human Checkpoint**: ✅ Review and confirm clarified requirements

---

### Phase 2: Framework Design (Agent 2)
**Purpose**: Create high-level architecture before implementation details

**Input**: Clarified requirements from Phase 1
**Output**: 
- `context/framework/system-architecture.md`
- `context/framework/module-design.md`
- `context/framework/technology-stack.md`
- `context/framework/architecture-decisions-draft.md`

**Process**:
1. Select architecture style (layered/microservices/event-driven)
2. Define module boundaries and responsibilities
3. Design inter-module interfaces
4. Make technology choices with alternatives

**Human Checkpoint**: ✅ Review and confirm system architecture

---

### Phase 3: Task Decomposition (Agent 3)
**Purpose**: Break modules into executable tasks with dependency analysis

**Input**: Framework design from Phase 2
**Output**: `context/tasks/decomposition.yaml`

**Process**:
1. Decompose each module into atomic tasks (2-8 hours each)
2. Identify task dependencies
3. Detect parallel execution opportunities
4. Estimate resources and timeline

**Human Checkpoint**: ✅ Review task granularity and dependencies

---

### Phase 4: Spec Authoring (Agent 4)
**Purpose**: Generate detailed specifications for each task

**Input**: Task decomposition from Phase 3
**Output**:
- `specs/requirements/FR-XXX-*.md`
- `specs/requirements/NFR-XXX-*.md`
- `specs/architecture/ADR-XXX-*.md`
- `specs/interface/*.yaml`

**Process**:
1. Write GWT (Given-When-Then) specifications
2. Create Architecture Decision Records
3. Design interface contracts
4. Ensure traceability to framework design

**Human Checkpoint**: ✅ Review detailed specifications

---

### Phase 5: Harness Configuration (Agent 5)
**Purpose**: Set up validation pipeline and quality gates

**Input**: Specifications from Phase 4
**Output**:
- `harness.yaml`
- `.github/workflows/ci.yml`
- `scripts/check_requirement_tags.py`

**Process**:
1. Define verification steps (compile, test, lint)
2. Configure CI/CD pipeline
3. Set up cost controls and observability
4. Create traceability check scripts

**Human Checkpoint**: ✅ Review and confirm harness configuration

---

### Phase 6: Parallel Coding (Agent 6)
**Purpose**: Implement code with multi-agent parallel execution

**Input**: 
- Specifications from Phase 4
- Harness from Phase 5
- Shared Architecture Context

**Output**: `src/` directory with implementation

**Process**:
1. Spawn multiple coding sub-agents (one per module)
2. Each agent implements tasks for its module
3. Continuous consistency checking against Context
4. Automatic coordination of interface changes

**Human Checkpoint**: 📊 Monitor progress, intervene if needed

---

### Phase 7: Self-Certification (Agent 7)
**Purpose**: Verify complete implementation meets all specs

**Input**: Code from Phase 6 + All specifications
**Output**:
- Test reports
- Coverage analysis
- Traceability matrix
- Certification report

**Process**:
1. Generate tests from GWT specifications
2. Execute comprehensive test suite
3. Verify coverage requirements
4. Check traceability FR ↔ Code ↔ Test

**Human Checkpoint**: ✅ Review certification report

---

## Shared Architecture Context

The Context maintains system state across all agents:

```yaml
context:
  master_framework:
    # Created by Agent 2, read-only afterwards
    layers:
      frontend: {responsibility: "...", scope: {...}}
      backend: {responsibility: "...", interfaces: {...}}
  
  global_state:
    # Updated by all agents in real-time
    modules:
      frontend: {status: "implementing", progress: 60}
      backend: {status: "testing", progress: 90}
  
  event_bus:
    # Cross-agent communication
    events:
      - type: "interface_changed"
        subscribers: ["Agent-4", "Agent-6"]
```

## Usage Examples

### Example 1: New Task Queue Library

```bash
/spec-coding init \
  --project-name "TaskQueue" \
  --description "A C++ task queue library similar to iOS GCD" \
  --language cpp \
  --features "async/sync/after operations,Serial/Concurrent/Parallel queues,Thread pool management" \
  --constraints "C++17, header-only option, <10μs latency"
```

### Example 2: Web API Service

```bash
/spec-coding init \
  --project-name "OrderService" \
  --description "RESTful API for order management" \
  --language typescript \
  --framework fastify \
  --database postgres \
  --features "CRUD operations, Webhook notifications, Rate limiting"
```

### Example 3: Complex System

```bash
/spec-coding init \
  --project-name "ECommercePlatform" \
  --complexity complex \
  --modules "user-service,order-service,payment-service,inventory-service" \
  --architecture microservices
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project-name` | Project name | Required |
| `--description` | Brief description | Required |
| `--language` | Programming language | `cpp` |
| `--complexity` | `simple` or `complex` | `auto` |
| `--architecture` | Architecture style | `auto-detect` |
| `--output` | Output directory | `./{project-name}` |
| `--skip-phases` | Skip specific phases | none |

## Directory Structure

```
{project-name}/
├── context/                    # Shared Architecture Context
│   ├── requirements/
│   │   └── clarified.md
│   ├── framework/
│   │   ├── system-architecture.md
│   │   ├── module-design.md
│   │   └── technology-stack.md
│   ├── tasks/
│   │   └── decomposition.yaml
│   └── state.yaml              # Global state
│
├── specs/                      # Detailed specifications
│   ├── requirements/
│   │   ├── FR-001-*.md
│   │   └── NFR-001-*.md
│   ├── architecture/
│   │   └── ADR-001-*.md
│   └── interface/
│       └── *.yaml
│
├── src/                        # Implementation
│   ├── frontend/
│   ├── backend/
│   ├── operator/
│   └── threadpool/
│
├── tests/                      # Test suite
│   ├── unit/
│   └── integration/
│
├── harness.yaml                # Validation configuration
└── README.md
```

## Human-in-the-Loop Checkpoints

The workflow pauses at these points for human review:

1. **After Agent 1** - Confirm clarified requirements
2. **After Agent 2** - Confirm system architecture ⭐ Critical
3. **After Agent 3** - Confirm task decomposition
4. **After Agent 4** - Confirm detailed specifications
5. **After Agent 5** - Confirm harness configuration
6. **During Agent 6** - Monitor coding progress
7. **After Agent 7** - Review certification

## Integration with Existing Workflows

### Git Integration

```bash
# Each phase creates a commit
/spec-coding init --project-name "MyProject"
# Creates:
# - commit 1: "docs: clarified requirements (Agent 1)"
# - commit 2: "docs: framework design (Agent 2)"
# - commit 3: "docs: task decomposition (Agent 3)"
# - ...
```

### CI/CD Integration

The generated `harness.yaml` integrates with:
- GitHub Actions
- GitLab CI
- Jenkins
- CircleCI

### IDE Integration

Install the companion VS Code extension for:
- Real-time progress visualization
- Context browser
- One-click checkpoint approval

## Troubleshooting

### Agent Stuck at Checkpoint

If an agent needs clarification:
```bash
/spec-coding resume --phase 2 --with-feedback "Use event-driven architecture instead of layered"
```

### Regenerate Specific Phase

```bash
/spec-coding regenerate --phase 4 --reason "Need to change interface design"
```

### View Context State

```bash
/spec-coding context --show global_state.modules
```

## Best Practices

1. **Always review Agent 2 output carefully** - Architecture decisions are hard to change later
2. **Keep task granularity small** - 2-8 hours per task for better parallelization
3. **Use consistent naming** - Follow the ID conventions (FR-XXX, ADR-XXX)
4. **Monitor Agent 6 closely** - This is where most issues surface
5. **Maintain traceability** - Ensure every code change references a requirement

## Advanced Features

### Custom Agent Prompts

Override default prompts:
```yaml
# .spec-coding/config.yaml
agents:
  agent-2-framework:
    prompt: "custom-framework-prompt.txt"
  agent-6-coding:
    model: "gpt-4-turbo"
    temperature: 0.2
```

### Parallel Agent Tuning

```bash
/spec-coding init \
  --parallel-agents 8 \
  --agent-assignment strategy:by-module
```

### Custom Validation Rules

Add project-specific rules to `harness.yaml`:
```yaml
validation:
  custom_rules:
    - name: "no_raw_pointers"
      pattern: "(int\*|void\*)"
      message: "Use smart pointers instead"
```

## Resources

- **Methodology Docs**: `/resources/spec-coding-methodology/`
- **Example Projects**: `/examples/`
- **Agent Prompts**: `/resources/prompts/`
- **Templates**: `/resources/templates/`

## License

MIT - Free for commercial and personal use.

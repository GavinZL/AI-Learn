# LangGraph Spec Coding Implementation

## TL;DR

> **Goal**: Transform the existing Spec Coding skill into a LangGraph-based state machine with CLI tool integration (Kimi CLI, Claude CLI)
>
> **Deliverables**:
> - `src/langgraph_workflow.py` - StateGraph with 7 agent nodes
> - `src/cli_integration.py` - CLI wrappers for Kimi/Claude/Aider
> - `src/state_persistence.py` - Redis/filesystem state persistence
> - `src/checkpoint_api.py` - HTTP/WebSocket API for human checkpoints
> - `examples/taskqueue_langgraph.py` - Runnable TaskQueue example
> - Updated SKILL.md with LangGraph usage instructions
>
> **Estimated Effort**: Large (6-8 hours)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Core Nodes → CLI Integration → Checkpoint API → Example

---

## Context

### Original Request
User wants to implement the Spec Coding Multi-Agent workflow using **LangGraph framework** with integration to **CLI coding tools** (Kimi CLI, Claude CLI, etc.) for actual code generation.

### Existing Foundation
A comprehensive skill structure already exists with:
- 7 agent definitions (orchestrator + phase agents)
- Prompt templates for all phases
- Python workflow orchestrator (custom, not LangGraph)
- Documentation and examples

### Gap
The current implementation is a custom Python orchestrator. The user specifically requested LangGraph integration for:
1. Proper state machine with StateGraph
2. Parallel execution support (coding phase)
3. State persistence across runs
4. Human checkpoint integration
5. CLI tool integration for actual code generation

---

## Work Objectives

### Core Objective
Create a LangGraph-based implementation that orchestrates 7 specialized agents through a state machine, with CLI tool integration for code generation and human checkpoints for review/approval.

### Concrete Deliverables
- `src/langgraph_workflow.py` - Main StateGraph with all 7 nodes
- `src/cli_integration.py` - CLI wrappers (Kimi, Claude, Aider, Cursor)
- `src/state_persistence.py` - State persistence (Redis/filesystem)
- `src/checkpoint_api.py` - HTTP/WebSocket API for human checkpoints
- `examples/taskqueue_langgraph.py` - Working TaskQueue example
- `tests/test_workflow.py` - Unit tests for workflow
- Updated `SKILL.md` with LangGraph usage instructions

### Definition of Done
- [ ] All 7 phases execute sequentially through LangGraph
- [ ] Coding phase spawns parallel sub-agents using Send
- [ ] CLI integration works with Kimi CLI (fallback to Claude)
- [ ] Human checkpoints pause execution and resume on approval
- [ ] State persists across interruptions (Redis or filesystem)
- [ ] TaskQueue example runs end-to-end successfully
- [ ] All tests pass

### Must Have
- LangGraph StateGraph implementation
- Kimi CLI integration for code generation
- Human checkpoint mechanism
- State persistence
- TaskQueue working example

### Must NOT Have (Guardrails)
- Do NOT modify existing skill structure (create parallel src/ directory)
- Do NOT remove the existing custom orchestrator (keep both options)
- Do NOT hardcode API keys in source
- Do NOT skip error handling for CLI failures

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES - Python project with scripts/
- **Automated tests**: Tests-after (add after implementation)
- **Framework**: pytest
- **Agent-Executed QA**: YES - Every task has verifiable scenarios

### QA Policy
Every task includes agent-executed QA scenarios:
- **Code tasks**: Import modules, run functions, assert outputs
- **CLI tasks**: Execute commands, verify exit codes, check outputs
- **API tasks**: Send HTTP requests, validate responses

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation - Sequential):
├── Task 1: Create src/ directory structure
├── Task 2: Implement SpecCodingState TypedDict
├── Task 3: Implement clarify_node (Agent 1)
├── Task 4: Implement framework_node (Agent 2)
└── Task 5: Implement decompose_node (Agent 3)

Wave 2 (Core Implementation - Parallel):
├── Task 6: Implement spec_node (Agent 4) [depends: Wave 1]
├── Task 7: Implement harness_node (Agent 5) [depends: Wave 1]
├── Task 8: Implement CLI integration module [depends: Wave 1]
└── Task 9: Implement state persistence [depends: Wave 1]

Wave 3 (Advanced Features - Parallel):
├── Task 10: Implement coding_router + coding_sub_agent [depends: 6,7,8]
├── Task 11: Implement coding_gather + certify_node [depends: 6,7,8]
├── Task 12: Implement checkpoint API (HTTP/WebSocket) [depends: 9]
└── Task 13: Build StateGraph and compile workflow [depends: 5,10,11]

Wave 4 (Integration & Testing):
├── Task 14: Create TaskQueue example [depends: 13]
├── Task 15: Write unit tests [depends: 13]
├── Task 16: Update SKILL.md documentation [depends: 14]
└── Task 17: Integration testing and bug fixes [depends: 14,15]

Critical Path: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 10 → Task 13 → Task 14 → Task 17
Parallel Speedup: ~40% faster than sequential
Max Concurrent: 4 (Wave 3)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | - | 2 |
| 2 | 1 | 3,4,5,6,7 |
| 3 | 2 | - |
| 4 | 2 | - |
| 5 | 2 | 13 |
| 6 | 2 | 10 |
| 7 | 2 | 10 |
| 8 | 1 | 10 |
| 9 | 1 | 12 |
| 10 | 6,7,8 | 13 |
| 11 | 6,7,8 | 13 |
| 12 | 9 | 13 |
| 13 | 5,10,11,12 | 14,15,16 |
| 14 | 13 | 17 |
| 15 | 13 | 17 |
| 16 | 13,14 | 17 |
| 17 | 14,15,16 | - |

### Agent Dispatch Summary

- **Wave 1**: Task 1-5 → `quick` (scaffolding, simple implementations)
- **Wave 2**: Task 6-9 → `unspecified-high` (complex node logic, external integrations)
- **Wave 3**: Task 10-13 → `deep` (parallel routing, gather logic, API design)
- **Wave 4**: Task 14-17 → `unspecified-high` (integration, testing, documentation)

---

## TODOs

- [ ] 1. Create src/ directory structure

  **What to do**:
  - Create `spec-coding-skill/src/` directory
  - Create empty `__init__.py` files
  - Create placeholder files for all modules
  - Add `requirements.txt` with dependencies

  **Must NOT do**:
  - Modify files outside src/ directory
  - Delete existing files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple directory structure creation, no complex logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (must complete before other src tasks)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 2-9
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `src/` directory exists with `__init__.py`
  - [ ] `src/langgraph_workflow.py` exists
  - [ ] `src/cli_integration.py` exists
  - [ ] `src/state_persistence.py` exists
  - [ ] `src/checkpoint_api.py` exists
  - [ ] `requirements.txt` created with langgraph, langchain, etc.

  **QA Scenarios**:
  ```
  Scenario: Verify directory structure
    Tool: Bash (ls)
    Steps:
      1. Run: ls -la spec-coding-skill/src/
      2. Assert: __init__.py exists
      3. Assert: langgraph_workflow.py exists
    Expected Result: All files present
    Evidence: .sisyphus/evidence/task-1-structure.txt
  ```

  **Commit**: YES
  - Message: `chore(src): create directory structure for LangGraph implementation`
  - Files: `spec-coding-skill/src/`, `spec-coding-skill/requirements.txt`

---

- [ ] 2. Implement SpecCodingState TypedDict

  **What to do**:
  - Define `SpecCodingState` TypedDict in `src/state_types.py`
  - Include all fields from design document
  - Add proper type annotations
  - Include Annotated fields for reduction

  **Must NOT do**:
  - Skip optional fields
  - Use `Any` type unnecessarily

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Type definitions only, no logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (must complete before node implementations)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 3-13
  - **Blocked By**: Task 1

  **References**:
  - `LANGGRAPH_IMPLEMENTATION.md` - State design section
  - LangGraph docs: https://python.langchain.com/docs/langgraph

  **Acceptance Criteria**:
  - [ ] `SpecCodingState` TypedDict defined with all fields
  - [ ] `ModuleState` TypedDict defined
  - [ ] Uses `Annotated` for event list reduction
  - [ ] Type hints are complete

  **QA Scenarios**:
  ```
  Scenario: Import and type check
    Tool: Bash (python)
    Steps:
      1. Run: python -c "from src.state_types import SpecCodingState; print('OK')"
      2. Assert: No import errors
    Expected Result: Clean import
    Evidence: .sisyphus/evidence/task-2-types.txt
  ```

  **Commit**: YES
  - Message: `feat(types): add SpecCodingState TypedDict`
  - Files: `spec-coding-skill/src/state_types.py`

---

- [ ] 3. Implement clarify_node (Agent 1)

  **What to do**:
  - Implement `clarify_node` function in `src/nodes.py`
  - Load prompt from `resources/prompts/agent-1-clarify.prompt`
  - Call LLM (ChatOpenAI) with system + human messages
  - Parse output and save to `context/requirements/clarified.md`
  - Update state with clarified requirements

  **Must NOT do**:
  - Hardcode API key
  - Skip error handling

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: LLM integration, file I/O, state updates
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 2)
  - **Parallel Group**: Wave 1
  - **Blocks**: - 
  - **Blocked By**: Task 2

  **References**:
  - `resources/prompts/agent-1-clarify.prompt`
  - `agents/agent-1-clarify.agent`

  **Acceptance Criteria**:
  - [ ] Function takes/returns SpecCodingState
  - [ ] Loads prompt template from file
  - [ ] Calls LLM and parses output
  - [ ] Saves artifact to correct path
  - [ ] Updates state with output

  **QA Scenarios**:
  ```
  Scenario: Test clarify_node function
    Tool: Bash (python)
    Steps:
      1. Run: python -c "from src.nodes import clarify_node; print('Import OK')"
      2. Create test state with mock data
      3. Call clarify_node
      4. Assert: Returns dict with clarified_requirements
    Expected Result: Function executes without errors
    Evidence: .sisyphus/evidence/task-3-clarify.txt
  ```

  **Commit**: YES
  - Message: `feat(nodes): implement clarify_node (Agent 1)`
  - Files: `spec-coding-skill/src/nodes.py`

---

- [ ] 4. Implement framework_node (Agent 2)

  **What to do**:
  - Implement `framework_node` function
  - Check if clarify phase is approved
  - Load prompt from `resources/prompts/agent-2-framework.prompt`
  - Call LLM with clarified requirements
  - Parse and save framework artifacts
  - Update master_framework in state

  **Must NOT do**:
  - Skip checkpoint validation
  - Modify state incorrectly

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Complex logic, checkpoint validation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: - 
  - **Blocked By**: Task 2

  **References**:
  - `resources/prompts/agent-2-framework.prompt`
  - `agents/agent-2-framework.agent`

  **Acceptance Criteria**:
  - [ ] Validates checkpoint status before proceeding
  - [ ] Loads correct prompt template
  - [ ] Saves multiple framework files
  - [ ] Updates master_framework in state

  **QA Scenarios**:
  ```
  Scenario: Test framework_node with approved checkpoint
    Tool: Bash (python)
    Steps:
      1. Create test state with checkpoint_status.clarify = 'approved'
      2. Call framework_node
      3. Assert: Returns dict with master_framework
    Expected Result: Framework generated
    Evidence: .sisyphus/evidence/task-4-framework.txt
  ```

  **Commit**: YES
  - Message: `feat(nodes): implement framework_node (Agent 2)`
  - Files: `spec-coding-skill/src/nodes.py`

---

- [ ] 5. Implement decompose_node (Agent 3)

  **What to do**:
  - Implement `decompose_node` function
  - Check framework checkpoint
  - Load prompt from `resources/prompts/agent-3-decompose.prompt`
  - Call LLM with framework
  - Parse decomposition and save to YAML
  - Update task_decomposition in state

  **Must NOT do**:
  - Skip checkpoint validation
  - Generate invalid YAML

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: YAML serialization, validation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 3-4)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 13
  - **Blocked By**: Task 2

  **References**:
  - `resources/prompts/agent-3-decompose.prompt`
  - `agents/agent-3-decompose.agent`

  **Acceptance Criteria**:
  - [ ] Validates checkpoint status
  - [ ] Generates valid YAML decomposition
  - [ ] Saves to context/tasks/decomposition.yaml
  - [ ] Updates state correctly

  **QA Scenarios**:
  ```
  Scenario: Test decomposition YAML output
    Tool: Bash (python)
    Steps:
      1. Create test state
      2. Call decompose_node
      3. Assert: YAML file exists and is valid
    Expected Result: Valid YAML created
    Evidence: .sisyphus/evidence/task-5-decompose.txt
  ```

  **Commit**: YES
  - Message: `feat(nodes): implement decompose_node (Agent 3)`
  - Files: `spec-coding-skill/src/nodes.py`

---

- [ ] 6. Implement spec_node (Agent 4)

  **What to do**:
  - Implement `spec_node` function
  - Check decompose checkpoint
  - Load prompt from `resources/prompts/agent-4-spec.prompt`
  - Call LLM with decomposition
  - Generate multiple spec files
  - Update fr_specs in state

  **Must NOT do**:
  - Create specs in wrong directory
  - Skip file naming convention

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Multiple file generation, categorization
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 10
  - **Blocked By**: Task 2

  **References**:
  - `resources/prompts/agent-4-spec.prompt`
  - `agents/agent-4-spec.agent`

  **Acceptance Criteria**:
  - [ ] Generates specs in specs/requirements/, specs/architecture/, etc.
  - [ ] Follows naming convention: FR-{id}-{title}.md
  - [ ] Updates state with fr_specs list

  **QA Scenarios**:
  ```
  Scenario: Verify spec file generation
    Tool: Bash (ls)
    Steps:
      1. Run spec_node
      2. Assert: specs/ directory has .md files
      3. Assert: Files follow naming convention
    Expected Result: Multiple spec files created
    Evidence: .sisyphus/evidence/task-6-spec.txt
  ```

  **Commit**: YES
  - Message: `feat(nodes): implement spec_node (Agent 4)`
  - Files: `spec-coding-skill/src/nodes.py`

---

- [ ] 7. Implement harness_node (Agent 5)

  **What to do**:
  - Implement `harness_node` function
  - Check spec checkpoint
  - Load prompt from `resources/prompts/agent-5-harness.prompt`
  - Call LLM with specs and language
  - Generate harness.yaml configuration
  - Update harness_config in state

  **Must NOT do**:
  - Skip language-specific configuration
  - Generate invalid test harness config

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Test framework configuration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 10
  - **Blocked By**: Task 2

  **References**:
  - `resources/prompts/agent-5-harness.prompt`
  - `agents/agent-5-harness.agent`

  **Acceptance Criteria**:
  - [ ] Generates valid harness.yaml
  - [ ] Includes language-specific settings
  - [ ] References specs correctly
  - [ ] Updates state correctly

  **QA Scenarios**:
  ```
  Scenario: Verify harness config
    Tool: Bash (python)
    Steps:
      1. Run harness_node
      2. Load harness.yaml
      3. Assert: Required fields present
    Expected Result: Valid harness config
    Evidence: .sisyphus/evidence/task-7-harness.txt
  ```

  **Commit**: YES
  - Message: `feat(nodes): implement harness_node (Agent 5)`
  - Files: `spec-coding-skill/src/nodes.py`

---

- [ ] 8. Implement CLI integration module

  **What to do**:
  - Create `src/cli_integration.py`
  - Implement `CLIIntegration` class
  - Support Kimi CLI: `kimi edit <dir> --prompt "..."`
  - Support Claude CLI: `claude code --dir <dir>`
  - Support Aider: `aider <files>`
  - Implement fallback to LLM if CLI unavailable
  - Handle timeouts and errors gracefully

  **Must NOT do**:
  - Hardcode paths or API keys
  - Skip error handling
  - Block indefinitely on CLI calls

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Subprocess management, external tool integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 6-7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 10
  - **Blocked By**: Task 1

  **References**:
  - Kimi CLI documentation
  - Claude CLI documentation
  - Aider documentation

  **Acceptance Criteria**:
  - [ ] Kimi CLI wrapper implemented
  - [ ] Claude CLI wrapper implemented
  - [ ] Aider wrapper implemented
  - [ ] Timeout handling (300s default)
  - [ ] Error handling with graceful fallback
  - [ ] Returns structured result dict

  **QA Scenarios**:
  ```
  Scenario: Test CLI detection
    Tool: Bash (python)
    Steps:
      1. Run: which kimi
      2. Run: which claude
      3. Test CLIIntegration.detect_available()
      4. Assert: Returns list of available CLIs
    Expected Result: Correctly detects available tools
    Evidence: .sisyphus/evidence/task-8-cli-detect.txt

  Scenario: Test CLI execution
    Tool: Bash (python)
    Steps:
      1. Mock CLI execution
      2. Call cli.code_module()
      3. Assert: Returns success/failure result
    Expected Result: Structured result returned
    Evidence: .sisyphus/evidence/task-8-cli-exec.txt
  ```

  **Commit**: YES
  - Message: `feat(cli): implement CLI integration for Kimi, Claude, Aider`
  - Files: `spec-coding-skill/src/cli_integration.py`

---

- [ ] 9. Implement state persistence

  **What to do**:
  - Create `src/state_persistence.py`
  - Implement `StatePersistence` base class
  - Implement `FileSystemPersistence` (JSON/YAML)
  - Implement `RedisPersistence` (optional)
  - Methods: save(), load(), delete()
  - Include serialization/deserialization

  **Must NOT do**:
  - Use pickle for serialization
  - Skip validation on load

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: I/O operations, serialization
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 6-8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 12
  - **Blocked By**: Task 1

  **References**:
  - LangGraph persistence docs

  **Acceptance Criteria**:
  - [ ] FileSystemPersistence implemented
  - [ ] RedisPersistence implemented
  - [ ] Proper error handling
  - [ ] JSON/YAML serialization
  - [ ] State validation on load

  **QA Scenarios**:
  ```
  Scenario: Test filesystem persistence
    Tool: Bash (python)
    Steps:
      1. Create test state
      2. Save to file
      3. Load from file
      4. Assert: Loaded state matches original
    Expected Result: Round-trip successful
    Evidence: .sisyphus/evidence/task-9-persist.txt
  ```

  **Commit**: YES
  - Message: `feat(persistence): implement filesystem and Redis state persistence`
  - Files: `spec-coding-skill/src/state_persistence.py`

---

- [ ] 10. Implement coding_router and coding_sub_agent

  **What to do**:
  - Implement `coding_router` function using `Send`
  - Implement `coding_sub_agent` function
  - Use CLI integration for code generation
  - Run harness verification after generation
  - Update module status in state
  - Publish events

  **Must NOT do**:
  - Skip harness verification
  - Ignore CLI failures
  - Block event publishing

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Parallel routing, complex state updates, external integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 11)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 6, 7, 8

  **References**:
  - LangGraph Send documentation
  - `resources/prompts/agent-6-coding.prompt`

  **Acceptance Criteria**:
  - [ ] coding_router returns List[Send]
  - [ ] coding_sub_agent takes/returns state
  - [ ] Uses CLI integration
  - [ ] Runs harness verification
  - [ ] Updates module status
  - [ ] Publishes events

  **QA Scenarios**:
  ```
  Scenario: Test coding_router
    Tool: Bash (python)
    Steps:
      1. Create test state with 3 modules
      2. Call coding_router
      3. Assert: Returns 3 Send objects
    Expected Result: Correct number of sends
    Evidence: .sisyphus/evidence/task-10-router.txt

  Scenario: Test coding_sub_agent
    Tool: Bash (python)
    Steps:
      1. Create test state with 1 module
      2. Mock CLI integration
      3. Call coding_sub_agent
      4. Assert: Module status updated
    Expected Result: Module marked complete
    Evidence: .sisyphus/evidence/task-10-subagent.txt
  ```

  **Commit**: YES
  - Message: `feat(coding): implement parallel coding nodes with CLI integration`
  - Files: `spec-coding-skill/src/nodes.py`

---

- [ ] 11. Implement coding_gather and certify_node

  **What to do**:
  - Implement `coding_gather` function
  - Aggregate results from all sub-agents
  - Check for failed modules
  - Implement `certify_node` function
  - Generate certification report
  - Save CERTIFICATION_REPORT.md

  **Must NOT do**:
  - Skip failed module detection
  - Generate incomplete certification

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: State aggregation, final validation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 10)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 6, 7, 8

  **References**:
  - `resources/prompts/agent-7-certify.prompt`

  **Acceptance Criteria**:
  - [ ] coding_gather aggregates module states
  - [ ] Detects failed modules
  - [ ] certify_node generates report
  - [ ] Report includes all modules
  - [ ] Saves to CERTIFICATION_REPORT.md

  **QA Scenarios**:
  ```
  Scenario: Test coding_gather with failures
    Tool: Bash (python)
    Steps:
      1. Create state with 1 failed module
      2. Call coding_gather
      3. Assert: Error recorded
    Expected Result: Failure detected
    Evidence: .sisyphus/evidence/task-11-gather.txt
  ```

  **Commit**: YES
  - Message: `feat(certify): implement coding_gather and certify_node`
  - Files: `spec-coding-skill/src/nodes.py`

---

- [ ] 12. Implement checkpoint API

  **What to do**:
  - Create `src/checkpoint_api.py`
  - Implement FastAPI app
  - Add WebSocket endpoint for real-time updates
  - Add HTTP endpoints: GET /status, POST /approve, POST /reject
  - Integrate with LangGraph interrupt mechanism
  - Serve UI for human review

  **Must NOT do**:
  - Skip authentication (document as TODO)
  - Use blocking I/O

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: API design, WebSocket handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10-11)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 13
  - **Blocked By**: Task 9

  **References**:
  - FastAPI documentation
  - LangGraph interrupt docs

  **Acceptance Criteria**:
  - [ ] FastAPI app implemented
  - [ ] WebSocket endpoint working
  - [ ] HTTP endpoints working
  - [ ] Integrates with LangGraph
  - [ ] Basic HTML UI for review

  **QA Scenarios**:
  ```
  Scenario: Test API endpoints
    Tool: Bash (curl)
    Steps:
      1. Start API server
      2. GET /status
      3. Assert: Returns current phase
      4. POST /approve with phase=clarify
      5. Assert: Returns success
    Expected Result: API working
    Evidence: .sisyphus/evidence/task-12-api.txt
  ```

  **Commit**: YES
  - Message: `feat(api): implement checkpoint API with WebSocket support`
  - Files: `spec-coding-skill/src/checkpoint_api.py`

---

- [ ] 13. Build StateGraph and compile workflow

  **What to do**:
  - Create `src/langgraph_workflow.py`
  - Build StateGraph with all nodes
  - Add conditional edges for checkpoint routing
  - Add parallel routing for coding phase
  - Compile with checkpointer
  - Export `app` for external use

  **Must NOT do**:
  - Skip checkpoint edges
  - Forget to compile

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Graph construction, edge routing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (must integrate all previous work)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 14-17
  - **Blocked By**: Tasks 5, 10, 11, 12

  **References**:
  - `LANGGRAPH_IMPLEMENTATION.md` - Building the StateGraph section

  **Acceptance Criteria**:
  - [ ] StateGraph built with all nodes
  - [ ] Conditional edges for checkpoints
  - [ ] Parallel routing for coding
  - [ ] Compiled with checkpointer
  - [ ] Exported as `app`

  **QA Scenarios**:
  ```
  Scenario: Test graph compilation
    Tool: Bash (python)
    Steps:
      1. Import app from src.langgraph_workflow
      2. Assert: app is compiled StateGraph
      3. Print graph structure
    Expected Result: Valid compiled graph
    Evidence: .sisyphus/evidence/task-13-graph.txt
  ```

  **Commit**: YES
  - Message: `feat(graph): build and compile complete StateGraph workflow`
  - Files: `spec-coding-skill/src/langgraph_workflow.py`

---

- [ ] 14. Create TaskQueue LangGraph example

  **What to do**:
  - Create `examples/taskqueue_langgraph.py`
  - Set up initial state for TaskQueue project
  - Configure checkpoint callback
  - Stream execution with progress display
  - Handle human checkpoints
  - Show final results

  **Must NOT do**:
  - Skip error handling
  - Hardcode sensitive data

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Integration example, end-to-end flow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 15-16)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 17
  - **Blocked By**: Task 13

  **References**:
  - `examples/taskqueue-example.json`
  - LangGraph streaming docs

  **Acceptance Criteria**:
  - [ ] Example runs without errors
  - [ ] Shows progress for each phase
  - [ ] Handles checkpoints
  - [ ] Displays final certification
  - [ ] Well-commented code

  **QA Scenarios**:
  ```
  Scenario: Run TaskQueue example
    Tool: Bash (python)
    Steps:
      1. Set OPENAI_API_KEY
      2. Run: python examples/taskqueue_langgraph.py
      3. Assert: All 7 phases execute
      4. Assert: Certification report generated
    Expected Result: End-to-end execution
    Evidence: .sisyphus/evidence/task-14-example.txt
  ```

  **Commit**: YES
  - Message: `feat(example): add TaskQueue LangGraph example`
  - Files: `spec-coding-skill/examples/taskqueue_langgraph.py`

---

- [ ] 15. Write unit tests

  **What to do**:
  - Create `tests/test_workflow.py`
  - Test state types
  - Test individual nodes
  - Test CLI integration
  - Test state persistence
  - Mock LLM calls

  **Must NOT do**:
  - Skip mocking (don't hit real APIs)
  - Leave tests failing

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Testing patterns, mocking
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 14, 16)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 17
  - **Blocked By**: Task 13

  **Acceptance Criteria**:
  - [ ] Tests for state types
  - [ ] Tests for nodes (mocked)
  - [ ] Tests for CLI integration
  - [ ] Tests for persistence
  - [ ] All tests pass

  **QA Scenarios**:
  ```
  Scenario: Run test suite
    Tool: Bash (pytest)
    Steps:
      1. Run: pytest tests/
      2. Assert: All tests pass
      3. Assert: Coverage > 70%
    Expected Result: Green tests
    Evidence: .sisyphus/evidence/task-15-tests.txt
  ```

  **Commit**: YES
  - Message: `test: add unit tests for workflow, nodes, CLI, persistence`
  - Files: `spec-coding-skill/tests/test_workflow.py`

---

- [ ] 16. Update SKILL.md documentation

  **What to do**:
  - Add LangGraph usage section to SKILL.md
  - Document StateGraph structure
  - Document CLI integration
  - Document checkpoint API
  - Add example usage
  - Keep existing documentation

  **Must NOT do**:
  - Remove existing docs
  - Skip documenting new features

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Reason**: Documentation, examples
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 14-15)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 17
  - **Blocked By**: Task 14

  **Acceptance Criteria**:
  - [ ] LangGraph section added
  - [ ] StateGraph documented
  - [ ] CLI integration documented
  - [ ] Checkpoint API documented
  - [ ] Example usage included

  **QA Scenarios**:
  ```
  Scenario: Verify documentation
    Tool: Bash (grep)
    Steps:
      1. Search for "LangGraph" in SKILL.md
      2. Search for "CLI Integration"
      3. Search for "Checkpoint API"
    Expected Result: All sections present
    Evidence: .sisyphus/evidence/task-16-docs.txt
  ```

  **Commit**: YES
  - Message: `docs: add LangGraph implementation documentation`
  - Files: `spec-coding-skill/SKILL.md`

---

- [ ] 17. Integration testing and bug fixes

  **What to do**:
  - Run end-to-end test with TaskQueue
  - Fix any bugs found
  - Verify all checkpoints work
  - Verify CLI integration works
  - Verify state persistence works
  - Final polish

  **Must NOT do**:
  - Ship with known bugs
  - Skip manual verification

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Debugging, integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (final integration)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Tasks 14, 15, 16

  **Acceptance Criteria**:
  - [ ] End-to-end test passes
  - [ ] All checkpoints work
  - [ ] CLI integration verified
  - [ ] State persistence verified
  - [ ] No critical bugs

  **QA Scenarios**:
  ```
  Scenario: Full integration test
    Tool: Bash (python)
    Steps:
      1. Clean environment
      2. Run TaskQueue example
      3. Approve each checkpoint
      4. Verify all outputs
      5. Check certification report
    Expected Result: Complete execution
    Evidence: .sisyphus/evidence/task-17-integration.txt
  ```

  **Commit**: YES
  - Message: `fix: resolve integration issues, final polish`
  - Files: All modified files

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Verify all deliverables exist and match plan. Check each TODO for completion status. Compare files against expected structure.
  Output: `Tasks [17/17] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest`, `mypy`, `flake8`. Check for proper error handling, type hints, documentation. Review LangGraph patterns.
  Output: `Tests [PASS] | Types [PASS] | Lint [PASS] | VERDICT`

- [ ] F3. **Integration Test** — `unspecified-high`
  Run TaskQueue example end-to-end. Verify all 7 phases, checkpoints, CLI integration, final certification.
  Output: `Phases [7/7] | Checkpoints [5/5] | CLI [OK] | VERDICT`

- [ ] F4. **Documentation Review** — `deep`
  Verify SKILL.md has LangGraph section. Check all APIs documented. Verify examples are runnable.
  Output: `Docs [COMPLETE] | Examples [VALID] | VERDICT`

---

## Commit Strategy

- Task 1-5: Individual commits
- Task 6-9: Individual commits
- Task 10-13: Individual commits
- Task 14-17: Individual commits

---

## Success Criteria

### Verification Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run example
python examples/taskqueue_langgraph.py

# Verify outputs
ls -la TaskQueue/context/requirements/clarified.md
ls -la TaskQueue/CERTIFICATION_REPORT.md
```

### Final Checklist
- [ ] All 17 tasks complete
- [ ] All tests pass
- [ ] TaskQueue example runs end-to-end
- [ ] SKILL.md updated with LangGraph docs
- [ ] No critical bugs

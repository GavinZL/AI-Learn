# AGENTS.md 实战模板

> 本文档提供不同项目类型的 AGENTS.md 模板，可直接复制到项目根目录使用。

---

## 模板一：TypeScript/Node.js 项目

```markdown
# AGENTS.md

## Project
{项目名称} — {一句话描述}

## Stack
- Runtime: Node.js 20+ / TypeScript 5.x
- Framework: Express / Fastify / Next.js
- Database: PostgreSQL + Prisma ORM
- Testing: Vitest
- Package: pnpm

## Structure
src/
├── types/       # 共享类型定义（无外部依赖）
├── config/      # 配置加载和验证（依赖: types）
├── db/          # 数据库访问层（依赖: types, config）
├── services/    # 业务逻辑（依赖: types, config, db）
├── api/         # HTTP 路由和控制器（依赖: services）
└── utils/       # 纯函数工具（依赖: types only）

## Dependency Rules
MUST only import downward: types → config → db → services → api
MUST NOT skip layers: api cannot import db directly
utils MUST only depend on types

## Code Rules
- MUST use async/await (no raw Promises or callbacks)
- MUST NOT use `any` type
- MUST handle errors with custom Error classes from types/errors.ts
- MUST add @require tags linking to specs/requirements/
- SHOULD prefer early returns over nested if-else
- MUST NOT use console.log in production code (use logger from config/)

## Testing
- Test files: `src/**/__tests__/*.test.ts`
- Min coverage: 80% lines
- Run: `pnpm test`
- MUST write tests for all public functions

## Commits
Format: `{type}({scope}): {description}`
Types: feat | fix | refactor | test | docs | chore
MUST include `Refs: FR-XXX-001` when implementing a requirement

## Verification
Pre-commit runs: typecheck → lint → format
Pre-push runs: tests → architecture check → traceability check

## Docs
- [Architecture](docs/ARCHITECTURE.md)
- [API Spec](specs/api/openapi.yaml)
- [Security](docs/SECURITY.md)
```

---

## 模板二：Python 项目

```markdown
# AGENTS.md

## Project
{项目名称} — {一句话描述}

## Stack
- Python 3.11+
- Framework: FastAPI
- ORM: SQLAlchemy 2.0
- Testing: pytest
- Package: uv / pip

## Structure
src/
├── models/      # SQLAlchemy 模型和 Pydantic schemas
├── config/      # 配置管理（pydantic-settings）
├── repos/       # 数据库访问层
├── services/    # 业务逻辑
├── api/         # FastAPI 路由
└── utils/       # 工具函数

## Dependency Rules
MUST only import downward: models → config → repos → services → api
utils MUST only depend on models

## Code Rules
- MUST use type hints for all function signatures
- MUST NOT use bare `except:`
- MUST use Pydantic for all input/output validation
- MUST add @require tags in docstrings
- SHOULD prefer composition over inheritance
- MUST NOT import from __init__.py across layers

## Testing
- Test files: `tests/`
- Run: `pytest --cov=src --cov-report=term-missing`
- Min coverage: 80%
- MUST use fixtures for database setup

## Commits
Same as standard Conventional Commits
MUST include `Refs: FR-XXX-001`

## Verification
Pre-commit: ruff check + ruff format + mypy
CI: pytest + coverage + architecture check

## Docs
- [Architecture](docs/ARCHITECTURE.md)
- [API Spec](specs/openapi.yaml)
```

---

## 模板三：C++ 项目

```markdown
# AGENTS.md

## Project
{项目名称} — {一句话描述}

## Stack
- C++17
- Build: CMake 3.20+
- Testing: Google Test
- Tooling: clang-tidy, clang-format

## Structure
src/
├── types/       # 类型定义和枚举
├── interfaces/  # 纯虚基类（接口定义）
├── core/        # 核心实现
├── utils/       # 工具函数
└── main.cpp     # 入口

## Dependency Rules
MUST only import downward: types → interfaces → core
utils MUST only depend on types
MUST NOT use circular includes

## Code Rules
- MUST use `#pragma once` for include guards
- MUST use smart pointers (no raw new/delete)
- MUST follow RAII for resource management
- MUST add @require tags in file-level comments
- MUST NOT use global mutable state
- SHOULD prefer const references for parameters

## Testing
- Test files: `tests/*.test.cpp`
- Run: `cd build && ctest --output-on-failure`
- MUST test all public interfaces
- MUST check for memory leaks with valgrind

## Build
```bash
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

## Verification
Pre-commit: compile check
Pre-push: clang-tidy + clang-format + tests
CI: full build + tests + valgrind + coverage

## Docs
- [Architecture](docs/ARCHITECTURE.md)
- [Interface Spec](specs/interface/*.yaml)
```

---

## 模板使用说明

1. 选择最接近的模板，复制到项目根目录
2. 替换所有 `{...}` 占位符
3. 根据项目实际情况调整 Structure 和 Dependency Rules
4. 保持在 100 行以内——详细内容放到 docs/ 子目录
5. 随着发现新的 Agent 错误模式，持续更新规则

---

*文档生成日期：2026年3月27日*

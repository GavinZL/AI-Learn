# GitHub Spec Kit 详细解析

> **核心结论**：GitHub Spec Kit 是 Spec-Driven Development 的官方开源工具链，提供从需求到代码的完整工作流支持，是实践 SDD 方法的最佳入门工具。

## 项目概况

| 维度 | 信息 |
|------|------|
| 项目名称 | GitHub Spec Kit |
| 仓库 | github/spec-kit |
| 发布时间 | 2025年9月 |
| 用途 | Spec-Driven Development 工具链 |
| 集成 | GitHub Copilot、GitHub Models |

---

## 一、核心理念

### 1.1 Spec-Driven Development 定义

> "Spec-driven development flips the script on traditional software development. For decades, code has been king."
> 
> —— GitHub Spec Kit 文档

**核心思想**：
- 规范先于代码
- 需求驱动实现
- 可追溯、可验证

### 1.2 与 Copilot Workspace 的关系

```
Spec Kit (规范定义)
    ↓
Copilot Workspace (任务执行)
    ↓
GitHub Models (代码生成)
    ↓
CI/CD (验证部署)
```

---

## 二、核心功能

### 2.1 Spec 文件格式

Spec Kit 支持多种规范格式：

| 格式 | 用途 | 示例 |
|------|------|------|
| Markdown | 需求文档 | `specs/requirements/*.md` |
| YAML | 配置规范 | `specs/config/*.yaml` |
| OpenAPI | API 定义 | `specs/openapi.yaml` |
| TypeSpec | 类型规范 | `specs/types/*.tsp` |

### 2.2 Spec 验证

```bash
# 验证 Spec 文件格式
spec-kit validate specs/

# 检查 Spec 与代码的一致性
spec-kit check-traceability src/ specs/

# 生成代码骨架
spec-kit generate specs/openapi.yaml --output src/
```

### 2.3 需求追溯

自动检查代码与需求的关系：

```bash
$ spec-kit trace src/

✓ FR-AUTH-001: 3 files reference this requirement
  - src/auth/login.ts
  - src/auth/session.ts
  - tests/auth.test.ts

✓ FR-AUTH-002: 2 files reference this requirement
  - src/auth/register.ts
  - tests/auth.test.ts

✗ FR-AUTH-003: No implementation found!
  Spec file: specs/requirements/auth.md:45
```

---

## 三、与 AI 工具集成

### 3.1 Copilot Workspace 集成

```
1. 开发者编写 Spec 文件
2. 在 Copilot Workspace 中引用 Spec
3. AI 根据 Spec 生成代码
4. Spec Kit 验证代码与 Spec 一致性
5. 自动添加追溯标签
```

### 3.2 Prompt 模板

Spec Kit 提供标准 Prompt 模板：

```markdown
# Task: Implement {FR-ID}

## Requirement
{从 Spec 文件自动提取}

## Constraints
{从 Spec 文件自动提取}

## Acceptance Criteria
{从 Spec 文件自动提取}

## Reference
- Architecture: {ADR-ID}
- API Spec: {OpenAPI 引用}

## Output Requirements
- Add @require {FR-ID} tags
- Follow coding standards in AGENTS.md
- Write unit tests for new code
```

---

## 四、目录结构

### 4.1 推荐项目结构

```
project/
├── specs/
│   ├── requirements/          # 需求文档
│   │   ├── auth.md
│   │   └── payment.md
│   ├── architecture/          # 架构决策
│   │   ├── ADR-001-auth.md
│   │   └── ADR-002-payment.md
│   ├── api/                   # API 定义
│   │   └── openapi.yaml
│   └── config/                # 配置规范
│       └── schema.yaml
├── src/                       # 源代码
│   └── ...
├── tests/                     # 测试
│   └── ...
├── AGENTS.md                  # Agent 指导文件
└── .spec-kit/
    └── config.yaml            # Spec Kit 配置
```

### 4.2 Spec 文件示例

```markdown
# FR-AUTH-001: User Login

## Description
Users must be able to log in with email and password.

## GWT
```gherkin
Scenario: Successful login
  Given user exists with email "test@example.com"
  When user submits login form
  Then user is redirected to dashboard
  And session token is set
```

## Constraints
- Password must be hashed with bcrypt
- Session expires after 24 hours
- Failed attempts limited to 5 per hour

## Acceptance Criteria
- [ ] Login form UI
- [ ] API endpoint POST /auth/login
- [ ] Session management
- [ ] Rate limiting

## References
- ADR-001: Authentication Strategy
- ADR-003: Session Management
```

---

## 五、最佳实践

### 5.1 需求 ID 规范

```
格式: {TYPE}-{DOMAIN}-{NUMBER}

TYPE:
  FR  - Functional Requirement (功能需求)
  NFR - Non-Functional Requirement (非功能需求)
  BR  - Business Rule (业务规则)

DOMAIN:
  AUTH, ORDER, PAYMENT, USER, etc.

示例:
  FR-AUTH-001
  NFR-PERF-003
  BR-PAYMENT-005
```

### 5.2 追溯标签使用

```typescript
// @require FR-AUTH-001
// @adr ADR-001
// @test auth.test.ts:login
export async function login(email: string, password: string) {
  // Implementation
}
```

### 5.3 CI 集成

```yaml
# .github/workflows/spec-check.yml
name: Spec Validation

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate Spec Files
        run: spec-kit validate specs/
        
      - name: Check Traceability
        run: spec-kit check-traceability src/ specs/
        
      - name: Check for Orphaned Code
        run: spec-kit check-orphans src/ specs/
```

---

## 六、与其他工具对比

| 工具 | 定位 | 优势 | 局限 |
|------|------|------|------|
| **GitHub Spec Kit** | SDD 工具链 | 官方支持、Copilot 集成 | GitHub 生态依赖 |
| **Aider** | AI 配对编程 | 终端友好、多模型支持 | 需要更多手动规范 |
| **Cursor** | AI IDE | 一体化体验 | 规范支持较弱 |
| **OpenHands** | 自主 Agent | 完全自动化 | 复杂项目需要强 Harness |

---

## 参考资源

- [GitHub Spec Kit 仓库](https://github.com/github/spec-kit)
- [GitHub Blog: Spec-Driven Development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai/)
- [Visual Studio Magazine: GitHub Open Sources Spec Kit](https://visualstudiomagazine.com/articles/2025/09/03/github-open-sources-kit-for-spec-driven-ai-development.aspx)

---

*文档生成日期：2026年3月27日*
*最后更新：2026年3月27日*
*信息来源：GitHub 官方博客、GitHub Spec Kit 文档*
*收集版本：v1*

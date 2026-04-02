# TypeScript 极速精通计划（C++ 背景版）

## TL;DR

> **目标**：从 0 到能独立开发 TypeScript 项目（CLI/Web/API）
> 
> **学习方式**：高强度实战驱动，通过对比 C++ 快速迁移知识
> **时间投入**：建议每天 2-3 小时，2 周完成核心路径
> **核心项目**：TypeScript CLI 工具 + Express API + React 前端

---

## 背景分析

### 你的优势（C++ → TypeScript）
| C++ 概念 | TypeScript 对应 | 迁移难度 |
|---------|----------------|---------|
| 静态类型系统 | ✅ 几乎相同，TS 更灵活 | ⭐ 低 |
| 模板/泛型 | ✅ `function f<T>()` 语法不同但概念一致 | ⭐ 低 |
| 接口/纯虚类 | ✅ `interface` 更简洁 | ⭐ 低 |
| 枚举 | ✅ `enum`，但 TS 还有更强大的联合类型 | ⭐ 低 |
| 命名空间/模块 | ⚠️ ES Modules，概念不同但更简单 | ⭐⭐ 中 |
| 编译/链接 | ⚠️ tsc 编译 + 包管理，完全不同 | ⭐⭐⭐ 需学习 |

### 需要全新学习的
- **类型推断**：TS 的 `auto` 超级强大，习惯不写类型
- **结构性类型**：鸭子类型，而非名义类型（C++ 是名义类型）
- **类型体操**：条件类型、映射类型、infer（高阶玩法）
- **JS 生态**：npm、Node.js 运行时、前端框架

---

## 学习路径（分 3 个阶段）

### Phase 1: 语法速通（3-4 天）
**目标**：理解 TS 类型系统，能写简单的脚本

#### 1.1 环境搭建
```bash
# 全局安装 TypeScript
npm install -g typescript

# 创建学习项目
mkdir ts-learning && cd ts-learning
npm init -y
npm install typescript @types/node --save-dev
npx tsc --init
```

**验证**（必须完成）：
```bash
# 创建 test.ts
echo 'console.log("TypeScript works!");' > test.ts
npx tsc test.ts
node test.js
# 输出: TypeScript works!
```

#### 1.2 核心语法清单（对照 C++）

| 主题 | C++ | TypeScript | 练习任务 |
|-----|-----|-----------|---------|
| 基础类型 | `int`, `string`, `bool` | `number`, `string`, `boolean` | 声明 5 种不同类型的变量 |
| 数组 | `vector<int>` | `number[]` 或 `Array<number>` | 写一个求和函数 |
| 对象/结构体 | `struct` | `interface` 或 `type` | 定义 User 接口 |
| 函数 | `int add(int a, int b)` | `function add(a: number, b: number): number` | 实现计算器 |
| 泛型 | `template<typename T>` | `function identity<T>(arg: T): T` | 实现通用栈类 |
| 类 | `class` | `class`（但有差异） | 实现一个类继承体系 |
| 枚举 | `enum class` | `enum` 或 const assertions | 定义订单状态枚举 |
| 联合类型 | 无（std::variant）| `string \| number` | 写一个接受多种类型的函数 |
| 可选参数 | 默认参数/重载 | `function f(x?: number)` | 实现可选配置对象 |

**关键差异点**（C++ 程序员最容易踩坑）：

1. **所有类型在编译后消失**
```typescript
// 这是合法的！运行时没有类型检查
function greet(name: string) {
  console.log(name.toUpperCase());
}

greet(123 as any); // 编译通过，运行时报错！
```

2. **接口是开放的（Declaration Merging）**
```typescript
interface User { name: string; }
interface User { age: number; }  // 同一个接口可以多次定义，自动合并！
```

3. **类型推断非常强**
```typescript
// 几乎从不需要显式写返回类型
function add(a: number, b: number) {
  return a + b;  // 自动推断为 number
}
```

#### 1.3 练习项目：类型系统挑战
创建一个 `src/types-challenge.ts`，实现以下功能：

```typescript
// 1. 实现一个通用的 Result<T, E> 类型（类似 Rust/C++ 的 expected）
// 2. 实现 DeepReadonly<T>，将所有属性变为只读
// 3. 实现一个类型安全的 EventEmitter
```

**验收标准**：
- [ ] 代码无 `any` 类型
- [ ] `npx tsc --noEmit` 零错误
- [ ] 使用 `as const` 和类型推断

---

### Phase 2: 实战项目（7-10 天）
**目标**：完成 3 个不同类型的项目，掌握 TS 在实际场景中的应用

#### 项目 1：CLI 工具（Node.js）
**项目**：文件批量重命名工具

**功能需求**：
- 递归扫描目录
- 支持正则匹配文件名
- 预览模式（只显示会做什么，不真改）
- 支持模板替换（如 `photo_{date}_{index}.jpg`）

**技术栈**：
- TypeScript
- Node.js fs/promises API
- Commander.js（CLI 框架）
- Chalk（终端颜色）

**关键 TS 概念实践**：
- [ ] 配置对象的类型定义
- [ ] 异步函数的 Promise 类型
- [ ] 错误处理（try/catch + Result 类型）
- [ ] 命令行参数的类型安全解析

**启动命令**：
```bash
mkdir file-renamer && cd file-renamer
npm init -y
npm install typescript @types/node commander chalk --save-dev
npx tsc --init
```

#### 项目 2：REST API（Express + TypeScript）
**项目**：任务管理 API

**功能需求**：
- CRUD 任务（增删改查）
- 任务分类（标签系统）
- 数据验证（Zod）
- JWT 认证

**技术栈**：
- Express
- TypeScript
- Zod（运行时类型验证）
- Prisma（ORM，可选）或 内存存储
- jsonwebtoken

**关键 TS 概念实践**：
- [ ] Express 的类型扩展（Request 对象加 user 属性）
- [ ] Zod 从 schema 推断 TypeScript 类型
- [ ] 中间件的类型定义
- [ ] 全局错误处理中间件

**API 端点**：
```
POST   /auth/login
POST   /auth/register
GET    /tasks
POST   /tasks
PUT    /tasks/:id
DELETE /tasks/:id
```

#### 项目 3：前端应用（React + TypeScript）
**项目**：任务管理前端（对接项目 2 的 API）

**功能需求**：
- 登录/注册页面
- 任务列表（支持筛选、排序）
- 新增/编辑任务弹窗
- 响应式设计

**技术栈**：
- React + Vite
- TypeScript
- TanStack Query（数据获取）
- Tailwind CSS（样式）
- React Hook Form + Zod（表单验证）

**关键 TS 概念实践**：
- [ ] 组件 Props 类型定义
- [ ] 泛型组件（如通用 Table 组件）
- [ ] 自定义 Hooks 的类型
- [ ] API 响应类型共享（前后端共用类型定义）

**启动命令**：
```bash
npm create vite@latest task-frontend -- --template react-ts
cd task-frontend
npm install
npm install @tanstack/react-query axios react-hook-form zod @hookform/resolvers
npm run dev
```

---

### Phase 3: 高级主题（3-4 天）
**目标**：掌握类型体操和工程化配置

#### 3.1 类型体操（Type Gymnastics）
学习内容：
- [ ] 条件类型：`T extends U ? X : Y`
- [ ] 映射类型：`{ [K in keyof T]: ... }`
- [ ] infer 关键字
- [ ] 模板字面量类型

**练习**：
```typescript
// 实现以下工具类型：

type DeepReadonly<T> = // 深度只读

type TupleToUnion<T> = // 元组转联合类型

type StringLength<S> = // 计算字符串长度（类型级别）

type Flatten<T> = // 拍平数组类型
```

#### 3.2 工程化配置
- [ ] `tsconfig.json` 详解
  - `strict: true`（永远开启）
  - `esModuleInterop`（处理 CommonJS/ESM）
  - `skipLibCheck`（加速编译）
- [ ] ESLint + Prettier 配置
- [ ] 路径别名（`@/` 导入）
- [ ] 声明文件（`.d.ts`）编写
- [ ] 类型声明发布（npm 包类型支持）

#### 3.3 性能与最佳实践
- [ ] 避免 `any`，使用 `unknown`
- [ ] 合理使用 `satisfies`（TS 4.9+）
- [ ] 类型收窄技巧（type guards）
- [ ] 编译性能优化（project references）

---

## 资源推荐

### 官方文档
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)（必看，质量极高）
- [tsconfig 选项](https://www.typescriptlang.org/tsconfig)

### 针对 C++ 背景
- [TypeScript for C++ Programmers](https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes-oop.html)（官方对比）

### 类型体操挑战
- [type-challenges](https://github.com/type-challenge/type-challenges)（GitHub，从简单到地狱难度）

### 工具
- [TypeScript Playground](https://www.typescriptlang.org/play)（在线实验）
- [AST Explorer](https://astexplorer.net/)（看 TS 如何解析代码）

---

## 验证检查清单

### Phase 1 完成标准
- [ ] 能用 TS 写简单的算法题（LeetCode 中等难度）
- [ ] 理解 `interface` vs `type` 的区别
- [ ] 能写出有泛型的函数和类
- [ ] 零 `any` 类型完成一个小脚本

### Phase 2 完成标准
- [ ] CLI 工具能正常运行，处理边界情况
- [ ] API 有完整的类型定义，Zod 验证
- [ ] 前端能正确调用 API，有 loading/error 状态
- [ ] 三个项目都能通过 `tsc --noEmit`

### Phase 3 完成标准
- [ ] 完成 type-challenges 中的 medium 难度 10 题
- [ ] 能独立配置一个 TS 项目的工程化（ESLint/Prettier/路径别名）
- [ ] 理解 d.ts 声明文件的作用，能为无类型的库写声明

---

## 每日学习建议

### 时间分配（每天 2-3 小时）
- **30 min**：阅读文档/教程，学习新概念
- **60-90 min**：动手写代码，做练习/项目
- **30 min**：复习和总结，记录学到的东西

### 学习技巧
1. **边学边练**：不要看完一章再动手，看一个概念就敲一遍
2. **对比 C++**：遇到新概念，问自己 "这和 C++ 的 X 有什么区别？"
3. **类型优先**：写代码前先想类型，类型想清楚了逻辑就清楚了
4. **严格模式**：`tsconfig.json` 里 `strict: true`，不要用 `any`

### 避坑指南
- ❌ 不要试图一次性理解所有高级类型
- ❌ 不要在类型体操上花太多时间（除非你想成为 TS 专家）
- ❌ 不要忽视 JavaScript 基础（TS 是 JS 的超集）
- ✅ 先学会用，再学会精
- ✅ 多用 IDE 的自动补全和类型提示
- ✅ 遇到类型错误，先读错误信息，通常很清楚

---

## 下一步

完成这个计划后，你将能够：
1. ✅ 独立开发 TypeScript 项目（CLI、API、前端）
2. ✅ 阅读和理解大型 TS 代码库
3. ✅ 为团队制定 TS 编码规范
4. ✅ 进行类型级别的元编程（类型体操）

**准备好了吗？从 Phase 1 开始，每天推进！**

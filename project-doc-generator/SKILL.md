---
name: project-doc-generator
description: |
  项目文档渐进式生成工具。使用渐进式披露思想，从概要到详细、按需分层构建文档体系。
  支持复杂项目的多维度文档组织（角色、场景、技术深度），文档存放在 .docs 隐藏目录。
  触发词: "生成文档", "创建文档", "文档生成", "项目文档", "渐进式文档", "复杂文档"
---

# Project Doc Generator - 渐进式文档生成器

使用**渐进式披露（Progressive Disclosure）**思想构建项目文档：从概要到详细、从概念到实现、按需分层展示信息。

**核心原则**: 读者应该只看到当前需要的信息，更深层的细节在需要时再展现。

**文档存放**: `.docs/` (隐藏目录)

---

## 使用方式

```
用户: 帮我生成项目文档
用户: 创建渐进式文档结构
用户: 为复杂项目生成文档
用户: 生成文档，包含架构决策和运维手册
```

---

## 渐进式文档架构

### 为什么需要复杂分层？

简单项目的文档可以扁平化，但复杂项目需要：
- **多维度导航**: 按角色（开发者/架构师/运维）、按场景（ onboarding/排障/升级）
- **信息密度控制**: 新成员看概览，资深工程师看实现细节
- **演化追踪**: 架构决策记录(ADR)、变更历史、迁移路径
- **知识沉淀**: 模式库、反模式、最佳实践

### 文档结构总览

```
.docs/
│
├── 📋 START-HERE.md              # ⭐ 入口：选择你的角色和场景
├── 📑 index.md                   # 完整索引和搜索入口
│
├── 00-meta/                      # 📖 关于本文档（元信息层）
│   ├── README.md
│   ├── how-to-read.md            # 如何使用本文档（阅读指南）
│   ├── navigation-guide.md       # 导航说明：不同角色的阅读路径
│   ├── document-history.md       # 文档变更历史
│   └── glossary.md               # 全局术语表（跨项目统一语言）
│
├── 10-fundamentals/              # 🎯 L1: 基础认知层（WHY & WHAT）
│   ├── README.md                 # 本层导航：为什么要做这个项目
│   │
│   ├── 01-vision/                # 愿景与目标（战略层）
│   │   ├── README.md
│   │   ├── problem-statement.md      # 问题陈述：我们在解决什么问题
│   │   ├── success-criteria.md       # 成功标准：怎么算做好了
│   │   ├── stakeholders.md           # 利益相关者：谁关心这个项目
│   │   └── business-context.md       # 业务背景：商业逻辑和价值
│   │
│   ├── 02-domain/                # 领域知识（业务层）
│   │   ├── README.md
│   │   ├── domain-model.md           # 领域模型：核心业务概念
│   │   ├── business-workflows.md     # 业务流程：关键业务流程图
│   │   ├── domain-events.md          # 领域事件：业务事件定义
│   │   └── constraints.md            # 约束条件：业务规则、法规限制
│   │
│   └── 03-concepts/              # 核心概念（技术概念层）
│       ├── README.md
│       ├── key-concepts.md           # 关键概念解释
│       ├── domain-terminology.md     # 领域术语表
│       └── comparison.md             # 与替代方案/竞品的对比
│
├── 20-architecture/              # 🏗️ L2: 架构设计层（HOW - 宏观）
│   ├── README.md                 # 本层导航：系统如何组织
│   │
│   ├── 01-overview/              # 架构概览
│   │   ├── README.md
│   │   ├── system-landscape.md       # 系统全景图：所有组件一览
│   │   ├── architectural-principles.md # 架构原则：设计哲学
│   │   └── quality-attributes.md     # 质量属性：非功能性需求
│   │
│   ├── 02-decisions/             # 架构决策记录(ADR)
│   │   ├── README.md
│   │   ├── 001-why-microservices.md  # 示例：为什么选择微服务
│   │   ├── 002-database-selection.md # 示例：数据库选型
│   │   ├── 003-caching-strategy.md   # 示例：缓存策略
│   │   └── template.md               # ADR模板
│   │
│   ├── 03-systems/               # 子系统划分
│   │   ├── README.md
│   │   ├── system-boundaries.md      # 系统边界：领域划分
│   │   ├── integration-points.md     # 集成点：系统间交互
│   │   ├── data-ownership.md         # 数据所有权：谁拥有什么数据
│   │   └── communication-patterns.md # 通信模式：同步/异步/消息
│   │
│   ├── 04-cross-cutting/         # 横切关注点
│   │   ├── README.md
│   │   ├── security/                 # 安全架构
│   │   │   ├── authentication.md
│   │   │   ├── authorization.md
│   │   │   └── data-protection.md
│   │   ├── observability/            # 可观测性
│   │   │   ├── logging.md
│   │   │   ├── monitoring.md
│   │   │   ├── tracing.md
│   │   │   └── alerting.md
│   │   ├── reliability/              # 可靠性
│   │   │   ├── resilience-patterns.md
│   │   │   ├── circuit-breaker.md
│   │   │   └── disaster-recovery.md
│   │   └── scalability/              # 扩展性
│   │       ├── horizontal-scaling.md
│   │       ├── sharding-strategy.md
│   │       └── caching-layers.md
│   │
│   └── 05-evolution/             # 架构演化
│       ├── README.md
│       ├── current-state.md          # 当前架构状态
│       ├── tech-debt.md              # 技术债务记录
│       ├── roadmap.md                # 架构演进路线
│       └── migrations/               # 迁移指南
│           ├── v1-to-v2.md
│           └── legacy-integration.md
│
├── 30-modules/                   # 📦 L3: 模块组件层（HOW - 中观）
│   ├── README.md                 # 本层导航：模块目录
│   ├── module-catalog.md         # 模块总目录表
│   │
│   ├── 10-core/                  # 核心域模块
│   │   └── {domain-module}/          # 每个模块独立目录
│   │       ├── README.md             # 模块概览：一句话描述+职责
│   │       ├── responsibilities.md   # 详细职责说明
│   │       ├── public-interface.md   # 对外暴露的接口/API
│   │       ├── data-model.md         # 内部数据模型
│   │       ├── state-machine.md      # 状态机（如有）
│   │       ├── dependencies.md       # 依赖关系图
│   │       └── lifecycle.md          # 生命周期管理
│   │
│   ├── 20-supporting/            # 支撑域模块
│   │   └── {support-module}/
│   │       └── ...
│   │
│   └── 30-infrastructure/        # 基础设施模块
│       └── {infra-module}/
│           └── ...
│
├── 40-implementation/            # 🔧 L4: 实现细节层（HOW - 微观）
│   ├── README.md                 # 本层导航：代码级文档
│   │
│   ├── 01-api/                   # API文档
│   │   ├── README.md
│   │   ├── rest-api/
│   │   │   ├── openapi-spec.yaml     # OpenAPI规范
│   │   │   ├── endpoint-reference.md # 端点详细说明
│   │   │   └── error-codes.md        # 错误码定义
│   │   ├── graphql/
│   │   │   ├── schema.md
│   │   │   └── resolver-guide.md
│   │   ├── grpc/
│   │   ├── events/                   # 事件契约
│   │   │   ├── event-catalog.md
│   │   │   └── schema-registry.md
│   │   └── webhooks.md
│   │
│   ├── 02-schemas/               # 数据模式
│   │   ├── README.md
│   │   ├── database/
│   │   │   ├── er-diagram.md
│   │   │   ├── schema-migrations.md
│   │   │   └── indexing-strategy.md
│   │   ├── cache/
│   │   └── message-schemas/
│   │
│   ├── 03-codebase/              # 代码库指南
│   │   ├── README.md
│   │   ├── project-structure.md      # 目录结构约定
│   │   ├── coding-standards.md       # 编码规范
│   │   ├── patterns/                 # 设计模式应用
│   │   │   ├── repository-pattern.md
│   │   │   ├── unit-of-work.md
│   │   │   └── saga-pattern.md
│   │   ├── anti-patterns.md          # 应避免的模式
│   │   └── code-review-checklist.md  # 代码审查清单
│   │
│   └── 04-changes/               # 变更记录
│       ├── README.md
│       ├── changelog.md              # 版本变更日志
│       ├── api-changelog.md          # API破坏性变更
│       └── deprecation-notices.md    # 废弃功能通知
│
├── 50-operations/                # 🚀 L5: 运维操作层（RUN）
│   ├── README.md                 # 本层导航：如何运行和维护
│   │
│   ├── 01-onboarding/            # 新手入门
│   │   ├── README.md
│   │   ├── quickstart.md             # 5分钟快速开始
│   │   ├── local-setup.md            # 本地开发环境搭建
│   │   ├── first-contribution.md     # 第一次贡献指南
│   │   └── environment-overview.md   # 环境说明(dev/staging/prod)
│   │
│   ├── 02-deployment/            # 部署指南
│   │   ├── README.md
│   │   ├── deployment-architecture.md
│   │   ├── ci-cd-pipeline.md
│   │   ├── release-process.md
│   │   ├── feature-flags.md
│   │   └── rollback-procedures.md
│   │
│   ├── 03-runbooks/              # 运维手册（SRE）
│   │   ├── README.md
│   │   ├── on-call/                  # 值班手册
│   │   │   ├── on-call-guide.md
│   │   │   ├── escalation-policy.md
│   │   │   └── incident-severity.md
│   │   ├── incident-response/        # 应急响应
│   │   │   ├── incident-commander.md
│   │   │   ├── communication.md
│   │   │   └── postmortem-template.md
│   │   ├── maintenance/              # 常规维护
│   │   │   ├── database-maintenance.md
│   │   │   ├── certificate-rotation.md
│   │   │   └── cleanup-tasks.md
│   │   └── playbooks/                # 场景化操作手册
│   │       ├── database-failover.md
│   │       ├── cache-warmup.md
│   │       └── traffic-rerouting.md
│   │
│   ├── 04-troubleshooting/       # 故障排查
│   │   ├── README.md
│   │   ├── faq.md
│   │   ├── common-issues/
│   │   │   ├── performance-issues.md
│   │   │   ├── memory-leaks.md
│   │   │   └── deadlock-detection.md
│   │   ├── debugging-guides/
│   │   │   ├── debug-locally.md
│   │   │   ├── debug-production.md
│   │   │   └── log-analysis.md
│   │   └── diagnostic-tools.md
│   │
│   ├── 05-performance/           # 性能优化
│   │   ├── README.md
│   │   ├── benchmarks.md
│   │   ├── slos-slas.md              # 服务级别目标
│   │   ├── capacity-planning.md
│   │   └── tuning-guides/
│   │       ├── database-tuning.md
│   │       ├── jvm-tuning.md
│   │       └── connection-pool-tuning.md
│   │
│   └── 06-security/              # 安全运维
│       ├── README.md
│       ├── security-checklist.md
│       ├── vulnerability-response.md
│       └── secret-rotation.md
│
└── 99-reference/                 # 📚 附录（REFERENCE）
    ├── README.md
    ├── external-resources.md       # 外部资源链接
    ├── tools.md                    # 工具清单
    ├── cheat-sheets/               # 速查表
    │   ├── git-commands.md
    │   ├── docker-commands.md
│   │   └── kubectl-commands.md
    └── templates/                  # 文档模板
        ├── adr-template.md
        ├── runbook-template.md
        └── incident-report-template.md
```

---

## 渐进式披露的路径设计

### 不同角色的阅读路径

```
┌─────────────────────────────────────────────────────────────────┐
│                        START-HERE.md                            │
│                   "选择你的角色和场景"                           │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   新成员      │    │   开发者      │    │   架构师      │
│  (Onboarding) │    │ (Developer)   │    │  (Architect)  │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│10-fundamentals│    │30-modules/    │    │10-fundamentals│
│   /01-vision  │    │10-core/       │    │   /02-domain  │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│50-operations/ │    │40-implementation│   │20-architecture│
│  01-onboarding│    │   /03-codebase │    │   /02-decisions│
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   开始编码    │    │   提交PR      │    │   评审方案    │
└───────────────┘    └───────────────┘    └───────────────┘

        ┌───────────────┐    ┌───────────────┐
        │   运维工程师   │    │   产品经理     │
        │    (SRE)      │    │    (PM)       │
        └───────┬───────┘    └───────┬───────┘
                │                     │
                ▼                     ▼
        ┌───────────────┐    ┌───────────────┐
        │20-architecture│    │10-fundamentals│
        │ /04-cross-cut │    │   /01-vision  │
        └───────┬───────┘    └───────┬───────┘
                │                     │
                ▼                     ▼
        ┌───────────────┐    ┌───────────────┐
        │50-operations/ │    │10-fundamentals│
        │  03-runbooks   │    │   /02-domain  │
        └───────┬───────┘    └───────┬───────┘
                │                     │
                ▼                     ▼
        ┌───────────────┐    ┌───────────────┐
        │  处理告警     │    │   评审需求    │
        └───────────────┘    └───────────────┘
```

### 按场景的渐进路径

| 场景 | 起点 | 渐进深入路径 |
|-----|------|-------------|
| **理解业务** | problem-statement → domain-model → business-workflows → success-criteria |
| **排查故障** | faq → common-issues → debugging-guides → runbooks/playbooks → log-analysis |
| **新增功能** | module-catalog → {target-module} → api-reference → code-review-checklist |
| **性能优化** | benchmarks → slos-slas → performance-issues → tuning-guides |
| **架构评审** | adr-index → quality-attributes → system-landscape → tech-debt |
| **生产事故** | incident-response → on-call-guide → runbooks → postmortem-template |

---

## 生成策略

### 智能分层生成

根据项目复杂度，动态决定生成深度：

```
简单项目（< 10个模块）:
  只生成: 10-fundamentals + 30-modules + 50-operations/01-onboarding

中等项目（10-50个模块）:
  生成: 10 + 20-architecture/overview + 30 + 40-api + 50-operations

复杂项目（> 50个模块 / 微服务架构）:
  完整生成所有层级，包括ADR、runbooks、cross-cutting concerns
```

### 生成顺序

```
Phase 1: 元信息层 (00-meta/)
  ├─ 生成 navigation-guide.md（定义阅读路径）
  └─ 生成 glossary.md（从代码中提取术语）

Phase 2: 快速入口 (START-HERE.md)
  └─ 基于项目分析，生成角色导航

Phase 3: 基础层 (10-fundamentals/)
  ├─ 从README提取生成 problem-statement
  ├─ 从package.json/Cargo.toml提取技术栈
  └─ 从代码注释提取 domain-model

Phase 4: 架构层 (20-architecture/)
  ├─ 扫描模块依赖生成 system-landscape
  ├─ 创建 ADR模板 + 常见决策示例
  └─ 从配置文件中提取 quality-attributes

Phase 5: 模块层 (30-modules/)
  └─ 每个模块自动生成：README + interface + dependencies

Phase 6: 实现层 (40-implementation/)
  ├─ 从代码生成 API文档
  ├─ 从数据库迁移文件生成 schema
  └─ 从.gitignore/CI配置生成 project-structure

Phase 7: 运维层 (50-operations/)
  ├─ 从Dockerfile生成 local-setup
  ├─ 从CI配置生成 deployment-guide
  └─ 创建常用runbook模板

Phase 8: 索引层
  └─ 生成 index.md（全局搜索入口）
```

---

## 关键设计决策

### 1. 两位数编号系统

```
00- 元信息（关于文档本身）
10- 基础层（WHY）
20- 架构层（HOW-宏观）
30- 模块层（HOW-中观）
40- 实现层（HOW-微观）
50- 运维层（RUN）
99- 附录

优势：
- 可在中间插入新层级（如 15-business-requirements/）
- 保持字典序排序 = 逻辑序
- 预留空间给未来扩展
```

### 2. 每层内部的再次分层

以 `20-architecture/` 为例：
```
01-overview/      → 先了解全景
02-decisions/     → 再看关键决策
03-systems/       → 然后子系统
04-cross-cutting/ → 最后横切关注点
05-evolution/     → 了解演化方向

阅读顺序 = 编号顺序，符合认知规律
```

### 3. 文档之间的链接策略

```markdown
# 每篇文档末尾的标准相关文档区块

## 相关文档

### 上一层层级
- [架构概览](../README.md) - 返回到架构层导航

### 平行层级
- [安全架构](../04-cross-cutting/security/authentication.md) - 相关横切关注点

### 下一层层级
- [用户模块](../../30-modules/10-core/user-module/README.md) - 具体实现

### 相关场景
- [故障排查](../../50-operations/04-troubleshooting/common-issues/performance-issues.md)
```

### 4. 渐进式详情的具体实现

**示例：缓存策略的渐进披露**

```
L2 - architecture/04-cross-cutting/scalability/caching-layers.md
  → "我们使用多级缓存策略：本地缓存+分布式缓存"
  
  链接到 ↓
  
L3 - modules/30-infrastructure/cache-module/README.md
  → "缓存模块提供统一的缓存抽象，支持Redis和本地Caffeine"
  
  链接到 ↓
  
L4 - implementation/03-codebase/patterns/cache-aside-pattern.md
  → "Cache-Aside模式的实现代码示例和注意事项"
  
  链接到 ↓
  
L5 - operations/03-runbooks/playbooks/cache-warmup.md
  → "缓存预热和失效的运维操作步骤"
```

---

## 实施步骤

### 第一步：项目扫描与分析

```bash
# 分析项目复杂度
find src -type f -name "*.ts" -o -name "*.js" -o -name "*.py" | wc -l
find src -type d | wc -l
cat package.json | grep -c '"dependencies"'

# 确定文档生成级别
if [ 模块数 < 10 ]; then LEVEL="simple"
elif [ 模块数 < 50 ]; then LEVEL="medium"
else LEVEL="complex"; fi
```

### 第二步：创建目录结构

```bash
mkdir -p .docs/{00-meta,10-fundamentals/{01-vision,02-domain,03-concepts},20-architecture/{01-overview,02-decisions,03-systems,04-cross-cutting/{security,observability,reliability,scalability},05-evolution/migrations},30-modules/{10-core,20-supporting,30-infrastructure},40-implementation/{01-api/{rest-api,graphql,events},02-schemas/{database,cache},03-codebase/patterns,04-changes},50-operations/{01-onboarding,02-deployment,03-runbooks/{on-call,incident-response,maintenance,playbooks},04-troubleshooting/{common-issues,debugging-guides},05-performance/tuning-guides,06-security},99-reference/cheat-sheets}
```

### 第三步：逐层生成内容

根据 `LEVEL` 决定生成深度：

| Level | 生成范围 |
|-------|---------|
| simple | 10-fundamentals + 30-modules + 50-operations/01-onboarding |
| medium | + 20-architecture/01-overview + 40-implementation/01-api |
| complex | 全部，包括所有子目录 |

### 第四步：生成导航和索引

```python
# 生成 START-HERE.md - 角色导航
# 生成 index.md - 全局索引
# 生成 00-meta/navigation-guide.md - 阅读路径指南
```

### 第五步：提交

```bash
git add .docs/
git commit -m "docs: add progressive documentation structure

- Add meta layer: navigation guide, glossary, history
- Add fundamentals layer: vision, domain, concepts
- Add architecture layer: overview, ADRs, systems, cross-cutting, evolution
- Add modules layer: core, supporting, infrastructure domains
- Add implementation layer: API, schemas, codebase, changes
- Add operations layer: onboarding, deployment, runbooks, troubleshooting
- Add reference layer: resources, tools, templates
- Add progressive navigation: START-HERE.md, index.md"
```

---

## 边界情况处理

| 情况 | 处理策略 |
|-----|---------|
| `.docs/` 已存在 | 创建 `.docs.backup.{timestamp}/`，保留历史 |
| 混合技术栈 | 在 30-modules/ 下按技术栈再分组 |
| 遗留系统 | 增加 `20-architecture/05-evolution/legacy-integration.md` |
| 多租户/多环境 | 在 50-operations/ 下增加 `environments/` 子目录 |
| 合规要求严格 | 在 20-architecture/04-cross-cutting/ 下增加 `compliance/` |
| 开源项目 | 在 10-fundamentals/ 下增加 `contributing/` |

---

## 与相关 Skill 的集成

- **summary-and-commit**: 文档生成完成后自动提交，并生成提交摘要
- **repo-scanner**: 深度扫描代码结构，辅助生成分层文档
- **todo**: 将文档生成任务分解为层级任务，追踪进度
- **github-mcp-boboyun**: 将ADR、架构文档同步到GitHub Wiki

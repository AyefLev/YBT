# 研备通 AI 阶段性完善 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前研备通 AI MVP 分阶段完善为可 Docker 演示、符合七层架构表达、具备多 AI、异步、观测日志、课程体系、题库、图文题与真实机构交付价值的系统。

**Architecture:** 当前系统保留 FastAPI + Vue + Docker Compose 主体结构，并通过 Nginx API Gateway、FastAPI API 服务、Redis 异步任务队列、独立 Worker、PostgreSQL/Redis 数据层拆分运行边界。后续按“先稳定现有功能，再补数据层和 AI 编排，再增强图文题与机构工作流，最后做演示和市场化包装”的顺序推进。每阶段都必须有可运行功能、可验证测试和可展示材料，避免只堆概念。

**Tech Stack:** FastAPI, SQLAlchemy, SQLite/PostgreSQL, Redis, Vue 3, TypeScript, Vite, Docker Compose, python-docx, OpenAI-compatible LLM APIs, pytest, Vitest.

---

## 1. 当前基线

当前系统已经具备：

- 用户认证与 RBAC。
- 机构知识库上传、解析、检索。
- 备课生成、习题生成、合规检查。
- 课程体系、题库管理、教研审核的初版。
- 多 AI 评审流程的雏形。
- 观测日志接口。
- Docker Compose 网关化演示启动。
- DOCX 导出。

当前明显短板：

- 课程体系仍偏“数据录入”，缺少围绕课次和知识点的完整教学资产闭环。
- 习题生成质量依赖 prompt，数学公式、图文题、综合题仍需要更强结构化控制。
- 真实图文题需要视觉模型、图片素材管理和导出策略。
- 数据层目前偏单库文件化，答辩时不够贴合“持久化数据库 + 缓存数据库”的架构表达。
- 多 AI 还需要从“同一模型多角色”升级为“多供应商/多模型互评”。
- 观测日志需要更像真实系统：请求日志、模型日志、任务日志、错误追踪、演示页面。
- 市场价值需要明确落到机构教研流程，而不是只展示通用大模型生成文本。

---

## 2. 七层架构对齐

后续所有阶段都要能映射到老师给出的七层架构：

| 架构层 | 当前状态 | 完善方向 |
| --- | --- | --- |
| 1. 基础设施层 | Docker 本地部署 | Docker Compose 固化演示；通过 gateway/api/worker/postgres/redis 拆分运行边界 |
| 2. 数据层 | SQLite 文件库 + Docker PostgreSQL/Redis | PostgreSQL 持久化库、Redis 缓存库和任务队列，保留 SQLite 本地简化模式 |
| 3. 业务层 | 后端业务模块已拆分 | 强化课程、题库、审核、导出、图文题业务闭环 |
| 4. 业务 API 接口层 | FastAPI 接口已具备 | 扩展 AI 编排、视觉模型、缓存、日志 API |
| 5. API Gateway 层 | Nginx 统一入口 + FastAPI API | 统一入口、路由转发、异步任务、请求追踪、限时/失败处理、统一错误响应 |
| 6. 表示层 | Vue Web UI | 全中文界面、演示仪表盘、可视化日志、公式/图片预览 |
| 7. 终端层 | 浏览器访问 | Docker 一键启动后通过浏览器演示，后续可扩展桌面壳 |

---

## 3. 阶段一：稳定现有功能和演示基础

**目标：** 先把当前功能做稳，避免答辩或演示时出现“生成失败看不懂、导出很丑、页面中英混杂、Docker 跑不起来”的问题。

**优先级：最高。**

### Task 1: 统一中文界面和术语

**Files:**

- Modify: `frontend/src/layouts/WorkbenchLayout.vue`
- Modify: `frontend/src/pages/*.vue`
- Modify: `README.md`

- [ ] 检查所有页面是否仍存在英文导航、英文按钮、英文状态文案。
- [ ] 将 `Workbench`、`Lesson Prep`、`Exercise Gen`、`Knowledge Base` 等统一改成“工作台、备课生成、习题生成、机构知识库”。
- [ ] 将 `low/medium/high` 在 UI 上统一显示为“低风险/中风险/高风险”。
- [ ] 保留后端字段值为英文枚举，前端负责翻译展示。
- [ ] Run:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

**验收标准：**

- 登录后主流程页面没有明显英文业务文案。
- 前端测试和构建通过。

### Task 2: 修复 DOCX 导出观感

**Files:**

- Modify: `backend/app/exports/service.py`
- Test: `backend/tests/test_exercises_exports.py`

- [ ] 确保导出的 Word 不出现 `[公式]`、`[SVG]`、`<svg>`、大量原始 LaTeX 源码。
- [ ] 矩阵公式优先转成 Word 表格或可读文本。
- [ ] SVG 题图先转成“示意图说明”，后续阶段再升级为图片嵌入。
- [ ] 课程大纲、题包、备课、习题导出都使用中文标签。
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_exercises_exports.py tests\test_phase3_exports.py -q --basetemp .pytest-tmp
```

**验收标准：**

- 用户下载的 DOCX 可直接打开阅读。
- 不再出现协议标记和源码块。

### Task 3: Docker 演示入口固定

**Files:**

- Modify: `docker-compose.yml`
- Modify: `README.md`
- Optional: `docs/phase3-demo-script.md`

- [ ] 明确 Docker 启动命令：

```powershell
docker compose up --build --force-recreate
```

- [ ] README 中写清楚：
  - 统一入口：`http://localhost:8080`
  - API 文档：`http://localhost:8080/docs`
  - 网关健康：`http://localhost:8080/gateway/health`
- [ ] 检查容器启动时 `.env` 缺失的错误提示是否清楚。
- [ ] Run:

```powershell
docker compose config
docker compose up --build
```

**验收标准：**

- 演示时可以从 Docker 一条命令启动。
- 出问题时能说明是 Docker、网络代理、API key 还是配置问题。

---

## 4. 阶段二：数据层升级，满足“持久化 + 缓存”

**目标：** 从“本地 SQLite MVP”升级为更符合系统架构表达的数据层：PostgreSQL 负责持久化，Redis 负责缓存和任务状态。

**优先级：高。**

### Task 4: Docker Compose 增加 PostgreSQL 和 Redis

**Files:**

- Modify: `docker-compose.yml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/conftest.py`

- [ ] 在 Compose 中增加 `postgres` 服务。
- [ ] 在 Compose 中增加 `redis` 服务。
- [ ] 后端容器默认使用：

```dotenv
DATABASE_URL=postgresql+psycopg://yanbeitong:yanbeitong@postgres:5432/yanbeitong
REDIS_URL=redis://redis:6379/0
```

- [ ] 本地开发仍允许 SQLite：

```dotenv
DATABASE_URL=sqlite:///../data/app.db
```

- [ ] Run:

```powershell
docker compose up --build
```

**验收标准：**

- Docker 演示时使用 PostgreSQL + Redis。
- 本地不装数据库时仍可用 SQLite 运行开发。

### Task 5: 引入缓存服务层

**Files:**

- Create: `backend/app/cache/client.py`
- Create: `backend/app/cache/service.py`
- Modify: `backend/app/materials/service.py`
- Modify: `backend/app/ai/service.py`
- Test: `backend/tests/test_cache.py`

- [ ] 新增 Redis 客户端封装，配置缺失时允许降级为内存缓存。
- [ ] 缓存模型能力接口 `/api/ai/capabilities` 的短期结果。
- [ ] 缓存知识库检索高频查询结果，设置 TTL。
- [ ] 后台任务状态写入 Redis，数据库只保存最终任务日志。
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_cache.py tests\test_materials_retrieval.py tests\test_ai.py -q --basetemp .pytest-tmp
```

**验收标准：**

- 可以对老师解释：PostgreSQL 是持久化数据库，Redis 是缓存数据库和任务状态缓存。
- Redis 不可用时系统不直接崩溃，而是给出日志或降级。

---

## 5. 阶段三：多 AI 编排和反幻觉机制

**目标：** 将“多 AI”从配置项升级为真实可展示流程：生成模型、审核模型、修订模型可以不同，并可展示模型间分歧。

**优先级：高。**

### Task 6: 多模型配置标准化

**Files:**

- Modify: `backend/app/core/config.py`
- Modify: `backend/app/ai/schemas.py`
- Modify: `backend/app/ai/router.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_ai.py`

- [ ] 支持三类文本模型：

```dotenv
LLM_GENERATE_MODEL=mimo-v2.5-pro
LLM_REVIEW_MODEL=deepseek-v4-pro
LLM_REVISE_MODEL=mimo-v2.5-pro
```

- [ ] 支持不同供应商 Base URL 和 API Key，至少预留：
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
  - `REVIEW_LLM_BASE_URL`
  - `REVIEW_LLM_API_KEY`
- [ ] `/api/ai/capabilities` 返回当前启用的模型角色。
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_ai.py -q --basetemp .pytest-tmp
```

**验收标准：**

- 前端能显示“生成模型、审核模型、修订模型”。
- 即使用同一个模型，也能解释为三个 AI 角色；换 key 后能变成真实多模型。

### Task 7: 生成-审核-修订闭环

**Files:**

- Modify: `backend/app/ai/service.py`
- Modify: `backend/app/lessons/service.py`
- Modify: `backend/app/exercises/service.py`
- Modify: `frontend/src/pages/LessonPage.vue`
- Modify: `frontend/src/pages/ExercisePage.vue`
- Test: `backend/tests/test_ai.py`

- [ ] 生成模型输出初稿。
- [ ] 审核模型输出：
  - 事实风险
  - 题型格式风险
  - 学科/知识点偏离风险
  - 可读性建议
- [ ] 如果审核模型判定 `warning`，修订模型生成改进版。
- [ ] 前端显示：
  - 初稿
  - AI 复核意见
  - 修订后版本
  - 采用哪个版本保存
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_ai.py tests\test_lessons.py tests\test_exercises_exports.py -q --basetemp .pytest-tmp
```

**验收标准：**

- 演示时能说明“不是单模型直接输出，而是多 AI 互相检查减少幻觉”。
- 生成失败不再悄悄 Mock，测试时能明确看到真实 API 是否成功。

---

## 6. 阶段四：图文题和视觉模型能力

**目标：** 支持真实教学场景中的图片题、图表题、几何图、流程图、材料截图，而不是简单禁止图片。

**优先级：中高。**

### Task 8: 图片素材管理

**Files:**

- Create: `backend/app/assets/models.py`
- Create: `backend/app/assets/router.py`
- Create: `backend/app/assets/service.py`
- Create: `frontend/src/pages/AssetsPage.vue`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_assets.py`

- [ ] 支持上传图片素材：
  - png
  - jpg
  - jpeg
  - webp
- [ ] 保存图片元数据：
  - 文件名
  - MIME 类型
  - 大小
  - 所属用户
  - 用途标签
- [ ] 前端提供“图片素材库”。
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_assets.py -q --basetemp .pytest-tmp
```

**验收标准：**

- 用户可以上传图片题素材。
- 素材能被习题生成时引用。

### Task 9: 视觉模型接入

**Files:**

- Modify: `backend/app/core/config.py`
- Create: `backend/app/ai/vision.py`
- Modify: `backend/app/ai/router.py`
- Modify: `frontend/src/pages/ExercisePage.vue`
- Test: `backend/tests/test_vision_ai.py`

- [ ] 增加视觉模型配置：

```dotenv
VISION_LLM_BASE_URL=
VISION_LLM_API_KEY=
VISION_LLM_MODEL=
```

- [ ] 后端提供“图片理解”服务：
  - 输入图片 ID
  - 输出图片描述、可考查知识点、可能题型
- [ ] 若没有视觉 API key：
  - 前端明确显示“视觉模型未配置”
  - 不要假装已识别图片
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_vision_ai.py tests\test_ai.py -q --basetemp .pytest-tmp
```

**验收标准：**

- 图文题可以走“图片上传 -> 视觉识别 -> 文本模型生成题目”的流程。
- mimo-v2.5-pro 不能看图时，也能通过单独视觉模型补齐能力。

### Task 10: 图文题 DOCX 导出

**Files:**

- Modify: `backend/app/exports/service.py`
- Test: `backend/tests/test_exercises_exports.py`

- [ ] 支持把上传图片插入 DOCX。
- [ ] SVG 简单题图可转换为 PNG 后插入，或保留为可读说明。
- [ ] 图片题导出时包含：
  - 题干
  - 图片
  - 小问
  - 答案与解析
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_exercises_exports.py -q --basetemp .pytest-tmp
```

**验收标准：**

- 导出的图文题 Word 文档能看到图片，而不是只看到代码或占位文本。

---

## 7. 阶段五：课程体系和题库产品化

**目标：** 让系统从“能生成内容”变成“机构能沉淀课程资产和题库资产”。

**优先级：中高。**

### Task 11: 课程体系补全课次与知识点操作

**Files:**

- Modify: `frontend/src/pages/CoursesPage.vue`
- Modify: `backend/app/courses/router.py`
- Modify: `backend/app/courses/service.py`
- Test: `backend/tests/test_courses.py`

- [ ] 课程详情页支持：
  - 添加章节
  - 添加课次
  - 添加知识点
  - 将知识点关联到课次
- [ ] 删除或归档时给出清晰提示。
- [ ] 前端不再只显示“创建课程”和“考试类型”。
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_courses.py -q --basetemp .pytest-tmp
cd ..\frontend
npm.cmd run build
```

**验收标准：**

- 课程体系页面能体现“课程 -> 章节 -> 课次 -> 知识点”的结构。

### Task 12: 生成内容沉淀到题库

**Files:**

- Modify: `backend/app/questions/service.py`
- Modify: `backend/app/exercises/service.py`
- Modify: `frontend/src/pages/ExercisePage.vue`
- Modify: `frontend/src/pages/QuestionBankPage.vue`
- Test: `backend/tests/test_questions.py`

- [ ] 习题生成后支持“保存为题库草稿”。
- [ ] 如果生成的是整份练习，先允许用户手动选择或编辑题目结构。
- [ ] 题库记录包含：
  - 学科
  - 知识点
  - 题型
  - 难度
  - 题干
  - 答案
  - 解析
  - 来源材料/来源练习
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_questions.py tests\test_exercises_exports.py -q --basetemp .pytest-tmp
```

**验收标准：**

- AI 生成内容不只是一次性文本，而能进入题库成为机构资产。

---

## 8. 阶段六：观测日志 API 化和演示仪表盘

**目标：** 让“观测日志 API 化”可见、可讲、可演示。

**优先级：中。**

### Task 13: 日志类型补全

**Files:**

- Modify: `backend/app/logs/models.py`
- Modify: `backend/app/logs/router.py`
- Modify: `backend/app/ai/service.py`
- Modify: `backend/app/materials/service.py`
- Test: `backend/tests/test_admin_logs.py`

- [ ] 操作日志：用户做了什么。
- [ ] 模型日志：调用哪个模型、耗时、是否失败、是否兜底。
- [ ] 任务日志：材料解析、导出、异步任务状态。
- [ ] 请求日志：接口路径、状态码、耗时。
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_admin_logs.py -q --basetemp .pytest-tmp
```

**验收标准：**

- `/api/logs/*` 能展示系统运行痕迹。
- 演示时可以打开日志页证明系统不是黑盒。

### Task 14: 前端观测仪表盘

**Files:**

- Modify: `frontend/src/pages/AdminPage.vue`
- Create: `frontend/src/pages/ObservabilityPage.vue`
- Modify: `frontend/src/router.ts`
- Modify: `frontend/src/layouts/WorkbenchLayout.vue`

- [ ] 页面展示：
  - 最近模型调用
  - 最近异步任务
  - 最近错误
  - 真实模型成功率
  - Mock 使用次数
- [ ] 支持一键刷新。
- [ ] Run:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

**验收标准：**

- 答辩时能展示“观测日志 API 化 + 前端可视化”。

---

## 9. 阶段七：市场化演示和答辩材料

**目标：** 让老师和潜在客户能理解系统价值，不只是看到一堆功能页面。

**优先级：中。**

### Task 15: 演示数据脚本

**Files:**

- Create: `backend/scripts/seed_demo_data.py`
- Modify: `README.md`
- Create: `docs/demo-scenario.md`

- [ ] 一键生成演示账号。
- [ ] 一键生成课程、章节、课次、知识点。
- [ ] 一键生成知识库材料、题库题目、审核记录。
- [ ] Run:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

**验收标准：**

- 演示不用现场手动造大量数据。

### Task 16: 市场价值演示脚本

**Files:**

- Create: `docs/yanbeitong-demo-script.md`

- [ ] 用一个完整故事串联：
  1. 机构创建考研数学课程。
  2. 上传讲义。
  3. 生成课次备课。
  4. 生成矩阵乘法综合题。
  5. 多 AI 复核发现格式/事实问题。
  6. 保存到题库。
  7. 教研负责人审核。
  8. 导出 Word 练习包。
  9. 展示模型调用日志和 Docker 容器。
- [ ] 明确对比通用大模型：
  - 通用大模型只生成一次性文本。
  - 研备通 AI 管理机构课程、知识库、题库、审核和导出交付。

**验收标准：**

- 演示能回答“为什么客户要买，而不是直接用通用大模型”。

---

## 10. 全局验收标准

每个阶段完成后必须执行：

```powershell
cd <项目目录>\YBT\backend
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp

cd <项目目录>\YBT\frontend
npm.cmd test
npm.cmd run build

cd <项目目录>\YBT
docker compose config
```

Docker 演示验收：

```powershell
cd <项目目录>\YBT
docker compose up --build --force-recreate
```

访问：

- 统一入口：`http://localhost:8080`
- API 文档：`http://localhost:8080/docs`
- 网关健康：`http://localhost:8080/gateway/health`

---

## 11. 推荐执行顺序

1. 阶段一：稳定现有功能和演示基础。
2. 阶段二：PostgreSQL + Redis 数据层升级。
3. 阶段三：多 AI 编排和反幻觉机制。
4. 阶段五：课程体系和题库产品化。
5. 阶段四：图文题和视觉模型能力。
6. 阶段六：观测日志 API 化和演示仪表盘。
7. 阶段七：市场化演示和答辩材料。

说明：

- 图文题很重要，但依赖视觉模型 API、图片素材和导出能力，所以不应压在最前。
- 数据层和多 AI 是老师明确提出的技术点，应优先做成可展示能力。
- 课程体系和题库是市场价值核心，应在视觉能力前后持续完善。

---

## 12. 风险和控制

| 风险 | 表现 | 控制方式 |
| --- | --- | --- |
| 功能越做越散 | 页面很多但主流程不清楚 | 始终围绕“课程资产 -> 生成 -> 复核 -> 审核 -> 导出” |
| 模型不稳定 | 生成失败或跑题 | 关闭静默 Mock，展示真实错误，多 AI 复核 |
| 图文题复杂度过高 | 图片、公式、导出互相牵连 | 先做图片素材和视觉描述，再做 Word 图片嵌入 |
| 数据库切换风险 | SQLite 到 PostgreSQL 兼容问题 | 保留 SQLite 测试模式，Docker 使用 PostgreSQL |
| 演示失败 | Docker、代理、API key、网络问题 | 准备 Mock 演示数据，但 UI 必须标明 Mock |

---

## 13. 当前下一步建议

建议立即执行：

1. 完成阶段一剩余收尾，确保 Docker 演示稳定。
2. 开始阶段二，将 Docker Compose 升级为 PostgreSQL + Redis。
3. 同时准备视觉模型 API key，但不阻塞阶段二。
4. 阶段二完成后，再做多 AI 编排和视觉题。

这样顺序最适合答辩：

- 先证明系统稳定。
- 再证明符合七层架构和老师要求。
- 最后证明市场价值和功能深度。

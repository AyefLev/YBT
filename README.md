# 研备通 AI

研备通 AI 是面向考研、成人教育和机构教研场景的智能备课与教学内容管理系统。项目把课程体系、章节知识点、资料知识库、教案生成、习题生成、题库沉淀、教研审核、班级作业和多模型配置放在同一个工作台中，帮助教师围绕真实教学流程组织内容，而不是只做单次 AI 生成。

当前版本提供 Vue 3 前端、FastAPI 后端、PostgreSQL 业务数据库、Redis 缓存与任务队列、Qdrant 向量库、异步 Worker 和 Nginx 网关，支持 Docker 一键启动。

## 核心能力

- 账号与权限：管理员、教管、教师、待审核教师、学生等角色，基于 RBAC 控制工作台入口和 API 权限。
- 课程体系：维护课程、章节、课次和知识点，用于关联教案、习题、资料和题库。
- 资料知识库：上传 txt、md、docx、pdf、pptx 等资料，解析为片段后写入 PostgreSQL，并可索引到 Qdrant 做语义检索。
- 教案生成：教师可选择课程、章节、课次、知识点和资料范围，补充提示词与格式要求后生成可编辑教案。
- 习题生成：可关联课程章节、知识点、已有教案和知识库资料，生成题目、答案、解析等结构化内容。
- 多 AI 流程：支持生成、审核、修订、视觉、Embedding 等模型角色配置；生成后可进行多 AI 核验和自动修订。
- 视觉模型：提供图片上传分析接口，可用于图文题、教学图片理解等场景。
- PPT 生成：已提供基于教案的 PPTX 生成与下载接口，支持页数和描述参数。
- 教研审核：教案与题库内容可提交审核，教管可通过、拒绝或退回草稿。
- 班级与作业：教师创建班级、学生邀请码加入、教师发布作业、学生提交、教师批改。
- 运维观测：提供模型调用日志、后台任务日志、操作日志、Token 与费用视图、系统健康检查。
- 前端工作台：可收起侧边栏、按权限生成导航、统一入口管理教案、习题、资料、课程、班级、审核和系统管理。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vue Router、Pinia、Vite、TypeScript |
| 后端 | FastAPI、SQLAlchemy、Pydantic、pytest |
| 数据库 | PostgreSQL，开发模式可使用 SQLite |
| 缓存/队列 | Redis |
| 向量库 | Qdrant |
| 网关 | Nginx |
| 部署 | Docker Compose |

## 项目结构

```text
YBT/
  backend/                 FastAPI 后端
    app/
      ai/                  模型配置、连通性检查、视觉分析、多模型调用
      auth/                登录注册、RBAC、管理员用户管理
      classrooms/          班级、作业、提交与批改
      courses/             课程、章节、课次、知识点
      materials/           资料上传、解析、片段管理
      retrieval/           语义检索与向量库封装
      lessons/             教案生成、保存、版本、审核提交
      exercises/           习题生成、保存、版本
      questions/           题库管理
      reviews/             教研审核
      presentations/       教案 PPTX 生成与下载
      exports/             DOCX/PPTX 导出记录
      logs/                操作、模型、任务日志
      tasks/               Redis 队列和 Worker 任务处理
    scripts/               演示数据脚本
    tests/                 后端测试
  frontend/                Vue 工作台
    src/
      layouts/             工作台布局
      pages/               业务页面
      navigation/          侧边栏导航配置
      api/                 API 客户端
      stores/              Pinia 状态
  infra/gateway/           Nginx 网关配置
  data/                    上传文件和导出文件
  docs/                    架构、演示和规划文档
  docker-compose.yml       Docker 编排
```

## Docker 启动

先准备后端环境变量：

```powershell
Copy-Item backend\.env.example backend\.env
```

至少需要把 `backend/.env` 中的 `JWT_SECRET` 改成 32 位以上的随机字符串。需要真实模型时，再配置各模型 API Key。

启动完整环境：

```powershell
docker compose up --build
```

启动后访问：

```text
工作台：http://localhost:8080
API 文档：http://localhost:8080/docs
网关健康检查：http://localhost:8080/gateway/health
```

默认 compose 会启动：

- `gateway`：Nginx 统一入口，转发前端页面、`/api/*` 和 Swagger 文档。
- `frontend`：Vue 工作台。
- `backend`：FastAPI API 服务。
- `worker`：异步任务服务，处理资料解析、向量索引、导出和 PPT 生成等任务。
- `postgres`：业务数据库。
- `redis`：缓存、任务队列和短期状态。
- `qdrant`：资料片段向量索引。

如需扩展 API 或 Worker：

```powershell
docker compose up --build --scale backend=2 --scale worker=2
```

## 本地开发

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

前端默认地址：

```text
http://127.0.0.1:5173
```

Vite 会把 `/api` 代理到 `http://127.0.0.1:8000`。

## 模型与向量库配置

系统支持通过数据库或 `.env` 配置不同用途的模型。管理端页面可维护生成、审核、修订、视觉等模型 API 配置；没有独立配置时会回退到通用 LLM 配置。

常用环境变量：

```dotenv
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=
LLM_MODEL=
LLM_GENERATE_MODEL=
LLM_REVIEW_MODEL=
LLM_REVISE_MODEL=
GENERATE_LLM_BASE_URL=
GENERATE_LLM_API_KEY=
REVIEW_LLM_BASE_URL=
REVIEW_LLM_API_KEY=
REVISE_LLM_BASE_URL=
REVISE_LLM_API_KEY=
LLM_MULTI_AGENT_REVIEW=true
LLM_TIMEOUT_SECONDS=120
LLM_MOCK_ON_FAILURE=true
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=128
VECTOR_STORE_PROVIDER=qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=yanbeitong_material_chunks
```

模型相关接口：

- `GET /api/ai/capabilities`：查看当前模型能力与配置状态。
- `GET /api/ai/connectivity?probe=true`：主动探测模型连通性。
- `GET/PATCH /api/ai/admin/provider-configs`：管理员维护模型配置。
- `POST /api/ai/vision/analyze`：上传图片并调用视觉模型分析。

## 主要页面

- `/login`：登录。
- `/register`：注册。
- `/dashboard`：教研工作台总览。
- `/dashboard/lesson/generate`：生成教案。
- `/dashboard/lesson/records`：已有教案。
- `/dashboard/exercise/generate`：生成练习。
- `/dashboard/exercise/records`：已有练习。
- `/dashboard/materials/library`：资料库。
- `/dashboard/materials/upload`：上传资料。
- `/dashboard/courses`：课程体系。
- `/dashboard/questions`：题库管理。
- `/dashboard/classrooms`：班级与作业。
- `/dashboard/reviews`：教研审核。
- `/dashboard/compliance`：内容检查。
- `/dashboard/observability`：运行总览。
- `/dashboard/observability/token`：Token 与费用。
- `/dashboard/health`：系统检查。
- `/dashboard/admin/users`：用户管理。
- `/dashboard/admin/api`：模型 API 配置。

## 主要 API

认证与用户：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET/POST/PATCH /api/admin/users`
- `GET /api/admin/teacher-applications`
- `POST /api/admin/teacher-applications/{user_id}/approve`

课程、资料与检索：

- `GET/POST /api/courses`
- `GET/PATCH/DELETE /api/courses/{course_id}`
- `POST /api/courses/{course_id}/chapters`
- `POST /api/chapters/{chapter_id}/sessions`
- `POST /api/courses/{course_id}/knowledge-points`
- `POST /api/materials/upload`
- `GET /api/materials`
- `GET /api/materials/{id}`
- `GET /api/materials/{id}/chunks`
- `POST /api/materials/{id}/reparse`
- `DELETE /api/materials/{id}`
- `POST /api/retrieval/search`

教案、习题、题库与审核：

- `POST /api/lessons/generate`
- `GET /api/lessons`
- `POST /api/lessons/{lesson_id}/versions`
- `POST /api/lessons/{lesson_id}/submit-review`
- `POST /api/exercises/generate`
- `GET /api/exercises`
- `POST /api/exercises/{exercise_id}/versions`
- `GET/POST /api/questions`
- `GET/PATCH/DELETE /api/questions/{question_id}`
- `POST /api/questions/{question_id}/submit-review`
- `GET /api/reviews/pending`
- `POST /api/reviews/{resource_type}/{resource_id}/approve`
- `POST /api/reviews/{resource_type}/{resource_id}/reject`
- `POST /api/reviews/{resource_type}/{resource_id}/return-draft`

导出与 PPT：

- `POST /api/exports/lesson/{lesson_id}/docx`
- `POST /api/exports/exercise/{exercise_id}/docx`
- `POST /api/exports/course/{course_id}/outline-docx`
- `POST /api/exports/questions/docx`
- `POST /api/presentations/lesson/{lesson_id}/generate`
- `GET /api/presentations/exports/{export_id}/pptx`

班级与作业：

- `GET/POST /api/classrooms`
- `POST /api/classrooms/join`
- `GET /api/classrooms/{classroom_id}/students`
- `POST /api/classrooms/{classroom_id}/assignments`
- `GET /api/assignments/my`
- `POST /api/assignments/{assignment_id}/submit`
- `POST /api/submissions/{submission_id}/grade`

日志与系统：

- `POST /api/compliance/check`
- `GET /api/logs/operations`
- `GET /api/logs/models`
- `GET /api/logs/jobs`
- `GET /api/health`

## 测试与构建

后端：

```powershell
cd backend
python -m pytest -v
```

前端：

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

## 演示数据

Docker 环境启动后可执行：

```powershell
docker compose exec backend python scripts/seed_demo_data.py
```

本地后端环境可执行：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

默认演示账号：

- 系统管理员：`demo_admin` / `Demo123456`
- 教管账号：`demo_manager` / `Demo123456`

更完整的演示路线见 `docs/demo-seed-and-walkthrough.md`。

## 备注

仓库中的部分历史文档存在编码损坏问题，当前 README 已重新整理为可读中文。后续如果继续维护文档，建议统一使用 UTF-8 编码并在提交前检查 GitHub 预览效果。

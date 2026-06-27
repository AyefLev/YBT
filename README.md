# 研备通 AI

研备通 AI 是面向成人考研机构的智能备课与教研辅助系统。当前版本包含认证与 RBAC、管理员/教师/学生分级、教师申请审核、班级邀请码、作业提交与批改、机构知识库、材料解析、向量检索、备课生成、习题生成、合规检查、多 AI 协同评审、DOCX 导出、观测日志、管理接口、API 网关、Redis 异步任务队列、Qdrant 向量数据库和 Docker 演示启动。

## 后端运行

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `backend/.env`，至少设置一个长度不少于 32 位的 `JWT_SECRET`。如需自动创建管理员，也配置：

```dotenv
ADMIN_BOOTSTRAP_USERNAME=admin
ADMIN_BOOTSTRAP_EMAIL=admin@example.com
ADMIN_BOOTSTRAP_PASSWORD=请替换成长密码
ADMIN_BOOTSTRAP_DISPLAY_NAME=System Admin
```

启动后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 前端运行

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

默认前端地址：

```text
http://127.0.0.1:5173
```

## AI 配置

后端默认按“真实 API 优先，Mock 兜底”的方式工作。可在 `backend/.env` 中配置 OpenAI 兼容接口：

```dotenv
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
LLM_API_KEY=你的真实密钥
LLM_MODEL=mimo-v2.5-pro
LLM_GENERATE_MODEL=mimo-v2.5-pro
LLM_REVIEW_MODEL=mimo-v2.5-pro
LLM_REVISE_MODEL=mimo-v2.5-pro
GENERATE_LLM_BASE_URL=
GENERATE_LLM_API_KEY=
REVIEW_LLM_BASE_URL=
REVIEW_LLM_API_KEY=
REVISE_LLM_BASE_URL=
REVISE_LLM_API_KEY=
LLM_MULTI_AGENT_REVIEW=true
LLM_TIMEOUT_SECONDS=60
LLM_MOCK_ON_FAILURE=true
VECTOR_STORE_PROVIDER=qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=yanbeitong_material_chunks
EMBEDDING_MODEL=local-hash-embedding-v1
EMBEDDING_DIMENSIONS=128
```

`LLM_MULTI_AGENT_REVIEW=true` 后，备课和习题生成会执行“生成 -> AI 评审”的多 AI 流程。

如果 `GENERATE_LLM_*`、`REVIEW_LLM_*`、`REVISE_LLM_*` 留空，系统会回退使用通用的 `LLM_BASE_URL` 和 `LLM_API_KEY`。如果填写独立配置，则生成、审核、修订可以分别调用不同供应商或不同模型。

## 二阶段能力

- 知识库管理：材料列表、详情、片段查看、删除、重解析。
- 文档解析增强：支持 txt、md、docx、pdf、pptx，并记录页码或幻灯片来源。
- 异步处理：材料上传后由后台线程执行解析，解析状态包括 `pending`、`parsing`、`parsed`、`empty`、`failed`。
- 观测日志：`/api/logs/jobs` 查看后台任务日志，`/api/logs/models` 查看模型调用日志。
- API 化：核心工作流可通过 `http://127.0.0.1:8000/docs` 直接调用。
- 分级账号：管理员负责系统运维、用户/RBAC、日志和机构知识库全局维护；教管负责教研审核和教学域课程/班级管理；教师管理自己的课程/班级/作业/个人资源；学生通过邀请码加入班级并提交作业。

## Docker 网关化演示启动

先确认 `backend/.env` 已配置 `JWT_SECRET`。如需真实模型，再填写 `LLM_API_KEY`。

```powershell
docker compose up --build
```

启动后访问：

```text
统一入口：http://localhost:8080
API 文档：http://localhost:8080/docs
网关健康：http://localhost:8080/gateway/health
```

Docker 演示环境会同时启动：

- `gateway`：Nginx API Gateway，统一转发前端页面、`/api/*` 和 Swagger 文档。
- `postgres`：持久化数据库，保存用户、课程、知识库、题库、审核、日志等业务数据。
- `redis`：缓存数据库，用于短期缓存模型能力、任务队列、任务状态和高频查询结果。
- `qdrant`：向量数据库，保存材料分块 embedding，用于机构知识库语义检索。
- `backend`：FastAPI API 服务，只处理同步请求和业务编排。
- `worker`：异步任务服务，从 Redis 队列消费材料解析、导出、后续 PPT 生成等后台任务。
- `frontend`：Vue Web 界面，只通过网关访问后端 API。

如需模拟更高并发的 API 或后台任务，可以横向扩容：

```powershell
docker compose up --build --scale backend=2 --scale worker=2
```

本地轻量开发仍可在 `backend/.env` 中使用 SQLite：

```dotenv
DATABASE_URL=sqlite:///../data/app.db
REDIS_URL=
TASK_QUEUE_MODE=inline
VECTOR_STORE_PROVIDER=disabled
```

服务化边界和新增模块约定见 [docs/service-architecture.md](docs/service-architecture.md)，当前架构、文件树、API 流和功能流程见 [docs/current-architecture-and-flows.md](docs/current-architecture-and-flows.md)。

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

## 主要接口

- `POST /api/auth/register`：注册教师用户
- `POST /api/auth/login`：登录获取 Bearer Token
- `GET/POST/PATCH /api/admin/users`：管理员用户数据库管理
- `GET /api/admin/teacher-applications`：教师申请列表
- `POST /api/admin/teacher-applications/{user_id}/approve`：通过教师申请
- `POST /api/materials/upload`：上传材料，可按权限写入 `personal` 或 `public` 资源域
- `GET /api/materials`：材料列表，教师可见个人资源和公共资源，教管/管理员可见全局
- `GET /api/materials/{id}`：材料详情
- `GET /api/materials/{id}/chunks`：材料片段
- `POST /api/materials/{id}/reparse`：重解析材料
- `DELETE /api/materials/{id}`：删除材料
- `POST /api/retrieval/search`：检索材料片段
- `POST /api/lessons/generate`：生成备课内容
- `POST /api/exercises/generate`：生成习题
- `POST /api/compliance/check`：合规检查
- `POST /api/exports/lesson/{lesson_id}/docx`：导出备课 DOCX
- `POST /api/exports/exercise/{exercise_id}/docx`：导出习题 DOCX
- `GET /api/logs/operations`：操作日志
- `GET /api/logs/models`：模型调用日志
- `GET /api/logs/jobs`：后台任务日志
- `GET/PATCH /api/ai/admin/provider-configs`：管理员维护生成/审核/修订/视觉模型 API 配置
- `GET /api/admin/roles`、`GET /api/admin/users`：管理端 RBAC 数据
- `GET/POST /api/classrooms`：班级列表、创建班级
- `POST /api/classrooms/join`：学生通过邀请码加入班级
- `GET /api/classrooms/{classroom_id}/students`：教师/教管/管理员按权限查看班级学生
- `POST /api/classrooms/{classroom_id}/assignments`：教师或教管发布作业，系统管理员只读不可发布
- `GET /api/assignments/my`：学生查看自己的作业
- `POST /api/assignments/{assignment_id}/submit`：学生提交作业
- `POST /api/submissions/{submission_id}/grade`：教师批改作业

## Phase 3 Institutional Workflow

- Course system: manage courses, chapters, sessions, and knowledge points.
- Question bank: save reusable structured questions with type, difficulty, options, answer, analysis, tags, and review status.
- Teaching review: teachers submit lessons and questions; teaching managers approve or reject teaching content; teachers return rejected own content to draft.
- DOCX exports: export course outlines and question practice packages.
- Frontend pages: `/dashboard/courses`, `/dashboard/questions`, and `/dashboard/reviews`.

Key APIs:

- `GET/POST /api/courses`
- `GET/PATCH/DELETE /api/courses/{course_id}`
- `POST /api/courses/{course_id}/chapters`
- `POST /api/chapters/{chapter_id}/sessions`
- `POST /api/courses/{course_id}/knowledge-points`
- `GET/POST /api/questions`
- `GET/PATCH/DELETE /api/questions/{question_id}`
- `POST /api/questions/{question_id}/submit-review`
- `POST /api/lessons/{lesson_id}/submit-review`
- `GET /api/reviews/pending`
- `POST /api/reviews/{resource_type}/{resource_id}/approve`
- `POST /api/reviews/{resource_type}/{resource_id}/reject`
- `POST /api/reviews/{resource_type}/{resource_id}/return-draft`
- `POST /api/exports/course/{course_id}/outline-docx`
- `POST /api/exports/questions/docx`
- `POST /api/presentations/lesson/{lesson_id}/generate`

## 演示数据初始化

从 Docker 启动后，可另开一个 PowerShell 窗口执行：

```powershell
docker compose exec backend python scripts/seed_demo_data.py
```

本地开发模式可执行：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

默认演示账号：

- 系统管理员：`demo_admin` / `Demo123456`
- 教管演示账号：`demo_manager` / `Demo123456`

详细演示路线见 [docs/demo-seed-and-walkthrough.md](docs/demo-seed-and-walkthrough.md)。

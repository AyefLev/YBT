# 研备通 AI 服务化重构说明

## 1. 运行边界

当前系统采用“网关 + API 服务 + 异步 Worker + 数据层”的拆分方式：

- `gateway`：统一入口，基于 Nginx 转发前端页面、后端 API、Swagger 文档。
- `frontend`：Vue WebUI，只通过相对路径 `/api/*` 调用后端。
- `backend`：FastAPI API 服务，只处理同步请求、鉴权、路由和业务编排。
- `worker`：后台任务服务，从 Redis 队列消费异步任务。
- `postgres`：持久化数据库，保存用户、课程、题库、材料、日志等业务数据。
- `redis`：缓存数据库，同时承载任务队列和短期状态缓存。
- `qdrant`：向量数据库，保存材料分块 embedding，支撑机构知识库语义检索。

外部用户只访问网关：

```text
http://localhost:8080
```

API 文档：

```text
http://localhost:8080/docs
```

## 2. 模块协作约定

业务模块仍保留在 `backend/app/<module>` 下，每个模块遵循：

- `router.py`：只暴露 HTTP API。
- `service.py`：业务逻辑，不直接依赖前端。
- `models.py`：数据库模型。
- `schemas.py`：API 输入输出模型。

模块之间优先通过以下方式协作：

1. 同步能力：通过 FastAPI API 调用或明确的 service 函数编排。
2. 异步能力：投递任务到 Redis 队列，由 worker 消费。
3. 共享状态：持久化数据写 PostgreSQL，短期状态写 Redis，语义向量写 Qdrant。

不要让前端直接访问数据库、文件目录或某个内部模块。

## 3. 异步任务机制

任务队列入口：

```python
from app.tasks.queue import enqueue_task

enqueue_task(
    "material.parse",
    {"material_id": material_id},
    queue="materials",
)
```

任务处理器注册在：

```text
backend/app/tasks/handlers.py
```

当前已注册：

- `material.parse`：材料解析任务。
- `material.index_vectors`：材料分块向量化和 Qdrant 索引任务。

用户与班级这类强一致的业务操作仍走同步 API 和 PostgreSQL 事务：管理员审批教师、创建/停用账号，教师创建班级和布置作业，学生加入班级和提交作业，都在 API 请求内完成。

后续新增 PPT 生成模块时，可以增加：

```python
def handle_presentation_generate(payload: dict[str, Any]) -> None:
    ...

TASK_HANDLERS["presentation.generate"] = handle_presentation_generate
```

建议队列命名：

- `materials`：材料解析、重解析、向量化。
- `exports`：批量 DOCX/PPT/PDF 导出。
- `presentations`：PPT 生成、模板渲染。
- `vision`：图片理解、图文题解析。

## 4. 缓存策略

当前 Redis 用于：

- AI 能力查询缓存：`ai:capabilities`。
- 知识库检索结果缓存：`retrieval:search:*`。
- 材料解析状态缓存：`material:{id}:parse_status`。
- 异步任务队列：`ybt:tasks:<queue>`。

建议后续缓存只放短期状态和可重新计算结果，不把权威业务数据只放 Redis。

## 5. 向量检索链路

材料知识库采用“关系型元数据 + 向量库索引”的拆分：

1. 前端上传资料到 `/api/materials/upload`。
2. API 服务保存文件和 `materials` 记录，然后投递 `material.parse`。
3. Worker 解析 txt、md、docx、pdf、pptx，写入 `material_chunks`。
4. 解析成功后投递 `material.index_vectors`。
5. Worker 生成本地 deterministic embedding，并将 chunk id、material id、owner id、resource scope 等 payload 写入 Qdrant。
6. `/api/retrieval/search` 优先按资源域权限和材料过滤 Qdrant 向量召回，再回 PostgreSQL 读取片段正文和来源。
7. 如果 Qdrant 未配置或暂时不可用，检索服务自动回退到关键词检索，保证演示流程不断。

当前默认 embedding 为 `local-hash-embedding-v1`，用于离线演示和测试。后续如接入真实 embedding API，只需替换 `backend/app/ai/embeddings.py` 的实现，材料解析和检索 API 不需要改。

## 6. 横向扩展

API 服务可以扩容：

```powershell
docker compose up --build --scale backend=2
```

后台任务也可以扩容：

```powershell
docker compose up --build --scale worker=2
```

如果某个模块任务很重，例如 PPT 生成，可以单独增加一个 worker 服务，只监听 `presentations` 队列。

## 7. 新模块接入建议

以 PPT 生成为例：

1. 新建 `backend/app/presentations/`。
2. 定义 `models.py` 保存生成记录和文件路径。
3. 定义 `schemas.py` 描述请求参数。
4. 定义 `router.py` 暴露 `/api/presentations/*`。
5. API 收到请求后先创建任务记录，再投递 `presentation.generate`。
6. worker 生成 PPT 文件后更新任务状态和导出记录。
7. 前端新增 `PresentationsPage.vue`，只调用 `/api/presentations/*`。
8. 网关不需要为新模块单独改路由，因为 `/api/*` 已统一转发。

这样新增功能不会挤进已有材料、备课、习题模块内部。

当前已经预留 `POST /api/presentations/lesson/{lesson_id}/generate` 和 `presentation.generate` 队列任务。现阶段 handler 只记录 skipped 任务日志；后续 PPT 组员可以独立实现模板渲染、文件落盘和下载接口。

## 8. 用户和权限边界

默认角色：

- `admin`：系统运维和机构管理角色，管理用户、角色、教师申请、日志、公共知识库和全部机构知识材料；可查看全局课程、班级、作业、备课、习题、题库，但不作为教师发布作业、批改作业或修改其他教师课程。
- `teaching_manager`：教导主任/教研管理角色，负责教研审核、课程和班级教学域管理，可管理教师课程和班级，可查看教学域全局数据。
- `teacher`：管理自己的课程、个人资料、班级、学生、作业、备课和习题；可使用公共资源，但不能查看其他教师个人资源。
- `student`：通过邀请码加入班级，查看作业，提交作业并查看批改结果。
- `pending_teacher`：教师申请待审核，无业务权限。

资源域：

- `personal`：教师个人资源域，只有上传者本人、教管和管理员可见；只有上传者本人或管理员可删除/重解析。
- `public`：公共机构资源域，教师均可检索使用；管理员和教管可上传公共资源，但只有管理员可删改所有公共资源，教管只能删改自己上传的公共资源。

权限实现位置：

- 权限码和默认角色：`backend/app/auth/permissions.py`。
- 默认角色种子和管理员权限同步：`backend/app/auth/service.py`。
- 课程所有权：`backend/app/courses/service.py`。
- 班级/作业管理域：`backend/app/classrooms/service.py`。
- 材料资源域和公共资源发布：`backend/app/materials/service.py`、`backend/app/materials/router.py`。
- 检索资源域过滤：`backend/app/retrieval/service.py`、`backend/app/retrieval/vector_store.py`。

模型 API 配置：

- 管理端接口：`/api/ai/admin/provider-configs`。
- 配置表：`ai_provider_configs`。
- 支持角色：`generate`、`review`、`revise`、`vision`。
- 运行规则：数据库配置启用时优先使用；未配置字段回退 `.env`；API Key 在接口响应中只返回是否已配置和脱敏预览。

班级和作业模块位于 `backend/app/classrooms/`：

- `classrooms`：班级和邀请码。
- `classroom_enrollments`：学生加入班级的关系。
- `assignments`：教师发布的作业。
- `assignment_submissions`：学生提交和教师批改结果。

前端入口是 `frontend/src/pages/ClassroomsPage.vue`，系统管理入口是 `frontend/src/pages/AdminPage.vue`。

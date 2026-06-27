# 研备通 AI 演示数据与演示流程

## 1. 从 Docker 启动系统

在项目根目录执行：

```powershell
cd <项目目录>\YBT
docker compose up --build
```

启动后访问：

- 统一入口：http://localhost:8080
- Swagger API 文档：http://localhost:8080/docs
- 网关健康检查：http://localhost:8080/gateway/health

## 2. 初始化演示数据

容器启动后，另开一个 PowerShell 窗口，在项目根目录执行：

```powershell
docker compose exec backend python scripts/seed_demo_data.py
```

如果不用 Docker、本地后端已启动，也可以执行：

```powershell
cd <项目目录>\YBT\backend
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

默认演示账号：

- 系统管理员：demo_admin / Demo123456
- 教管演示账号：demo_manager / Demo123456

脚本可重复执行，不会重复插入同一批演示课程、材料、习题、题库题目和日志。

## 3. 建议演示路线

1. 使用 `demo_admin` 登录系统，先进入演示检查，展示后端、数据库、缓存、向量数据库、模型配置和观测日志状态；需要验证真实模型 API 时，再点击“检测真实模型 API”按钮。
2. 进入工作台，展示备课数、习题数和待处理风险。
3. 切换到 `demo_manager`，进入课程体系，展示课程、章节、课次、知识点四级结构。
4. 进入班级与作业，展示教师创建班级、学生邀请码加入、作业提交和教师批改。
5. 进入机构知识库，展示演示材料和材料片段检索。
6. 进入习题生成，现场生成一道习题，说明系统按真实 API 调用模型；失败会直接暴露错误，便于测试。
7. 点击保存到题库，把生成内容沉淀为可复用题库资源。
8. 进入题库管理，展示题目可审核、可筛选、可导出。
9. 进入教研审核，展示教学内容从草稿到审核的流程。
10. 进入系统管理，展示管理员用户数据库、教师审核、角色权限。
11. 进入观测日志，展示模型调用、后台任务和错误统计。
12. 打开 Docker Desktop，展示 Gateway、PostgreSQL、Redis、Qdrant、后端 API、Worker、前端容器同时运行。
13. 打开 Swagger API 文档，展示系统能力已经 API 化。

## 4. 对应老师要求的展示点

- 多 AI：生成、审核、修订模型可分别配置。
- 用户分级：管理员负责系统管理和机构知识库全局维护，教管负责教学域管理和教研审核，教师/学生按各自业务范围操作；教师申请可由管理员审核。
- 班级作业：教师通过班级号/邀请码组织学生，学生提交作业，教师批改反馈。
- 异步：材料解析任务由后端后台任务处理，避免阻塞上传请求。
- 观测日志：模型调用日志、任务日志、错误汇总可在页面和 API 中查看。
- API 化：核心流程均通过 FastAPI 暴露，可在 Swagger 中直接演示。
- Docker 化：系统可通过 `docker compose up --build` 一键启动。
- 多数据层：PostgreSQL 用于持久化业务数据，Redis 用于缓存和任务队列，Qdrant 用于向量知识库检索。
- 异步任务：API 容器只投递任务，Worker 容器消费 Redis 队列。
- 向量数据库：材料解析后由 Worker 生成 embedding 并写入 Qdrant，检索接口优先走语义向量召回。
- API Gateway：外部统一从 `http://localhost:8080` 进入。
- 七层架构：前端展示层、FastAPI 网关层、业务 API 层、容器业务层、数据层、云/本地基础设施层都能在演示中对应说明。

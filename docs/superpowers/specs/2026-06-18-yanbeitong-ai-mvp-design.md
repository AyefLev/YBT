# 研备通 AI 第一版设计规格

日期：2026-06-18

## 1. 项目目标

第一版目标是完成一个可运行、可答辩、可继续扩展的教师备课工作台。系统服务成人考研机构内部教研场景，主线为“上传资料 -> 检索引用 -> 生成教案/习题 -> 合规检查 -> 保存版本 -> 导出 DOCX”。

本阶段不追求一次性覆盖详细设计文档中的全部模块，而是先把教师备课闭环做成真实可用的软件雏形。

## 2. 已确认范围

- 主线：教师备课。
- 技术栈：Vue + FastAPI + SQLite。
- 架构：模块化单体。
- AI 接入：真实 OpenAI-compatible API 优先，失败或未配置时 Mock 兜底。
- 模型配置：通过 `.env` 配置 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`。
- 知识库：第一版使用轻量文本检索，接口和数据结构预留未来 RAG/向量库升级。
- 资料类型：支持 `txt`、`md`、`docx`、`pdf`、`pptx`。
- 权限：完整用户注册、角色管理、权限配置。
- 版本：教案、习题、资料解析结果采用简化版本管理。
- 导出：支持教案 DOCX 和习题 DOCX。

## 3. 总体架构

第一版采用前后端分离的模块化单体架构。

```text
frontend/               Vue 教师工作台
backend/                FastAPI 后端
data/
  uploads/              上传资料
  exports/              导出文档
  app.db                SQLite 数据库
```

后端仍然是一个 FastAPI 服务，但按领域拆分模块，避免形成单个大文件。

```text
backend/app/
  main.py
  core/          配置、数据库、权限依赖、异常处理
  auth/          注册、登录、JWT、角色权限
  ai/            OpenAI-compatible 客户端、Mock 兜底、模型日志
  materials/     上传、解析、文本切片
  retrieval/     轻量检索，预留向量检索接口
  lessons/       教案生成、保存、版本
  exercises/     习题生成、保存、版本
  compliance/    风险词、隐私正则、审核记录
  resources/     资源库统一查询、版本恢复
  exports/       DOCX 导出
  logs/          操作日志
```

核心原则：

- 前端首页是教师工作台，不做营销落地页。
- 后端模块边界按业务领域划分，后续可独立拆出 AI、RAG、导出等服务。
- SQLite 表结构按后续迁移 MySQL/PostgreSQL 的习惯设计。
- 数据库只保存结构化数据和文件路径，大文件保存在本地文件目录。
- 所有生成、保存、导出、权限变更写入操作日志。

## 4. 前端页面结构

登录后根据角色展示菜单。首页优先服务备课流程。

第一版页面：

- 登录/注册页：支持注册、登录；管理员可管理角色和权限。
- 教师工作台首页：展示新建备课快捷入口、最近教案、最近资料、模型状态。
- 新建备课页：课程信息表单、知识库引用开关、教案编辑器、引用来源、合规结果、保存、导出。
- 习题生成页：知识点、题型、难度、数量、是否参考资料；结果以卡片展示，可保存版本并导出。
- 机构知识库页：上传资料，展示解析状态、切片数量、检索测试。
- 合规审核页：支持独立粘贴内容检测，也复用于教案和习题生成结果。
- 资源库页：查看教案、习题、资料，查看版本历史，恢复旧版本。
- 系统管理页：用户、角色、权限配置、操作日志、模型配置。

角色权限：

- 管理员：全部菜单。
- 教研主管：备课、习题、知识库、资源库、合规、日志查看。
- 教师：备课、习题、知识库、自己的资源。
- 运营：知识库、合规、资源库；市场分析后续扩展。

## 5. 后端 API

所有接口统一使用 `/api` 前缀。

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me

GET  /api/admin/users
POST /api/admin/users/{id}/roles
GET  /api/admin/roles
POST /api/admin/roles
POST /api/admin/roles/{id}/permissions

POST /api/materials/upload
GET  /api/materials
GET  /api/materials/{id}
POST /api/materials/{id}/reparse
POST /api/retrieval/search

POST /api/lessons/generate
POST /api/lessons/{id}/save-version
GET  /api/lessons
GET  /api/lessons/{id}
GET  /api/lessons/{id}/versions
POST /api/lessons/{id}/restore-version

POST /api/exercises/generate
POST /api/exercises/{id}/save-version
GET  /api/exercises
GET  /api/exercises/{id}
GET  /api/exercises/{id}/versions
POST /api/exercises/{id}/restore-version

POST /api/compliance/check
GET  /api/compliance/rules
POST /api/compliance/rules

POST /api/exports/lesson/{id}/docx
POST /api/exports/exercises/docx

GET  /api/logs/operations
GET  /api/logs/models
GET  /api/health
```

关键行为：

- `/api/lessons/generate` 在 `use_materials=true` 时先检索知识库，再拼接 Prompt。
- AI 调用失败自动回退 Mock，并在返回值中带 `provider_status`。
- 生成结果先返回前端编辑，用户点击保存后才写入资源和版本。
- 合规检测在生成后自动执行，导出前再次执行。
- 写操作记录 `operation_logs`。
- 模型调用和 Mock 兜底记录 `model_logs`。

## 6. 数据库设计

核心表：

```text
users
roles
permissions
role_permissions
user_roles
operation_logs

materials
material_chunks

lessons
lesson_versions

exercises
exercise_versions
exercise_tags

compliance_rules
compliance_logs

model_logs
export_records
```

关键字段：

```text
users
- id, username, email, password_hash, display_name, is_active, created_at

roles
- id, code, name, description

permissions
- id, code, name, module

materials
- id, title, file_name, file_type, file_path, uploader_id, parse_status, created_at

material_chunks
- id, material_id, chunk_index, content, page_no, slide_no, token_count
- future_vector_id, future_embedding_model

lessons
- id, title, subject, chapter, stage, duration_minutes, student_level
- current_content, owner_id, compliance_level, created_at, updated_at

lesson_versions
- id, lesson_id, version_no, content, change_note, created_by, created_at

exercises
- id, title, subject, knowledge_point, question_type, difficulty
- current_content_json, owner_id, compliance_level, created_at, updated_at

exercise_versions
- id, exercise_id, version_no, content_json, change_note, created_by, created_at

compliance_rules
- id, category, pattern, risk_level, suggestion, enabled

compliance_logs
- id, content_type, content_id, risk_level, matched_terms_json, suggestion_json, checked_at

model_logs
- id, task_type, provider, model, prompt_tokens, completion_tokens
- latency_ms, success, fallback_used, error_message, created_at

export_records
- id, resource_type, resource_id, file_path, exported_by, created_at
```

权限码示例：

- `lesson:create`
- `lesson:export`
- `exercise:create`
- `material:upload`
- `admin:user_manage`
- `admin:role_manage`
- `log:view`

版本恢复规则：

- 当前内容保存在 `lessons.current_content` 或 `exercises.current_content_json`。
- 每次保存都创建完整版本快照。
- 恢复旧版本时，把旧版本内容复制为当前内容，并创建一个新的版本记录。
- 不覆盖或删除历史版本。

## 7. AI 调用流程

真实 API 优先，Mock 兜底。

```text
业务模块发起请求
-> 拼接系统 Prompt、表单数据、检索片段
-> 检查是否配置真实 API
-> 调用 OpenAI-compatible API
-> 成功则返回真实模型结果
-> 失败、超时或未配置则调用 Mock
-> 写入 model_logs
-> 返回 provider_status 给前端
```

`.env` 配置：

```env
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
LLM_API_KEY=
LLM_MODEL=mimo-v2.5-pro
LLM_TIMEOUT_SECONDS=60
LLM_MOCK_ON_FAILURE=true
```

说明：截图中的 Base URL 技术上兼容 OpenAI 接口协议。但该套餐页面提示 API Key 不应用于自动化脚本或应用后端，因此系统只按协议兼容，不建议把该 Key 作为正式后端长期调用凭证。

## 8. 知识库与检索

资料上传流程：

```text
上传 txt/md/docx/pdf/pptx
-> 提取文本
-> 按段落、页或幻灯片切片
-> 保存 materials 和 material_chunks
-> 在备课或习题生成时检索 top_k 片段
-> 把片段和来源写入 Prompt
```

解析策略：

- `txt/md`：直接读取文本。
- `docx`：提取段落和表格文本。
- `pdf`：按页提取文本，保存 `page_no`。
- `pptx`：按幻灯片提取文本框内容，保存 `slide_no`。
- 扫描 PDF 或图片型 PPT：第一版不做 OCR，只提示未识别到可解析文本。

检索策略：

- 第一版使用关键词命中、简单文本相似度和来源过滤排序。
- 返回 `top_k` 片段、来源文件、页码或幻灯片编号。
- 接口保持 `/api/retrieval/search` 不变，未来可替换为 embedding + 向量库。

## 9. 合规检测

检测内容：

- 教育培训高风险承诺：保证上岸、100%通过、必过、保分、内部押题、命题人参与等。
- 隐私信息：手机号、邮箱、身份证号等。
- 版权风险：疑似长文本复制教材、讲义或未授权资料。
- 行业边界：提醒系统定位为成人考研机构，不面向义务教育阶段中小学学科培训。

输出：

- 风险等级：低、中、高。
- 命中词或命中正则。
- 风险位置。
- 修改建议。
- 审核日志。

教案和习题生成后自动检测。导出前再次检测；存在高风险时，前端提示用户确认或修改。

## 10. DOCX 导出

教案导出结构：

- 标题。
- 课程信息。
- 教学目标。
- 重点难点。
- 课堂流程。
- 板书/讲解结构。
- 互动问题。
- 课后任务。
- 引用来源。
- 合规提示。

习题导出结构：

- 标题。
- 知识点、题型、难度。
- 题目。
- 答案。
- 解析。
- 易错点。
- 标签。

导出文件保存到 `data/exports`，并写入 `export_records`。

## 11. 里程碑

1. 项目骨架
   - Vue 项目。
   - FastAPI 项目。
   - SQLite 初始化、配置、`.env.example`。
   - 健康检查接口。

2. 权限系统
   - 注册、登录、JWT。
   - 用户、角色、权限配置。
   - 菜单级权限和后端接口权限。

3. 知识库
   - 上传 `txt/md/docx/pdf/pptx`。
   - 文本解析、切片、保存。
   - 检索测试。

4. AI 与合规
   - OpenAI-compatible 客户端。
   - 真实 API 优先，Mock 兜底。
   - 模型调用日志。
   - 合规规则检测。

5. 教案主流程
   - 新建备课表单。
   - 引用知识库片段。
   - 生成、编辑、保存版本。
   - 历史版本查看和恢复。
   - 导出教案 DOCX。

6. 习题主流程
   - 按知识点生成习题。
   - 编辑、保存版本。
   - 导出习题 DOCX。

7. 资源库与日志
   - 教案、习题、资料统一列表。
   - 操作日志。
   - 模型日志。
   - 基础测试与演示数据。

## 12. 验收标准

- 能注册和登录，并按角色看到不同菜单。
- 管理员能创建角色并配置权限。
- 能上传至少一份 `docx`、`pdf` 或 `pptx` 并解析出文本片段。
- 能在备课生成时选择参考资料，并显示引用来源。
- 配置真实 API 时优先调用真实模型；API 不通时自动 Mock 兜底。
- 能生成一份结构化教案，编辑后保存为版本。
- 能生成习题，保存并查看版本。
- 输入“保证上岸、100%通过”能提示高风险。
- 能导出教案和习题 DOCX。
- 能查看操作日志和模型调用日志。

## 13. 第一版明确不做

- 不做向量数据库和 embedding，只预留升级接口。
- 不做 OCR。
- 不做完整审核发布流，只做版本管理。
- 不做支付、多租户 SaaS、移动端 App。
- 不做市场分析和成本 ROI 的完整实现，只保留后续扩展位。

## 14. 自审结论

- 本规格无未完成占位标记。
- 范围聚焦教师备课主线，没有把市场分析、ROI、支付、多租户等后续模块混入第一版。
- 架构、API、数据表和验收标准互相一致。
- AI 真实 API 和 Mock 兜底的优先级明确。
- 知识库检索的第一版实现和未来 RAG 升级边界明确。

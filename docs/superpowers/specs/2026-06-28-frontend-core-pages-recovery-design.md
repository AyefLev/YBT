# 前端核心页面恢复设计

日期：2026-06-28

## 背景与根因

提交 `8c5af90` 调整教案和练习题页面 UI 时，保留了两个 Vue 单文件组件的
`<template>` 与 `<style scoped>`，但删除了完整的 `<script setup lang="ts">`。
因此开发服务器仍能显示页面标题，模板中的表单、状态和事件绑定却全部未定义，
同时 `vue-tsc --noEmit` 报出大量 `TS2339`，生产构建失败。

受影响文件：

- `frontend/src/pages/LessonPage.vue`
- `frontend/src/pages/ExercisePage.vue`

当前 `frontend/src/layouts/WorkbenchLayout.vue` 及其未跟踪测试包含用户已有修改，
本次修复必须保留且不覆盖。

## 目标

1. 保留提交 `8c5af90` 引入的新版模板与样式。
2. 从父提交 `8fd45e9` 恢复两个页面完整的脚本逻辑。
3. 解决旧脚本与新版模板之间的少量接口差异。
4. 让教案生成、教案记录、练习生成和练习记录页面重新渲染并可操作。
5. 让前端单元测试和 `npm run build` 通过。
6. 让 Docker 重建后的前端通过 Nginx 网关正常访问。
7. embedding 统一使用 `text-embedding-v4`，不引入 `gte-rerank-v2`。

## 方案

采用“保留新版视图，恢复上一提交脚本”的最小恢复方案。

### 页面脚本

从 `8fd45e9` 中提取两个页面各自的 `<script setup lang="ts">`，插入当前组件模板之前。
恢复后先运行类型检查，用错误信息识别新版模板新增或改名的绑定，仅补充必要适配，
不整体回退模板，不重写业务流程。

### 回归测试

先新增一个源码结构回归测试，验证两个核心页面：

- 存在 `<script setup lang="ts">`；
- 定义模板依赖的核心状态；
- 定义生成、保存等核心事件；
- 不再退化成只有模板和样式的空壳组件。

测试必须在修复前失败、恢复脚本后通过。随后运行现有 Vitest 全量测试与生产构建。

### Embedding 配置

运行时 `backend/.env` 已配置 `text-embedding-v4`。为了避免 Docker Compose 的
`local-hash-embedding-v1` 覆盖运行时配置，将 Compose 默认值、`.env.example`
和 README 示例统一为 `text-embedding-v4`，维度统一为当前 Qdrant 集合使用的
128 维输出。管理员数据库中的 embedding provider 配置继续作为运行时首选配置。

`gte-rerank-v2` 不用于 embedding，也不在本次增加 rerank 阶段。

## 数据流

页面继续通过现有 API 客户端调用后端：

1. 用户选择课程、章节、课时、知识点和材料。
2. 页面组装请求并调用教案或练习生成 API。
3. 后端执行检索、生成、审核、修订和合规检查。
4. 页面展示生成内容、引用、审核意见和合规结果。
5. 用户保存后进入版本记录、导出或课件流程。

本次不修改后端接口契约和数据库结构。

## 错误处理

沿用原脚本现有的 loading、error、notice 状态和 API 异常处理。恢复过程中若新版模板
引用了旧脚本没有提供的字段，优先补充计算属性或薄适配函数，不改变后端数据格式。

## 验证标准

必须同时满足：

1. 新增回归测试经历 RED → GREEN。
2. `npm test` 全部通过。
3. `npm run build` 退出码为 0。
4. 浏览器登录后，教案和练习生成页出现完整表单。
5. 教案/练习记录路由能够渲染。
6. Docker Compose 重建前端后，网关和健康接口正常。
7. `/api/ai/capabilities` 显示 embedding 模型为 `text-embedding-v4`。

## 非目标

- 不重做页面视觉设计。
- 不改变生成、审核和修订模型。
- 不引入本地模型、reranker 或新的向量数据库。
- 不修复与两个核心页面无关的功能。

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '../api/client'

interface DatabaseTable {
  name: string
  label: string
  category: string
  row_count: number
  available: boolean
  note: string
}

interface DatabaseManagement {
  status: string
  kind: string
  table_count: number
  available_table_count: number
  total_rows: number
  message: string
  safety_notes: string[]
  tables: DatabaseTable[]
}

interface DemoSeedResult {
  message: string
  username: string
  password: string
  manager_username: string
  manager_password: string
  course_id: number
  chapter_id: number
  session_id: number
  knowledge_point_id: number
  material_id: number
  exercise_id: number
  question_id: number
}

const database = ref<DatabaseManagement | null>(null)
const seedResult = ref<DemoSeedResult | null>(null)
const loading = ref(false)
const seeding = ref(false)
const error = ref('')

const categoryGroups = computed(() => {
  const groups = new Map<string, DatabaseTable[]>()
  for (const table of database.value?.tables ?? []) {
    groups.set(table.category, [...(groups.get(table.category) ?? []), table])
  }
  return Array.from(groups.entries()).map(([category, tables]) => ({
    category,
    tables,
    rowCount: tables.reduce((total, table) => total + table.row_count, 0),
  }))
})
const knowledgeRows = computed(() => countTable('materials') + countTable('material_chunks'))
const contentRows = computed(() => countTable('lessons') + countTable('exercises') + countTable('question_bank_items'))

async function loadDatabase() {
  loading.value = true
  error.value = ''
  try {
    database.value = await api<DatabaseManagement>('/api/logs/database')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '数据库状态加载失败'
  } finally {
    loading.value = false
  }
}

async function seedDemoData() {
  seeding.value = true
  error.value = ''
  seedResult.value = null
  try {
    seedResult.value = await api<DemoSeedResult>('/api/logs/demo-seed', { method: 'POST' })
    await loadDatabase()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '演示数据初始化失败'
  } finally {
    seeding.value = false
  }
}

function countTable(name: string): number {
  return database.value?.tables.find((table) => table.name === name)?.row_count ?? 0
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    healthy: '正常',
    degraded: '部分异常',
    unhealthy: '不可用',
    unknown: '未知',
  }
  return labels[status] ?? status
}

function statusClass(status: string): string {
  if (status === 'healthy') return 'success'
  if (status === 'degraded') return 'warning'
  if (status === 'unhealthy') return 'danger'
  return ''
}

onMounted(loadDatabase)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">系统管理</p>
        <h1>数据库管理</h1>
        <p>查看业务表规模、知识库切片和日志数据量，并可一键初始化答辩演示样例。该页面只保留低风险维护动作。</p>
      </div>
      <div class="hero-actions">
        <button type="button" class="btn-secondary" :disabled="loading" @click="loadDatabase">
          {{ loading ? '刷新中...' : '刷新状态' }}
        </button>
        <button type="button" class="btn-primary" :disabled="seeding" @click="seedDemoData">
          {{ seeding ? '初始化中...' : '初始化演示数据' }}
        </button>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-else-if="loading && !database" class="notice">正在读取数据库状态...</p>

    <template v-if="database">
      <section class="metric-grid database-metrics">
        <article class="metric-card">
          <span>数据库状态</span>
          <strong>
            <span class="status-pill" :class="statusClass(database.status)">
              {{ statusLabel(database.status) }}
            </span>
          </strong>
          <small>{{ database.kind }} · {{ database.message }}</small>
        </article>
        <article class="metric-card">
          <span>已识别表</span>
          <strong>{{ database.available_table_count }}</strong>
          <small>白名单 {{ database.table_count }} 张</small>
        </article>
        <article class="metric-card">
          <span>总记录数</span>
          <strong>{{ database.total_rows }}</strong>
          <small>仅统计核心业务表</small>
        </article>
        <article class="metric-card">
          <span>知识库记录</span>
          <strong>{{ knowledgeRows }}</strong>
          <small>资料 {{ countTable('materials') }} · 切片 {{ countTable('material_chunks') }}</small>
        </article>
        <article class="metric-card">
          <span>内容产物</span>
          <strong>{{ contentRows }}</strong>
          <small>教案 / 练习 / 题库</small>
        </article>
      </section>

      <div class="two-column-grid">
        <section class="panel stack">
          <div class="panel-title">
            <h2>低风险维护</h2>
            <small>适合课堂演示，不触碰破坏性操作</small>
          </div>
          <ul class="clean-list">
            <li v-for="note in database.safety_notes" :key="note">
              <strong>{{ note }}</strong>
            </li>
          </ul>
        </section>

        <section class="panel stack">
          <div class="panel-title">
            <h2>演示数据</h2>
            <small>按钮可重复执行，数据按固定标题和账号更新</small>
          </div>
          <p v-if="!seedResult" class="muted">
            会创建演示管理员、演示教管、课程章节、知识点、资料切片、练习题、题库题目和观测日志。
          </p>
          <div v-else class="demo-result">
            <strong>{{ seedResult.message }}</strong>
            <div class="demo-accounts">
              <span>管理员：{{ seedResult.username }} / {{ seedResult.password }}</span>
              <span>教管：{{ seedResult.manager_username }} / {{ seedResult.manager_password }}</span>
            </div>
            <small>
              课程 {{ seedResult.course_id }} · 章节 {{ seedResult.chapter_id }} · 课次 {{ seedResult.session_id }} ·
              知识点 {{ seedResult.knowledge_point_id }} · 资料 {{ seedResult.material_id }} ·
              练习 {{ seedResult.exercise_id }} · 题目 {{ seedResult.question_id }}
            </small>
          </div>
        </section>
      </div>

      <section class="panel stack">
        <div class="panel-title">
          <h2>核心表概览</h2>
          <small>按业务域查看当前数据规模</small>
        </div>
        <div class="table-groups">
          <article v-for="group in categoryGroups" :key="group.category" class="table-group">
            <div class="table-group-title">
              <h3>{{ group.category }}</h3>
              <span>{{ group.rowCount }} 条</span>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>表</th>
                    <th>用途</th>
                    <th>记录数</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="table in group.tables" :key="table.name">
                    <td>
                      <strong>{{ table.label }}</strong>
                      <small>{{ table.name }}</small>
                    </td>
                    <td>{{ table.note }}</td>
                    <td>{{ table.row_count }}</td>
                    <td>
                      <span class="status-pill" :class="table.available ? 'success' : 'warning'">
                        {{ table.available ? '已创建' : '未创建' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.database-metrics {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.database-metrics .metric-card strong {
  display: flex;
  align-items: center;
  min-height: 36px;
}

.demo-result {
  display: grid;
  gap: 10px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 12px;
  color: var(--brand-ink);
  background: var(--brand-soft);
}

.demo-accounts {
  display: grid;
  gap: 6px;
}

.table-groups {
  display: grid;
  gap: 16px;
}

.table-group {
  display: grid;
  gap: 10px;
}

.table-group-title {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.table-group-title span {
  color: var(--muted);
  font-weight: 820;
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}

table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  background: #ffffff;
}

th,
td {
  border-bottom: 1px solid var(--line);
  padding: 11px 12px;
  text-align: left;
  vertical-align: top;
}

tr:last-child td {
  border-bottom: 0;
}

th {
  color: var(--text);
  font-weight: 900;
}

td {
  color: var(--text-soft);
}

td:first-child {
  display: grid;
  gap: 4px;
}

td small {
  overflow-wrap: anywhere;
}

@media (max-width: 1180px) {
  .database-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .database-metrics {
    grid-template-columns: 1fr;
  }
}
</style>

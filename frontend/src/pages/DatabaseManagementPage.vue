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
  vector_store: DatabaseVectorStore
  tables: DatabaseTable[]
}

interface DatabaseVectorStore {
  provider: string
  collection: string
  enabled: boolean
  status: string
  message: string
  points_count: number
  dimensions: number | null
  distance: string
  indexed_chunk_count: number
  chunk_count: number
}

interface VectorSearchHit {
  id: number
  material_id: number
  material_title: string
  content: string
  score: number
  page_no: number | null
  slide_no: number | null
}

interface VectorSearchResult {
  query: string
  retrieval_mode: string
  cache_hit: boolean
  hits: VectorSearchHit[]
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
const searching = ref(false)
const error = ref('')
const vectorQuery = ref('')
const vectorLimit = ref(5)
const vectorSearchResult = ref<VectorSearchResult | null>(null)
const vectorSearchError = ref('')

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
    error.value = err instanceof Error ? err.message : '基础样例同步失败'
  } finally {
    seeding.value = false
  }
}

async function searchVectorStore() {
  if (!vectorQuery.value.trim()) {
    vectorSearchError.value = '请输入要检索的内容。'
    return
  }
  searching.value = true
  vectorSearchError.value = ''
  vectorSearchResult.value = null
  try {
    vectorSearchResult.value = await api<VectorSearchResult>('/api/logs/database/vector-search', {
      method: 'POST',
      body: JSON.stringify({
        query: vectorQuery.value,
        top_k: vectorLimit.value,
      }),
    })
  } catch (err) {
    vectorSearchError.value = err instanceof Error ? err.message : '检索失败'
  } finally {
    searching.value = false
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
    disabled: '未启用',
  }
  return labels[status] ?? status
}

function statusClass(status: string): string {
  if (status === 'healthy') return 'success'
  if (status === 'degraded' || status === 'disabled') return 'warning'
  if (status === 'unhealthy') return 'danger'
  return ''
}

function retrievalModeLabel(value: string): string {
  const labels: Record<string, string> = {
    vector: '向量检索',
    lexical: '关键词回退',
    cache: '缓存命中',
  }
  return labels[value] ?? value
}

onMounted(loadDatabase)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">系统管理</p>
        <h1>数据库管理</h1>
        <p>查看业务表规模、知识库切片、向量索引和日志数据量。该页面只保留低风险维护动作。</p>
      </div>
      <div class="hero-actions">
        <button type="button" class="btn-secondary" :disabled="loading" @click="loadDatabase">
          {{ loading ? '刷新中...' : '刷新状态' }}
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
          <span>向量索引</span>
          <strong>{{ database.vector_store.points_count }}</strong>
          <small>{{ database.vector_store.provider }} · 已标记 {{ database.vector_store.indexed_chunk_count }}</small>
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
            <small>不触碰破坏性操作</small>
          </div>
          <ul class="clean-list">
            <li v-for="note in database.safety_notes" :key="note">
              <strong>{{ note }}</strong>
            </li>
          </ul>
          <details class="maintenance-details">
            <summary>数据维护</summary>
            <p class="muted">用于补齐课程、资料、题库和观测日志的基础样例，可重复执行。</p>
            <button type="button" class="btn-secondary" :disabled="seeding" @click="seedDemoData">
              {{ seeding ? '处理中...' : '同步基础样例' }}
            </button>
            <div v-if="seedResult" class="demo-result">
              <strong>{{ seedResult.message }}</strong>
              <small>
                课程 {{ seedResult.course_id }} · 章节 {{ seedResult.chapter_id }} · 课次 {{ seedResult.session_id }} ·
                知识点 {{ seedResult.knowledge_point_id }} · 资料 {{ seedResult.material_id }} ·
                练习 {{ seedResult.exercise_id }} · 题目 {{ seedResult.question_id }}
              </small>
            </div>
          </details>
        </section>

        <section class="panel stack">
          <div class="panel-title">
            <h2>向量数据库</h2>
            <small>{{ database.vector_store.collection }}</small>
          </div>
          <div class="vector-status-grid">
            <div>
              <span>状态</span>
              <strong>
                <span class="status-pill" :class="statusClass(database.vector_store.status)">
                  {{ statusLabel(database.vector_store.status) }}
                </span>
              </strong>
            </div>
            <div>
              <span>向量点</span>
              <strong>{{ database.vector_store.points_count }}</strong>
            </div>
            <div>
              <span>维度</span>
              <strong>{{ database.vector_store.dimensions ?? '-' }}</strong>
            </div>
            <div>
              <span>切片覆盖</span>
              <strong>{{ database.vector_store.indexed_chunk_count }} / {{ database.vector_store.chunk_count }}</strong>
            </div>
          </div>
          <p class="muted">{{ database.vector_store.message }}</p>
        </section>
      </div>

      <section class="panel stack">
        <div class="panel-title">
          <h2>知识库检索</h2>
          <small>用于验证当前向量库与回退检索链路</small>
        </div>
        <div class="vector-search-form">
          <label>
            检索内容
            <input v-model.trim="vectorQuery" placeholder="例如：矩阵乘法、导数定义、课堂练习" @keyup.enter="searchVectorStore" />
          </label>
          <label>
            返回条数
            <input v-model.number="vectorLimit" type="number" min="1" max="20" />
          </label>
          <button type="button" class="btn-primary" :disabled="searching" @click="searchVectorStore">
            {{ searching ? '检索中...' : '检索' }}
          </button>
        </div>
        <p v-if="vectorSearchError" class="alert" role="alert">{{ vectorSearchError }}</p>
        <div v-if="vectorSearchResult" class="search-results">
          <div class="search-summary">
            <strong>{{ retrievalModeLabel(vectorSearchResult.retrieval_mode) }}</strong>
            <small>{{ vectorSearchResult.cache_hit ? '来自缓存' : '实时查询' }} · {{ vectorSearchResult.hits.length }} 条结果</small>
          </div>
          <p v-if="!vectorSearchResult.hits.length" class="empty-state">没有匹配的知识库切片。</p>
          <article v-for="hit in vectorSearchResult.hits" :key="hit.id" class="search-hit">
            <div>
              <strong>{{ hit.material_title }}</strong>
              <small>资料 {{ hit.material_id }} · 切片 {{ hit.id }} · 相关度 {{ hit.score.toFixed(3) }}</small>
            </div>
            <p>{{ hit.content }}</p>
          </article>
        </div>
      </section>

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
  grid-template-columns: repeat(6, minmax(0, 1fr));
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

.maintenance-details {
  display: grid;
  gap: 10px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}

.maintenance-details summary {
  cursor: pointer;
  color: var(--text);
  font-weight: 900;
}

.maintenance-details p {
  margin: 8px 0;
}

.vector-status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.vector-status-grid > div {
  display: grid;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--surface-soft);
}

.vector-status-grid span {
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 820;
}

.vector-status-grid strong {
  color: var(--text);
  overflow-wrap: anywhere;
}

.vector-search-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px auto;
  gap: 12px;
  align-items: end;
}

.search-results {
  display: grid;
  gap: 12px;
}

.search-summary {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--surface-soft);
}

.search-hit {
  display: grid;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.search-hit div {
  display: grid;
  gap: 4px;
}

.search-hit p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.7;
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
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .database-metrics,
  .vector-status-grid,
  .vector-search-form {
    grid-template-columns: 1fr;
  }
}
</style>

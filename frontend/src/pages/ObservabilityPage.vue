<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '../api/client'

interface RecentError {
  source: string
  task_type: string | null
  message: string
  created_at: string
}

interface LogSummary {
  model_total: number
  model_success: number
  model_failed: number
  mock_fallbacks: number
  average_latency_ms: number
  job_total: number
  job_failed: number
  operation_total: number
  recent_errors: RecentError[]
}

interface ModelLog {
  id: number
  task_type: string | null
  provider: string
  model: string
  latency_ms: number | null
  success: boolean
  fallback_used: boolean
  error_message: string | null
  created_at: string
}

interface JobLog {
  id: number
  job_type: string
  status: string
  resource_type: string | null
  resource_id: number | null
  error_message: string | null
  duration_ms: number | null
  created_at: string
}

interface OperationLog {
  id: number
  action: string
  resource: string | null
  detail: string | null
  created_at: string
}

const summary = ref<LogSummary | null>(null)
const modelLogs = ref<ModelLog[]>([])
const jobLogs = ref<JobLog[]>([])
const operationLogs = ref<OperationLog[]>([])
const loading = ref(false)
const error = ref('')

const successRate = computed(() => {
  if (!summary.value?.model_total) return '0%'
  return `${Math.round((summary.value.model_success / summary.value.model_total) * 100)}%`
})

async function loadObservability() {
  loading.value = true
  error.value = ''
  try {
    const [summaryResult, modelResult, jobResult, operationResult] = await Promise.all([
      api<LogSummary>('/api/logs/summary'),
      api<ModelLog[]>('/api/logs/models'),
      api<JobLog[]>('/api/logs/jobs'),
      api<OperationLog[]>('/api/logs/operations'),
    ])
    summary.value = summaryResult
    modelLogs.value = modelResult
    jobLogs.value = jobResult
    operationLogs.value = operationResult
  } catch (err) {
    error.value = err instanceof Error ? err.message : '观测日志加载失败'
  } finally {
    loading.value = false
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

function taskLabel(value: string | null): string {
  if (!value) return '未知任务'
  const labels: Record<string, string> = {
    lesson: '备课生成',
    lesson_review: '备课审核',
    lesson_revise: '备课修订',
    exercise: '习题生成',
    exercise_review: '习题审核',
    exercise_revise: '习题修订',
  }
  return labels[value] ?? value
}

function statusText(success: boolean): string {
  return success ? '成功' : '失败'
}

onMounted(loadObservability)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">观测日志</p>
        <h1>系统运行观测</h1>
        <p>查看模型调用、Mock 兜底、异步任务和操作日志，用于调试和答辩展示。</p>
      </div>
      <button type="button" class="btn-secondary" :disabled="loading" @click="loadObservability">
        {{ loading ? '刷新中...' : '刷新日志' }}
      </button>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>

    <section class="metric-grid">
      <article>
        <span>模型调用</span>
        <strong>{{ summary?.model_total ?? 0 }}</strong>
        <small>成功率 {{ successRate }}</small>
      </article>
      <article>
        <span>Mock 兜底</span>
        <strong>{{ summary?.mock_fallbacks ?? 0 }}</strong>
        <small>用于识别真实 API 是否失败</small>
      </article>
      <article>
        <span>平均耗时</span>
        <strong>{{ summary?.average_latency_ms ?? 0 }}ms</strong>
        <small>模型调用平均延迟</small>
      </article>
      <article>
        <span>任务失败</span>
        <strong>{{ summary?.job_failed ?? 0 }}</strong>
        <small>异步任务总数 {{ summary?.job_total ?? 0 }}</small>
      </article>
    </section>

    <section class="panel stack">
      <h2>最近模型调用</h2>
      <p v-if="!modelLogs.length" class="empty-state">暂无模型调用日志。</p>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>任务</th>
              <th>模型</th>
              <th>来源</th>
              <th>耗时</th>
              <th>状态</th>
              <th>Mock</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in modelLogs.slice(0, 20)" :key="log.id">
              <td>{{ formatDate(log.created_at) }}</td>
              <td>{{ taskLabel(log.task_type) }}</td>
              <td>{{ log.model }}</td>
              <td>{{ log.provider }}</td>
              <td>{{ log.latency_ms ?? 0 }}ms</td>
              <td>
                <span class="status-pill" :class="log.success ? 'success' : 'high'">
                  {{ statusText(log.success) }}
                </span>
              </td>
              <td>{{ log.fallback_used ? '是' : '否' }}</td>
              <td>{{ log.error_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="two-column-grid">
      <section class="panel stack">
        <h2>最近错误</h2>
        <p v-if="!summary?.recent_errors.length" class="empty-state">暂无错误记录。</p>
        <ul v-else class="clean-list">
          <li v-for="item in summary.recent_errors" :key="`${item.source}-${item.created_at}`">
            <strong>{{ item.source === 'model' ? '模型错误' : '任务错误' }} · {{ taskLabel(item.task_type) }}</strong>
            <small>{{ formatDate(item.created_at) }}</small>
            <p>{{ item.message }}</p>
          </li>
        </ul>
      </section>

      <section class="panel stack">
        <h2>异步任务</h2>
        <p v-if="!jobLogs.length" class="empty-state">暂无任务日志。</p>
        <ul v-else class="clean-list">
          <li v-for="job in jobLogs.slice(0, 8)" :key="job.id">
            <strong>{{ job.job_type }} · {{ job.status }}</strong>
            <small>
              {{ formatDate(job.created_at) }} · {{ job.resource_type || '资源' }} {{ job.resource_id ?? '' }}
            </small>
            <p v-if="job.error_message">{{ job.error_message }}</p>
          </li>
        </ul>
      </section>
    </div>

    <section class="panel stack">
      <h2>最近操作</h2>
      <p v-if="!operationLogs.length" class="empty-state">暂无操作日志。</p>
      <ul v-else class="clean-list operation-list">
        <li v-for="operation in operationLogs.slice(0, 12)" :key="operation.id">
          <strong>{{ operation.action }}</strong>
          <small>{{ formatDate(operation.created_at) }} · {{ operation.resource || '系统' }}</small>
          <p v-if="operation.detail">{{ operation.detail }}</p>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-grid article {
  display: grid;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.metric-grid span,
.metric-grid small,
td,
th,
.clean-list small {
  color: var(--muted);
}

.metric-grid strong {
  color: var(--text);
  font-size: 1.8rem;
}

.table-wrap {
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 860px;
}

th,
td {
  border-bottom: 1px solid var(--line);
  padding: 10px 8px;
  text-align: left;
  vertical-align: top;
}

th {
  color: var(--text);
  font-weight: 900;
}

.clean-list p {
  margin: 4px 0 0;
  white-space: pre-wrap;
}

.operation-list li {
  grid-template-columns: minmax(160px, 0.3fr) minmax(0, 1fr);
}

@media (max-width: 1080px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>

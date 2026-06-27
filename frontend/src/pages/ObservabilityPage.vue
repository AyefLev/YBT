<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

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
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  cost_currency: string
  average_latency_ms: number
  job_total: number
  job_failed: number
  operation_total: number
  recent_errors: RecentError[]
}

interface ModelLog {
  id: number
  user_id: number | null
  task_type: string | null
  provider: string
  api_role: string
  api_base_url: string
  model: string
  prompt_tokens: number | null
  completion_tokens: number | null
  estimated_cost: number
  cost_currency: string
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

interface TokenUsage {
  user_id: number | null
  username: string
  display_name: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  cost_currency: string
  call_count: number
}

interface ModelUsage {
  api_role: string
  api_base_url: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  cost_currency: string
  call_count: number
}

const route = useRoute()
const summary = ref<LogSummary | null>(null)
const modelLogs = ref<ModelLog[]>([])
const jobLogs = ref<JobLog[]>([])
const operationLogs = ref<OperationLog[]>([])
const tokenUsage = ref<TokenUsage[]>([])
const modelUsage = ref<ModelUsage[]>([])
const loading = ref(false)
const error = ref('')

const pageMode = computed(() => String(route.meta.pageMode || 'overview'))
const showOverview = computed(() => pageMode.value === 'overview')
const showToken = computed(() => pageMode.value === 'token')
const successRate = computed(() => {
  if (!summary.value?.model_total) return '0%'
  return `${Math.round((summary.value.model_success / summary.value.model_total) * 100)}%`
})
const fallbackRate = computed(() => {
  if (!summary.value?.model_total) return 0
  return Math.round((summary.value.mock_fallbacks / summary.value.model_total) * 100)
})
const maxUserTokens = computed(() => Math.max(1, ...tokenUsage.value.map((item) => item.total_tokens)))
const maxModelUsageWeight = computed(() =>
  Math.max(1, ...modelUsage.value.map((item) => modelUsageWeight(item))),
)

async function loadObservability() {
  loading.value = true
  error.value = ''
  try {
    const [summaryResult, modelResult, jobResult, operationResult, tokenResult, modelUsageResult] = await Promise.all([
      api<LogSummary>('/api/logs/summary'),
      api<ModelLog[]>('/api/logs/models'),
      api<JobLog[]>('/api/logs/jobs'),
      api<OperationLog[]>('/api/logs/operations'),
      api<TokenUsage[]>('/api/logs/token-usage'),
      api<ModelUsage[]>('/api/logs/model-usage'),
    ])
    summary.value = summaryResult
    modelLogs.value = modelResult
    jobLogs.value = jobResult
    operationLogs.value = operationResult
    tokenUsage.value = tokenResult
    modelUsage.value = modelUsageResult
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

function userLabel(item: TokenUsage): string {
  return item.display_name || item.username || (item.user_id ? `用户 ${item.user_id}` : '系统任务')
}

function modelRoleLabel(value: string): string {
  const labels: Record<string, string> = {
    generate: '生成',
    review: '复核',
    revise: '修订',
    vision: '视觉',
    embedding: '向量',
  }
  return labels[value] ?? (value || '默认')
}

function formatCost(value: number | null | undefined, currency = 'CNY'): string {
  const amount = Number(value || 0)
  const digits = amount >= 1 ? 2 : 4
  const unit = currency === 'mixed' ? '混合币种' : currency || 'CNY'
  return `${amount.toFixed(digits)} ${unit}`
}

function modelUsageWeight(item: ModelUsage): number {
  return item.estimated_cost > 0 ? item.estimated_cost : item.total_tokens
}

function tokenTotal(log: ModelLog): number {
  return (log.prompt_tokens ?? 0) + (log.completion_tokens ?? 0)
}

onMounted(loadObservability)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">观测日志</p>
        <h1>{{ showToken ? 'Token 与费用' : '系统运行观测' }}</h1>
        <p>{{ showToken ? '按用户、模型和 API 维度查看 token 消耗与估算费用。' : '查看模型调用、Mock 兜底、异步任务和操作日志，用于调试和答辩展示。' }}</p>
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
        <small>占比 {{ fallbackRate }}%</small>
      </article>
      <article>
        <span>Token 消耗</span>
        <strong>{{ summary?.total_tokens ?? 0 }}</strong>
        <small>费用 {{ formatCost(summary?.estimated_cost, summary?.cost_currency) }}</small>
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

    <section v-if="showToken" class="panel stack">
      <div class="panel-title">
        <h2>Token 用量</h2>
        <small>按用户汇总模型调用与估算费用</small>
      </div>
      <p v-if="!tokenUsage.length" class="empty-state">暂无 token 使用记录。</p>
      <ul v-else class="usage-list">
        <li v-for="item in tokenUsage" :key="`${item.user_id}-${item.username}`">
          <div>
            <strong>{{ userLabel(item) }}</strong>
            <small>{{ item.call_count }} 次调用 · 输入 {{ item.prompt_tokens }} · 输出 {{ item.completion_tokens }}</small>
          </div>
          <div class="usage-bar" aria-hidden="true">
            <span :style="{ width: `${Math.max(4, Math.round((item.total_tokens / maxUserTokens) * 100))}%` }" />
          </div>
          <strong>{{ item.total_tokens }} · {{ formatCost(item.estimated_cost, item.cost_currency) }}</strong>
        </li>
      </ul>
    </section>

    <section v-if="showToken" class="panel stack">
      <div class="panel-title">
        <h2>模型/API 用量</h2>
        <small>按功能模型、接口地址和模型名汇总</small>
      </div>
      <p v-if="!modelUsage.length" class="empty-state">暂无模型/API 使用记录。</p>
      <ul v-else class="usage-list model-usage-list">
        <li v-for="item in modelUsage" :key="`${item.api_role}-${item.api_base_url}-${item.model}-${item.cost_currency}`">
          <div>
            <strong>{{ modelRoleLabel(item.api_role) }} · {{ item.model || '未记录模型' }}</strong>
            <small>{{ item.api_base_url || '默认接口' }} · {{ item.call_count }} 次调用 · {{ item.total_tokens }} token</small>
          </div>
          <div class="usage-bar" aria-hidden="true">
            <span :style="{ width: `${Math.max(4, Math.round((modelUsageWeight(item) / maxModelUsageWeight) * 100))}%` }" />
          </div>
          <strong>{{ formatCost(item.estimated_cost, item.cost_currency) }}</strong>
        </li>
      </ul>
    </section>

    <section v-if="showOverview" class="panel stack">
      <h2>最近模型调用</h2>
      <p v-if="!modelLogs.length" class="empty-state">暂无模型调用日志。</p>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>任务</th>
              <th>API</th>
              <th>模型</th>
              <th>用户</th>
              <th>Token</th>
              <th>费用</th>
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
              <td>{{ modelRoleLabel(log.api_role) }}</td>
              <td>{{ log.model }}</td>
              <td>{{ log.user_id ?? '系统' }}</td>
              <td>{{ tokenTotal(log) }}</td>
              <td>{{ formatCost(log.estimated_cost, log.cost_currency) }}</td>
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

    <div v-if="showOverview" class="two-column-grid">
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

    <section v-if="showOverview" class="panel stack">
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
  grid-template-columns: repeat(5, minmax(0, 1fr));
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

.usage-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.usage-list li {
  display: grid;
  grid-template-columns: minmax(160px, 0.35fr) minmax(180px, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.usage-list li > div:first-child {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.usage-list strong {
  overflow-wrap: anywhere;
}

.model-usage-list li {
  grid-template-columns: minmax(240px, 0.45fr) minmax(180px, 1fr) minmax(120px, auto);
}

.usage-bar {
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.usage-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb, #14b8a6);
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

  .usage-list li {
    grid-template-columns: 1fr;
  }
}
</style>

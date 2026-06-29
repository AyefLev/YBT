<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
  status: string
  created_at: string
}

interface JobLog {
  id: number
  job_type: string
  status: string
  resource_type: string | null
  resource_id: number | null
  user_id: number | null
  detail: string | null
  error_message: string | null
  duration_ms: number | null
  created_at: string
}

interface OperationLog {
  id: number
  user_id: number | null
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

interface DailyUsage {
  day: string
  group_key: string
  group_label: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  cost_currency: string
  call_count: number
}

type LogType = 'model' | 'job' | 'operation'

const route = useRoute()
const summary = ref<LogSummary | null>(null)
const modelLogs = ref<ModelLog[]>([])
const jobLogs = ref<JobLog[]>([])
const operationLogs = ref<OperationLog[]>([])
const tokenUsage = ref<TokenUsage[]>([])
const modelUsage = ref<ModelUsage[]>([])
const dailyModelUsage = ref<DailyUsage[]>([])
const dailyUserUsage = ref<DailyUsage[]>([])
const loading = ref(false)
const error = ref('')
const activeLogType = ref<LogType>('model')
const logKeyword = ref('')
const logStatus = ref('all')
const logUserId = ref('')
const autoRefresh = ref(false)
const expandedUser = ref<string | null>(null)
const expandedModel = ref<string | null>(null)
let refreshTimer: number | null = null

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
const maxDailyCost = computed(() => Math.max(0.0001, ...dailyTotals.value.map((item) => item.cost)))
const maxDailyTokens = computed(() => Math.max(1, ...dailyTotals.value.map((item) => item.tokens)))
const maxUserTokens = computed(() => Math.max(1, ...tokenUsage.value.map((item) => item.total_tokens)))
const maxModelUsageWeight = computed(() =>
  Math.max(1, ...modelUsage.value.map((item) => modelUsageWeight(item))),
)
const dailyTotals = computed(() => {
  const days = new Map<string, { day: string; tokens: number; cost: number; calls: number; currency: string }>()
  for (const item of dailyModelUsage.value) {
    const current = days.get(item.day) ?? { day: item.day, tokens: 0, cost: 0, calls: 0, currency: item.cost_currency }
    current.tokens += item.total_tokens
    current.cost += item.estimated_cost
    current.calls += item.call_count
    current.currency = current.currency === item.cost_currency ? current.currency : 'mixed'
    days.set(item.day, current)
  }
  return Array.from(days.values()).sort((left, right) => left.day.localeCompare(right.day))
})
const modelDailyGroups = computed(() => groupDailyUsage(dailyModelUsage.value))
const userDailyGroups = computed(() => groupDailyUsage(dailyUserUsage.value))

async function loadObservability() {
  loading.value = true
  error.value = ''
  try {
    const [summaryResult, modelResult, jobResult, operationResult, tokenResult, modelUsageResult, dailyModelResult, dailyUserResult] = await Promise.all([
      api<LogSummary>('/api/logs/summary'),
      api<ModelLog[]>(`/api/logs/models?${logQuery('model')}`),
      api<JobLog[]>(`/api/logs/jobs?${logQuery('job')}`),
      api<OperationLog[]>(`/api/logs/operations?${logQuery('operation')}`),
      api<TokenUsage[]>('/api/logs/token-usage'),
      api<ModelUsage[]>('/api/logs/model-usage'),
      api<DailyUsage[]>('/api/logs/usage-daily?group_by=model&days=30'),
      api<DailyUsage[]>('/api/logs/usage-daily?group_by=user&days=30'),
    ])
    summary.value = summaryResult
    modelLogs.value = modelResult
    jobLogs.value = jobResult
    operationLogs.value = operationResult
    tokenUsage.value = tokenResult
    modelUsage.value = modelUsageResult
    dailyModelUsage.value = dailyModelResult
    dailyUserUsage.value = dailyUserResult
  } catch (err) {
    error.value = err instanceof Error ? err.message : '观测日志加载失败'
  } finally {
    loading.value = false
  }
}

function logQuery(type: LogType): string {
  const params = new URLSearchParams({ limit: '200' })
  if (logKeyword.value.trim()) params.set('q', logKeyword.value.trim())
  if (logUserId.value.trim()) params.set('user_id', logUserId.value.trim())
  if (logStatus.value !== 'all') {
    if (type === 'model') params.set('success', String(logStatus.value === 'success'))
    if (type === 'job') params.set('status', logStatus.value === 'success' ? 'succeeded' : 'failed')
  }
  return params.toString()
}

function groupDailyUsage(rows: DailyUsage[]) {
  const groups = new Map<string, { key: string; label: string; tokens: number; cost: number; calls: number; currency: string; days: DailyUsage[] }>()
  for (const row of rows) {
    const group = groups.get(row.group_key) ?? {
      key: row.group_key,
      label: row.group_label,
      tokens: 0,
      cost: 0,
      calls: 0,
      currency: row.cost_currency,
      days: [],
    }
    group.tokens += row.total_tokens
    group.cost += row.estimated_cost
    group.calls += row.call_count
    group.currency = group.currency === row.cost_currency ? group.currency : 'mixed'
    group.days.push(row)
    groups.set(row.group_key, group)
  }
  return Array.from(groups.values()).sort((left, right) => right.cost - left.cost || right.tokens - left.tokens)
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

function formatDay(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(`${value}T00:00:00`))
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
    demo_seed: '基础数据同步',
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

function toggleUser(key: string) {
  expandedUser.value = expandedUser.value === key ? null : key
}

function toggleModel(key: string) {
  expandedModel.value = expandedModel.value === key ? null : key
}

function logsForUser(key: string): ModelLog[] {
  return modelLogs.value.filter((log) => String(log.user_id ?? 'system') === key).slice(0, 8)
}

function logsForModel(key: string): ModelLog[] {
  const [role, ...modelParts] = key.split(':')
  const model = modelParts.join(':')
  return modelLogs.value
    .filter((log) => (log.api_role || 'default') === role && log.model === model)
    .slice(0, 8)
}

function setAutoRefresh(enabled: boolean) {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (enabled) {
    refreshTimer = window.setInterval(loadObservability, 5000)
  }
}

watch(autoRefresh, setAutoRefresh)
onMounted(loadObservability)
onBeforeUnmount(() => setAutoRefresh(false))
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">观测日志</p>
        <h1>{{ showToken ? 'Token 与费用' : '系统运行观测' }}</h1>
        <p>{{ showToken ? '按用户、模型和 API 维度查看 token 消耗、请求次数和估算费用。' : '集中查看模型调用、后台任务和操作日志，支持筛选历史记录与自动刷新。' }}</p>
      </div>
      <div class="hero-actions">
        <label v-if="showOverview" class="checkbox refresh-toggle">
          <input v-model="autoRefresh" type="checkbox" />
          自动刷新
        </label>
        <button type="button" class="btn-secondary" :disabled="loading" @click="loadObservability">
          {{ loading ? '刷新中...' : '刷新日志' }}
        </button>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>

    <section class="metric-grid">
      <article>
        <span>模型调用</span>
        <strong>{{ summary?.model_total ?? 0 }}</strong>
        <small>成功率 {{ successRate }}</small>
      </article>
      <article>
        <span>兜底返回</span>
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
        <small>任务总数 {{ summary?.job_total ?? 0 }}</small>
      </article>
    </section>

    <section v-if="showOverview" class="panel stack">
      <div class="panel-title">
        <h2>日志检索</h2>
        <small>当前最多显示 200 条，自动刷新每 5 秒更新一次。</small>
      </div>
      <div class="log-toolbar">
        <div class="segmented">
          <button type="button" :class="{ active: activeLogType === 'model' }" @click="activeLogType = 'model'">模型调用</button>
          <button type="button" :class="{ active: activeLogType === 'job' }" @click="activeLogType = 'job'">后台任务</button>
          <button type="button" :class="{ active: activeLogType === 'operation' }" @click="activeLogType = 'operation'">操作记录</button>
        </div>
        <label>
          关键词
          <input v-model.trim="logKeyword" placeholder="任务、模型、资源或错误内容" @keyup.enter="loadObservability" />
        </label>
        <label>
          状态
          <select v-model="logStatus" @change="loadObservability">
            <option value="all">全部</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
          </select>
        </label>
        <label>
          用户 ID
          <input v-model.trim="logUserId" inputmode="numeric" placeholder="可选" @keyup.enter="loadObservability" />
        </label>
        <button type="button" class="btn-primary" @click="loadObservability">筛选</button>
      </div>

      <div v-if="activeLogType === 'model'" class="table-wrap">
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
              <th>耗时</th>
              <th>状态</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in modelLogs" :key="log.id">
              <td>{{ formatDate(log.created_at) }}</td>
              <td>{{ taskLabel(log.task_type) }}</td>
              <td>{{ modelRoleLabel(log.api_role) }}</td>
              <td>{{ log.model }}</td>
              <td>{{ log.user_id ?? '系统' }}</td>
              <td>{{ tokenTotal(log) }}</td>
              <td>{{ formatCost(log.estimated_cost, log.cost_currency) }}</td>
              <td>{{ log.latency_ms ?? 0 }}ms</td>
              <td><span class="status-pill" :class="log.success ? 'success' : 'high'">{{ statusText(log.success) }}</span></td>
              <td>{{ log.error_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!modelLogs.length" class="empty-state">暂无匹配的模型调用日志。</p>
      </div>

      <div v-else-if="activeLogType === 'job'" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>任务</th>
              <th>状态</th>
              <th>资源</th>
              <th>用户</th>
              <th>耗时</th>
              <th>详情</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in jobLogs" :key="job.id">
              <td>{{ formatDate(job.created_at) }}</td>
              <td>{{ job.job_type }}</td>
              <td>{{ job.status }}</td>
              <td>{{ job.resource_type || '-' }} {{ job.resource_id ?? '' }}</td>
              <td>{{ job.user_id ?? '系统' }}</td>
              <td>{{ job.duration_ms ?? 0 }}ms</td>
              <td>{{ job.detail || '-' }}</td>
              <td>{{ job.error_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!jobLogs.length" class="empty-state">暂无匹配的后台任务日志。</p>
      </div>

      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>操作</th>
              <th>资源</th>
              <th>用户</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="operation in operationLogs" :key="operation.id">
              <td>{{ formatDate(operation.created_at) }}</td>
              <td>{{ operation.action }}</td>
              <td>{{ operation.resource || '-' }}</td>
              <td>{{ operation.user_id ?? '系统' }}</td>
              <td>{{ operation.detail || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!operationLogs.length" class="empty-state">暂无匹配的操作记录。</p>
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
        <h2>后台任务状态</h2>
        <p v-if="!jobLogs.length" class="empty-state">暂无任务日志。</p>
        <ul v-else class="clean-list">
          <li v-for="job in jobLogs.slice(0, 8)" :key="job.id">
            <strong>{{ job.job_type }} · {{ job.status }}</strong>
            <small>{{ formatDate(job.created_at) }} · {{ job.resource_type || '资源' }} {{ job.resource_id ?? '' }}</small>
            <p v-if="job.error_message">{{ job.error_message }}</p>
            <p v-else-if="job.detail">{{ job.detail }}</p>
          </li>
        </ul>
      </section>
    </div>

    <section v-if="showToken" class="panel stack">
      <div class="panel-title">
        <h2>近 30 日用量</h2>
        <small>按天汇总调用费用、Token 和请求次数</small>
      </div>
      <p v-if="!dailyTotals.length" class="empty-state">暂无 token 使用记录。</p>
      <div v-else class="daily-chart">
        <article v-for="item in dailyTotals" :key="item.day" class="daily-bar">
          <div class="bar-track">
            <span class="cost-bar" :style="{ height: `${Math.max(6, Math.round((item.cost / maxDailyCost) * 100))}%` }" />
            <span class="token-bar" :style="{ height: `${Math.max(6, Math.round((item.tokens / maxDailyTokens) * 100))}%` }" />
          </div>
          <small>{{ formatDay(item.day) }}</small>
          <strong>{{ formatCost(item.cost, item.currency) }}</strong>
          <em>{{ item.tokens }} token · {{ item.calls }} 次</em>
        </article>
      </div>
    </section>

    <div v-if="showToken" class="two-column-grid usage-columns">
      <section class="panel stack">
        <div class="panel-title">
          <h2>按用户</h2>
          <small>点击条目查看最近调用</small>
        </div>
        <p v-if="!tokenUsage.length" class="empty-state">暂无用户用量。</p>
        <ul v-else class="usage-list">
          <li v-for="item in tokenUsage" :key="`${item.user_id}-${item.username}`">
            <button type="button" class="usage-row" @click="toggleUser(String(item.user_id ?? 'system'))">
              <span>
                <strong>{{ userLabel(item) }}</strong>
                <small>{{ item.call_count }} 次 · 输入 {{ item.prompt_tokens }} · 输出 {{ item.completion_tokens }}</small>
              </span>
              <span class="usage-bar" aria-hidden="true">
                <i :style="{ width: `${Math.max(4, Math.round((item.total_tokens / maxUserTokens) * 100))}%` }" />
              </span>
              <strong>{{ item.total_tokens }} · {{ formatCost(item.estimated_cost, item.cost_currency) }}</strong>
            </button>
            <div v-if="expandedUser === String(item.user_id ?? 'system')" class="usage-detail">
              <p v-if="!logsForUser(String(item.user_id ?? 'system')).length" class="muted">当前筛选范围内暂无调用明细。</p>
              <p v-for="log in logsForUser(String(item.user_id ?? 'system'))" :key="log.id">
                {{ formatDate(log.created_at) }} · {{ modelRoleLabel(log.api_role) }} · {{ log.model }} · {{ tokenTotal(log) }} token · {{ formatCost(log.estimated_cost, log.cost_currency) }}
              </p>
            </div>
          </li>
        </ul>
      </section>

      <section class="panel stack">
        <div class="panel-title">
          <h2>按模型/API</h2>
          <small>展开查看接口、Token 和费用</small>
        </div>
        <p v-if="!modelUsage.length" class="empty-state">暂无模型用量。</p>
        <ul v-else class="usage-list">
          <li v-for="item in modelUsage" :key="`${item.api_role}-${item.api_base_url}-${item.model}-${item.cost_currency}`">
            <button type="button" class="usage-row" @click="toggleModel(`${item.api_role || 'default'}:${item.model}`)">
              <span>
                <strong>{{ modelRoleLabel(item.api_role) }} · {{ item.model || '未记录模型' }}</strong>
                <small>{{ item.api_base_url || '默认接口' }} · {{ item.call_count }} 次 · {{ item.total_tokens }} token</small>
              </span>
              <span class="usage-bar" aria-hidden="true">
                <i :style="{ width: `${Math.max(4, Math.round((modelUsageWeight(item) / maxModelUsageWeight) * 100))}%` }" />
              </span>
              <strong>{{ formatCost(item.estimated_cost, item.cost_currency) }}</strong>
            </button>
            <div v-if="expandedModel === `${item.api_role || 'default'}:${item.model}`" class="usage-detail">
              <div class="mini-bars">
                <span
                  v-for="day in modelDailyGroups.find((group) => group.key === `${item.api_role || 'default'}:${item.model}`)?.days ?? []"
                  :key="day.day"
                  :title="`${day.day} · ${day.total_tokens} token · ${formatCost(day.estimated_cost, day.cost_currency)}`"
                  :style="{ height: `${Math.max(10, Math.round((day.total_tokens / maxDailyTokens) * 100))}%` }"
                />
              </div>
              <p v-for="log in logsForModel(`${item.api_role || 'default'}:${item.model}`)" :key="log.id">
                {{ formatDate(log.created_at) }} · 用户 {{ log.user_id ?? '系统' }} · {{ tokenTotal(log) }} token · {{ formatCost(log.estimated_cost, log.cost_currency) }}
              </p>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <section v-if="showToken" class="panel stack">
      <div class="panel-title">
        <h2>用户日趋势</h2>
        <small>按用户聚合最近 30 日调用量</small>
      </div>
      <div class="trend-grid">
        <article v-for="group in userDailyGroups.slice(0, 8)" :key="group.key">
          <div>
            <strong>{{ group.label }}</strong>
            <small>{{ group.calls }} 次 · {{ group.tokens }} token · {{ formatCost(group.cost, group.currency) }}</small>
          </div>
          <div class="mini-bars">
            <span
              v-for="day in group.days"
              :key="day.day"
              :title="`${day.day} · ${day.total_tokens} token`"
              :style="{ height: `${Math.max(10, Math.round((day.total_tokens / maxDailyTokens) * 100))}%` }"
            />
          </div>
        </article>
      </div>
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

.refresh-toggle {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  background: #ffffff;
}

.log-toolbar {
  display: grid;
  grid-template-columns: auto minmax(220px, 1fr) 140px 120px auto;
  gap: 12px;
  align-items: end;
}

.segmented {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #ffffff;
}

.segmented button {
  border: 0;
  border-right: 1px solid var(--line);
  padding: 10px 12px;
  color: var(--muted);
  background: transparent;
  font-weight: 850;
}

.segmented button:last-child {
  border-right: 0;
}

.segmented button.active {
  color: var(--brand-ink);
  background: var(--brand-soft);
}

.table-wrap {
  overflow: auto;
}

table {
  width: 100%;
  min-width: 920px;
  border-collapse: collapse;
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

.daily-chart {
  display: grid;
  grid-template-columns: repeat(15, minmax(42px, 1fr));
  gap: 10px;
  overflow: auto;
  padding-bottom: 4px;
}

.daily-bar {
  display: grid;
  gap: 6px;
  min-width: 54px;
}

.bar-track {
  position: relative;
  display: flex;
  height: 150px;
  align-items: end;
  gap: 4px;
  border-bottom: 1px solid var(--line-strong);
}

.cost-bar,
.token-bar {
  display: block;
  width: 14px;
  border-radius: 6px 6px 0 0;
}

.cost-bar {
  background: #f59e0b;
}

.token-bar {
  background: #38bdf8;
}

.daily-bar strong {
  font-size: 0.82rem;
}

.daily-bar em {
  color: var(--muted);
  font-size: 0.76rem;
  font-style: normal;
  line-height: 1.35;
}

.usage-columns {
  align-items: start;
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
  gap: 8px;
}

.usage-row {
  display: grid;
  width: 100%;
  grid-template-columns: minmax(160px, 0.45fr) minmax(120px, 1fr) minmax(120px, auto);
  gap: 12px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  color: inherit;
  background: #ffffff;
  text-align: left;
}

.usage-row > span:first-child {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.usage-row strong {
  overflow-wrap: anywhere;
}

.usage-bar {
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.usage-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb, #14b8a6);
}

.usage-detail {
  display: grid;
  gap: 8px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 12px;
  background: var(--brand-soft);
}

.usage-detail p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.6;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.trend-grid article {
  display: grid;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.mini-bars {
  display: flex;
  height: 70px;
  align-items: end;
  gap: 4px;
  border-bottom: 1px solid var(--line-strong);
}

.mini-bars span {
  width: 9px;
  min-height: 10px;
  border-radius: 5px 5px 0 0;
  background: #38bdf8;
}

@media (max-width: 1180px) {
  .metric-grid,
  .trend-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .log-toolbar {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .metric-grid,
  .log-toolbar,
  .trend-grid,
  .usage-row {
    grid-template-columns: 1fr;
  }

  .segmented {
    display: grid;
  }

  .segmented button {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, apiForm } from '../api/client'

interface HealthComponent {
  status: 'healthy' | 'degraded' | 'unhealthy' | string
  kind: string
  message: string
}

interface ModelHealth {
  text_model: string
  generate_model: string
  generate_configured: boolean
  review_model: string
  review_configured: boolean
  revise_model: string
  revise_configured: boolean
  vision_model: string | null
  vision_configured: boolean
  embedding_model: string
  embedding_configured: boolean
  api_key_configured: boolean
  vision_api_key_configured: boolean
  multi_agent_review: boolean
  mock_on_failure: boolean
}

interface ObservabilityHealth {
  model_total: number
  model_failed: number
  job_total: number
  job_failed: number
  operation_total: number
}

interface DemoHealth {
  docker_ready_items: string[]
  suggested_next_action: string
}

interface SystemHealth {
  overall_status: 'healthy' | 'degraded' | 'unhealthy' | string
  database: HealthComponent
  cache: HealthComponent
  vector_store: HealthComponent
  models: ModelHealth
  observability: ObservabilityHealth
  demo: DemoHealth
}

interface ModelConnectivityCheck {
  role: string
  model: string
  configured: boolean
  status: string
  latency_ms: number | null
  message: string
}

interface ModelConnectivity {
  probe_enabled: boolean
  checks: ModelConnectivityCheck[]
}

interface AIResult {
  content: string
  provider: string
  model: string
  fallback_used: boolean
  error_message: string | null
}

interface ModelTestResponse {
  role: string
  content: string
  provider_status: AIResult | null
  vector_dimensions: number | null
  vector_preview: number[]
}

const health = ref<SystemHealth | null>(null)
const connectivity = ref<ModelConnectivity | null>(null)
const loading = ref(false)
const probing = ref(false)
const modelTesting = ref(false)
const error = ref('')
const probeError = ref('')
const modelTestError = ref('')
const activeTestRole = ref('generate')
const modelTestPrompt = ref('请只回复 ok，用于模型连通性与输出格式测试。')
const modelTestFile = ref<File | null>(null)
const modelTestResult = ref<ModelTestResponse | null>(null)

const overallText = computed(() => statusLabel(health.value?.overall_status ?? 'unknown'))
const modelTestTabs = [
  { role: 'generate', label: '生成模型' },
  { role: 'review', label: '审核模型' },
  { role: 'revise', label: '修订模型' },
  { role: 'embedding', label: '向量模型' },
  { role: 'vision', label: '视觉模型' },
]
const activeTestTab = computed(() =>
  modelTestTabs.find((item) => item.role === activeTestRole.value) ?? modelTestTabs[0],
)
const activeConnectivity = computed(() =>
  connectivity.value?.checks.find((item) => item.role === activeTestRole.value) ?? null,
)
const isVisionTest = computed(() => activeTestRole.value === 'vision')
const isEmbeddingTest = computed(() => activeTestRole.value === 'embedding')
const activePromptPlaceholder = computed(() => {
  if (isVisionTest.value) return '请分析这张图片里可用于教学的关键信息。'
  if (isEmbeddingTest.value) return '输入一段要转成向量的教学文本。'
  return '请只回复 ok，用于模型连通性与输出格式测试。'
})

async function loadHealth() {
  loading.value = true
  error.value = ''
  try {
    const [healthResult, connectivityResult] = await Promise.all([
      api<SystemHealth>('/api/logs/health'),
      api<ModelConnectivity>('/api/ai/connectivity'),
    ])
    health.value = healthResult
    connectivity.value = connectivityResult
  } catch (err) {
    error.value = err instanceof Error ? err.message : '演示检查加载失败'
  } finally {
    loading.value = false
  }
}

async function probeModels() {
  probing.value = true
  probeError.value = ''
  try {
    connectivity.value = await api<ModelConnectivity>('/api/ai/connectivity?probe=true')
  } catch (err) {
    probeError.value = err instanceof Error ? err.message : '模型连通性检测失败'
  } finally {
    probing.value = false
  }
}

function selectModelTestFile(event: Event) {
  const input = event.target as HTMLInputElement
  modelTestFile.value = input.files?.[0] ?? null
  modelTestResult.value = null
  modelTestError.value = ''
}

function selectModelTestRole(role: string) {
  activeTestRole.value = role
  modelTestResult.value = null
  modelTestError.value = ''
  modelTestFile.value = null
  modelTestPrompt.value = role === 'vision'
    ? '请分析这张图片里可用于教学的关键信息，并给出可转成课件或习题的建议。'
    : '请只回复 ok，用于模型连通性与输出格式测试。'
}

async function runModelTest() {
  if (isVisionTest.value && !modelTestFile.value) {
    modelTestError.value = '请先选择一张图片。'
    return
  }
  modelTesting.value = true
  modelTestError.value = ''
  modelTestResult.value = null
  try {
    if (isVisionTest.value) {
      const form = new FormData()
      form.append('prompt', modelTestPrompt.value)
      form.append('file', modelTestFile.value as File)
      modelTestResult.value = await apiForm<ModelTestResponse>('/api/ai/admin/model-tests/vision-image', form)
    } else {
      modelTestResult.value = await api<ModelTestResponse>(`/api/ai/admin/model-tests/${activeTestRole.value}`, {
        method: 'POST',
        body: JSON.stringify({ prompt: modelTestPrompt.value }),
      })
    }
  } catch (err) {
    modelTestError.value = err instanceof Error ? err.message : '模型测试失败'
  } finally {
    modelTesting.value = false
  }
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    healthy: '正常',
    degraded: '部分异常',
    unhealthy: '不可用',
    unknown: '未知',
    not_tested: '未检测',
    not_configured: '未配置',
    success: '成功',
    failed: '失败',
  }
  return labels[status] ?? status
}

function statusClass(status: string): string {
  if (status === 'healthy' || status === 'success') return 'success'
  if (status === 'degraded' || status === 'not_tested') return 'warning'
  if (status === 'unhealthy' || status === 'failed' || status === 'not_configured') return 'danger'
  return ''
}

function booleanText(value: boolean): string {
  return value ? '已配置' : '未配置'
}

function roleLabel(role: string): string {
  const labels: Record<string, string> = {
    generate: '生成模型',
    review: '审核模型',
    revise: '修订模型',
    vision: '视觉模型',
    embedding: '向量模型',
  }
  return labels[role] ?? role
}

onMounted(loadHealth)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">演示检查</p>
        <h1>系统健康检查</h1>
        <p>集中检查后端、数据库、缓存、模型配置和观测日志。点击模型检测按钮时，才会真正请求模型 API。</p>
      </div>
      <div class="hero-actions">
        <button type="button" class="btn-secondary" :disabled="loading" @click="loadHealth">
          {{ loading ? '检查中...' : '重新检查' }}
        </button>
        <button type="button" class="btn-primary" :disabled="probing" @click="probeModels">
          {{ probing ? '检测中...' : '检测真实模型 API' }}
        </button>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="probeError" class="alert" role="alert">{{ probeError }}</p>
    <p v-else-if="loading && !health" class="notice">正在读取系统健康状态...</p>

    <template v-if="health">
      <section class="metric-grid health-metrics">
        <article class="metric-card">
          <span>整体状态</span>
          <strong>
            <span class="status-pill" :class="statusClass(health.overall_status)">
              {{ overallText }}
            </span>
          </strong>
        </article>
        <article class="metric-card">
          <span>模型调用</span>
          <strong>{{ health.observability.model_total }}</strong>
          <small>失败 {{ health.observability.model_failed }} 次</small>
        </article>
        <article class="metric-card">
          <span>后台任务</span>
          <strong>{{ health.observability.job_total }}</strong>
          <small>失败 {{ health.observability.job_failed }} 次</small>
        </article>
      </section>

      <div class="two-column-grid">
        <section class="panel stack">
          <h2>基础服务</h2>
          <div class="service-row">
            <div>
              <strong>数据库</strong>
              <small>{{ health.database.kind }}</small>
            </div>
            <span class="status-pill" :class="statusClass(health.database.status)">
              {{ statusLabel(health.database.status) }}
            </span>
          </div>
          <p class="muted">{{ health.database.message }}</p>

          <div class="service-row">
            <div>
              <strong>缓存</strong>
              <small>{{ health.cache.kind }}</small>
            </div>
            <span class="status-pill" :class="statusClass(health.cache.status)">
              {{ statusLabel(health.cache.status) }}
            </span>
          </div>
          <p class="muted">{{ health.cache.message }}</p>

          <div class="service-row">
            <div>
              <strong>向量数据库</strong>
              <small>{{ health.vector_store.kind }}</small>
            </div>
            <span class="status-pill" :class="statusClass(health.vector_store.status)">
              {{ statusLabel(health.vector_store.status) }}
            </span>
          </div>
          <p class="muted">{{ health.vector_store.message }}</p>
        </section>

        <section class="panel stack">
          <h2>模型配置</h2>
          <dl class="kv-list">
            <div>
              <dt>主模型</dt>
              <dd>{{ health.models.text_model }}</dd>
            </div>
            <div>
              <dt>生成 / 审核 / 修订</dt>
              <dd>
                {{ health.models.generate_model || '未配置' }}
                <span class="status-pill" :class="statusClass(health.models.generate_configured ? 'success' : 'not_configured')">
                  {{ health.models.generate_configured ? '可用' : '未配置' }}
                </span>
                /
                {{ health.models.review_model || '未配置' }}
                <span class="status-pill" :class="statusClass(health.models.review_configured ? 'success' : 'not_configured')">
                  {{ health.models.review_configured ? '可用' : '未配置' }}
                </span>
                /
                {{ health.models.revise_model || '未配置' }}
                <span class="status-pill" :class="statusClass(health.models.revise_configured ? 'success' : 'not_configured')">
                  {{ health.models.revise_configured ? '可用' : '未配置' }}
                </span>
              </dd>
            </div>
            <div>
              <dt>文本模型密钥</dt>
              <dd>{{ booleanText(health.models.api_key_configured) }}</dd>
            </div>
            <div>
              <dt>视觉模型</dt>
              <dd>
                {{ health.models.vision_model || '未配置' }}
                <span class="status-pill" :class="statusClass(health.models.vision_configured ? 'success' : 'not_configured')">
                  {{ health.models.vision_configured ? '可用' : '未配置' }}
                </span>
              </dd>
            </div>
            <div>
              <dt>向量模型</dt>
              <dd>
                {{ health.models.embedding_model || '未配置' }}
                <span class="status-pill" :class="statusClass(health.models.embedding_configured ? 'success' : 'not_configured')">
                  {{ health.models.embedding_configured ? '可用' : '未配置' }}
                </span>
              </dd>
            </div>
          </dl>
          <p class="strategy-note">
            生成审核策略：多 AI 审核{{ health.models.multi_agent_review ? '已启用' : '未启用' }}，
            失败兜底{{ health.models.mock_on_failure ? '已启用' : '未启用' }}。策略开关由后端环境与生成流程控制。
          </p>
        </section>
      </div>

      <section class="panel stack">
        <div class="panel-title">
          <h2>模型连通性</h2>
          <small>{{ connectivity?.probe_enabled ? '已执行真实请求' : '仅检查配置，未请求模型 API' }}</small>
        </div>
        <div v-if="connectivity" class="connectivity-grid">
          <article v-for="check in connectivity.checks" :key="check.role">
            <div>
              <strong>{{ roleLabel(check.role) }}</strong>
              <small>{{ check.model || '未配置模型' }}</small>
            </div>
            <span class="status-pill" :class="statusClass(check.status)">
              {{ statusLabel(check.status) }}
            </span>
            <p>{{ check.message }}</p>
            <small v-if="check.latency_ms !== null">耗时 {{ check.latency_ms }}ms</small>
          </article>
        </div>
      </section>

      <section class="panel demo-entry">
        <div>
          <h2>演示数据</h2>
          <p class="muted">
            样例账号、课程、知识库、练习和题库初始化已移到数据库管理页，便于答辩时一键准备和查看数据规模。
          </p>
        </div>
        <RouterLink class="btn-secondary" to="/dashboard/admin/database">
          打开数据库管理
        </RouterLink>
      </section>
      <section class="panel stack">
        <div class="panel-title">
          <h2>模型单项测试</h2>
          <small>按标签单独测试 API 管理中保存的模型配置。</small>
        </div>
        <div class="test-tabs" role="tablist" aria-label="模型测试类型">
          <button
            v-for="tab in modelTestTabs"
            :key="tab.role"
            type="button"
            role="tab"
            :aria-selected="activeTestRole === tab.role"
            :class="{ active: activeTestRole === tab.role }"
            @click="selectModelTestRole(tab.role)"
          >
            {{ tab.label }}
          </button>
        </div>
        <div class="test-summary">
          <div>
            <strong>{{ activeTestTab.label }}</strong>
            <small>
              {{ activeConnectivity?.model || '未配置模型' }}
              · {{ activeConnectivity ? statusLabel(activeConnectivity.status) : '未检测' }}
            </small>
          </div>
          <span v-if="activeConnectivity" class="status-pill" :class="statusClass(activeConnectivity.status)">
            {{ statusLabel(activeConnectivity.status) }}
          </span>
        </div>
        <div class="vision-test-grid">
          <label>
            测试输入
            <textarea v-model.trim="modelTestPrompt" rows="4" :placeholder="activePromptPlaceholder" />
          </label>
          <label v-if="isVisionTest">
            图片
            <input type="file" accept="image/*" @change="selectModelTestFile" />
          </label>
        </div>
        <button
          type="button"
          class="btn-primary"
          :disabled="modelTesting || (isVisionTest && !modelTestFile)"
          @click="runModelTest"
        >
          {{ modelTesting ? '测试中...' : `测试${activeTestTab.label}` }}
        </button>
        <p v-if="modelTestError" class="alert" role="alert">{{ modelTestError }}</p>
        <div v-if="modelTestResult" class="vision-result">
          <strong>{{ modelTestResult.provider_status?.model || activeTestTab.label }}</strong>
          <p>{{ modelTestResult.content }}</p>
          <small v-if="modelTestResult.vector_dimensions">
            向量维度 {{ modelTestResult.vector_dimensions }} · 前 8 维：
            {{ modelTestResult.vector_preview.join(' / ') }}
          </small>
          <small v-else-if="modelTestResult.provider_status">
            来源 {{ modelTestResult.provider_status.provider }}
            {{ modelTestResult.provider_status.fallback_used ? ' · 使用了兜底内容' : '' }}
          </small>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.health-metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-card strong {
  display: flex;
  align-items: center;
  min-height: 32px;
}

.service-row {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}

.service-row:first-of-type {
  border-top: 0;
  padding-top: 0;
}

.service-row div {
  display: grid;
  gap: 4px;
}

.kv-list {
  display: grid;
  gap: 12px;
  margin: 0;
}

.kv-list div {
  display: grid;
  grid-template-columns: 130px minmax(0, 1fr);
  gap: 12px;
  border-bottom: 1px solid #edf1f7;
  padding-bottom: 10px;
}

.kv-list div:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.kv-list dt {
  color: var(--muted);
  font-weight: 800;
}

.kv-list dd {
  margin: 0;
  color: var(--text);
  overflow-wrap: anywhere;
}

.strategy-note {
  margin: 0;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 11px 12px;
  color: var(--brand-ink);
  background: var(--brand-soft);
  line-height: 1.6;
}

.connectivity-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.connectivity-grid article {
  display: grid;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.connectivity-grid p {
  margin: 0;
  color: var(--muted);
  line-height: 1.5;
}

.demo-entry {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}

.demo-entry p {
  margin: 8px 0 0;
  line-height: 1.6;
}

.test-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.test-tabs button {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 12px;
  color: #334155;
  background: #ffffff;
  font-weight: 900;
}

.test-tabs button.active {
  border-color: #93c5fd;
  color: var(--brand-dark);
  background: var(--brand-soft);
}

.test-summary {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--surface-soft);
}

.test-summary div {
  display: grid;
  gap: 4px;
}

.vision-test-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.5fr);
  gap: 12px;
  align-items: end;
}

.vision-result {
  display: grid;
  gap: 8px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 12px;
  background: #eff6ff;
}

.vision-result p {
  margin: 0;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .health-metrics,
  .connectivity-grid,
  .vision-test-grid {
    grid-template-columns: 1fr;
  }

  .kv-list div {
    grid-template-columns: 1fr;
  }

  .demo-entry {
    display: grid;
  }
}
</style>

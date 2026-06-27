<script setup lang="ts">
import { reactive, ref } from 'vue'

import { api } from '../api/client'

interface ComplianceResult {
  risk_level: string
  matched_terms: string[]
  suggestions: string[]
}

const form = reactive({
  content_type: 'lesson',
  content_id: '',
  content: '',
})

const result = ref<ComplianceResult | null>(null)
const loading = ref(false)
const error = ref('')

function riskLabel(value: string): string {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  }
  return labels[value] ?? value
}

async function checkCompliance() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await api<ComplianceResult>('/api/compliance/check', {
      method: 'POST',
      body: JSON.stringify({
        content_type: form.content_type,
        content_id: form.content_id || null,
        content: form.content,
      }),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '合规检查失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">审核</p>
        <h1>合规检查</h1>
        <p>对教案、习题或材料片段进行风险检查，查看命中词和修改建议。</p>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>

    <div class="audit-grid">
      <form class="panel stack" @submit.prevent="checkCompliance">
        <label>
          内容类型
          <select v-model="form.content_type">
            <option value="lesson">备课</option>
            <option value="exercise">习题</option>
            <option value="material">材料</option>
            <option value="other">其他</option>
          </select>
        </label>
        <label>
          内容 ID（可选）
          <input v-model.trim="form.content_id" placeholder="用于关联业务记录" />
        </label>
        <label>
          待检查内容
          <textarea v-model.trim="form.content" rows="14" required placeholder="粘贴需要检查的文本" />
        </label>
        <button class="btn-primary" type="submit" :disabled="loading">
          {{ loading ? '检查中...' : '开始检查' }}
        </button>
      </form>

      <section class="panel stack">
        <h2>检查结果</h2>
        <p v-if="!result" class="empty-state">提交内容后会在这里显示风险等级、命中词和修改建议。</p>
        <template v-else>
          <div class="risk-card" :class="result.risk_level">
            <span>风险等级</span>
            <strong>{{ riskLabel(result.risk_level) }}</strong>
          </div>

          <section class="stack">
            <h3>命中词</h3>
            <p v-if="!result.matched_terms.length" class="empty-state">未命中敏感词。</p>
            <ul v-else class="clean-list">
              <li v-for="term in result.matched_terms" :key="term">{{ term }}</li>
            </ul>
          </section>

          <section class="stack">
            <h3>修改建议</h3>
            <p v-if="!result.suggestions.length" class="empty-state">暂无修改建议。</p>
            <ul v-else class="clean-list">
              <li v-for="suggestion in result.suggestions" :key="suggestion">{{ suggestion }}</li>
            </ul>
          </section>
        </template>
      </section>
    </div>
  </section>
</template>

<style scoped>
.audit-grid {
  display: grid;
  grid-template-columns: minmax(280px, 520px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.risk-card {
  display: grid;
  gap: 6px;
  border-radius: 8px;
  padding: 16px;
  color: var(--brand-dark);
  background: var(--brand-soft);
}

.risk-card span {
  color: var(--muted);
}

.risk-card strong {
  font-size: 1.7rem;
}

.risk-card.low {
  color: #166534;
  background: var(--success-soft);
}

.risk-card.medium {
  color: #92400e;
  background: var(--warning-soft);
}

.risk-card.high {
  color: #991b1b;
  background: var(--danger-soft);
}

@media (max-width: 860px) {
  .audit-grid {
    grid-template-columns: 1fr;
  }
}
</style>

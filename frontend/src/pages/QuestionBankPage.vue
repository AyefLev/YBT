<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { api, apiBlob, downloadBlobResponse } from '../api/client'
import MarkdownPreview from '../components/MarkdownPreview.vue'
import { useAuthStore } from '../stores/auth'

interface Question {
  id: number
  owner_id: number
  owner_name: string
  owner_username: string
  title: string
  subject: string
  question_type: string
  difficulty: string
  stem: string
  options: string[]
  answer: string
  analysis: string
  tags: string[]
  status: string
}

const auth = useAuthStore()
const questions = ref<Question[]>([])
const loading = ref('')
const error = ref('')
const notice = ref('')
const filters = reactive({ subject: '', difficulty: '', status: '' })
const form = reactive({
  title: '',
  subject: '',
  question_type: 'short_answer',
  difficulty: 'basic',
  stem: '',
  options_text: '',
  answer: '',
  analysis: '',
  tags_text: '',
})
const canCreateQuestions = computed(() => auth.user?.permissions.includes('exercise:create') ?? false)
const canExportQuestions = computed(() => auth.user?.permissions.includes('lesson:export') ?? false)

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function splitTags(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function typeLabel(value: string): string {
  const labels: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    fill_blank: '填空题',
    short_answer: '简答题',
    true_false: '判断题',
  }
  return labels[value] ?? value
}

function difficultyLabel(value: string): string {
  const labels: Record<string, string> = {
    basic: '基础',
    medium: '中等',
    advanced: '提高',
  }
  return labels[value] ?? value
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    draft: '草稿',
    pending_review: '待审核',
    approved: '已通过',
    rejected: '已退回',
  }
  return labels[value] ?? value
}

async function loadQuestions() {
  const params = new URLSearchParams()
  if (filters.subject) params.set('subject', filters.subject)
  if (filters.difficulty) params.set('difficulty', filters.difficulty)
  if (filters.status) params.set('status', filters.status)
  const query = params.toString()
  try {
    questions.value = await api<Question[]>(`/api/questions${query ? `?${query}` : ''}`)
  } catch (err) {
    setError(err, '题库列表加载失败')
  }
}

async function createQuestion() {
  loading.value = 'create'
  error.value = ''
  notice.value = ''
  try {
    const question = await api<Question>('/api/questions', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title,
        subject: form.subject,
        question_type: form.question_type,
        difficulty: form.difficulty,
        stem: form.stem,
        options: splitLines(form.options_text),
        answer: form.answer,
        analysis: form.analysis,
        tags: splitTags(form.tags_text),
      }),
    })
    Object.assign(form, {
      title: '',
      subject: '',
      question_type: 'short_answer',
      difficulty: 'basic',
      stem: '',
      options_text: '',
      answer: '',
      analysis: '',
      tags_text: '',
    })
    notice.value = `题目 ${question.id} 已创建`
    await loadQuestions()
  } catch (err) {
    setError(err, '题目创建失败')
  } finally {
    loading.value = ''
  }
}

async function submitReview(question: Question) {
  loading.value = `submit-${question.id}`
  error.value = ''
  try {
    await api<Question>(`/api/questions/${question.id}/submit-review`, { method: 'POST' })
    notice.value = `题目 ${question.id} 已提交审核`
    await loadQuestions()
  } catch (err) {
    setError(err, '提交审核失败')
  } finally {
    loading.value = ''
  }
}

async function exportQuestions() {
  const ids = questions.value.map((question) => question.id)
  if (!ids.length) return
  try {
    const result = await apiBlob('/api/exports/questions/docx', {
      method: 'POST',
      body: JSON.stringify({ question_ids: ids }),
    })
    downloadBlobResponse(result, 'question-package.docx')
    notice.value = `题库文档已开始下载：${result.filename ?? 'question-package.docx'}`
  } catch (err) {
    setError(err, '题库导出失败')
  }
}

onMounted(loadQuestions)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">题库管理</p>
        <h1>机构题库</h1>
        <p>创建、筛选、提交审核并导出机构题库题目。</p>
      </div>
    </header>

    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="question-grid">
      <form v-if="canCreateQuestions" class="panel stack" @submit.prevent="createQuestion">
        <h2>创建题目</h2>
        <input v-model.trim="form.title" required placeholder="题目标题" />
        <input v-model.trim="form.subject" required placeholder="学科" />
        <select v-model="form.question_type">
          <option value="single_choice">单选题</option>
          <option value="multiple_choice">多选题</option>
          <option value="fill_blank">填空题</option>
          <option value="short_answer">简答题</option>
          <option value="true_false">判断题</option>
        </select>
        <select v-model="form.difficulty">
          <option value="basic">基础</option>
          <option value="medium">中等</option>
          <option value="advanced">提高</option>
        </select>
        <textarea v-model.trim="form.stem" required rows="4" placeholder="题干" />
        <textarea v-model="form.options_text" rows="3" placeholder="选项，每行一个" />
        <textarea v-model.trim="form.answer" rows="2" placeholder="答案" />
        <textarea v-model.trim="form.analysis" rows="3" placeholder="解析" />
        <input v-model.trim="form.tags_text" placeholder="标签，多个标签用英文逗号分隔" />
        <button class="btn-primary" :disabled="loading === 'create'">创建题目</button>
      </form>

      <section class="panel stack">
        <h2>筛选与导出</h2>
        <input v-model.trim="filters.subject" placeholder="按学科筛选" />
        <select v-model="filters.difficulty">
          <option value="">全部难度</option>
          <option value="basic">基础</option>
          <option value="medium">中等</option>
          <option value="advanced">提高</option>
        </select>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option value="draft">草稿</option>
          <option value="pending_review">待审核</option>
          <option value="approved">已通过</option>
          <option value="rejected">已退回</option>
        </select>
        <button type="button" class="btn-primary" @click="loadQuestions">检索</button>
        <button v-if="canExportQuestions" type="button" class="btn-secondary" :disabled="!questions.length" @click="exportQuestions">
          导出当前列表
        </button>
      </section>
    </div>

    <section class="panel stack">
      <h2>题目列表</h2>
      <p v-if="!questions.length" class="empty-state">暂无题目。</p>
      <ul v-else class="question-list">
        <li v-for="question in questions" :key="question.id">
          <div class="stack">
            <strong>{{ question.id }} · {{ question.title }}</strong>
            <small>
              {{ question.subject }} · {{ typeLabel(question.question_type) }} ·
              {{ difficultyLabel(question.difficulty) }}
              · 所属教师 {{ question.owner_name || question.owner_username || `用户 ${question.owner_id}` }}
              <span class="status-pill" :class="question.status">{{ statusLabel(question.status) }}</span>
            </small>
            <div class="question-preview">
              <MarkdownPreview :content="question.stem" />
            </div>
            <div v-if="question.options.length" class="option-list">
              <span v-for="option in question.options" :key="option">{{ option }}</span>
            </div>
            <p><strong>答案：</strong>{{ question.answer || '未设置' }}</p>
            <details v-if="question.analysis" class="analysis-detail">
              <summary>Analysis</summary>
              <MarkdownPreview :content="question.analysis" />
            </details>
          </div>
          <button
            v-if="canCreateQuestions"
            type="button"
            class="btn-secondary"
            :disabled="question.status === 'pending_review'"
            @click="submitReview(question)"
          >
            提交审核
          </button>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.question-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.question-list {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.question-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  border-bottom: 1px solid #edf1f7;
  padding-bottom: 14px;
}

.question-list li:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.question-list p {
  margin: 0;
  white-space: pre-wrap;
}

.question-preview,
.answer-preview,
.analysis-detail {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--surface-soft);
}

.answer-preview {
  display: grid;
  gap: 6px;
}

.option-list {
  display: grid;
  gap: 8px;
}

.option-list span {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 8px 10px;
  color: #1e3a8a;
  background: #eff6ff;
}

.analysis-detail summary {
  cursor: pointer;
  font-weight: 800;
  color: #1d4ed8;
}

@media (max-width: 900px) {
  .question-grid,
  .question-list li {
    grid-template-columns: 1fr;
  }
}
</style>

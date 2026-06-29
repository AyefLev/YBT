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

interface QuestionPayload {
  title: string
  subject: string
  question_type: string
  difficulty: string
  stem: string
  options: string[]
  answer: string
  analysis: string
  tags: string[]
}

const auth = useAuthStore()
const questions = ref<Question[]>([])
const loading = ref('')
const error = ref('')
const notice = ref('')
const filters = reactive({ subject: '', difficulty: '', status: '' })
const entryMode = ref<'bulk' | 'single'>('bulk')
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
const bulkForm = reactive({
  subject: '',
  question_type: 'single_choice',
  difficulty: 'basic',
  tags_text: '',
  text: '',
})
const canCreateQuestions = computed(() => auth.user?.permissions.includes('exercise:create') ?? false)
const canExportQuestions = computed(() => auth.user?.permissions.includes('lesson:export') ?? false)
const parsedBulkQuestions = computed(() => parseBulkQuestions())

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

function titleFromStem(stem: string, index: number): string {
  const firstLine = stem.split('\n').find((line) => line.trim())?.trim() ?? ''
  const cleaned = firstLine.replace(/^题目\s*[一二三四五六七八九十\d]*\s*[.．、:：]?\s*/, '').trim()
  return (cleaned || `批量导入题目 ${index}`).slice(0, 48)
}

function splitQuestionBlocks(value: string): string[] {
  const normalized = value.replace(/\r\n/g, '\n').trim()
  if (!normalized) return []
  const byDivider = normalized
    .split(/\n\s*-{3,}\s*\n/g)
    .map((block) => block.trim())
    .filter(Boolean)
  if (byDivider.length > 1) return byDivider

  const starts = Array.from(normalized.matchAll(/(^|\n)\s*题目\s*[一二三四五六七八九十\d]+\s*[.．、:：]?/g))
  if (starts.length <= 1) return [normalized]
  return starts
    .map((match, index) => {
      const start = match.index ?? 0
      const end = starts[index + 1]?.index ?? normalized.length
      return normalized.slice(start, end).trim()
    })
    .filter(Boolean)
}

function parseBulkQuestions(): QuestionPayload[] {
  const tags = splitTags(bulkForm.tags_text)
  if (!bulkForm.subject.trim()) return []
  return splitQuestionBlocks(bulkForm.text)
    .map((block, index) => parseQuestionBlock(block, index + 1, tags))
    .filter((question): question is QuestionPayload => Boolean(question))
}

function parseQuestionBlock(block: string, index: number, tags: string[]): QuestionPayload | null {
  const lines = block
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  if (!lines.length) return null

  const stemLines: string[] = []
  const options: string[] = []
  const analysisLines: string[] = []
  let answer = ''
  let section: 'stem' | 'analysis' = 'stem'

  lines.forEach((rawLine) => {
    const line = rawLine.replace(/^题目\s*[一二三四五六七八九十\d]+\s*[.．、:：]?\s*/, '').trim()
    if (!line) return

    const answerMatch = line.match(/^(?:答案|正确答案)\s*[:：]\s*(.+)$/)
    if (answerMatch) {
      answer = answerMatch[1].trim()
      section = 'stem'
      return
    }

    const analysisMatch = line.match(/^(?:解析|答案解析)\s*[:：]\s*(.*)$/)
    if (analysisMatch) {
      section = 'analysis'
      if (analysisMatch[1].trim()) analysisLines.push(analysisMatch[1].trim())
      return
    }

    const optionMatch = line.match(/^([A-Ha-h])[\s.．、)]\s*(.+)$/)
    if (optionMatch && section === 'stem') {
      options.push(`${optionMatch[1].toUpperCase()}. ${optionMatch[2].trim()}`)
      return
    }

    if (section === 'analysis') {
      analysisLines.push(line)
    } else {
      stemLines.push(line)
    }
  })

  const stem = stemLines.join('\n').trim()
  if (!stem) return null
  return {
    title: titleFromStem(stem, index),
    subject: bulkForm.subject.trim(),
    question_type: bulkForm.question_type,
    difficulty: bulkForm.difficulty,
    stem,
    options,
    answer,
    analysis: analysisLines.join('\n'),
    tags,
  }
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

async function createBulkQuestions() {
  const payload = parsedBulkQuestions.value
  if (!payload.length) {
    error.value = '请填写学科，并至少录入一道可识别的题目'
    notice.value = ''
    return
  }
  loading.value = 'bulk-create'
  error.value = ''
  notice.value = ''
  try {
    const created = await api<Question[]>('/api/questions/bulk', {
      method: 'POST',
      body: JSON.stringify({ questions: payload }),
    })
    Object.assign(bulkForm, {
      subject: bulkForm.subject,
      question_type: bulkForm.question_type,
      difficulty: bulkForm.difficulty,
      tags_text: bulkForm.tags_text,
      text: '',
    })
    notice.value = `已批量保存 ${created.length} 道题`
    await loadQuestions()
  } catch (err) {
    setError(err, '题目批量保存失败')
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
      <section v-if="canCreateQuestions" class="panel stack">
        <div class="mode-tabs">
          <button type="button" :class="{ active: entryMode === 'bulk' }" @click="entryMode = 'bulk'">批量录入</button>
          <button type="button" :class="{ active: entryMode === 'single' }" @click="entryMode = 'single'">单题精修</button>
        </div>

        <form v-if="entryMode === 'bulk'" class="stack" @submit.prevent="createBulkQuestions">
          <h2>批量录入题目</h2>
          <div class="three-field-grid">
            <input v-model.trim="bulkForm.subject" required placeholder="学科" />
            <select v-model="bulkForm.question_type">
              <option value="single_choice">单选题</option>
              <option value="multiple_choice">多选题</option>
              <option value="fill_blank">填空题</option>
              <option value="short_answer">简答题</option>
              <option value="true_false">判断题</option>
            </select>
            <select v-model="bulkForm.difficulty">
              <option value="basic">基础</option>
              <option value="medium">中等</option>
              <option value="advanced">提高</option>
            </select>
          </div>
          <textarea
            v-model="bulkForm.text"
            required
            rows="14"
            placeholder="题目1：函数在某点连续的条件是什么？
A. 左极限存在
B. 右极限存在
C. 函数值存在
D. 左右极限存在且等于函数值
答案：D
解析：连续要求极限存在并等于函数值。
---
题目2：..."
          />
          <input v-model.trim="bulkForm.tags_text" placeholder="标签，多个标签用英文逗号分隔" />
          <div class="bulk-summary">
            <strong>已识别 {{ parsedBulkQuestions.length }} 道题</strong>
            <span v-if="parsedBulkQuestions.length">保存后均进入草稿，可继续逐题修改或提交审核。</span>
          </div>
          <button class="btn-primary" :disabled="loading === 'bulk-create' || !parsedBulkQuestions.length">批量保存</button>
        </form>

        <form v-else class="stack" @submit.prevent="createQuestion">
          <h2>单题精修</h2>
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
          <button class="btn-primary" :disabled="loading === 'create'">保存题目</button>
        </form>
      </section>

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
              <summary>查看解析</summary>
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

.mode-tabs {
  display: inline-flex;
  gap: 4px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 4px;
  background: var(--surface-soft);
}

.mode-tabs button {
  border: 0;
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--muted);
  background: transparent;
  font-weight: 900;
}

.mode-tabs button.active {
  color: #ffffff;
  background: var(--brand);
}

.three-field-grid {
  display: grid;
  grid-template-columns: 1fr 160px 140px;
  gap: 10px;
}

.bulk-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 10px 12px;
  background: #eff6ff;
}

.bulk-summary span {
  color: var(--muted);
  font-size: 0.9rem;
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
  .question-list li,
  .three-field-grid {
    grid-template-columns: 1fr;
  }
}
</style>

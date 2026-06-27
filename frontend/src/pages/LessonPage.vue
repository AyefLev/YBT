<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { api, apiBlob, downloadBlobResponse } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { clearSelectionDependentState } from './workbenchSelection'

interface Compliance {
  risk_level: string
  matched_terms: string[]
  suggestions: string[]
}

interface AIReview {
  enabled: boolean
  status: string
  reviewer_model: string
  warnings: string[]
  suggestions: string[]
  raw_review: string
  revised_content: string | null
}

interface LessonRead {
  id: number
  owner_id: number
  owner_name: string
  owner_username: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
  title: string
  subject: string
  chapter: string
  stage: string
  duration_minutes: number
  student_level: string
  current_content: string
  material_ids: number[]
  prompt_template: string
  output_format: string
  compliance_level: string
  updated_at: string
}

interface Course {
  id: number
  title: string
  subject: string
}

interface Chapter {
  id: number
  title: string
  sessions: LessonSession[]
}

interface LessonSession {
  id: number
  title: string
  teaching_goal: string
}

interface KnowledgePoint {
  id: number
  chapter_id: number | null
  session_id: number | null
  name: string
}

interface CourseDetail extends Course {
  chapters: Chapter[]
  knowledge_points: KnowledgePoint[]
}

interface LessonVersion {
  id: number
  version_no: number
  content: string
  change_note: string
  created_at: string
}

interface LessonGenerateResponse {
  content: string
  references: Array<{ id: number; material_id: number; content: string; score: number }>
  compliance: Compliance
  review: AIReview | null
}

const auth = useAuthStore()
const form = reactive({
  course_id: 0,
  chapter_id: 0,
  session_id: 0,
  knowledge_point_id: 0,
  title: '新课备课',
  subject: '英语',
  chapter: '',
  stage: '强化',
  duration_minutes: 90,
  student_level: '基础一般',
  teaching_goal: '',
  use_materials: false,
  material_ids: '',
  prompt_template: '',
  output_format: '',
  change_note: '首次保存',
})

const content = ref('')
const lessons = ref<LessonRead[]>([])
const courses = ref<Course[]>([])
const selectedCourse = ref<CourseDetail | null>(null)
const versions = ref<LessonVersion[]>([])
const compliance = ref<Compliance | null>(null)
const review = ref<AIReview | null>(null)
const references = ref<LessonGenerateResponse['references']>([])
const generatedContent = ref('')
const selectedLessonId = ref<number | null>(null)
const loading = ref('')
const error = ref('')
const notice = ref('')

const selectedLesson = computed(() => lessons.value.find((lesson) => lesson.id === selectedLessonId.value))
const canCreateLessons = computed(() => auth.user?.permissions.includes('lesson:create') ?? false)
const canExportLessons = computed(() => auth.user?.permissions.includes('lesson:export') ?? false)
const selectedChapter = computed(() =>
  selectedCourse.value?.chapters.find((chapter) => chapter.id === form.chapter_id) ?? null,
)
const availableSessions = computed(() => selectedChapter.value?.sessions ?? [])
const availableKnowledgePoints = computed(() =>
  selectedCourse.value?.knowledge_points.filter((point) =>
    (!form.chapter_id || point.chapter_id === form.chapter_id) &&
    (!form.session_id || point.session_id === form.session_id || point.session_id === null),
  ) ?? [],
)
const revisedPreviewContent = computed(() => review.value?.revised_content ?? '')
const dependentState = {
  versions,
  compliance,
  references,
  generatedContent,
}

function materialIds(): number[] {
  return form.material_ids
    .split(',')
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value > 0)
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function riskLabel(value: string): string {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  }
  return labels[value] ?? value
}

function setMessage(message = '') {
  notice.value = message
  error.value = ''
}

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

function fillFromLesson(lesson: LessonRead, clearDependentState = false) {
  if (clearDependentState) {
    clearSelectionDependentState(dependentState, lesson.current_content)
    review.value = null
  }

  selectedLessonId.value = lesson.id
  form.title = lesson.title
  form.course_id = lesson.course_id ?? 0
  form.chapter_id = lesson.chapter_id ?? 0
  form.session_id = lesson.session_id ?? 0
  form.knowledge_point_id = lesson.knowledge_point_id ?? 0
  form.subject = lesson.subject
  form.chapter = lesson.chapter
  form.stage = lesson.stage
  form.duration_minutes = lesson.duration_minutes
  form.student_level = lesson.student_level
  form.material_ids = lesson.material_ids.join(',')
  form.prompt_template = lesson.prompt_template
  form.output_format = lesson.output_format
  content.value = lesson.current_content
}

async function loadCourses() {
  courses.value = await api<Course[]>('/api/courses')
}

async function loadCourseDetail(courseId: number) {
  if (!courseId) {
    selectedCourse.value = null
    return
  }
  selectedCourse.value = await api<CourseDetail>(`/api/courses/${courseId}`)
  form.subject = selectedCourse.value.subject || form.subject
}

async function selectCourse() {
  form.chapter_id = 0
  form.session_id = 0
  form.knowledge_point_id = 0
  await loadCourseDetail(form.course_id)
}

async function loadLessons() {
  try {
    lessons.value = await api<LessonRead[]>('/api/lessons')
  } catch (err) {
    setError(err, '备课列表加载失败')
  }
}

async function generateLesson() {
  loading.value = 'generate'
  setMessage()
  try {
    const result = await api<LessonGenerateResponse>('/api/lessons/generate', {
      method: 'POST',
      body: JSON.stringify({
        subject: form.subject,
        course_id: form.course_id || null,
        chapter_id: form.chapter_id || null,
        session_id: form.session_id || null,
        knowledge_point_id: form.knowledge_point_id || null,
        chapter: form.chapter,
        stage: form.stage,
        duration_minutes: form.duration_minutes,
        student_level: form.student_level,
        teaching_goal: form.teaching_goal,
        use_materials: form.use_materials,
        material_ids: materialIds(),
        prompt_template: form.prompt_template,
        output_format: form.output_format,
      }),
    })
    content.value = result.content
    compliance.value = result.compliance
    review.value = result.review
    references.value = result.references
    generatedContent.value = result.content
    setMessage('备课内容已生成，可继续编辑后保存。')
  } catch (err) {
    setError(err, '备课生成失败')
  } finally {
    loading.value = ''
  }
}

function adoptRevisedContent() {
  if (!revisedPreviewContent.value) return
  content.value = revisedPreviewContent.value
  generatedContent.value = revisedPreviewContent.value
  setMessage('已采用 AI 修订稿，可继续编辑后保存。')
}

async function saveLesson() {
  loading.value = 'save'
  setMessage()
  try {
    const saved = await api<LessonRead>('/api/lessons', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title,
        course_id: form.course_id || null,
        chapter_id: form.chapter_id || null,
        session_id: form.session_id || null,
        knowledge_point_id: form.knowledge_point_id || null,
        subject: form.subject,
        chapter: form.chapter,
        stage: form.stage,
        duration_minutes: form.duration_minutes,
        student_level: form.student_level,
        content: content.value,
        material_ids: materialIds(),
        prompt_template: form.prompt_template,
        output_format: form.output_format,
        change_note: form.change_note,
      }),
    })
    fillFromLesson(saved, true)
    await loadLessons()
    setMessage('备课已保存。')
  } catch (err) {
    setError(err, '备课保存失败')
  } finally {
    loading.value = ''
  }
}

async function loadVersions(lesson: LessonRead) {
  loading.value = 'versions'
  setMessage()
  fillFromLesson(lesson, true)
  try {
    versions.value = await api<LessonVersion[]>(`/api/lessons/${lesson.id}/versions`)
  } catch (err) {
    setError(err, '版本记录加载失败')
  } finally {
    loading.value = ''
  }
}

async function exportLesson(lessonId = selectedLessonId.value) {
  if (!lessonId) {
    setError(new Error('请先选择或保存一份备课'), '导出失败')
    return
  }

  loading.value = 'export'
  setMessage()
  try {
    const result = await apiBlob(`/api/exports/lesson/${lessonId}/docx`, { method: 'POST' })
    downloadBlobResponse(result, `lesson-${lessonId}.docx`)
    setMessage('导出文件已开始下载。')
  } catch (err) {
    setError(err, '备课导出失败')
  } finally {
    loading.value = ''
  }
}

onMounted(async () => {
  await Promise.all([loadLessons(), loadCourses()])
})
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">备课</p>
        <h1>新建备课</h1>
        <p>填写教学目标，生成可编辑教案，并保存为可追溯的版本记录。</p>
      </div>
      <button v-if="canExportLessons" type="button" class="btn-secondary" :disabled="!selectedLessonId || loading === 'export'" @click="exportLesson()">
        {{ loading === 'export' ? '导出中...' : '导出 DOCX' }}
      </button>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="canCreateLessons" class="editor-grid">
      <form class="panel form-grid" @submit.prevent="generateLesson">
        <label>
          课程
          <select v-model.number="form.course_id" @change="selectCourse">
            <option :value="0">不绑定课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">
              {{ course.title }}
            </option>
          </select>
        </label>
        <label>
          章节
          <select v-model.number="form.chapter_id" :disabled="!selectedCourse">
            <option :value="0">不绑定章节</option>
            <option v-for="chapter in selectedCourse?.chapters ?? []" :key="chapter.id" :value="chapter.id">
              {{ chapter.title }}
            </option>
          </select>
        </label>
        <label>
          课次
          <select v-model.number="form.session_id" :disabled="!form.chapter_id">
            <option :value="0">不绑定课次</option>
            <option v-for="session in availableSessions" :key="session.id" :value="session.id">
              {{ session.title }}
            </option>
          </select>
        </label>
        <label>
          知识点
          <select v-model.number="form.knowledge_point_id" :disabled="!selectedCourse">
            <option :value="0">不绑定知识点</option>
            <option v-for="point in availableKnowledgePoints" :key="point.id" :value="point.id">
              {{ point.name }}
            </option>
          </select>
        </label>
        <label>
          标题
          <input v-model.trim="form.title" required />
        </label>
        <label>
          学科
          <input v-model.trim="form.subject" required />
        </label>
        <label>
          章节
          <input v-model.trim="form.chapter" required />
        </label>
        <label>
          阶段
          <input v-model.trim="form.stage" required />
        </label>
        <label>
          课时分钟
          <input v-model.number="form.duration_minutes" type="number" min="1" required />
        </label>
        <label>
          学情
          <input v-model.trim="form.student_level" required />
        </label>
        <label class="wide">
          教学目标
          <textarea v-model.trim="form.teaching_goal" rows="4" required />
        </label>
        <label class="checkbox wide">
          <input v-model="form.use_materials" type="checkbox" />
          使用机构知识库材料
        </label>
        <label class="wide">
          材料 ID（多个用英文逗号分隔）
          <input v-model.trim="form.material_ids" :disabled="!form.use_materials" placeholder="例如：1,2,3" />
        </label>
        <label class="wide">
          教师补充提示词
          <textarea v-model.trim="form.prompt_template" rows="3" placeholder="例如：强调例题讲解、课堂互动和易错点" />
        </label>
        <label class="wide">
          输出格式要求
          <textarea v-model.trim="form.output_format" rows="2" placeholder="例如：按教学目标、导入、讲解、练习、总结输出" />
        </label>
        <button class="btn-primary wide" type="submit" :disabled="loading === 'generate'">
          {{ loading === 'generate' ? '生成中...' : '生成备课' }}
        </button>
      </form>

      <section class="panel stack">
        <label>
          生成内容
          <textarea v-model="content" rows="18" placeholder="生成或粘贴备课内容后保存。" />
        </label>
        <label>
          版本说明
          <input v-model.trim="form.change_note" />
        </label>
        <button class="btn-primary" type="button" :disabled="!content || loading === 'save'" @click="saveLesson">
          {{ loading === 'save' ? '保存中...' : '保存备课' }}
        </button>

        <div v-if="compliance" class="result-card">
          <strong>合规风险：{{ riskLabel(compliance.risk_level) }}</strong>
          <p v-if="compliance.matched_terms.length">命中词：{{ compliance.matched_terms.join('、') }}</p>
          <p v-if="compliance.suggestions.length">建议：{{ compliance.suggestions.join('；') }}</p>
        </div>

        <div v-if="review?.enabled" class="result-card">
          <strong>AI 复核：{{ review.status }} · {{ review.reviewer_model }}</strong>
          <p v-if="review.warnings.length">风险：{{ review.warnings.join('；') }}</p>
          <p v-if="review.suggestions.length">建议：{{ review.suggestions.join('；') }}</p>
        </div>

        <div v-if="revisedPreviewContent" class="revision-card">
          <div class="revision-header">
            <strong>AI 修订稿</strong>
            <button type="button" class="btn-secondary" @click="adoptRevisedContent">采用修订稿</button>
          </div>
          <pre>{{ revisedPreviewContent }}</pre>
        </div>

        <div v-if="references.length" class="result-card">
          <strong>引用材料</strong>
          <p v-for="reference in references.slice(0, 3)" :key="reference.id">
            材料 {{ reference.material_id }}：{{ reference.content }}
          </p>
        </div>
      </section>
    </div>

    <section class="panel stack">
      <h2>已保存备课</h2>
      <p v-if="!lessons.length" class="empty-state">暂无备课记录。</p>
      <ul v-else class="item-list">
        <li v-for="lesson in lessons" :key="lesson.id" :class="{ active: lesson.id === selectedLessonId }">
          <div class="stack">
            <strong>{{ lesson.title }}</strong>
            <small>
              {{ lesson.subject }} · {{ lesson.chapter }}
              · 所属教师 {{ lesson.owner_name || lesson.owner_username || `用户 ${lesson.owner_id}` }}
              <span class="status-pill" :class="lesson.compliance_level">{{ riskLabel(lesson.compliance_level) }}</span>
              {{ formatDate(lesson.updated_at) }}
            </small>
          </div>
          <div class="actions">
            <button type="button" class="btn-secondary" @click="loadVersions(lesson)">版本</button>
            <button v-if="canExportLessons" type="button" class="btn-secondary" @click="exportLesson(lesson.id)">导出</button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="selectedLesson && versions.length" class="panel stack">
      <h2>{{ selectedLesson.title }} 的版本</h2>
      <ul class="clean-list version-list">
        <li v-for="version in versions" :key="version.id">
          <strong>版本 {{ version.version_no }}</strong>
          <small>{{ version.change_note || '无说明' }} · {{ formatDate(version.created_at) }}</small>
          <p>{{ version.content }}</p>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.editor-grid {
  display: grid;
  grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.result-card {
  display: grid;
  gap: 6px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 12px;
  color: #1e3a8a;
  background: #eff6ff;
}

.result-card p,
.version-list p {
  margin: 0;
  white-space: pre-wrap;
}

.revision-card {
  display: grid;
  gap: 10px;
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 12px;
  color: #14532d;
  background: #f0fdf4;
}

.revision-header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.revision-card pre {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  font-family: inherit;
  line-height: 1.55;
}

.item-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.item-list li {
  display: flex;
  gap: 14px;
  justify-content: space-between;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
}

.item-list li.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

@media (max-width: 940px) {
  .editor-grid,
  .item-list li {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api, apiBlob, downloadBlobResponse } from '../api/client'
import MarkdownPreview from '../components/MarkdownPreview.vue'
import MaterialPicker from '../components/MaterialPicker.vue'
import { useAuthStore } from '../stores/auth'
import { buildTeachingContextQuery, parseTeachingContextQuery } from './contextQuery'
import {
  clearGenerationDraft,
  draftStorageKey,
  loadGenerationDraft,
  saveGenerationDraft,
  type GenerationDraft,
} from './generationDraft'
import { lessonDefaultsFromContext } from './teachingContext'
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
  summary: string
  sessions: LessonSession[]
}

interface LessonSession {
  id: number
  title: string
  duration_minutes: number
  teaching_goal: string
}

interface KnowledgePoint {
  id: number
  chapter_id: number | null
  session_id: number | null
  name: string
  description: string
  difficulty: string
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

interface MaterialRead {
  id: number
  title: string
  resource_scope: string
  parse_status: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
}

interface PresentationResponse {
  lesson_id: number
  queued: boolean
  message: string
}

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
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
  reference_count: 5,
  retrieval_focus: 'balanced',
  prompt_template: '',
  output_format: '',
  change_note: '首次保存',
})

const content = ref('')
const lessons = ref<LessonRead[]>([])
const courses = ref<Course[]>([])
const selectedCourse = ref<CourseDetail | null>(null)
const materials = ref<MaterialRead[]>([])
const selectedMaterialIds = ref<number[]>([])
const versions = ref<LessonVersion[]>([])
const compliance = ref<Compliance | null>(null)
const review = ref<AIReview | null>(null)
const references = ref<LessonGenerateResponse['references']>([])
const generatedContent = ref('')
const selectedLessonId = ref<number | null>(null)
const loading = ref('')
const error = ref('')
const notice = ref('')
const presentationMessage = ref('')
const draftAvailable = ref(false)
const ownerFilter = ref('all')

const selectedLesson = computed(() => lessons.value.find((lesson) => lesson.id === selectedLessonId.value))
const canCreateLessons = computed(() => auth.user?.permissions.includes('lesson:create') ?? false)
const canExportLessons = computed(() => auth.user?.permissions.includes('lesson:export') ?? false)
const canViewAllLessons = computed(() => auth.user?.permissions.includes('lesson:view_all') ?? false)
const isAdmin = computed(() => auth.user?.roles.includes('admin') ?? false)
const isTeachingManager = computed(() => auth.user?.roles.includes('teaching_manager') ?? false)
const showManagementRecords = computed(() => canViewAllLessons.value)
const requestedPageMode = computed(() => String(route.meta.pageMode || 'generate'))
const pageMode = computed(() => {
  if (requestedPageMode.value === 'generate' && !canCreateLessons.value && canViewAllLessons.value) {
    return 'records'
  }
  return requestedPageMode.value
})
const showGenerator = computed(() => canCreateLessons.value && pageMode.value === 'generate')
const showRecords = computed(() => pageMode.value === 'records')
const recordsTitle = computed(() => {
  if (!showManagementRecords.value) return '我的教案'
  return isAdmin.value ? '教案总览' : '教研教案总览'
})
const recordsDescription = computed(() => {
  if (!showManagementRecords.value) return '查看、导出并复用自己保存的教案。'
  if (isTeachingManager.value) return '按教师筛选教案，可用于教研检查和后续协作。'
  return '按教师筛选查看教案归属、合规风险和版本记录。'
})
const lessonOwnerOptions = computed(() => {
  const owners = new Map<number, string>()
  for (const lesson of lessons.value) {
    owners.set(lesson.owner_id, lesson.owner_name || lesson.owner_username || `用户 ${lesson.owner_id}`)
  }
  return [...owners.entries()].map(([id, name]) => ({ id, name }))
})
const visibleLessons = computed(() => {
  if (!showManagementRecords.value || ownerFilter.value === 'all') return lessons.value
  const ownerId = Number(ownerFilter.value)
  return lessons.value.filter((lesson) => lesson.owner_id === ownerId)
})
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
const contextIds = computed(() => ({
  course_id: form.course_id || null,
  chapter_id: form.chapter_id || null,
  session_id: form.session_id || null,
  knowledge_point_id: form.knowledge_point_id || null,
}))
const dependentState = {
  versions,
  compliance,
  references,
  generatedContent,
}

function materialIds(): number[] {
  if (selectedMaterialIds.value.length) return selectedMaterialIds.value
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

function currentDraft(status: GenerationDraft<Record<string, unknown>>['status']) {
  return {
    form: { ...form },
    content: content.value,
    selectedMaterialIds: [...selectedMaterialIds.value],
    generatedContent: generatedContent.value,
    compliance: compliance.value,
    review: review.value,
    references: references.value,
    status,
  }
}

function persistDraft(status: GenerationDraft<Record<string, unknown>>['status'] = 'editing') {
  if (!canCreateLessons.value || !auth.user) return
  saveGenerationDraft(draftStorageKey('lesson', auth.user.id), currentDraft(status))
  draftAvailable.value = true
}

async function restoreDraft() {
  if (!canCreateLessons.value || !auth.user) return
  const draft = loadGenerationDraft<Record<string, unknown>>(draftStorageKey('lesson', auth.user.id))
  if (!draft) return
  Object.assign(form, draft.form)
  content.value = draft.content || ''
  selectedMaterialIds.value = draft.selectedMaterialIds || []
  generatedContent.value = draft.generatedContent || ''
  compliance.value = draft.compliance as Compliance | null
  review.value = draft.review as AIReview | null
  references.value = (draft.references || []) as LessonGenerateResponse['references']
  draftAvailable.value = true
  if (form.course_id) await loadCourseDetail(form.course_id)
  setMessage(draft.status === 'generating' ? '已恢复生成中的未保存教案草稿。' : '已恢复未保存教案草稿。')
}

function discardDraft() {
  if (!auth.user) return
  clearGenerationDraft(draftStorageKey('lesson', auth.user.id))
  draftAvailable.value = false
  setMessage('未保存草稿已清除。')
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
  selectedMaterialIds.value = lesson.material_ids
  form.prompt_template = lesson.prompt_template
  form.output_format = lesson.output_format
  content.value = lesson.current_content
}

function canReuseLesson(lesson: LessonRead): boolean {
  if (!canCreateLessons.value) return false
  return lesson.owner_id === auth.user?.id || isTeachingManager.value
}

function reuseLessonLabel(lesson: LessonRead): string {
  return lesson.owner_id === auth.user?.id ? '继续编辑' : '复用生成'
}

async function reuseLesson(lesson: LessonRead) {
  fillFromLesson(lesson, true)
  if (lesson.owner_id !== auth.user?.id) {
    selectedLessonId.value = null
    form.title = `${lesson.title}（副本）`
  }
  if (form.course_id) await loadCourseDetail(form.course_id)
  await router.push('/dashboard/lesson/generate')
  persistDraft('editing')
  setMessage(lesson.owner_id === auth.user?.id ? '已载入自己的教案，可继续编辑后保存。' : '已载入该教案内容，可基于它生成新的教案。')
}

async function loadCourses() {
  courses.value = await api<Course[]>('/api/courses')
}

async function loadMaterials() {
  materials.value = await api<MaterialRead[]>('/api/materials')
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

async function applyRouteContext() {
  const context = parseTeachingContextQuery(route.query)
  if (!context.course_id) return
  form.course_id = context.course_id
  form.chapter_id = context.chapter_id
  form.session_id = context.session_id
  form.knowledge_point_id = context.knowledge_point_id
  await loadCourseDetail(form.course_id)
  if (selectedCourse.value) {
    const defaults = lessonDefaultsFromContext(selectedCourse.value, context)
    form.chapter = defaults.chapter || form.chapter
    form.duration_minutes = defaults.duration_minutes || form.duration_minutes
    form.teaching_goal = defaults.teaching_goal || form.teaching_goal
  }
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
  persistDraft('generating')
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
        reference_count: form.reference_count,
        retrieval_focus: form.retrieval_focus,
        prompt_template: form.prompt_template,
        output_format: form.output_format,
      }),
    })
    content.value = result.content
    compliance.value = result.compliance
    review.value = result.review
    references.value = result.references
    generatedContent.value = result.content
    persistDraft('generated')
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
  persistDraft('generated')
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
    if (auth.user) {
      clearGenerationDraft(draftStorageKey('lesson', auth.user.id))
      draftAvailable.value = false
    }
    await loadLessons()
    setMessage('备课已保存。')
  } catch (err) {
    setError(err, '备课保存失败')
  } finally {
    loading.value = ''
  }
}

async function generatePresentation() {
  if (!selectedLessonId.value) {
    setError(new Error('请先保存一份备课'), 'PPT 生成失败')
    return
  }
  loading.value = 'presentation'
  presentationMessage.value = ''
  setMessage()
  try {
    const result = await api<PresentationResponse>(
      `/api/presentations/lesson/${selectedLessonId.value}/generate`,
      {
        method: 'POST',
        body: JSON.stringify({ template_name: 'default' }),
      },
    )
    presentationMessage.value = result.message
    setMessage(result.queued ? 'PPT 生成任务已提交。' : result.message)
  } catch (err) {
    setError(err, 'PPT 生成失败')
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
  await Promise.all([loadLessons(), loadCourses(), loadMaterials()])
  await applyRouteContext()
  await restoreDraft()
})

onBeforeUnmount(() => {
  persistDraft(loading.value === 'generate' ? 'generating' : 'editing')
})

watch([form, content, selectedMaterialIds], () => {
  persistDraft(loading.value === 'generate' ? 'generating' : 'editing')
}, { deep: true })
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">教案</p>
        <h1>{{ pageMode === 'records' ? recordsTitle : '生成教案' }}</h1>
        <p>{{ pageMode === 'records' ? recordsDescription : '填写教学目标，生成可编辑教案，并保存为可追溯的版本记录。' }}</p>
      </div>
      <button v-if="canExportLessons" type="button" class="btn-secondary" :disabled="!selectedLessonId || loading === 'export'" @click="exportLesson()">
        {{ loading === 'export' ? '导出中...' : '导出 DOCX' }}
      </button>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="draftAvailable && canCreateLessons" class="draft-banner">
      当前页面有未保存草稿，切换页面后会自动保留。
      <button type="button" class="btn-secondary" @click="discardDraft">清除草稿</button>
    </p>

    <div v-if="showGenerator" class="editor-grid">
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
        <div class="wide">
          <MaterialPicker
            v-model="selectedMaterialIds"
            :materials="materials"
            :context-ids="contextIds"
            :disabled="!form.use_materials"
          />
          <div class="retrieval-grid">
            <label>
              参考资料数量
              <input v-model.number="form.reference_count" type="number" min="1" max="20" />
            </label>
            <label>
              检索侧重点
              <select v-model="form.retrieval_focus">
                <option value="precise">更精准</option>
                <option value="balanced">均衡</option>
                <option value="broad">更宽泛</option>
              </select>
            </label>
          </div>
          <RouterLink
            class="inline-action"
            :to="{ path: '/dashboard/materials/upload', query: { ...buildTeachingContextQuery(contextIds), return_to: '/dashboard/lesson/generate' } }"
          >
            上传当前课程资料
          </RouterLink>
        </div>
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
        <div class="content-grid">
          <label>
            可编辑内容
            <textarea v-model="content" rows="18" placeholder="生成或粘贴备课内容后保存。" />
          </label>
          <div class="preview-pane">
            <strong>阅读预览</strong>
            <p v-if="!content" class="empty-state">生成内容后会在这里按标题、列表和表格排版展示。</p>
            <MarkdownPreview v-else :content="content" />
          </div>
        </div>
        <label>
          版本说明
          <input v-model.trim="form.change_note" />
        </label>
        <button class="btn-primary" type="button" :disabled="!content || loading === 'save'" @click="saveLesson">
          {{ loading === 'save' ? '保存中...' : '保存备课' }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!selectedLessonId || loading === 'presentation'"
          @click="generatePresentation"
        >
          {{ loading === 'presentation' ? '提交中...' : '生成 PPT' }}
        </button>
        <p v-if="presentationMessage" class="notice">{{ presentationMessage }}</p>

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
          <MarkdownPreview :content="revisedPreviewContent" />
        </div>

        <div v-if="references.length" class="result-card">
          <strong>引用材料</strong>
          <p v-for="reference in references.slice(0, 3)" :key="reference.id">
            材料 {{ reference.material_id }}：{{ reference.content }}
          </p>
        </div>
      </section>
    </div>

    <section v-if="showRecords" class="panel stack">
      <div class="panel-title">
        <div>
          <h2>{{ recordsTitle }}</h2>
          <small>{{ showManagementRecords ? '全局记录会标注所属教师，管理员默认只查看和运维。' : '只显示当前账号创建的教案。' }}</small>
        </div>
        <label v-if="showManagementRecords && lessonOwnerOptions.length" class="compact-filter">
          所属教师
          <select v-model="ownerFilter">
            <option value="all">全部教师</option>
            <option v-for="owner in lessonOwnerOptions" :key="owner.id" :value="String(owner.id)">
              {{ owner.name }}
            </option>
          </select>
        </label>
      </div>
      <p v-if="!visibleLessons.length" class="empty-state">暂无备课记录。</p>
      <ul v-else class="item-list">
        <li v-for="lesson in visibleLessons" :key="lesson.id" :class="{ active: lesson.id === selectedLessonId }">
          <div class="stack">
            <strong>{{ lesson.title }}</strong>
            <small>
              {{ lesson.subject }} · {{ lesson.chapter }}
              <template v-if="showManagementRecords">
                · 所属教师 {{ lesson.owner_name || lesson.owner_username || `用户 ${lesson.owner_id}` }}
              </template>
              <span class="status-pill" :class="lesson.compliance_level">{{ riskLabel(lesson.compliance_level) }}</span>
              {{ formatDate(lesson.updated_at) }}
            </small>
          </div>
          <div class="actions">
            <button v-if="canReuseLesson(lesson)" type="button" class="btn-secondary" @click="reuseLesson(lesson)">
              {{ reuseLessonLabel(lesson) }}
            </button>
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
          <MarkdownPreview :content="version.content" />
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

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.9fr);
  gap: 14px;
}

.preview-pane {
  display: grid;
  align-content: start;
  gap: 10px;
  min-height: 100%;
  max-height: 680px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--surface-soft);
}

.retrieval-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
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

.compact-filter {
  max-width: 220px;
}

@media (max-width: 1180px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 940px) {
  .editor-grid,
  .retrieval-grid,
  .item-list li {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>

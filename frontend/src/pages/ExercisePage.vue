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

interface AIResult {
  content: string
  provider: string
  model: string
  fallback_used: boolean
  error_message: string | null
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

interface ModelCapabilities {
  text_model: string
  text_configured: boolean
  generate_model: string
  generate_configured: boolean
  review_model: string
  review_configured: boolean
  revise_model: string
  revise_configured: boolean
  vision_model: string
  vision_configured: boolean
  embedding_model: string
  embedding_configured: boolean
  mock_on_failure: boolean
  multi_agent_review: boolean
}

interface ExerciseRead {
  id: number
  owner_id: number
  owner_name: string
  owner_username: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
  lesson_id: number | null
  title: string
  subject: string
  knowledge_point: string
  question_type: string
  difficulty: string
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

interface LessonOption {
  id: number
  title: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
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

interface ExerciseVersion {
  id: number
  version_no: number
  content: string
  change_note: string
  created_at: string
}

interface QuestionBankDraft {
  id: number
}

interface ExerciseGenerateResponse {
  content: string
  references: Array<{ id: number; material_id: number; content: string; score: number }>
  provider_status: AIResult
  compliance: Compliance
  review: AIReview | null
}

type PreviewBlock =
  | { type: 'text'; content: string }
  | { type: 'formula'; content: string; matrixRows: string[][] | null }
  | { type: 'svg'; content: string }

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const form = reactive({
  course_id: 0,
  chapter_id: 0,
  session_id: 0,
  knowledge_point_id: 0,
  lesson_id: 0,
  title: '课堂练习',
  subject: '数学',
  knowledge_point: '',
  question_type: '选择题',
  difficulty: '中等',
  count: 5,
  use_materials: false,
  material_ids: '',
  reference_count: 5,
  retrieval_focus: 'balanced',
  prompt_template: '',
  output_format: '',
  multi_agent_review: true,
  auto_revise: true,
  change_note: '首次保存',
})

const content = ref('')
const exercises = ref<ExerciseRead[]>([])
const courses = ref<Course[]>([])
const selectedCourse = ref<CourseDetail | null>(null)
const lessons = ref<LessonOption[]>([])
const materials = ref<MaterialRead[]>([])
const selectedMaterialIds = ref<number[]>([])
const versions = ref<ExerciseVersion[]>([])
const compliance = ref<Compliance | null>(null)
const review = ref<AIReview | null>(null)
const references = ref<ExerciseGenerateResponse['references']>([])
const generatedContent = ref('')
const selectedExerciseId = ref<number | null>(null)
const capabilities = ref<ModelCapabilities | null>(null)
const providerStatus = ref<AIResult | null>(null)
const loading = ref('')
const error = ref('')
const notice = ref('')
const draftAvailable = ref(false)
const ownerFilter = ref('all')

const selectedExercise = computed(() =>
  exercises.value.find((exercise) => exercise.id === selectedExerciseId.value),
)
const canCreateExercises = computed(() => auth.user?.permissions.includes('exercise:create') ?? false)
const canExportExercises = computed(() => auth.user?.permissions.includes('lesson:export') ?? false)
const canViewAllExercises = computed(() => auth.user?.permissions.includes('exercise:view_all') ?? false)
const isAdmin = computed(() => auth.user?.roles.includes('admin') ?? false)
const isTeachingManager = computed(() => auth.user?.roles.includes('teaching_manager') ?? false)
const showManagementRecords = computed(() => canViewAllExercises.value)
const requestedPageMode = computed(() => String(route.meta.pageMode || 'generate'))
const pageMode = computed(() => {
  if (requestedPageMode.value === 'generate' && !canCreateExercises.value && canViewAllExercises.value) {
    return 'records'
  }
  return requestedPageMode.value
})
const showGenerator = computed(() => canCreateExercises.value && pageMode.value === 'generate')
const showRecords = computed(() => pageMode.value === 'records')
const recordsTitle = computed(() => {
  if (!showManagementRecords.value) return '我的练习'
  return isAdmin.value ? '练习总览' : '教研练习总览'
})
const recordsDescription = computed(() => {
  if (!showManagementRecords.value) return '查看、导出并复用自己保存的练习题。'
  if (isTeachingManager.value) return '按教师筛选练习题，可用于教研检查和题库沉淀。'
  return '按教师筛选查看练习归属、合规风险和版本记录。'
})
const exerciseOwnerOptions = computed(() => {
  const owners = new Map<number, string>()
  for (const exercise of exercises.value) {
    owners.set(exercise.owner_id, exercise.owner_name || exercise.owner_username || `用户 ${exercise.owner_id}`)
  }
  return [...owners.entries()].map(([id, name]) => ({ id, name }))
})
const visibleExercises = computed(() => {
  if (!showManagementRecords.value || ownerFilter.value === 'all') return exercises.value
  const ownerId = Number(ownerFilter.value)
  return exercises.value.filter((exercise) => exercise.owner_id === ownerId)
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
const availableLessons = computed(() =>
  lessons.value.filter((lesson) =>
    (!form.course_id || lesson.course_id === form.course_id) &&
    (!form.chapter_id || lesson.chapter_id === form.chapter_id) &&
    (!form.session_id || lesson.session_id === form.session_id),
  ),
)
const contextIds = computed(() => ({
  course_id: form.course_id || null,
  chapter_id: form.chapter_id || null,
  session_id: form.session_id || null,
  knowledge_point_id: form.knowledge_point_id || null,
}))
const previewBlocks = computed(() => parsePreviewBlocks(content.value))
const previewLimit = 14
const visiblePreviewBlocks = computed(() => previewBlocks.value.slice(0, previewLimit))
const hiddenPreviewCount = computed(() => Math.max(previewBlocks.value.length - previewLimit, 0))
const revisedPreviewContent = computed(() =>
  review.value?.revised_content ? normalizeGeneratedMathText(review.value.revised_content) : '',
)
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

function providerLabel(status: AIResult | null): string {
  if (!status) return '尚未生成'
  if (status.fallback_used || status.provider === 'mock') return '测试内容'
  return '智能生成成功'
}

function providerClass(status: AIResult | null): string {
  if (!status) return ''
  return status.fallback_used || status.provider === 'mock' ? 'warning' : 'success'
}

function capabilityText(): string {
  if (!capabilities.value) return '正在读取智能生成状态...'
  const generate = capabilities.value.generate_configured ? '生成服务可用' : '生成服务未配置'
  const reviewModel = capabilities.value.multi_agent_review ? '自动复核开启' : '自动复核关闭'
  const fallback = capabilities.value.mock_on_failure ? '失败时会提供测试内容' : '失败时不提供测试内容'
  return `${generate}；${reviewModel}；${fallback}`
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
    providerStatus: providerStatus.value,
    status,
  }
}

function persistDraft(status: GenerationDraft<Record<string, unknown>>['status'] = 'editing') {
  if (!canCreateExercises.value || !auth.user) return
  saveGenerationDraft(draftStorageKey('exercise', auth.user.id), currentDraft(status))
  draftAvailable.value = true
}

async function restoreDraft() {
  if (!canCreateExercises.value || !auth.user) return
  const draft = loadGenerationDraft<Record<string, unknown>>(draftStorageKey('exercise', auth.user.id))
  if (!draft) return
  Object.assign(form, draft.form)
  content.value = draft.content || ''
  selectedMaterialIds.value = draft.selectedMaterialIds || []
  generatedContent.value = draft.generatedContent || ''
  compliance.value = draft.compliance as Compliance | null
  review.value = draft.review as AIReview | null
  references.value = (draft.references || []) as ExerciseGenerateResponse['references']
  providerStatus.value = (draft.providerStatus || null) as AIResult | null
  draftAvailable.value = true
  if (form.course_id) await loadCourseDetail(form.course_id)
  setMessage(draft.status === 'generating' ? '已恢复生成中的未保存习题草稿。' : '已恢复未保存习题草稿。')
}

function discardDraft() {
  if (!auth.user) return
  clearGenerationDraft(draftStorageKey('exercise', auth.user.id))
  draftAvailable.value = false
  setMessage('未保存草稿已清除。')
}

function fillFromExercise(exercise: ExerciseRead, clearDependentState = false) {
  if (clearDependentState) {
    clearSelectionDependentState(dependentState, exercise.current_content)
    review.value = null
    providerStatus.value = null
  }

  selectedExerciseId.value = exercise.id
  form.course_id = exercise.course_id ?? 0
  form.chapter_id = exercise.chapter_id ?? 0
  form.session_id = exercise.session_id ?? 0
  form.knowledge_point_id = exercise.knowledge_point_id ?? 0
  form.lesson_id = exercise.lesson_id ?? 0
  form.title = exercise.title
  form.subject = exercise.subject
  form.knowledge_point = exercise.knowledge_point
  form.question_type = exercise.question_type
  form.difficulty = exercise.difficulty
  form.material_ids = exercise.material_ids.join(',')
  selectedMaterialIds.value = exercise.material_ids
  form.prompt_template = exercise.prompt_template
  form.output_format = exercise.output_format
  content.value = normalizeGeneratedMathText(exercise.current_content)
}

function canReuseExercise(exercise: ExerciseRead): boolean {
  if (!canCreateExercises.value) return false
  return exercise.owner_id === auth.user?.id || isTeachingManager.value
}

function reuseExerciseLabel(exercise: ExerciseRead): string {
  return exercise.owner_id === auth.user?.id ? '继续编辑' : '复用生成'
}

async function reuseExercise(exercise: ExerciseRead) {
  fillFromExercise(exercise, true)
  if (exercise.owner_id !== auth.user?.id) {
    selectedExerciseId.value = null
    form.title = `${exercise.title}（副本）`
  }
  if (form.course_id) await loadCourseDetail(form.course_id)
  await router.push('/dashboard/exercise/generate')
  persistDraft('editing')
  setMessage(exercise.owner_id === auth.user?.id ? '已载入自己的习题，可继续编辑后保存。' : '已载入该习题内容，可基于它生成新的习题。')
}

async function loadCourses() {
  courses.value = await api<Course[]>('/api/courses')
}

async function loadLessons() {
  lessons.value = await api<LessonOption[]>('/api/lessons')
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
  form.lesson_id = 0
  await loadCourseDetail(form.course_id)
}

async function applyRouteContext() {
  const context = parseTeachingContextQuery(route.query)
  if (!context.course_id && !context.lesson_id && !context.exercise_id) return

  form.course_id = context.course_id
  form.chapter_id = context.chapter_id
  form.session_id = context.session_id
  form.knowledge_point_id = context.knowledge_point_id
  form.lesson_id = context.lesson_id

  if (form.course_id) {
    await loadCourseDetail(form.course_id)
    if (selectedCourse.value) {
      const defaults = lessonDefaultsFromContext(selectedCourse.value, context)
      form.knowledge_point = defaults.knowledge_point || form.knowledge_point
    }
  }

  if (!form.lesson_id && availableLessons.value.length) {
    form.lesson_id = availableLessons.value[0].id
  }

  if (context.exercise_id) {
    const matchedExercise = exercises.value.find((exercise) => exercise.id === context.exercise_id)
    if (matchedExercise) fillFromExercise(matchedExercise, true)
  }
}

async function loadCapabilities() {
  try {
    capabilities.value = await api<ModelCapabilities>('/api/ai/capabilities')
  } catch {
    capabilities.value = null
  }
}

async function loadExercises() {
  try {
    exercises.value = await api<ExerciseRead[]>('/api/exercises')
  } catch (err) {
    setError(err, '习题列表加载失败')
  }
}

async function generateExercise() {
  loading.value = 'generate'
  providerStatus.value = null
  setMessage()
  persistDraft('generating')
  try {
    const result = await api<ExerciseGenerateResponse>('/api/exercises/generate', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title,
        course_id: form.course_id || null,
        chapter_id: form.chapter_id || null,
        session_id: form.session_id || null,
        knowledge_point_id: form.knowledge_point_id || null,
        lesson_id: form.lesson_id || null,
        subject: form.subject,
        knowledge_point: form.knowledge_point,
        question_type: form.question_type,
        difficulty: form.difficulty,
        count: form.count,
        use_materials: form.use_materials,
        material_ids: materialIds(),
        reference_count: form.reference_count,
        retrieval_focus: form.retrieval_focus,
        prompt_template: form.prompt_template,
        output_format: form.output_format,
        multi_agent_review: form.multi_agent_review,
        auto_revise: form.auto_revise,
      }),
    })
    const normalizedContent = normalizeGeneratedMathText(result.content)
    content.value = normalizedContent
    compliance.value = result.compliance
    review.value = result.review
    references.value = result.references
    providerStatus.value = result.provider_status
    generatedContent.value = normalizedContent
    persistDraft('generated')
    setMessage(
      result.provider_status.fallback_used
        ? '已生成测试内容，请管理员检查智能生成服务配置。'
        : '习题已生成，可继续编辑后保存。',
    )
  } catch (err) {
    setError(err, '习题生成失败')
  } finally {
    loading.value = ''
    await loadCapabilities()
  }
}

function adoptRevisedContent() {
  if (!revisedPreviewContent.value) return
  content.value = revisedPreviewContent.value
  generatedContent.value = revisedPreviewContent.value
  persistDraft('generated')
  setMessage('已采用 AI 修订稿，可继续编辑后保存。')
}

async function saveExercise() {
  loading.value = 'save'
  setMessage()
  try {
    const saved = await api<ExerciseRead>('/api/exercises', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title,
        course_id: form.course_id || null,
        chapter_id: form.chapter_id || null,
        session_id: form.session_id || null,
        knowledge_point_id: form.knowledge_point_id || null,
        lesson_id: form.lesson_id || null,
        subject: form.subject,
        knowledge_point: form.knowledge_point,
        question_type: form.question_type,
        difficulty: form.difficulty,
        content: normalizeGeneratedMathText(content.value),
        material_ids: materialIds(),
        prompt_template: form.prompt_template,
        output_format: form.output_format,
        change_note: form.change_note,
      }),
    })
    fillFromExercise(saved, true)
    if (auth.user) {
      clearGenerationDraft(draftStorageKey('exercise', auth.user.id))
      draftAvailable.value = false
    }
    await loadExercises()
    setMessage('习题已保存。')
  } catch (err) {
    setError(err, '习题保存失败')
  } finally {
    loading.value = ''
  }
}

async function saveToQuestionBank(exerciseId = selectedExerciseId.value) {
  if (!exerciseId) {
    setError(new Error('请先保存一份习题'), '题库沉淀失败')
    return
  }

  loading.value = `question-bank-${exerciseId}`
  setMessage()
  try {
    const created = await api<QuestionBankDraft[]>(`/api/exercises/${exerciseId}/save-to-question-bank`, {
      method: 'POST',
    })
    setMessage(`已保存 ${created.length} 道题库草稿，可到题库管理中继续编辑和提交审核。`)
  } catch (err) {
    setError(err, '题库沉淀失败')
  } finally {
    loading.value = ''
  }
}

async function loadVersions(exercise: ExerciseRead) {
  loading.value = 'versions'
  setMessage()
  fillFromExercise(exercise, true)
  try {
    versions.value = await api<ExerciseVersion[]>(`/api/exercises/${exercise.id}/versions`)
  } catch (err) {
    setError(err, '版本记录加载失败')
  } finally {
    loading.value = ''
  }
}

async function exportExercise(exerciseId = selectedExerciseId.value) {
  if (!exerciseId) {
    setError(new Error('请先选择或保存一份习题'), '导出失败')
    return
  }

  loading.value = 'export'
  setMessage()
  try {
    const result = await apiBlob(`/api/exports/exercise/${exerciseId}/docx`, { method: 'POST' })
    downloadBlobResponse(result, `exercise-${exerciseId}.docx`)
    setMessage('导出文件已开始下载。')
  } catch (err) {
    setError(err, '习题导出失败')
  } finally {
    loading.value = ''
  }
}

function parsePreviewBlocks(raw: string): PreviewBlock[] {
  const blocks: PreviewBlock[] = []
  const pattern = /\[(公式|SVG)\]([\s\S]*?)\[\/\1\]/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(raw))) {
    const before = raw.slice(lastIndex, match.index).trim()
    if (before) blocks.push({ type: 'text', content: normalizeGeneratedMathText(before) })

    const body = match[2].trim()
    if (match[1] === 'SVG') {
      blocks.push({ type: 'svg', content: sanitizeSvg(body) })
    } else {
      blocks.push({ type: 'formula', content: body, matrixRows: parseLatexMatrix(body) })
    }
    lastIndex = pattern.lastIndex
  }

  const rest = raw.slice(lastIndex).trim()
  if (rest) blocks.push({ type: 'text', content: normalizeGeneratedMathText(rest) })
  return blocks
}

function sanitizeSvg(svg: string): string {
  if (!/^<svg[\s>]/i.test(svg)) return ''
  return svg
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '')
    .replace(/\son\w+='[^']*'/gi, '')
    .replace(/\s(?:href|xlink:href)=["'][^"']*["']/gi, '')
}

function parseLatexMatrix(formula: string): string[][] | null {
  const match = formula.match(/\\begin\{[bpv]?matrix\}([\s\S]*?)\\end\{[bpv]?matrix\}/)
  if (!match) return null
  return match[1]
    .split('\\\\')
    .map((row) => row.trim())
    .filter(Boolean)
    .map((row) => row.split('&').map((cell) => cell.trim()))
}

function normalizeGeneratedMathText(value: string): string {
  if (!value) return value

  const segments: string[] = []
  const pattern = /\[(公式|SVG)\]([\s\S]*?)\[\/\1\]/gi
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = pattern.exec(value))) {
    segments.push(normalizeInlineLatex(value.slice(lastIndex, match.index)))
    segments.push(match[0])
    lastIndex = pattern.lastIndex
  }
  segments.push(normalizeInlineLatex(value.slice(lastIndex)))
  return segments.join('')
}

function normalizeInlineLatex(value: string): string {
  const replacements: Record<string, string> = {
    '\\times': '×',
    '\\cdot': '·',
    '\\div': '÷',
    '\\leq': '≤',
    '\\geq': '≥',
    '\\neq': '≠',
    '\\in': '∈',
    '\\sum': 'Σ',
    '\\left': '',
    '\\right': '',
  }

  let text = value
    .replace(/\\\(([\s\S]*?)\\\)/g, '$1')
    .replace(/\\\[([\s\S]*?)\\\]/g, '$1')
    .replace(/\\(?:mathrm|operatorname|text|mathbf|mathit)\{([^{}]+)\}/g, '$1')

  for (const [source, target] of Object.entries(replacements)) {
    text = text.split(source).join(target)
  }

  return text
    .replace(/_\{([^{}]+)\}/g, '_$1')
    .replace(/\^\{([^{}]+)\}/g, '^$1')
    .replace(/\\\{/g, '{')
    .replace(/\\\}/g, '}')
    .replace(/\\\[/g, '')
    .replace(/\\\]/g, '')
    .replace(/\\\(/g, '')
    .replace(/\\\)/g, '')
    .replace(/\\([A-Za-z]+)/g, '$1')
    .replace(/[ \t]+/g, ' ')
}

onMounted(async () => {
  await Promise.all([loadCapabilities(), loadExercises(), loadCourses(), loadLessons(), loadMaterials()])
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
        <p class="eyebrow">练习题</p>
        <h1>{{ pageMode === 'records' ? recordsTitle : '生成练习' }}</h1>
        <p>{{ pageMode === 'records' ? recordsDescription : '按知识点、题型与难度生成练习，支持公式、矩阵、表格和可渲染示意图。' }}</p>
      </div>
      <button v-if="canExportExercises" type="button" class="btn-secondary" :disabled="!selectedExerciseId || loading === 'export'" @click="exportExercise()">
        {{ loading === 'export' ? '导出中...' : '导出 DOCX' }}
      </button>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="draftAvailable && canCreateExercises" class="draft-banner">
      当前页面有未保存草稿，切换页面后会自动保留。
      <button type="button" class="btn-secondary" @click="discardDraft">清除草稿</button>
    </p>

    <section v-if="showGenerator" class="panel model-card">
      <div>
        <h2>模型状态</h2>
        <p>{{ capabilityText() }}</p>
      </div>
      <span class="status-pill" :class="providerClass(providerStatus)">
        {{ providerLabel(providerStatus) }}
      </span>
    </section>

    <div v-if="showGenerator" class="editor-grid">
      <form class="panel form-grid" @submit.prevent="generateExercise">
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
        <label class="wide">
          关联教案
          <select v-model.number="form.lesson_id">
            <option :value="0">不绑定教案</option>
            <option v-for="lesson in availableLessons" :key="lesson.id" :value="lesson.id">
              {{ lesson.title }}
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
          知识点
          <input v-model.trim="form.knowledge_point" required />
        </label>
        <label>
          题型
          <select v-model="form.question_type">
            <option>选择题</option>
            <option>填空题</option>
            <option>判断题</option>
            <option>简答题</option>
            <option>计算题</option>
            <option>证明题</option>
            <option>综合题</option>
          </select>
        </label>
        <label>
          难度
          <select v-model="form.difficulty">
            <option>基础</option>
            <option>中等</option>
            <option>提高</option>
          </select>
        </label>
        <label>
          题量
          <input v-model.number="form.count" type="number" min="1" required />
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
            :to="{ path: '/dashboard/materials/upload', query: { ...buildTeachingContextQuery(contextIds), return_to: '/dashboard/exercise/generate' } }"
          >
            上传当前课程资料
          </RouterLink>
        </div>
        <label class="checkbox">
          <input v-model="form.multi_agent_review" type="checkbox" />
          多 AI 核验
        </label>
        <label class="checkbox">
          <input v-model="form.auto_revise" type="checkbox" />
          有风险时自动修订
        </label>
        <label class="wide">
          教师补充提示词
          <textarea v-model.trim="form.prompt_template" rows="3" placeholder="例如：贴合本节课例题，答案解析分步骤" />
        </label>
        <label class="wide">
          输出格式要求
          <textarea v-model.trim="form.output_format" rows="2" placeholder="例如：每题包含题干、答案、解析、知识点标签" />
        </label>
        <button class="btn-primary wide" type="submit" :disabled="loading === 'generate'">
          {{ loading === 'generate' ? '生成中...' : '生成习题' }}
        </button>
      </form>

      <section class="panel stack">
        <div class="content-grid">
          <label>
            可编辑内容
            <textarea v-model="content" rows="20" placeholder="生成或粘贴习题内容后保存。" />
          </label>
          <div class="preview-pane">
            <strong>阅读预览</strong>
            <p v-if="!content" class="empty-state">生成内容后会在这里预览公式、矩阵和示意图。</p>
            <div v-else class="preview-blocks">
              <template v-for="(block, index) in visiblePreviewBlocks" :key="index">
                <MarkdownPreview v-if="block.type === 'text'" :content="block.content" />
                <div v-else-if="block.type === 'formula'" class="formula-block">
                  <table v-if="block.matrixRows" class="matrix-preview">
                    <tbody>
                      <tr v-for="(row, rowIndex) in block.matrixRows" :key="rowIndex">
                        <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <pre v-else>{{ block.content }}</pre>
                </div>
                <div v-else class="svg-block" v-html="block.content" />
              </template>
              <p v-if="hiddenPreviewCount" class="preview-more">
                已折叠 {{ hiddenPreviewCount }} 个后续片段，完整内容请在左侧编辑区查看和修改。
              </p>
            </div>
          </div>
        </div>

        <label>
          版本说明
          <input v-model.trim="form.change_note" />
        </label>
        <button class="btn-primary" type="button" :disabled="!content || loading === 'save'" @click="saveExercise">
          {{ loading === 'save' ? '保存中...' : '保存习题' }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="!selectedExerciseId || loading === `question-bank-${selectedExerciseId}`"
          @click="saveToQuestionBank()"
        >
          {{ loading === `question-bank-${selectedExerciseId}` ? '保存到题库中...' : '保存到题库草稿' }}
        </button>

        <div v-if="compliance" class="result-card">
          <strong>合规风险：{{ riskLabel(compliance.risk_level) }}</strong>
          <p v-if="compliance.matched_terms.length">命中词：{{ compliance.matched_terms.join('、') }}</p>
          <p v-if="compliance.suggestions.length">建议：{{ compliance.suggestions.join('；') }}</p>
        </div>

        <div v-if="providerStatus" class="result-card">
          <strong>生成状态：{{ providerLabel(providerStatus) }}</strong>
          <p>服务：{{ providerStatus.fallback_used ? '测试服务' : '智能生成服务' }}</p>
          <p v-if="providerStatus.error_message">错误：{{ providerStatus.error_message }}</p>
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
          <small>{{ showManagementRecords ? '全局记录会标注所属教师，管理员默认只查看和运维。' : '只显示当前账号创建的练习。' }}</small>
        </div>
        <label v-if="showManagementRecords && exerciseOwnerOptions.length" class="compact-filter">
          所属教师
          <select v-model="ownerFilter">
            <option value="all">全部教师</option>
            <option v-for="owner in exerciseOwnerOptions" :key="owner.id" :value="String(owner.id)">
              {{ owner.name }}
            </option>
          </select>
        </label>
      </div>
      <p v-if="!visibleExercises.length" class="empty-state">暂无习题记录。</p>
      <ul v-else class="item-list">
        <li v-for="exercise in visibleExercises" :key="exercise.id" :class="{ active: exercise.id === selectedExerciseId }">
          <div class="stack">
            <strong>{{ exercise.title }}</strong>
            <small>
              {{ exercise.subject }} · {{ exercise.knowledge_point }}
              <template v-if="showManagementRecords">
                · 所属教师 {{ exercise.owner_name || exercise.owner_username || `用户 ${exercise.owner_id}` }}
              </template>
              <span class="status-pill" :class="exercise.compliance_level">{{ riskLabel(exercise.compliance_level) }}</span>
              {{ formatDate(exercise.updated_at) }}
            </small>
          </div>
          <div class="actions">
            <button v-if="canReuseExercise(exercise)" type="button" class="btn-secondary" @click="reuseExercise(exercise)">
              {{ reuseExerciseLabel(exercise) }}
            </button>
            <button type="button" class="btn-secondary" @click="loadVersions(exercise)">版本</button>
            <button
              v-if="canCreateExercises"
              type="button"
              class="btn-secondary"
              :disabled="loading === `question-bank-${exercise.id}`"
              @click="saveToQuestionBank(exercise.id)"
            >
              题库草稿
            </button>
            <button v-if="canExportExercises" type="button" class="btn-secondary" @click="exportExercise(exercise.id)">导出</button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="selectedExercise && versions.length" class="panel stack">
      <h2>{{ selectedExercise.title }} 的版本</h2>
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
.model-card {
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
}

.model-card h2,
.model-card p {
  margin: 0;
}

.model-card p {
  margin-top: 6px;
  color: var(--muted);
}

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

.preview-blocks {
  display: grid;
  gap: 8px;
}

.text-block,
.formula-block pre {
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
}

.text-block {
  color: var(--text);
  font-family: inherit;
  line-height: 1.55;
  max-height: 220px;
  padding-right: 4px;
}

.formula-block {
  overflow: auto;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 8px 10px;
  color: #1e3a8a;
  background: #eff6ff;
}

.matrix-preview {
  position: relative;
  border-collapse: separate;
  border-spacing: 10px 4px;
  margin: 0 auto;
  font-family: "Times New Roman", serif;
  font-size: 1rem;
}

.matrix-preview::before,
.matrix-preview::after {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  border: 2px solid #1e3a8a;
  content: "";
}

.matrix-preview::before {
  left: -10px;
  border-right: 0;
}

.matrix-preview::after {
  right: -10px;
  border-left: 0;
}

.matrix-preview td {
  min-width: 22px;
  text-align: center;
}

.svg-block {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px;
  background: #ffffff;
}

.svg-block :deep(svg) {
  max-width: 100%;
  max-height: 260px;
  height: auto;
}

.preview-more {
  margin: 0;
  border: 1px dashed #bfdbfe;
  border-radius: 8px;
  padding: 8px 10px;
  color: #1d4ed8;
  background: #eff6ff;
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
  .item-list li,
  .model-card {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>

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

interface PresentationSlide {
  slide_no: number
  title: string
  bullets: string[]
  speaker_notes: string
  visual_prompt: string
}

interface PresentationResponse {
  lesson_id: number
  status: string
  queued: boolean
  message: string
  slides: PresentationSlide[]
  export_id: number | null
  download_url: string | null
  filename: string | null
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
  multi_agent_review: true,
  auto_revise: true,
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
const presentationSlideCount = ref<number | null>(null)
const presentationDescription = ref('')
const presentationSlides = ref<PresentationSlide[]>([])
const presentationDownloadUrl = ref('')
const presentationFilename = ref('')
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
        multi_agent_review: form.multi_agent_review,
        auto_revise: form.auto_revise,
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
  presentationSlides.value = []
  presentationDownloadUrl.value = ''
  presentationFilename.value = ''
  loading.value = 'presentation'
  presentationMessage.value = ''
  setMessage()
  try {
    const result = await api<PresentationResponse>(
      `/api/presentations/lesson/${selectedLessonId.value}/generate`,
      {
        method: 'POST',
        body: JSON.stringify({
          slide_count: presentationSlideCount.value || null,
          description: presentationDescription.value,
        }),
      },
    )
    presentationMessage.value = result.message
    presentationSlides.value = result.slides
    presentationDownloadUrl.value = result.download_url || ''
    presentationFilename.value = result.filename || ''
    setMessage(result.queued ? 'PPT 生成任务已提交。' : result.message)
  } catch (err) {
    setError(err, 'PPT 生成失败')
  } finally {
    loading.value = ''
  }
}

async function downloadPresentation() {
  if (!presentationDownloadUrl.value) return

  loading.value = 'presentation-download'
  setMessage()
  try {
    const result = await apiBlob(presentationDownloadUrl.value)
    downloadBlobResponse(
      result,
      presentationFilename.value || `lesson-${selectedLessonId.value ?? 'presentation'}.pptx`,
    )
    setMessage('PPT 文件已开始下载。')
  } catch (err) {
    setError(err, 'PPT 下载失败')
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
      <div class="hero-content">
        <p class="eyebrow">教案</p>
        <h1>{{ pageMode === 'records' ? recordsTitle : '生成教案' }}</h1>
        <p class="hero-desc">{{ pageMode === 'records' ? recordsDescription : '填写教学目标，生成可编辑教案，并保存为可追溯的版本记录。' }}</p>
      </div>
      <button v-if="canExportLessons" type="button" class="btn-secondary outline" :disabled="!selectedLessonId || loading === 'export'" @click="exportLesson()">
        {{ loading === 'export' ? '导出中...' : '导出 DOCX' }}
      </button>
    </header>

    <div v-if="error" class="alert error" role="alert">{{ error }}</div>
    <div v-if="notice" class="alert success">{{ notice }}</div>
    <div v-if="draftAvailable && showGenerator" class="draft-banner">
      <span>当前页面有未保存草稿，切换页面后会自动保留。</span>
      <button type="button" class="btn-text" @click="discardDraft">清除草稿</button>
    </div>

    <div v-if="showGenerator" class="editor-layout">
      <form class="card form-container" @submit.prevent="generateLesson">
        <div class="form-section-title">基础信息</div>
        <div class="form-grid-2">
          <label class="form-field">
            <span>课程</span>
            <select v-model.number="form.course_id" @change="selectCourse" class="ui-input">
              <option :value="0">不绑定课程</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.title }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>章节</span>
            <select v-model.number="form.chapter_id" :disabled="!selectedCourse" class="ui-input">
              <option :value="0">不绑定章节</option>
              <option v-for="chapter in selectedCourse?.chapters ?? []" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>课次</span>
            <select v-model.number="form.session_id" :disabled="!form.chapter_id" class="ui-input">
              <option :value="0">不绑定课次</option>
              <option v-for="session in availableSessions" :key="session.id" :value="session.id">{{ session.title }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>知识点</span>
            <select v-model.number="form.knowledge_point_id" :disabled="!selectedCourse" class="ui-input">
              <option :value="0">不绑定知识点</option>
              <option v-for="point in availableKnowledgePoints" :key="point.id" :value="point.id">{{ point.name }}</option>
            </select>
          </label>
        </div>

        <div class="form-divider"></div>
        <div class="form-section-title">教学设置</div>
        
        <label class="form-field wide">
          <span>教案标题</span>
          <input v-model.trim="form.title" required class="ui-input" />
        </label>
        
        <div class="form-grid-2">
          <label class="form-field">
            <span>学科</span>
            <input v-model.trim="form.subject" required class="ui-input" />
          </label>
          <label class="form-field">
            <span>授课章节</span>
            <input v-model.trim="form.chapter" required class="ui-input" />
          </label>
          <label class="form-field">
            <span>阶段</span>
            <input v-model.trim="form.stage" required class="ui-input" />
          </label>
          <label class="form-field">
            <span>课时 (分钟)</span>
            <input v-model.number="form.duration_minutes" type="number" min="1" required class="ui-input" />
          </label>
        </div>

        <label class="form-field wide">
          <span>学情分析</span>
          <input v-model.trim="form.student_level" required class="ui-input" placeholder="例如：基础一般，缺乏做题技巧" />
        </label>
        <label class="form-field wide">
          <span>教学目标</span>
          <textarea v-model.trim="form.teaching_goal" rows="3" required class="ui-input textarea"></textarea>
        </label>

        <div class="form-divider"></div>
        
        <label class="checkbox-field wide">
          <input v-model="form.use_materials" type="checkbox" class="ui-checkbox" />
          <span>使用机构知识库材料</span>
        </label>
        
        <div v-if="form.use_materials" class="materials-zone wide">
          <MaterialPicker
            v-model="selectedMaterialIds"
            :materials="materials"
            :context-ids="contextIds"
          />
          <div class="retrieval-grid">
            <label class="form-field">
              <span>参考资料数量</span>
              <input v-model.number="form.reference_count" type="number" min="1" max="20" class="ui-input" />
            </label>
            <label class="form-field">
              <span>检索侧重点</span>
              <select v-model="form.retrieval_focus" class="ui-input">
                <option value="precise">更精准</option>
                <option value="balanced">均衡</option>
                <option value="broad">更宽泛</option>
              </select>
            </label>
          </div>
          <RouterLink
            class="action-link"
            :to="{ path: '/dashboard/materials/upload', query: { ...buildTeachingContextQuery(contextIds), return_to: '/dashboard/lesson/generate' } }"
          >
            + 上传当前课程资料
          </RouterLink>
        </div>

        <label class="form-field wide mt-4">
          <span>教师补充提示词</span>
          <textarea v-model.trim="form.prompt_template" rows="2" class="ui-input textarea" placeholder="例如：强调例题讲解、课堂互动和易错点"></textarea>
        </label>
        <label class="form-field wide">
          <span>输出格式要求</span>
          <textarea v-model.trim="form.output_format" rows="2" class="ui-input textarea" placeholder="例如：按教学目标、导入、讲解、练习、总结输出"></textarea>
        </label>

        <div class="review-options wide">
          <label class="checkbox-field">
            <input v-model="form.multi_agent_review" type="checkbox" class="ui-checkbox" />
            <span>启用多 AI 复核</span>
          </label>
          <label class="checkbox-field">
            <input v-model="form.auto_revise" type="checkbox" class="ui-checkbox" :disabled="!form.multi_agent_review" />
            <span>发现问题时自动生成修订稿</span>
          </label>
        </div>
        
        <button class="btn-primary wide mt-4" type="submit" :disabled="loading === 'generate'">
          <span v-if="loading === 'generate'" class="spinner"></span>
          {{ loading === 'generate' ? '生成中...' : '生成备课' }}
        </button>
      </form>

      <div class="workspace-column stack">
        <section class="card content-area">
          <div class="split-pane">
            <div class="pane-section editor-section">
              <label class="pane-title">教案内容 (可编辑)</label>
              <textarea v-model="content" class="ui-input editor-textarea" placeholder="生成或粘贴备课内容后保存。"></textarea>
            </div>
            <div class="pane-section preview-section">
              <strong class="pane-title">阅读预览</strong>
              <div class="preview-container">
                <p v-if="!content" class="empty-state">生成内容后会在这里按标题、列表和表格排版展示。</p>
                <MarkdownPreview v-else :content="content" />
              </div>
            </div>
          </div>
          <div class="save-actions">
            <label class="form-field inline-field">
              <span>版本说明:</span>
              <input v-model.trim="form.change_note" class="ui-input small-input" />
            </label>
            <button class="btn-primary" type="button" :disabled="!content || loading === 'save'" @click="saveLesson">
              {{ loading === 'save' ? '保存中...' : '保存备课' }}
            </button>
          </div>
        </section>

        <section class="card presentation-zone">
          <div class="zone-header">
            <h3>PPT 智能生成</h3>
            <span class="badge">AI 驱动</span>
          </div>
          <div class="presentation-tools">
            <label class="form-field">
              <span>页数预估</span>
              <input v-model.number="presentationSlideCount" type="number" min="1" max="30" class="ui-input" placeholder="自动" />
            </label>
            <label class="form-field wide">
              <span>风格与内容要求</span>
              <textarea
                v-model.trim="presentationDescription"
                rows="2"
                class="ui-input textarea"
                placeholder="例如：强调推导过程、案例、课堂互动，采用活泼的视觉风格"
              ></textarea>
            </label>
          </div>
          <div class="presentation-actions">
            <button class="btn-primary outline" type="button" :disabled="!selectedLessonId || loading === 'presentation'" @click="generatePresentation">
              {{ loading === 'presentation' ? '提交生成任务...' : '一键生成 PPT' }}
            </button>
            <button v-if="presentationDownloadUrl" class="btn-secondary" type="button" :disabled="loading === 'presentation-download'" @click="downloadPresentation">
              {{ loading === 'presentation-download' ? '下载中...' : '下载 PPT 文件' }}
            </button>
          </div>
          
          <p v-if="presentationMessage" class="status-text">{{ presentationMessage }}</p>
          
          <div v-if="presentationSlides.length" class="slide-outline-container">
            <h4>大纲预览</h4>
            <ol class="presentation-outline">
              <li v-for="slide in presentationSlides" :key="slide.slide_no">
                <strong>{{ slide.slide_no }}. {{ slide.title }}</strong>
                <p>{{ slide.bullets.join(' / ') }}</p>
              </li>
            </ol>
          </div>
        </section>

        <div class="insights-stack">
          <div v-if="compliance" class="insight-card warning">
            <div class="card-header">合规风险：{{ riskLabel(compliance.risk_level) }}</div>
            <div class="card-body">
              <p v-if="compliance.matched_terms.length"><strong>命中词：</strong>{{ compliance.matched_terms.join('、') }}</p>
              <p v-if="compliance.suggestions.length"><strong>建议：</strong>{{ compliance.suggestions.join('；') }}</p>
            </div>
          </div>

          <div v-if="review" class="insight-card info">
            <div class="card-header">AI 复核：{{ review.enabled ? review.status : '未启用' }} ({{ review.reviewer_model }})</div>
            <div class="card-body">
              <p v-if="!review.enabled">本次生成未启用多 AI 复核，可在左侧勾选后重新生成。</p>
              <template v-else>
                <p v-if="review.warnings.length"><strong>风险：</strong>{{ review.warnings.join('；') }}</p>
                <p v-if="review.suggestions.length"><strong>建议：</strong>{{ review.suggestions.join('；') }}</p>
              </template>
            </div>
          </div>

          <div v-if="revisedPreviewContent" class="insight-card success">
            <div class="card-header flex-between">
              <span>AI 修订建议稿</span>
              <button type="button" class="btn-text small" @click="adoptRevisedContent">采纳修订</button>
            </div>
            <div class="card-body scrollable">
              <MarkdownPreview :content="revisedPreviewContent" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <section v-if="showRecords" class="card stack">
      <div class="records-header">
        <div class="header-text">
          <h2>{{ recordsTitle }}</h2>
          <p class="subtitle">{{ showManagementRecords ? '全局记录会标注所属教师，管理员默认只查看和运维。' : '只显示当前账号创建的教案。' }}</p>
        </div>
        <label v-if="showManagementRecords && lessonOwnerOptions.length" class="form-field inline-field">
          <span>所属教师</span>
          <select v-model="ownerFilter" class="ui-input">
            <option value="all">全部教师</option>
            <option v-for="owner in lessonOwnerOptions" :key="owner.id" :value="String(owner.id)">{{ owner.name }}</option>
          </select>
        </label>
      </div>
      
      <div v-if="!visibleLessons.length" class="empty-state large">暂无备课记录。</div>
      <ul v-else class="record-list">
        <li v-for="lesson in visibleLessons" :key="lesson.id" class="record-item" :class="{ active: lesson.id === selectedLessonId }">
          <div class="record-info">
            <strong class="title">{{ lesson.title }}</strong>
            <div class="meta">
              <span class="tag">{{ lesson.subject }}</span>
              <span class="tag">{{ lesson.chapter }}</span>
              <template v-if="showManagementRecords">
                <span class="divider">•</span>
                <span>教师: {{ lesson.owner_name || lesson.owner_username || `用户 ${lesson.owner_id}` }}</span>
              </template>
              <span class="divider">•</span>
              <span>{{ formatDate(lesson.updated_at) }}</span>
              <span class="status-pill mini" :class="lesson.compliance_level">{{ riskLabel(lesson.compliance_level) }}</span>
            </div>
          </div>
          <div class="record-actions">
            <button v-if="canReuseLesson(lesson)" type="button" class="btn-text" @click="reuseLesson(lesson)">{{ reuseLessonLabel(lesson) }}</button>
            <button type="button" class="btn-text" @click="loadVersions(lesson)">历史版本</button>
            <button v-if="canExportLessons" type="button" class="btn-text" @click="exportLesson(lesson.id)">导出</button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="selectedLesson && versions.length" class="card stack mt-4">
      <h2>{{ selectedLesson.title }} - 历史版本</h2>
      <div class="timeline">
        <div v-for="version in versions" :key="version.id" class="timeline-item">
          <div class="timeline-header">
            <strong class="version-badge">V{{ version.version_no }}</strong>
            <span class="note">{{ version.change_note || '无版本说明' }}</span>
            <span class="date">{{ formatDate(version.created_at) }}</span>
          </div>
          <div class="timeline-content">
            <MarkdownPreview :content="version.content" />
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<style scoped>
/* Core Layout */
.page-shell {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 20px;
}

.eyebrow {
  color: #2563eb;
  font-weight: 700;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

h1 {
  font-size: 1.8rem;
  color: #0f172a;
  margin: 0 0 8px 0;
}

.hero-desc {
  color: #64748b;
  margin: 0;
  font-size: 0.95rem;
}

/* Cards & Containers */
.card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02), 0 10px 15px -3px rgba(15, 23, 42, 0.02);
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(320px, 400px) minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

/* Form Styles */
.form-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 24px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
}

.form-container::-webkit-scrollbar { width: 4px; }
.form-container::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

.form-section-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.form-divider {
  height: 1px;
  background: #f1f5f9;
  margin: 8px 0;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field span {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.form-field.wide, .wide {
  grid-column: 1 / -1;
}

.inline-field {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}
.inline-field span {
  flex-shrink: 0;
}

.ui-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.95rem;
  color: #0f172a;
  background: #ffffff;
  transition: all 0.2s ease;
  font-family: inherit;
}

.ui-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.ui-input:disabled {
  background: #f8fafc;
  color: #94a3b8;
  cursor: not-allowed;
}

.ui-input.textarea {
  resize: vertical;
  min-height: 80px;
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.review-options {
  display: grid;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #eff6ff;
}

.ui-checkbox {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  cursor: pointer;
}

.materials-zone {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 16px;
  margin-top: 8px;
}

.retrieval-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}

.action-link {
  display: inline-block;
  margin-top: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
}
.action-link:hover { text-decoration: underline; }

.mt-4 { margin-top: 16px; }

/* Buttons */
button { font-family: inherit; }
.btn-primary, .btn-secondary, .btn-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary { background: #2563eb; color: white; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary.outline { background: transparent; color: #2563eb; border: 1px solid #2563eb; }
.btn-primary.outline:hover:not(:disabled) { background: #eff6ff; }
.btn-primary:disabled { background: #93c5fd; cursor: not-allowed; }

.btn-secondary { background: #f1f5f9; color: #334155; }
.btn-secondary:hover:not(:disabled) { background: #e2e8f0; }

.btn-text { background: transparent; color: #64748b; padding: 6px 12px; }
.btn-text:hover { color: #0f172a; background: #f1f5f9; }
.btn-text.small { font-size: 0.85rem; padding: 4px 8px; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s ease-in-out infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Workspace Column (Right side) */
.workspace-column {
  min-width: 0;
}

.content-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.split-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  min-height: 500px;
}

.pane-section { display: flex; flex-direction: column; gap: 8px; }
.pane-title { font-size: 0.9rem; font-weight: 700; color: #334155; }

.editor-textarea {
  flex: 1;
  min-height: 400px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
  background: #fafafa;
}

.preview-container {
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 20px;
  background: #ffffff;
  overflow-y: auto;
  max-height: 600px;
}

.save-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f1f5f9;
  padding-top: 16px;
  margin-top: 8px;
}
.small-input { width: 300px; }

/* PPT Zone */
.presentation-zone {
  background: linear-gradient(to right bottom, #ffffff, #f8fafc);
  border: 1px solid #e0e7ff;
}

.zone-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.zone-header h3 { margin: 0; color: #1e40af; font-size: 1.2rem; }
.badge { background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; }

.presentation-tools {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.presentation-actions { display: flex; gap: 12px; }
.status-text { color: #047857; font-weight: 600; margin-top: 12px; font-size: 0.9rem; }

.slide-outline-container {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px dashed #cbd5e1;
}
.slide-outline-container h4 { margin: 0 0 12px 0; color: #334155; }
.presentation-outline {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 12px;
}
.presentation-outline li {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 3px solid #3b82f6;
  padding: 12px 16px;
  border-radius: 6px;
}
.presentation-outline strong { color: #0f172a; display: block; margin-bottom: 4px; }
.presentation-outline p { margin: 0; color: #64748b; font-size: 0.85rem; }

/* Insights / Alerts */
.alerts-wrapper, .draft-banner {
  padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between;
}
.alert { padding: 12px 16px; border-radius: 8px; font-weight: 500; }
.alert.error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; }
.alert.success, .draft-banner { background: #ecfdf5; border: 1px solid #a7f3d0; color: #047857; }

.insight-card { border-radius: 8px; border: 1px solid; overflow: hidden; }
.insight-card .card-header { padding: 10px 16px; font-weight: 700; font-size: 0.9rem; }
.insight-card .card-body { padding: 12px 16px; background: #ffffff; font-size: 0.9rem; line-height: 1.5; }
.insight-card .card-body p { margin: 0 0 8px 0; }
.insight-card .card-body p:last-child { margin: 0; }
.insight-card.warning { border-color: #fde047; }
.insight-card.warning .card-header { background: #fef9c3; color: #854d0e; }
.insight-card.info { border-color: #bfdbfe; }
.insight-card.info .card-header { background: #eff6ff; color: #1e40af; }
.insight-card.success { border-color: #bbf7d0; }
.insight-card.success .card-header { background: #f0fdf4; color: #166534; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }

/* Records List */
.records-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-text h2 { margin: 0 0 4px 0; font-size: 1.4rem; color: #0f172a; }
.subtitle { margin: 0; color: #64748b; font-size: 0.9rem; }

.record-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }
.record-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px; border: 1px solid #e2e8f0; border-radius: 10px;
  background: #ffffff; transition: border-color 0.2s, box-shadow 0.2s;
}
.record-item:hover { border-color: #cbd5e1; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.record-item.active { border-color: #3b82f6; background: #eff6ff; }
.record-info { display: flex; flex-direction: column; gap: 8px; }
.record-info .title { font-size: 1.05rem; color: #0f172a; }
.record-info .meta { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #64748b; }
.tag { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #475569; }
.divider { color: #cbd5e1; }
.record-actions { display: flex; gap: 8px; }

/* Status Pills */
.status-pill {
  display: inline-block; padding: 2px 8px; border-radius: 99px;
  font-size: 0.75rem; font-weight: 600; text-align: center;
}
.status-pill.low { background: #dcfce7; color: #166534; }
.status-pill.medium { background: #fef3c7; color: #92400e; }
.status-pill.high { background: #fee2e2; color: #b91c1c; }

/* Timeline */
.timeline { display: flex; flex-direction: column; gap: 20px; border-left: 2px solid #e2e8f0; margin-left: 12px; padding-left: 24px; }
.timeline-item { position: relative; }
.timeline-item::before {
  content: ''; position: absolute; left: -31px; top: 0; width: 14px; height: 14px;
  background: #ffffff; border: 2px solid #3b82f6; border-radius: 50%;
}
.timeline-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.version-badge { background: #1e293b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.timeline-header .note { font-weight: 600; color: #334155; }
.timeline-header .date { color: #94a3b8; font-size: 0.85rem; }
.timeline-content { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }

@media (max-width: 1200px) {
  .editor-layout { grid-template-columns: 1fr; }
  .form-container { position: static; max-height: none; }
}
@media (max-width: 900px) {
  .split-pane { grid-template-columns: 1fr; min-height: auto; }
  .form-grid-2 { grid-template-columns: 1fr; }
  .presentation-tools { grid-template-columns: 1fr; }
  .record-item { flex-direction: column; align-items: flex-start; gap: 16px; }
  .record-actions { width: 100%; justify-content: flex-end; border-top: 1px solid #f1f5f9; padding-top: 12px; }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api, apiForm } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { parseTeachingContextQuery } from './contextQuery'

interface MaterialRead {
  id: number
  title: string
  subject: string
  purpose: string
  resource_scope: string
  uploader_id: number
  uploader_name: string
  uploader_username: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
  chunk_strategy: string
  chunk_size: number
  chunk_overlap: number
  tags: string[]
  file_name: string
  file_type: string
  parse_status: string
  parse_error: string | null
  chunk_count: number
  created_at: string
}

interface MaterialChunk {
  id: number
  material_id: number
  chunk_index: number
  content: string
  page_no: number | null
  slide_no: number | null
  token_count: number
}

interface MaterialParseStatus {
  material_id: number
  status: string
  detail: string
  error_message: string | null
  cache_hit: boolean
}

interface RetrievedChunk {
  id: number
  material_id: number
  material_title: string
  source: string
  content: string
  page_no: number | null
  slide_no: number | null
  score: number
}

interface RetrievalSearchResponse {
  chunks: RetrievedChunk[]
  cache_hit: boolean
  retrieval_mode: string
}

interface Course {
  id: number
  title: string
  subject: string
  exam_type: string
  status: string
}

interface Chapter {
  id: number
  title: string
  sessions: LessonSession[]
}

interface LessonSession {
  id: number
  chapter_id: number
  title: string
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

const auth = useAuthStore()
const route = useRoute()
const title = ref('')
const subject = ref('')
const purpose = ref('')
const resourceScope = ref('personal')
const tags = ref('')
const file = ref<File | null>(null)
const chunkStrategy = ref('fixed')
const chunkSize = ref(800)
const chunkOverlap = ref(80)
const courses = ref<Course[]>([])
const selectedCourse = ref<CourseDetail | null>(null)
const courseId = ref(0)
const chapterId = ref(0)
const sessionId = ref(0)
const knowledgePointId = ref(0)
const materials = ref<MaterialRead[]>([])
const selectedChunks = ref<MaterialChunk[]>([])
const query = ref('')
const materialIds = ref('')
const chunks = ref<RetrievedChunk[]>([])
const parseStatuses = ref<Record<number, MaterialParseStatus>>({})
const retrievalCacheHit = ref<boolean | null>(null)
const retrievalMode = ref('')
const loading = ref('')
const error = ref('')
const notice = ref('')
const returnTo = ref('')
const canUploadMaterial = computed(() => auth.user?.permissions.includes('material:upload') ?? false)
const canPublishPublic = computed(() => auth.user?.permissions.includes('material:publish_public') ?? false)
const canManageAllMaterials = computed(() => auth.user?.permissions.includes('material:manage_all') ?? false)
const pageMode = computed(() => String(route.meta.pageMode || 'library'))
const showUploadPage = computed(() => canUploadMaterial.value && pageMode.value === 'upload')
const showLibraryPage = computed(() => pageMode.value === 'library')
const availableSessions = computed(() => {
  if (!selectedCourse.value) return []
  return selectedCourse.value.chapters
    .filter((chapter) => !chapterId.value || chapter.id === chapterId.value)
    .flatMap((chapter) => chapter.sessions)
})
const availableKnowledgePoints = computed(() => {
  if (!selectedCourse.value) return []
  return selectedCourse.value.knowledge_points.filter((point) => {
    if (sessionId.value) return point.session_id === sessionId.value
    if (chapterId.value) return point.chapter_id === chapterId.value || point.chapter_id === null
    return true
  })
})

function setFile(event: Event) {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
}

function ids(): number[] {
  return materialIds.value
    .split(',')
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value > 0)
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '等待解析',
    parsing: '解析中',
    parsed: '已解析',
    empty: '无内容',
    failed: '解析失败',
  }
  return labels[status] ?? status
}

function scopeLabel(scope: string): string {
  const labels: Record<string, string> = {
    personal: '个人资源',
    public: '公共资源',
  }
  return labels[scope] ?? scope
}

function chunkStrategyLabel(strategy: string): string {
  const labels: Record<string, string> = {
    fixed: '按长度切分',
    paragraph: '按自然段切分',
    parent_child: '按标题层级切分',
  }
  return labels[strategy] ?? strategy
}

function canManageMaterial(material: MaterialRead): boolean {
  return canManageAllMaterials.value || material.uploader_id === auth.user?.id
}

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

async function loadMaterials() {
  try {
    materials.value = await api<MaterialRead[]>('/api/materials')
  } catch (err) {
    setError(err, '材料列表加载失败')
  }
}

async function loadCourses() {
  try {
    courses.value = await api<Course[]>('/api/courses')
  } catch (err) {
    setError(err, '课程列表加载失败')
  }
}

async function selectCourse() {
  chapterId.value = 0
  sessionId.value = 0
  knowledgePointId.value = 0
  selectedCourse.value = null
  if (!courseId.value) return

  loading.value = `course-${courseId.value}`
  error.value = ''
  try {
    selectedCourse.value = await api<CourseDetail>(`/api/courses/${courseId.value}`)
  } catch (err) {
    setError(err, '课程详情加载失败')
  } finally {
    loading.value = ''
  }
}

async function applyRouteContext() {
  const context = parseTeachingContextQuery(route.query)
  returnTo.value = typeof route.query.return_to === 'string' ? route.query.return_to : ''
  if (!context.course_id) return

  courseId.value = context.course_id
  loading.value = `course-${courseId.value}`
  error.value = ''
  try {
    selectedCourse.value = await api<CourseDetail>(`/api/courses/${courseId.value}`)
    chapterId.value = context.chapter_id
    sessionId.value = context.session_id
    knowledgePointId.value = context.knowledge_point_id
  } catch (err) {
    setError(err, '课程详情加载失败')
  } finally {
    loading.value = ''
  }
}

function selectChapter() {
  sessionId.value = 0
  knowledgePointId.value = 0
}

function selectSession() {
  knowledgePointId.value = 0
  const sessionChapter = selectedCourse.value?.chapters.find((chapter) =>
    chapter.sessions.some((session) => session.id === sessionId.value),
  )
  if (sessionChapter) chapterId.value = sessionChapter.id
}

async function uploadMaterial() {
  if (!file.value) {
    setError(new Error('请选择要上传的文件'), '上传失败')
    return
  }

  loading.value = 'upload'
  error.value = ''
  notice.value = ''
  try {
    const form = new FormData()
    form.set('title', title.value)
    form.set('subject', subject.value)
    form.set('purpose', purpose.value)
    form.set('resource_scope', resourceScope.value)
    form.set('tags', tags.value)
    form.set('file', file.value)
    form.set('chunk_strategy', chunkStrategy.value)
    form.set('chunk_size', String(chunkSize.value))
    form.set('chunk_overlap', String(chunkOverlap.value))
    if (courseId.value) form.set('course_id', String(courseId.value))
    if (chapterId.value) form.set('chapter_id', String(chapterId.value))
    if (sessionId.value) form.set('session_id', String(sessionId.value))
    if (knowledgePointId.value) form.set('knowledge_point_id', String(knowledgePointId.value))
    const uploaded = await apiForm<MaterialRead>('/api/materials/upload', form)
    materialIds.value = String(uploaded.id)
    notice.value = `材料 ${uploaded.id} 已上传，状态：${statusLabel(uploaded.parse_status)}。`
    await loadMaterials()
  } catch (err) {
    setError(err, '材料上传失败')
  } finally {
    loading.value = ''
  }
}

async function loadChunks(material: MaterialRead) {
  loading.value = `chunks-${material.id}`
  error.value = ''
  notice.value = ''
  try {
    selectedChunks.value = await api<MaterialChunk[]>(`/api/materials/${material.id}/chunks`)
    notice.value = selectedChunks.value.length ? `已加载材料 ${material.id} 的片段。` : '这份材料暂无片段。'
  } catch (err) {
    setError(err, '材料片段加载失败')
  } finally {
    loading.value = ''
  }
}

async function reparseMaterial(material: MaterialRead) {
  loading.value = `reparse-${material.id}`
  error.value = ''
  notice.value = ''
  try {
    const updated = await api<MaterialRead>(`/api/materials/${material.id}/reparse`, { method: 'POST' })
    notice.value = `材料 ${updated.id} 已提交重新解析，状态：${statusLabel(updated.parse_status)}。`
    await loadMaterials()
  } catch (err) {
    setError(err, '重新解析失败')
  } finally {
    loading.value = ''
  }
}

async function loadParseStatus(material: MaterialRead) {
  loading.value = `status-${material.id}`
  error.value = ''
  notice.value = ''
  try {
    const status = await api<MaterialParseStatus>(`/api/materials/${material.id}/parse-status`)
    parseStatuses.value = { ...parseStatuses.value, [material.id]: status }
    notice.value = `材料 ${material.id} 当前状态：${statusLabel(status.status)}，来源：${status.cache_hit ? '缓存' : '数据库'}。`
  } catch (err) {
    setError(err, '解析状态加载失败')
  } finally {
    loading.value = ''
  }
}

async function deleteMaterial(material: MaterialRead) {
  loading.value = `delete-${material.id}`
  error.value = ''
  notice.value = ''
  try {
    await api<void>(`/api/materials/${material.id}`, { method: 'DELETE' })
    materials.value = materials.value.filter((item) => item.id !== material.id)
    selectedChunks.value = selectedChunks.value.filter((chunk) => chunk.material_id !== material.id)
    delete parseStatuses.value[material.id]
    notice.value = `材料 ${material.id} 已删除。`
  } catch (err) {
    setError(err, '删除材料失败')
  } finally {
    loading.value = ''
  }
}

async function searchMaterials() {
  loading.value = 'search'
  error.value = ''
  notice.value = ''
  try {
    const result = await api<RetrievalSearchResponse>('/api/retrieval/search', {
      method: 'POST',
      body: JSON.stringify({
        query: query.value,
        top_k: 8,
        material_ids: ids(),
      }),
    })
    chunks.value = result.chunks
    retrievalCacheHit.value = Boolean(result.cache_hit)
    retrievalMode.value = result.retrieval_mode || ''
    const source = retrievalCacheHit.value ? '缓存命中' : retrievalModeLabel(retrievalMode.value)
    notice.value = result.chunks.length ? `已返回相关片段（${source}）。` : `没有找到匹配内容（${source}）。`
  } catch (err) {
    setError(err, '知识库检索失败')
  } finally {
    loading.value = ''
  }
}

function retrievalModeLabel(mode: string): string {
  const labels: Record<string, string> = {
    vector: '向量检索',
    lexical: '关键词检索',
    cache: '缓存命中',
  }
  return labels[mode] ?? '实时检索'
}

onMounted(async () => {
  await Promise.all([loadMaterials(), loadCourses()])
  await applyRouteContext()
})
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">资料库</p>
        <h1>{{ pageMode === 'upload' ? '上传资料' : (canUploadMaterial ? '教学资料库' : '公共资料库') }}</h1>
        <p>{{ pageMode === 'upload' ? '上传教材、讲义或课件，并设置课程归属、切片方式和资源域。' : (canUploadMaterial ? '查看资料解析状态、预览内容，并检索相关片段。' : '查看机构公开资料，预览资料片段并按问题检索相关内容。') }}</p>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <RouterLink v-if="returnTo" class="inline-action" :to="returnTo">
      返回生成页面
    </RouterLink>

    <div v-if="showUploadPage || showLibraryPage" class="two-column-grid">
      <form v-if="showUploadPage" class="panel stack" @submit.prevent="uploadMaterial">
        <h2>上传材料</h2>
        <label>
          材料标题
          <input v-model.trim="title" required />
        </label>
        <label>
          学科
          <input v-model.trim="subject" placeholder="例如：英语、数学" />
        </label>
        <label>
          用途
          <input v-model.trim="purpose" placeholder="例如：备课、习题、讲义" />
        </label>
        <label v-if="canPublishPublic">
          资源域
          <select v-model="resourceScope">
            <option value="personal">个人资源</option>
            <option value="public">公共资源</option>
          </select>
        </label>
        <label>
          标签
          <input v-model.trim="tags" placeholder="多个标签用英文逗号分隔" />
        </label>
        <div class="scope-grid">
          <label>
            切片方式
            <select v-model="chunkStrategy">
              <option value="fixed">按长度切分</option>
              <option value="paragraph">按自然段切分</option>
              <option value="parent_child">按标题层级切分</option>
            </select>
          </label>
          <label>
            每段长度
            <input v-model.number="chunkSize" type="number" min="200" max="4000" step="50" />
          </label>
          <label>
            相邻重叠
            <input v-model.number="chunkOverlap" type="number" min="0" max="2000" step="20" />
          </label>
        </div>
        <label>
          关联课程
          <select v-model.number="courseId" @change="selectCourse">
            <option :value="0">不绑定课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">
              {{ course.title }} · {{ course.subject }}
            </option>
          </select>
        </label>
        <div v-if="selectedCourse" class="scope-grid">
          <label>
            章节
            <select v-model.number="chapterId" @change="selectChapter">
              <option :value="0">不绑定章节</option>
              <option v-for="chapter in selectedCourse.chapters" :key="chapter.id" :value="chapter.id">
                {{ chapter.title }}
              </option>
            </select>
          </label>
          <label>
            课次
            <select v-model.number="sessionId" @change="selectSession">
              <option :value="0">不绑定课次</option>
              <option v-for="session in availableSessions" :key="session.id" :value="session.id">
                {{ session.title }}
              </option>
            </select>
          </label>
          <label>
            知识点
            <select v-model.number="knowledgePointId">
              <option :value="0">不绑定知识点</option>
              <option v-for="point in availableKnowledgePoints" :key="point.id" :value="point.id">
                {{ point.name }}
              </option>
            </select>
          </label>
        </div>
        <label>
          文件
          <input type="file" accept=".txt,.md,.pdf,.docx,.pptx" required @change="setFile" />
        </label>
        <button class="btn-primary" type="submit" :disabled="loading === 'upload'">
          {{ loading === 'upload' ? '上传中...' : '上传材料' }}
        </button>
      </form>

      <section v-else-if="pageMode === 'upload'" class="panel stack">
        <h2>公共资料</h2>
        <p class="empty-state">当前账号只能查看公开资料，上传和重新解析由教师或管理员完成。</p>
      </section>

      <form v-if="showLibraryPage" class="panel stack" @submit.prevent="searchMaterials">
        <h2>检索材料</h2>
        <label>
          检索问题
          <textarea v-model.trim="query" rows="4" required placeholder="例如：书信格式" />
        </label>
        <label>
          限定材料 ID（可选）
          <input v-model.trim="materialIds" placeholder="例如：1,2,3" />
        </label>
        <button class="btn-primary" type="submit" :disabled="loading === 'search'">
          {{ loading === 'search' ? '检索中...' : '检索' }}
        </button>
      </form>
    </div>

    <section v-if="showLibraryPage" class="panel stack">
      <div class="panel-title">
        <h2>材料列表</h2>
        <button type="button" class="btn-secondary" @click="loadMaterials">刷新</button>
      </div>
      <p v-if="!materials.length" class="empty-state">暂无材料。</p>
      <ul v-else class="material-list">
        <li v-for="material in materials" :key="material.id">
          <div class="stack">
            <strong>{{ material.id }} · {{ material.title }}</strong>
            <small>
              {{ material.file_name }} · {{ material.subject || '未填学科' }}
              · {{ scopeLabel(material.resource_scope) }}
              · 上传人 {{ material.uploader_name || material.uploader_username || `用户 ${material.uploader_id}` }}
              <span class="status-pill" :class="material.parse_status">{{ statusLabel(material.parse_status) }}</span>
              {{ material.chunk_count }} 个片段
            </small>
            <small>
              切片：{{ chunkStrategyLabel(material.chunk_strategy) }}
              · 每段约 {{ material.chunk_size }} 字
              · 重叠 {{ material.chunk_overlap }} 字
            </small>
            <p v-if="material.tags.length" class="tags">{{ material.tags.join(' / ') }}</p>
            <p
              v-if="material.course_id || material.chapter_id || material.session_id || material.knowledge_point_id"
              class="status-detail"
            >
              归属：课程 {{ material.course_id || '-' }}
              · 章节 {{ material.chapter_id || '-' }}
              · 课次 {{ material.session_id || '-' }}
              · 知识点 {{ material.knowledge_point_id || '-' }}
            </p>
            <p v-if="material.parse_error" class="parse-error">{{ material.parse_error }}</p>
            <p v-if="parseStatuses[material.id]" class="status-detail">
              状态详情：{{ statusLabel(parseStatuses[material.id].status) }}
              · {{ parseStatuses[material.id].cache_hit ? '缓存命中' : '数据库回退' }}
              <span v-if="parseStatuses[material.id].detail"> · {{ parseStatuses[material.id].detail }}</span>
            </p>
          </div>
          <div class="actions">
            <button type="button" class="btn-secondary" @click="loadChunks(material)">预览内容</button>
            <button type="button" class="btn-secondary" @click="loadParseStatus(material)">解析状态</button>
            <button v-if="canManageMaterial(material)" type="button" class="btn-secondary" @click="reparseMaterial(material)">重新解析</button>
            <button v-if="canManageMaterial(material)" type="button" class="btn-danger" @click="deleteMaterial(material)">删除</button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="showLibraryPage && selectedChunks.length" class="panel stack">
      <h2>资料内容预览</h2>
      <ul class="clean-list">
        <li v-for="chunk in selectedChunks" :key="chunk.id">
          <strong>片段 {{ chunk.chunk_index + 1 }}</strong>
          <p>{{ chunk.content }}</p>
          <small v-if="chunk.page_no || chunk.slide_no">
            {{ chunk.page_no ? `页码 ${chunk.page_no}` : '' }}
            {{ chunk.slide_no ? `幻灯片 ${chunk.slide_no}` : '' }}
          </small>
        </li>
      </ul>
    </section>

    <section v-if="showLibraryPage" class="panel stack">
      <div class="panel-title">
        <h2>检索结果</h2>
        <span v-if="retrievalCacheHit !== null" class="status-pill" :class="retrievalCacheHit ? 'parsed' : 'pending'">
          {{ retrievalCacheHit ? '缓存命中' : retrievalModeLabel(retrievalMode) }}
        </span>
      </div>
      <p v-if="!chunks.length" class="empty-state">暂无检索结果。</p>
      <ul v-else class="clean-list">
        <li v-for="chunk in chunks" :key="chunk.id">
          <strong>{{ chunk.source }} · 匹配度 {{ chunk.score.toFixed(2) }}</strong>
          <p>{{ chunk.content }}</p>
          <small>
            材料 {{ chunk.material_id }}
            {{ chunk.page_no ? ` · 页码 ${chunk.page_no}` : '' }}
            {{ chunk.slide_no ? ` · 幻灯片 ${chunk.slide_no}` : '' }}
          </small>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.material-list {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.material-list li {
  display: flex;
  gap: 14px;
  justify-content: space-between;
  border-bottom: 1px solid #edf1f7;
  padding-bottom: 14px;
}

.material-list li:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

p {
  margin: 0;
  white-space: pre-wrap;
}

.tags {
  color: var(--brand);
  font-size: 0.9rem;
}

.parse-error {
  color: #b42318;
}

.status-detail {
  color: #475569;
  font-size: 0.9rem;
}

.scope-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

@media (max-width: 820px) {
  .material-list li {
    display: grid;
  }

  .scope-grid {
    grid-template-columns: 1fr;
  }
}
</style>

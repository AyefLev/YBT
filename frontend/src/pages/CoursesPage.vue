<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, apiBlob, downloadBlobResponse } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { buildTeachingContextQuery } from './contextQuery'
import { buildCourseAssetTree } from './courseStructure'

interface Course {
  id: number
  owner_id: number
  owner_name: string
  owner_username: string
  title: string
  subject: string
  exam_type: string
  description: string
  status: string
}

interface Chapter {
  id: number
  title: string
  summary: string
  order_index: number
  sessions: LessonSession[]
}

interface LessonSession {
  id: number
  title: string
  duration_minutes: number
  teaching_goal: string
  order_index: number
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

interface TeachingAsset {
  asset_type: string
  id: number
  title: string
  owner_id: number | null
  owner_name: string
  resource_scope: string
  status: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
}

interface CourseAssetsResponse {
  course_id: number
  assets: TeachingAsset[]
}

const auth = useAuthStore()
const courses = ref<Course[]>([])
const selected = ref<CourseDetail | null>(null)
const courseAssets = ref<TeachingAsset[]>([])
const loading = ref('')
const error = ref('')
const notice = ref('')

const courseForm = reactive({ title: '', subject: '', exam_type: '', description: '' })
const chapterForm = reactive({ title: '', summary: '', order_index: 1 })
const sessionForm = reactive({ chapter_id: 0, title: '', duration_minutes: 45, teaching_goal: '', order_index: 1 })
const pointForm = reactive({ chapter_id: 0, session_id: 0, name: '', description: '', difficulty: 'basic' })

const assetTree = computed(() => (selected.value ? buildCourseAssetTree(selected.value) : null))
const sessionCount = computed(() =>
  selected.value?.chapters.reduce((total, chapter) => total + chapter.sessions.length, 0) ?? 0,
)
const canCreateCourses = computed(() => auth.user?.permissions.includes('course:create') ?? false)
const canManageAllCourses = computed(() => auth.user?.permissions.includes('course:manage_all') ?? false)
const canExportCourse = computed(() => auth.user?.permissions.includes('lesson:export') ?? false)
const canManageSelected = computed(() =>
  Boolean(selected.value && (canManageAllCourses.value || selected.value.owner_id === auth.user?.id)),
)

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: '草稿',
    active: '启用',
    archived: '归档',
  }
  return labels[status] ?? status
}

function difficultyLabel(value: string): string {
  const labels: Record<string, string> = {
    basic: '基础',
    medium: '中等',
    advanced: '提高',
  }
  return labels[value] ?? value
}

function assetTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    material: '材料',
    lesson: '教案',
    exercise: '习题',
  }
  return labels[value] ?? value
}

function assetStatusLabel(asset: TeachingAsset): string {
  if (!asset.status) return '未标记'
  const labels: Record<string, string> = {
    pending: '等待解析',
    parsing: '解析中',
    parsed: '已解析',
    failed: '解析失败',
    approved: '已通过',
    needs_revision: '需修订',
    compliant: '合规',
    warning: '需关注',
    blocked: '已阻断',
  }
  return labels[asset.status] ?? asset.status
}

function assetKey(asset: TeachingAsset): string {
  return `${asset.asset_type}-${asset.id}`
}

function assetsForCourseRoot(): TeachingAsset[] {
  return courseAssets.value.filter((asset) => !asset.chapter_id && !asset.session_id && !asset.knowledge_point_id)
}

function assetsForChapter(chapterId: number): TeachingAsset[] {
  return courseAssets.value.filter(
    (asset) => asset.chapter_id === chapterId && !asset.session_id && !asset.knowledge_point_id,
  )
}

function assetsForSession(sessionId: number): TeachingAsset[] {
  return courseAssets.value.filter((asset) => asset.session_id === sessionId && !asset.knowledge_point_id)
}

function assetsForPoint(pointId: number): TeachingAsset[] {
  return courseAssets.value.filter((asset) => asset.knowledge_point_id === pointId)
}

async function loadCourses() {
  try {
    courses.value = await api<Course[]>('/api/courses')
    if (!selected.value && courses.value[0]) {
      await loadDetail(courses.value[0].id)
    }
  } catch (err) {
    setError(err, '课程列表加载失败')
  }
}

async function loadDetail(courseId: number) {
  loading.value = `course-${courseId}`
  error.value = ''
  try {
    const [detail, assets] = await Promise.all([
      api<CourseDetail>(`/api/courses/${courseId}`),
      api<CourseAssetsResponse>(`/api/courses/${courseId}/assets`),
    ])
    selected.value = detail
    courseAssets.value = assets.assets
    sessionForm.chapter_id = selected.value.chapters[0]?.id ?? 0
    pointForm.chapter_id = selected.value.chapters[0]?.id ?? 0
    pointForm.session_id = selected.value.chapters[0]?.sessions[0]?.id ?? 0
  } catch (err) {
    courseAssets.value = []
    setError(err, '课程详情加载失败')
  } finally {
    loading.value = ''
  }
}

async function createCourse() {
  loading.value = 'course'
  error.value = ''
  notice.value = ''
  try {
    const course = await api<Course>('/api/courses', {
      method: 'POST',
      body: JSON.stringify({ ...courseForm, status: 'draft' }),
    })
    Object.assign(courseForm, { title: '', subject: '', exam_type: '', description: '' })
    notice.value = `课程 ${course.id} 已创建`
    await loadCourses()
    await loadDetail(course.id)
  } catch (err) {
    setError(err, '课程创建失败')
  } finally {
    loading.value = ''
  }
}

async function createChapter() {
  if (!selected.value) return
  loading.value = 'chapter'
  error.value = ''
  try {
    await api<Chapter>(`/api/courses/${selected.value.id}/chapters`, {
      method: 'POST',
      body: JSON.stringify(chapterForm),
    })
    Object.assign(chapterForm, { title: '', summary: '', order_index: chapterForm.order_index + 1 })
    await loadDetail(selected.value.id)
  } catch (err) {
    setError(err, '章节创建失败')
  } finally {
    loading.value = ''
  }
}

async function createSession() {
  if (!selected.value || !sessionForm.chapter_id) return
  loading.value = 'session'
  error.value = ''
  try {
    await api<LessonSession>(`/api/chapters/${sessionForm.chapter_id}/sessions`, {
      method: 'POST',
      body: JSON.stringify({ ...sessionForm, lesson_id: null }),
    })
    Object.assign(sessionForm, { ...sessionForm, title: '', teaching_goal: '', order_index: sessionForm.order_index + 1 })
    await loadDetail(selected.value.id)
  } catch (err) {
    setError(err, '课次创建失败')
  } finally {
    loading.value = ''
  }
}

async function createPoint() {
  if (!selected.value) return
  loading.value = 'point'
  error.value = ''
  const sessionChapterId = chapterIdForSession(pointForm.session_id)
  const payload = {
    ...pointForm,
    chapter_id: sessionChapterId ?? (pointForm.chapter_id || null),
    session_id: pointForm.session_id || null,
  }
  try {
    await api<KnowledgePoint>(`/api/courses/${selected.value.id}/knowledge-points`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    Object.assign(pointForm, { ...pointForm, name: '', description: '' })
    await loadDetail(selected.value.id)
  } catch (err) {
    setError(err, '知识点创建失败')
  } finally {
    loading.value = ''
  }
}

function chapterIdForSession(sessionId: number): number | null {
  if (!selected.value || !sessionId) return null
  for (const chapter of selected.value.chapters) {
    if (chapter.sessions.some((session) => session.id === sessionId)) return chapter.id
  }
  return null
}

async function exportOutline() {
  if (!selected.value) return
  try {
    const result = await apiBlob(`/api/exports/course/${selected.value.id}/outline-docx`, { method: 'POST' })
    downloadBlobResponse(result, `course-${selected.value.id}-outline.docx`)
    notice.value = `课程大纲已开始下载：${result.filename ?? 'course-outline.docx'}`
  } catch (err) {
    setError(err, '课程大纲导出失败')
  }
}

onMounted(loadCourses)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">课程体系</p>
        <h1>机构课程结构</h1>
        <p>维护课程、章节、课次和知识点，形成可复用的教研资产。</p>
      </div>
    </header>

    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="course-grid">
      <form v-if="canCreateCourses" class="panel stack" @submit.prevent="createCourse">
        <h2>创建课程</h2>
        <input v-model.trim="courseForm.title" required placeholder="课程名称" />
        <input v-model.trim="courseForm.subject" required placeholder="学科，例如：英语、数学" />
        <input v-model.trim="courseForm.exam_type" required placeholder="适用项目，例如：成人考研数学" />
        <textarea v-model.trim="courseForm.description" rows="3" placeholder="课程说明" />
        <button class="btn-primary" :disabled="loading === 'course'">创建课程</button>
      </form>

      <section class="panel stack">
        <h2>课程列表</h2>
        <p v-if="!courses.length" class="empty-state">暂无课程。</p>
        <ul v-else class="clean-list">
          <li v-for="course in courses" :key="course.id">
            <button type="button" class="text-link" @click="loadDetail(course.id)">
              {{ course.id }} · {{ course.title }}
            </button>
            <small>{{ course.subject }} · {{ course.exam_type }} · {{ statusLabel(course.status) }}</small>
            <small>所属教师：{{ course.owner_name || course.owner_username || `用户 ${course.owner_id}` }}</small>
          </li>
        </ul>
      </section>
    </div>

    <section v-if="selected" class="panel stack">
      <div class="panel-title">
        <div>
          <h2>{{ selected.title }}</h2>
          <p class="muted">
            {{ selected.subject }} · {{ selected.exam_type }} · {{ statusLabel(selected.status) }}
          </p>
          <p class="muted">
            所属教师：{{ selected.owner_name || selected.owner_username || `用户 ${selected.owner_id}` }}
          </p>
          <p class="muted">{{ selected.description || '暂无课程说明。' }}</p>
        </div>
        <button v-if="canExportCourse" type="button" class="btn-secondary" @click="exportOutline">导出课程大纲</button>
      </div>

      <div class="metric-grid">
        <div>
          <span>章节数</span>
          <strong>{{ selected.chapters.length }}</strong>
        </div>
        <div>
          <span>课次数</span>
          <strong>{{ sessionCount }}</strong>
        </div>
        <div>
          <span>知识点数</span>
          <strong>{{ selected.knowledge_points.length }}</strong>
        </div>
        <div>
          <span>归类资产</span>
          <strong>{{ courseAssets.length }}</strong>
        </div>
      </div>

      <div v-if="canManageSelected" class="two-column-grid">
        <form class="stack" @submit.prevent="createChapter">
          <h3>添加章节</h3>
          <input v-model.trim="chapterForm.title" required placeholder="章节名称" />
          <textarea v-model.trim="chapterForm.summary" rows="2" placeholder="章节摘要" />
          <input v-model.number="chapterForm.order_index" type="number" min="0" />
          <button class="btn-primary" :disabled="loading === 'chapter'">添加章节</button>
        </form>

        <form class="stack" @submit.prevent="createSession">
          <h3>添加课次</h3>
          <select v-model.number="sessionForm.chapter_id" required>
            <option :value="0" disabled>选择章节</option>
            <option v-for="chapter in selected.chapters" :key="chapter.id" :value="chapter.id">
              {{ chapter.title }}
            </option>
          </select>
          <input v-model.trim="sessionForm.title" required placeholder="课次名称" />
          <input v-model.number="sessionForm.duration_minutes" type="number" min="1" />
          <textarea v-model.trim="sessionForm.teaching_goal" rows="2" placeholder="教学目标" />
          <button class="btn-primary" :disabled="loading === 'session' || !sessionForm.chapter_id">添加课次</button>
        </form>
      </div>

      <form v-if="canManageSelected" class="point-form" @submit.prevent="createPoint">
        <h3>添加知识点</h3>
        <select v-model.number="pointForm.chapter_id">
          <option :value="0">不绑定章节</option>
          <option v-for="chapter in selected.chapters" :key="chapter.id" :value="chapter.id">
            {{ chapter.title }}
          </option>
        </select>
        <select v-model.number="pointForm.session_id">
          <option :value="0">不绑定课次</option>
          <template v-for="chapter in selected.chapters" :key="chapter.id">
            <option v-for="session in chapter.sessions" :key="session.id" :value="session.id">
              {{ session.title }}
            </option>
          </template>
        </select>
        <input v-model.trim="pointForm.name" required placeholder="知识点名称" />
        <input v-model.trim="pointForm.description" placeholder="知识点说明" />
        <select v-model="pointForm.difficulty">
          <option value="basic">基础</option>
          <option value="medium">中等</option>
          <option value="advanced">提高</option>
        </select>
        <button class="btn-primary" :disabled="loading === 'point'">添加知识点</button>
      </form>

      <div class="two-column-grid">
        <section class="stack">
          <h3>课程资产树</h3>
          <div v-if="assetsForCourseRoot().length" class="asset-block">
            <strong>课程级资产</strong>
            <ul class="asset-list">
              <li v-for="asset in assetsForCourseRoot()" :key="assetKey(asset)">
                <span>{{ assetTypeLabel(asset.asset_type) }} #{{ asset.id }} · {{ asset.title }}</span>
                <small>
                  {{ assetStatusLabel(asset) }}
                  <template v-if="asset.owner_name"> · {{ asset.owner_name }}</template>
                  <template v-if="asset.resource_scope">
                    · {{ asset.resource_scope === 'public' ? '公共资源' : '个人资源' }}
                  </template>
                </small>
              </li>
            </ul>
          </div>
          <p v-if="!assetTree?.chapters.length" class="empty-state">先添加章节，再继续添加课次和知识点。</p>
          <div v-else class="course-tree">
            <article v-for="chapter in assetTree.chapters" :key="chapter.id" class="tree-chapter">
              <header>
                <strong>{{ chapter.order_index }}. {{ chapter.title }}</strong>
                <small>{{ chapter.summary || '暂无章节摘要' }}</small>
              </header>
              <div v-if="chapter.knowledgePoints.length" class="knowledge-stack">
                <div v-for="point in chapter.knowledgePoints" :key="point.id" class="knowledge-item">
                  <span class="knowledge-chip">{{ point.name }} · {{ difficultyLabel(point.difficulty) }}</span>
                  <div class="quick-actions">
                    <RouterLink :to="{ path: '/dashboard/materials', query: buildTeachingContextQuery({ course_id: selected.id, chapter_id: chapter.id, knowledge_point_id: point.id }) }">上传资料</RouterLink>
                    <RouterLink :to="{ path: '/dashboard/lesson', query: buildTeachingContextQuery({ course_id: selected.id, chapter_id: chapter.id, knowledge_point_id: point.id }) }">生成教案</RouterLink>
                    <RouterLink :to="{ path: '/dashboard/exercise', query: buildTeachingContextQuery({ course_id: selected.id, chapter_id: chapter.id, knowledge_point_id: point.id }) }">生成习题</RouterLink>
                  </div>
                  <ul v-if="assetsForPoint(point.id).length" class="asset-list compact">
                    <li v-for="asset in assetsForPoint(point.id)" :key="assetKey(asset)">
                      <span>{{ assetTypeLabel(asset.asset_type) }} #{{ asset.id }} · {{ asset.title }}</span>
                      <small>{{ assetStatusLabel(asset) }}</small>
                    </li>
                  </ul>
                </div>
              </div>
              <ul v-if="assetsForChapter(chapter.id).length" class="asset-list">
                <li v-for="asset in assetsForChapter(chapter.id)" :key="assetKey(asset)">
                  <span>{{ assetTypeLabel(asset.asset_type) }} #{{ asset.id }} · {{ asset.title }}</span>
                  <small>
                    {{ assetStatusLabel(asset) }}
                    <template v-if="asset.owner_name"> · {{ asset.owner_name }}</template>
                  </small>
                </li>
              </ul>
              <div v-if="chapter.sessions.length" class="session-list">
                <article v-for="session in chapter.sessions" :key="session.id" class="session-card">
                  <div>
                    <strong>{{ session.order_index }}. {{ session.title }}</strong>
                    <small>{{ session.duration_minutes }} 分钟</small>
                  </div>
                  <div class="quick-actions">
                    <RouterLink :to="{ path: '/dashboard/materials', query: buildTeachingContextQuery({ course_id: selected.id, chapter_id: chapter.id, session_id: session.id }) }">上传资料</RouterLink>
                    <RouterLink :to="{ path: '/dashboard/lesson', query: buildTeachingContextQuery({ course_id: selected.id, chapter_id: chapter.id, session_id: session.id }) }">生成教案</RouterLink>
                    <RouterLink :to="{ path: '/dashboard/exercise', query: buildTeachingContextQuery({ course_id: selected.id, chapter_id: chapter.id, session_id: session.id }) }">生成习题</RouterLink>
                    <RouterLink :to="{ path: '/dashboard/classrooms', query: buildTeachingContextQuery({ course_id: selected.id, chapter_id: chapter.id, session_id: session.id }) }">发布作业</RouterLink>
                  </div>
                  <p v-if="session.teaching_goal">{{ session.teaching_goal }}</p>
                  <div v-if="session.knowledgePoints.length" class="knowledge-stack">
                    <div v-for="point in session.knowledgePoints" :key="point.id" class="knowledge-item">
                      <span class="knowledge-chip">{{ point.name }} · {{ difficultyLabel(point.difficulty) }}</span>
                      <ul v-if="assetsForPoint(point.id).length" class="asset-list compact">
                        <li v-for="asset in assetsForPoint(point.id)" :key="assetKey(asset)">
                          <span>{{ assetTypeLabel(asset.asset_type) }} #{{ asset.id }} · {{ asset.title }}</span>
                          <small>{{ assetStatusLabel(asset) }}</small>
                        </li>
                      </ul>
                    </div>
                  </div>
                  <p v-else class="muted">该课次暂未绑定知识点。</p>
                  <ul v-if="assetsForSession(session.id).length" class="asset-list">
                    <li v-for="asset in assetsForSession(session.id)" :key="assetKey(asset)">
                      <span>{{ assetTypeLabel(asset.asset_type) }} #{{ asset.id }} · {{ asset.title }}</span>
                      <small>
                        {{ assetStatusLabel(asset) }}
                        <template v-if="asset.owner_name"> · {{ asset.owner_name }}</template>
                      </small>
                    </li>
                  </ul>
                </article>
              </div>
              <p v-else class="muted">该章节暂未添加课次。</p>
            </article>
          </div>
        </section>
        <section class="stack">
          <h3>未绑定知识点</h3>
          <p v-if="!assetTree?.unassignedKnowledgePoints.length" class="empty-state">
            暂无未绑定知识点。
          </p>
          <ul v-else class="clean-list">
            <li v-for="point in assetTree.unassignedKnowledgePoints" :key="point.id">
              <strong>{{ point.name }}</strong>
              <small>{{ difficultyLabel(point.difficulty) }} · {{ point.description || '暂无说明' }}</small>
              <ul v-if="assetsForPoint(point.id).length" class="asset-list compact">
                <li v-for="asset in assetsForPoint(point.id)" :key="assetKey(asset)">
                  <span>{{ assetTypeLabel(asset.asset_type) }} #{{ asset.id }} · {{ asset.title }}</span>
                  <small>{{ assetStatusLabel(asset) }}</small>
                </li>
              </ul>
            </li>
          </ul>
        </section>
      </div>
    </section>
  </section>
</template>

<style scoped>
.course-grid {
  display: grid;
  grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
  gap: 16px;
}

.point-form {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  align-items: end;
}

.point-form h3 {
  grid-column: 1 / -1;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-grid div {
  display: grid;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: var(--surface-soft);
}

.metric-grid span {
  color: var(--muted);
  font-size: 0.9rem;
  font-weight: 800;
}

.metric-grid strong {
  color: var(--text);
  font-size: 1.7rem;
}

.text-link {
  border: 0;
  padding: 0;
  color: var(--brand);
  background: transparent;
  font-weight: 900;
  text-align: left;
}

.course-tree {
  display: grid;
  gap: 12px;
}

.tree-chapter,
.session-card {
  display: grid;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.tree-chapter header,
.session-card > div:first-child {
  display: flex;
  gap: 12px;
  align-items: baseline;
  justify-content: space-between;
}

.session-list {
  display: grid;
  gap: 10px;
  padding-left: 14px;
}

.session-card {
  border-color: #dbeafe;
  background: #eff6ff;
}

.session-card p {
  margin: 0;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.knowledge-stack {
  display: grid;
  gap: 8px;
}

.knowledge-item {
  display: grid;
  gap: 6px;
  justify-items: start;
}

.knowledge-chip {
  border: 1px solid #bbf7d0;
  border-radius: 999px;
  padding: 4px 9px;
  color: #166534;
  background: #f0fdf4;
  font-size: 0.86rem;
  font-weight: 800;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.quick-actions a {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 9px;
  color: var(--brand-dark);
  background: #ffffff;
  font-size: 0.86rem;
  font-weight: 900;
  text-decoration: none;
}

.asset-block {
  display: grid;
  gap: 8px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  padding: 10px;
  background: var(--surface-soft);
}

.asset-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.asset-list li {
  display: flex;
  gap: 10px;
  align-items: baseline;
  justify-content: space-between;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  background: #ffffff;
}

.asset-list.compact li {
  border-color: #d1fae5;
  padding: 6px 8px;
}

.asset-list span {
  min-width: 0;
  overflow-wrap: anywhere;
  font-weight: 800;
}

.asset-list small {
  flex: none;
  color: var(--muted);
}

@media (max-width: 980px) {
  .course-grid,
  .metric-grid,
  .point-form {
    grid-template-columns: 1fr;
  }

  .asset-list li {
    display: grid;
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

interface LessonRead {
  id: number
  owner_name: string
  owner_username: string
  title: string
  compliance_level: string
  updated_at: string
}

interface ExerciseRead {
  id: number
  owner_name: string
  owner_username: string
  title: string
  compliance_level: string
  updated_at: string
}

const auth = useAuthStore()
const lessons = ref<LessonRead[]>([])
const exercises = ref<ExerciseRead[]>([])
const loading = ref(true)
const error = ref('')

const riskyCount = computed(
  () =>
    lessons.value.filter((item) => item.compliance_level !== 'low').length +
    exercises.value.filter((item) => item.compliance_level !== 'low').length,
)
const canCreateLessons = computed(() => auth.user?.permissions.includes('lesson:create') ?? false)
const canCreateExercises = computed(() => auth.user?.permissions.includes('exercise:create') ?? false)
const canViewLessons = computed(() =>
  Boolean(auth.user?.permissions.some((permission) => ['lesson:create', 'lesson:view_all'].includes(permission))),
)
const canViewExercises = computed(() =>
  Boolean(auth.user?.permissions.some((permission) => ['exercise:create', 'exercise:view_all'].includes(permission))),
)
const recentLessons = computed(() => lessons.value.slice(0, 5))
const recentExercises = computed(() => exercises.value.slice(0, 5))
const quickLinks = computed(() =>
  [
    { label: '班级与作业', description: '进入班级、作业发布和批改流程', to: '/dashboard/classrooms', show: hasAnyPermission('class:join', 'class:manage', 'class:view_all') },
    { label: '资料库', description: '管理课程材料、章节资料和公共知识', to: '/dashboard/materials/library', show: hasAnyPermission('material:view_public', 'material:upload', 'material:view_all') },
    { label: '课程体系', description: '维护课程、章节、课次和知识点', to: '/dashboard/courses', show: hasAnyPermission('course:create', 'course:view_all') },
    { label: '题库管理', description: '沉淀可复用题目和答案解析', to: '/dashboard/questions', show: hasAnyPermission('exercise:create', 'question:view_all') },
    { label: '教研审核', description: '处理教案、习题和内容复核', to: '/dashboard/reviews', show: hasAnyPermission('review:manage') },
    { label: '系统检查', description: '查看模型、向量库和运行状态', to: '/dashboard/health', show: hasAnyPermission('log:view') },
  ].filter((item) => item.show),
)

function hasAnyPermission(...permissions: string[]): boolean {
  return permissions.some((permission) => auth.user?.permissions.includes(permission))
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

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const [lessonList, exerciseList] = await Promise.all([
      canViewLessons.value ? api<LessonRead[]>('/api/lessons') : Promise.resolve([]),
      canViewExercises.value ? api<ExerciseRead[]>('/api/exercises') : Promise.resolve([]),
    ])
    lessons.value = lessonList
    exercises.value = exerciseList
  } catch (err) {
    error.value = err instanceof Error ? err.message : '工作台数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <section class="page-shell dashboard-shell">
    <header class="page-hero dashboard-hero">
      <div>
        <p class="eyebrow">工作台</p>
        <h1>教研工作台</h1>
        <p>围绕课程、章节、知识库和 AI 生成链路组织教学内容，让教案、习题、资料和审核状态都能被快速定位。</p>
      </div>
      <div class="hero-actions">
        <RouterLink v-if="canCreateLessons" class="btn-primary" to="/dashboard/lesson/generate">生成教案</RouterLink>
        <RouterLink v-if="canCreateExercises" class="btn-secondary" to="/dashboard/exercise/generate">生成练习</RouterLink>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="notice">正在加载工作台数据...</p>

    <section class="metric-grid dashboard-metrics">
      <article v-if="canViewLessons" class="metric-card">
        <span>已保存教案</span>
        <strong>{{ lessons.length }}</strong>
        <small>可继续编辑、导出或生成 PPT</small>
      </article>
      <article v-if="canViewExercises" class="metric-card">
        <span>已保存练习</span>
        <strong>{{ exercises.length }}</strong>
        <small>可复用到题库或发布给班级</small>
      </article>
      <article v-if="canViewLessons || canViewExercises" class="metric-card">
        <span>待关注风险</span>
        <strong>{{ riskyCount }}</strong>
        <small>来自合规检查和 AI 复核结果</small>
      </article>
      <article class="metric-card">
        <span>常用入口</span>
        <strong>{{ quickLinks.length }}</strong>
        <small>按当前账号权限自动筛选</small>
      </article>
    </section>

    <div v-if="canViewLessons || canViewExercises" class="dashboard-main-grid">
      <section class="panel stack">
        <div class="panel-title">
          <div>
            <h2>最近教案</h2>
            <small>按更新时间展示最近保存的教案</small>
          </div>
          <RouterLink class="btn-secondary" to="/dashboard/lesson/records">查看全部</RouterLink>
        </div>
        <ul v-if="recentLessons.length" class="clean-list activity-list">
          <li v-for="lesson in recentLessons" :key="lesson.id">
            <div>
              <strong>{{ lesson.title }}</strong>
              <small>{{ lesson.owner_name || lesson.owner_username || '未标记教师' }} · {{ formatDate(lesson.updated_at) }}</small>
            </div>
            <span class="status-pill" :class="lesson.compliance_level">{{ riskLabel(lesson.compliance_level) }}</span>
          </li>
        </ul>
        <p v-else class="empty-state">暂无教案记录，可以先创建一份课程教案。</p>
      </section>

      <section class="panel stack">
        <div class="panel-title">
          <div>
            <h2>最近练习</h2>
            <small>按更新时间展示最近保存的习题</small>
          </div>
          <RouterLink class="btn-secondary" to="/dashboard/exercise/records">查看全部</RouterLink>
        </div>
        <ul v-if="recentExercises.length" class="clean-list activity-list">
          <li v-for="exercise in recentExercises" :key="exercise.id">
            <div>
              <strong>{{ exercise.title }}</strong>
              <small>{{ exercise.owner_name || exercise.owner_username || '未标记教师' }} · {{ formatDate(exercise.updated_at) }}</small>
            </div>
            <span class="status-pill" :class="exercise.compliance_level">{{ riskLabel(exercise.compliance_level) }}</span>
          </li>
        </ul>
        <p v-else class="empty-state">暂无练习记录，可以基于课程章节生成课堂练习。</p>
      </section>
    </div>

    <section class="panel stack">
      <div class="panel-title">
        <div>
          <h2>继续工作</h2>
          <small>常用工作流会根据你的角色权限自动出现</small>
        </div>
      </div>
      <div class="quick-grid">
        <RouterLink v-for="link in quickLinks" :key="link.to" :to="link.to">
          <strong>{{ link.label }}</strong>
          <span>{{ link.description }}</span>
        </RouterLink>
      </div>
    </section>
  </section>
</template>

<style scoped>
.dashboard-shell {
  gap: 22px;
}

.dashboard-hero {
  align-items: center;
}

.dashboard-metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-main-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.activity-list li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.activity-list strong {
  color: var(--text);
}

.activity-list small {
  display: block;
  margin-top: 5px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.quick-grid a {
  display: grid;
  gap: 7px;
  min-height: 96px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 15px;
  color: var(--text);
  background: var(--surface-soft);
  text-decoration: none;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    transform 0.08s ease;
}

.quick-grid a:hover {
  border-color: #bfdbfe;
  background: var(--brand-soft);
}

.quick-grid a:active {
  transform: translateY(1px);
}

.quick-grid strong {
  color: var(--text);
}

.quick-grid span {
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.55;
}

@media (max-width: 1100px) {
  .dashboard-metrics,
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .dashboard-main-grid,
  .dashboard-metrics,
  .quick-grid {
    grid-template-columns: 1fr;
  }

  .activity-list li {
    display: grid;
  }
}
</style>

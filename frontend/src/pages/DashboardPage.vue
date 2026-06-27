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
      api<LessonRead[]>('/api/lessons'),
      api<ExerciseRead[]>('/api/exercises'),
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
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">总览</p>
        <h1>教研工作台</h1>
        <p>集中查看备课、习题、知识库与审核状态，演示时可以从这里进入完整教研流程。</p>
      </div>
      <div class="hero-actions">
        <RouterLink v-if="canCreateLessons" class="btn-primary" to="/dashboard/lesson">新建备课</RouterLink>
        <RouterLink v-if="canCreateExercises" class="btn-secondary" to="/dashboard/exercise">生成习题</RouterLink>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="notice">正在加载工作台数据...</p>

    <div class="metric-grid">
      <article class="metric-card">
        <span>已保存备课</span>
        <strong>{{ lessons.length }}</strong>
      </article>
      <article class="metric-card">
        <span>已保存习题</span>
        <strong>{{ exercises.length }}</strong>
      </article>
      <article class="metric-card">
        <span>待关注合规风险</span>
        <strong>{{ riskyCount }}</strong>
      </article>
    </div>

    <div class="two-column-grid">
      <section class="panel stack">
        <div class="panel-title">
          <h2>最近备课</h2>
          <RouterLink class="btn-secondary" to="/dashboard/lesson">进入备课</RouterLink>
        </div>
        <ul v-if="lessons.length" class="clean-list">
          <li v-for="lesson in lessons.slice(0, 5)" :key="lesson.id">
            <strong>{{ lesson.title }}</strong>
            <small>
              <span class="status-pill" :class="lesson.compliance_level">
                {{ riskLabel(lesson.compliance_level) }}
              </span>
              {{ lesson.owner_name || lesson.owner_username || '未标记教师' }}
              {{ formatDate(lesson.updated_at) }}
            </small>
          </li>
        </ul>
        <p v-else class="empty-state">暂无备课记录，可以先创建一份教案。</p>
      </section>

      <section class="panel stack">
        <div class="panel-title">
          <h2>最近习题</h2>
          <RouterLink class="btn-secondary" to="/dashboard/exercise">进入习题</RouterLink>
        </div>
        <ul v-if="exercises.length" class="clean-list">
          <li v-for="exercise in exercises.slice(0, 5)" :key="exercise.id">
            <strong>{{ exercise.title }}</strong>
            <small>
              <span class="status-pill" :class="exercise.compliance_level">
                {{ riskLabel(exercise.compliance_level) }}
              </span>
              {{ exercise.owner_name || exercise.owner_username || '未标记教师' }}
              {{ formatDate(exercise.updated_at) }}
            </small>
          </li>
        </ul>
        <p v-else class="empty-state">暂无习题记录，可以生成一组课堂练习。</p>
      </section>
    </div>

    <section class="panel stack">
      <h2>常用入口</h2>
      <div class="quick-grid">
        <RouterLink to="/dashboard/materials">机构知识库</RouterLink>
        <RouterLink to="/dashboard/courses">课程体系</RouterLink>
        <RouterLink to="/dashboard/questions">题库管理</RouterLink>
        <RouterLink to="/dashboard/reviews">教研审核</RouterLink>
        <RouterLink to="/dashboard/compliance">合规检查</RouterLink>
      </div>
    </section>
  </section>
</template>

<style scoped>
.quick-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.quick-grid a {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  color: var(--brand-dark);
  background: var(--brand-soft);
  font-weight: 800;
  text-align: center;
  text-decoration: none;
}

small {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

@media (max-width: 980px) {
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>

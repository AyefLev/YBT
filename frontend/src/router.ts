import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type Router,
  type RouterHistory,
} from 'vue-router'

import WorkbenchLayout from './layouts/WorkbenchLayout.vue'
import AdminPage from './pages/AdminPage.vue'
import ClassroomsPage from './pages/ClassroomsPage.vue'
import CompliancePage from './pages/CompliancePage.vue'
import CoursesPage from './pages/CoursesPage.vue'
import DashboardPage from './pages/DashboardPage.vue'
import ExercisePage from './pages/ExercisePage.vue'
import LessonPage from './pages/LessonPage.vue'
import LoginPage from './pages/LoginPage.vue'
import MaterialsPage from './pages/MaterialsPage.vue'
import ObservabilityPage from './pages/ObservabilityPage.vue'
import QuestionBankPage from './pages/QuestionBankPage.vue'
import RegisterPage from './pages/RegisterPage.vue'
import ResourcesPage from './pages/ResourcesPage.vue'
import ReviewQueuePage from './pages/ReviewQueuePage.vue'
import SystemHealthPage from './pages/SystemHealthPage.vue'

import { TOKEN_KEY } from './api/client'

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: LoginPage },
  { path: '/register', component: RegisterPage },
  {
    path: '/dashboard',
    component: WorkbenchLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', component: DashboardPage },
      { path: 'lesson', component: LessonPage },
      { path: 'exercise', component: ExercisePage },
      { path: 'materials', component: MaterialsPage },
      { path: 'courses', component: CoursesPage },
      { path: 'classrooms', component: ClassroomsPage },
      { path: 'questions', component: QuestionBankPage },
      { path: 'reviews', component: ReviewQueuePage },
      { path: 'compliance', component: CompliancePage },
      { path: 'observability', component: ObservabilityPage },
      { path: 'health', component: SystemHealthPage },
      { path: 'resources', component: ResourcesPage },
      { path: 'admin', component: AdminPage },
    ],
  },
]

function createDefaultHistory(): RouterHistory {
  return typeof window === 'undefined' ? createMemoryHistory() : createWebHistory()
}

export function createAppRouter(history: RouterHistory = createDefaultHistory()): Router {
  const router = createRouter({
    history,
    routes,
  })

  router.beforeEach((to) => {
    if (to.matched.some((route) => route.meta.requiresAuth) && !localStorage.getItem(TOKEN_KEY)) {
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      }
    }
  })

  return router
}

export default createAppRouter()

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

import { getAuthToken } from './api/client'
import { useAuthStore } from './stores/auth'

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
      { path: 'lesson', component: LessonPage, meta: { permissions: ['lesson:create', 'lesson:view_all'], blockedRoles: ['admin'], pageMode: 'generate' } },
      { path: 'lesson/generate', component: LessonPage, meta: { permissions: ['lesson:create'], blockedRoles: ['admin'], pageMode: 'generate' } },
      { path: 'lesson/records', component: LessonPage, meta: { permissions: ['lesson:create', 'lesson:view_all'], blockedRoles: ['admin'], pageMode: 'records' } },
      { path: 'exercise', component: ExercisePage, meta: { permissions: ['exercise:create', 'exercise:view_all'], blockedRoles: ['admin'], pageMode: 'generate' } },
      { path: 'exercise/generate', component: ExercisePage, meta: { permissions: ['exercise:create'], blockedRoles: ['admin'], pageMode: 'generate' } },
      { path: 'exercise/records', component: ExercisePage, meta: { permissions: ['exercise:create', 'exercise:view_all'], blockedRoles: ['admin'], pageMode: 'records' } },
      { path: 'materials', component: MaterialsPage, meta: { permissions: ['material:upload', 'material:view_all', 'material:view_public'], blockedRoles: ['admin'], pageMode: 'library' } },
      { path: 'materials/upload', component: MaterialsPage, meta: { permissions: ['material:upload'], blockedRoles: ['admin'], pageMode: 'upload' } },
      { path: 'materials/library', component: MaterialsPage, meta: { permissions: ['material:upload', 'material:view_all', 'material:view_public'], blockedRoles: ['admin'], pageMode: 'library' } },
      { path: 'courses', component: CoursesPage, meta: { permissions: ['course:create', 'course:view_all'], blockedRoles: ['admin'] } },
      { path: 'classrooms', component: ClassroomsPage, meta: { permissions: ['class:manage', 'class:join', 'class:view_all'], blockedRoles: ['admin'] } },
      { path: 'questions', component: QuestionBankPage, meta: { permissions: ['exercise:create', 'question:view_all'], blockedRoles: ['admin'] } },
      { path: 'reviews', component: ReviewQueuePage, meta: { permissions: ['review:manage'], blockedRoles: ['admin'] } },
      { path: 'compliance', component: CompliancePage, meta: { permissions: ['review:manage'], blockedRoles: ['admin'] } },
      { path: 'observability', component: ObservabilityPage, meta: { permissions: ['log:view'], pageMode: 'overview' } },
      { path: 'observability/token', component: ObservabilityPage, meta: { permissions: ['log:view'], pageMode: 'token' } },
      { path: 'health', component: SystemHealthPage, meta: { permissions: ['log:view'] } },
      { path: 'resources', component: ResourcesPage, meta: { permissions: ['lesson:create', 'exercise:create', 'material:upload', 'material:view_public', 'course:create', 'question:view_all'], blockedRoles: ['admin'] } },
      { path: 'admin', component: AdminPage, meta: { permissions: ['admin:user_manage'], pageMode: 'users' } },
      { path: 'admin/users', component: AdminPage, meta: { permissions: ['admin:user_manage'], pageMode: 'users' } },
      { path: 'admin/api', component: AdminPage, meta: { permissions: ['admin:content_manage'], pageMode: 'api' } },
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

  router.beforeEach(async (to) => {
    const requiresAuth = to.matched.some((route) => route.meta.requiresAuth)
    if (requiresAuth && !getAuthToken()) {
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      }
    }

    if (!requiresAuth) return undefined

    const auth = useAuthStore()
    if (!auth.user) {
      try {
        await auth.loadMe()
      } catch {
        return {
          path: '/login',
          query: { redirect: to.fullPath },
        }
      }
    }

    const requiredPermissions = to.matched.flatMap((route) => {
      const permissions = route.meta.permissions
      return Array.isArray(permissions) ? permissions.map(String) : []
    })
    if (
      requiredPermissions.length &&
      !requiredPermissions.some((permission) => auth.user?.permissions.includes(permission))
    ) {
      return { path: '/dashboard' }
    }
    const blockedRoles = to.matched.flatMap((route) => {
      const roles = route.meta.blockedRoles
      return Array.isArray(roles) ? roles.map(String) : []
    })
    if (blockedRoles.some((role) => auth.user?.roles.includes(role))) {
      return { path: '/dashboard' }
    }
    return undefined
  })

  return router
}

export default createAppRouter()

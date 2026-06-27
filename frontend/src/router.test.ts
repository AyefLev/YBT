import { createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, test, vi } from 'vitest'

import { TOKEN_KEY } from './api/client'
import { createAppRouter } from './router'

describe('router auth guard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('localStorage', createStorage())
    vi.stubGlobal('sessionStorage', createStorage())
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  test('redirects dashboard navigation without token to login with redirect query', async () => {
    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query).toEqual({ redirect: '/dashboard' })
  })

  test('allows dashboard navigation with token', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'valid-token')
    stubCurrentUser()
    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard')

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  test('registers protected workbench child routes under dashboard', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'valid-token')
    stubCurrentUser()
    const router = createAppRouter(createMemoryHistory())

    const dashboardRoutes = router.getRoutes().filter((route) => route.path === '/dashboard')
    expect(dashboardRoutes.some((route) => route.meta.requiresAuth)).toBe(true)

    for (const path of [
      '/dashboard',
      '/dashboard/lesson',
      '/dashboard/lesson/generate',
      '/dashboard/lesson/records',
      '/dashboard/exercise',
      '/dashboard/exercise/generate',
      '/dashboard/exercise/records',
      '/dashboard/materials',
      '/dashboard/materials/upload',
      '/dashboard/materials/library',
      '/dashboard/courses',
      '/dashboard/classrooms',
      '/dashboard/questions',
      '/dashboard/reviews',
      '/dashboard/compliance',
      '/dashboard/observability',
      '/dashboard/observability/token',
      '/dashboard/health',
      '/dashboard/resources',
      '/dashboard/admin',
      '/dashboard/admin/users',
      '/dashboard/admin/api',
    ]) {
      await router.push(path)
      expect(router.currentRoute.value.path).toBe(path)
      expect(router.currentRoute.value.matched.length).toBeGreaterThan(0)
    }
  })
})

function stubCurrentUser() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      Response.json({
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        display_name: '管理员',
        is_active: true,
        requested_role: 'admin',
        account_status: 'approved',
        review_note: '',
        reviewed_by_id: null,
        reviewed_at: null,
        roles: ['admin'],
        permissions: [
          'lesson:create',
          'lesson:view_all',
          'exercise:create',
          'exercise:view_all',
          'material:upload',
          'material:view_all',
          'material:view_public',
          'course:create',
          'course:view_all',
          'class:manage',
          'class:join',
          'class:view_all',
          'question:view_all',
          'review:manage',
          'log:view',
          'admin:user_manage',
          'admin:content_manage',
        ],
      }),
    ),
  )
}

function createStorage(): Storage {
  const store = new Map<string, string>()
  return {
    get length() {
      return store.size
    },
    clear: () => store.clear(),
    getItem: (key: string) => store.get(key) ?? null,
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key)
    },
    setItem: (key: string, value: string) => {
      store.set(key, value)
    },
  }
}

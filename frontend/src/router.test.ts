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
      expect(router.resolve(path).matched.length).toBeGreaterThan(0)
    }
  })

  test('blocks system admins from teaching routes even with stale teaching permissions', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'valid-token')
    stubCurrentUser({
      roles: ['admin'],
      permissions: [
        'lesson:create',
        'exercise:create',
        'material:upload',
        'course:create',
        'class:manage',
        'review:manage',
        'log:view',
        'admin:user_manage',
        'admin:content_manage',
      ],
    })
    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard/materials/upload')

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  test('allows system admins to access platform management routes', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'valid-token')
    stubCurrentUser({
      roles: ['admin'],
      permissions: ['log:view', 'admin:user_manage', 'admin:content_manage'],
    })
    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard/admin/api')

    expect(router.currentRoute.value.path).toBe('/dashboard/admin/api')
  })

  test('blocks teachers from compliance review routes', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'valid-token')
    stubCurrentUser({
      roles: ['teacher'],
      permissions: ['lesson:create', 'exercise:create', 'material:upload'],
    })
    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard/compliance')

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })
})

function stubCurrentUser(
  overrides: Partial<{
    roles: string[]
    permissions: string[]
  }> = {},
) {
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
        roles: overrides.roles ?? ['teacher'],
        permissions: overrides.permissions ?? ['lesson:create', 'exercise:create', 'material:upload'],
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

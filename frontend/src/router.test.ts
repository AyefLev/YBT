import { createMemoryHistory } from 'vue-router'
import { beforeEach, describe, expect, test, vi } from 'vitest'

import { TOKEN_KEY } from './api/client'
import { createAppRouter } from './router'

describe('router auth guard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('localStorage', createLocalStorage())
    localStorage.clear()
  })

  test('redirects dashboard navigation without token to login with redirect query', async () => {
    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query).toEqual({ redirect: '/dashboard' })
  })

  test('allows dashboard navigation with token', async () => {
    localStorage.setItem(TOKEN_KEY, 'valid-token')
    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard')

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  test('registers protected workbench child routes under dashboard', async () => {
    localStorage.setItem(TOKEN_KEY, 'valid-token')
    const router = createAppRouter(createMemoryHistory())

    const dashboardRoutes = router.getRoutes().filter((route) => route.path === '/dashboard')
    expect(dashboardRoutes.some((route) => route.meta.requiresAuth)).toBe(true)

    for (const path of [
      '/dashboard',
      '/dashboard/lesson',
      '/dashboard/exercise',
      '/dashboard/materials',
      '/dashboard/courses',
      '/dashboard/classrooms',
      '/dashboard/questions',
      '/dashboard/reviews',
      '/dashboard/compliance',
      '/dashboard/observability',
      '/dashboard/health',
      '/dashboard/resources',
      '/dashboard/admin',
    ]) {
      await router.push(path)
      expect(router.currentRoute.value.path).toBe(path)
      expect(router.currentRoute.value.matched.length).toBeGreaterThan(0)
    }
  })
})

function createLocalStorage(): Storage {
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

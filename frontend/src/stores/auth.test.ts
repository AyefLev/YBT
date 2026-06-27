import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, test, vi } from 'vitest'

import { TOKEN_KEY } from '../api/client'
import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('localStorage', createStorage())
    vi.stubGlobal('sessionStorage', createStorage())
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  test('rolls back token when current-user load fails after login', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          Response.json({
            access_token: 'bad-token',
            token_type: 'bearer',
          }),
        )
        .mockResolvedValueOnce(
          Response.json(
            { detail: 'invalid token' },
            {
              status: 401,
              statusText: 'Unauthorized',
            },
          ),
        ),
    )

    const auth = useAuthStore()

    await expect(auth.login({ username: 'teacher', password: 'secret-password' })).rejects.toThrow(
      'invalid token',
    )
    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
  })

  test('clears a stale session when loadMe fails', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'stale-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        Response.json(
          { detail: 'invalid token' },
          {
            status: 401,
            statusText: 'Unauthorized',
          },
        ),
      ),
    )

    const auth = useAuthStore()
    auth.token = 'stale-token'

    await expect(auth.loadMe()).rejects.toThrow('invalid token')
    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
  })
})

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

import { beforeEach, describe, expect, test, vi } from 'vitest'

import { ApiError, TOKEN_KEY, api, apiBlob, apiForm, downloadBlobResponse } from './client'

describe('api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('localStorage', createLocalStorage())
    localStorage.clear()
  })

  test('returns undefined for successful empty JSON responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(null, {
          status: 204,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    )

    await expect(api('/api/empty')).resolves.toBeUndefined()
  })

  test('throws ApiError with status text for non-OK empty responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('', {
          status: 401,
          statusText: 'Unauthorized',
          headers: { 'content-type': 'application/json' },
        }),
      ),
    )

    await expect(api('/api/protected')).rejects.toMatchObject({
      name: 'ApiError',
      status: 401,
      message: 'Unauthorized',
    })
  })

  test('apiForm sends multipart bodies with auth and without JSON content type', async () => {
    localStorage.setItem(TOKEN_KEY, 'valid-token')
    const form = new FormData()
    form.set('title', '教材')

    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        id: 1,
        title: '教材',
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiForm('/api/materials/upload', form)).resolves.toMatchObject({ id: 1 })

    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(options.body).toBe(form)
    const headers = options.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer valid-token')
    expect(headers.has('Content-Type')).toBe(false)
  })

  test('apiBlob returns attachment blob and filename from content disposition', async () => {
    localStorage.setItem(TOKEN_KEY, 'valid-token')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('docx-bytes', {
        status: 200,
        headers: {
          'content-disposition': 'attachment; filename="lesson.docx"',
          'content-type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiBlob('/api/exports/lesson/1/docx', { method: 'POST' })

    expect(result.filename).toBe('lesson.docx')
    await expect(result.blob.text()).resolves.toBe('docx-bytes')
    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).get('Authorization')).toBe('Bearer valid-token')
  })

  test('downloadBlobResponse creates a temporary download link and revokes object URL', () => {
    const link = {
      href: '',
      download: '',
      click: vi.fn(),
    } as unknown as HTMLAnchorElement
    const createElement = vi.fn().mockReturnValue(link)
    const createObjectURL = vi.fn().mockReturnValue('blob:download-url')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('document', { createElement })
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    vi.stubGlobal('window', {})
    vi.stubGlobal('setTimeout', (handler: TimerHandler) => {
      if (typeof handler === 'function') handler()
      return 1
    })

    downloadBlobResponse({ blob: new Blob(['docx-bytes']), filename: 'course.docx' }, 'fallback.docx')

    expect(createElement).toHaveBeenCalledWith('a')
    expect(link.href).toBe('blob:download-url')
    expect(link.download).toBe('course.docx')
    expect(link.click).toHaveBeenCalledOnce()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:download-url')
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

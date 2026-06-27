export type ApiOptions = RequestInit & {
  skipAuth?: boolean
}

export interface ApiBlobResponse {
  blob: Blob
  filename: string | null
}

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, message: string, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

const TOKEN_KEY = 'token'

function browserSessionStorage(): Storage | null {
  return typeof sessionStorage === 'undefined' ? null : sessionStorage
}

function browserLocalStorage(): Storage | null {
  return typeof localStorage === 'undefined' ? null : localStorage
}

export function getAuthToken(): string | null {
  return browserSessionStorage()?.getItem(TOKEN_KEY) ?? null
}

export function setAuthToken(token: string): void {
  browserSessionStorage()?.setItem(TOKEN_KEY, token)
  browserLocalStorage()?.removeItem(TOKEN_KEY)
}

export function clearAuthToken(): void {
  browserSessionStorage()?.removeItem(TOKEN_KEY)
  browserLocalStorage()?.removeItem(TOKEN_KEY)
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined
  }

  const text = await response.text()
  if (!text) {
    return undefined
  }

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return JSON.parse(text) as unknown
  }
  return text
}

function errorMessage(response: Response, body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    return typeof detail === 'string' ? detail : JSON.stringify(detail)
  }
  if (typeof body === 'string' && body.trim()) {
    return body
  }
  return response.statusText || '请求失败'
}

function requestHeaders(options: ApiOptions): Headers {
  const headers = new Headers(options.headers)

  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const token = getAuthToken()
  if (token && !options.skipAuth) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return headers
}

function filenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) {
    return null
  }

  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (encoded?.[1]) {
    return decodeURIComponent(encoded[1].replace(/"/g, ''))
  }

  const plain = disposition.match(/filename="?([^";]+)"?/i)
  return plain?.[1] ?? null
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = requestHeaders(options)

  const response = await fetch(path, {
    ...options,
    headers,
  })
  const body = await parseResponse(response)

  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(response, body), body)
  }

  return body as T
}

export function apiForm<T>(path: string, form: FormData, options: ApiOptions = {}): Promise<T> {
  return api<T>(path, {
    method: 'POST',
    ...options,
    body: form,
  })
}

export async function apiBlob(path: string, options: ApiOptions = {}): Promise<ApiBlobResponse> {
  const headers = requestHeaders(options)
  const response = await fetch(path, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const body = await parseResponse(response)
    throw new ApiError(response.status, errorMessage(response, body), body)
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get('content-disposition')),
  }
}

export function downloadBlobResponse(response: ApiBlobResponse, fallbackFilename: string): void {
  const url = URL.createObjectURL(response.blob)
  const link = document.createElement('a')
  link.href = url
  link.download = response.filename || fallbackFilename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

export { TOKEN_KEY }

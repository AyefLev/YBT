import { defineStore } from 'pinia'

import { TOKEN_KEY, api } from '../api/client'

export interface User {
  id: number
  username: string
  email: string
  display_name: string
  is_active: boolean
  requested_role: string
  account_status: string
  review_note: string
  reviewed_by_id: number | null
  reviewed_at: string | null
  roles: string[]
  permissions: string[]
}

interface TokenResponse {
  access_token: string
  token_type: string
}

interface LoginPayload {
  username: string
  password: string
}

interface RegisterPayload extends LoginPayload {
  email: string
  display_name: string
  role?: 'teacher' | 'student'
  apply_for_teacher_review?: boolean
  application_note?: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    token: localStorage.getItem(TOKEN_KEY),
    loading: false,
  }),
  actions: {
    clearSession() {
      this.user = null
      this.token = null
      localStorage.removeItem(TOKEN_KEY)
    },
    async loadMe() {
      try {
        this.user = await api<User>('/api/auth/me')
        return this.user
      } catch (error) {
        this.clearSession()
        throw error
      }
    },
    async login(payload: LoginPayload) {
      this.loading = true
      try {
        const token = await api<TokenResponse>('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify(payload),
          skipAuth: true,
        })
        this.token = token.access_token
        localStorage.setItem(TOKEN_KEY, token.access_token)
        try {
          await this.loadMe()
        } catch (error) {
          this.clearSession()
          throw error
        }
      } finally {
        this.loading = false
      }
    },
    async register(payload: RegisterPayload) {
      this.loading = true
      try {
        await api<User>('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify(payload),
          skipAuth: true,
        })
        await this.login({ username: payload.username, password: payload.password })
      } finally {
        this.loading = false
      }
    },
    logout() {
      this.clearSession()
    },
  },
})

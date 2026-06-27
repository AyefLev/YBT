<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login({ username: username.value, password: password.value })
    await router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败，请检查账号或稍后重试'
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card">
      <p class="eyebrow">研备通 AI</p>
      <h1>登录工作台</h1>
      <p class="intro">进入成人考研机构智能备课与教研辅助系统。</p>

      <form class="stack" @submit.prevent="submit">
        <label>
          用户名
          <input v-model.trim="username" autocomplete="username" required />
        </label>

        <label>
          密码
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>

        <p v-if="error" class="alert" role="alert">{{ error }}</p>

        <button class="btn-primary" type="submit" :disabled="auth.loading">
          {{ auth.loading ? '正在登录...' : '登录' }}
        </button>
      </form>

      <p class="switch">
        还没有账号？
        <RouterLink to="/register">注册账号</RouterLink>
      </p>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.14), transparent 42%),
    var(--bg);
}

.auth-card {
  width: min(100%, 430px);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 30px;
  background: var(--surface);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

h1 {
  margin: 0;
  font-size: 1.8rem;
}

.intro {
  margin: 10px 0 24px;
  color: var(--muted);
}

.switch {
  margin: 18px 0 0;
  color: var(--muted);
}

.switch a {
  color: var(--brand);
  font-weight: 800;
  text-decoration: none;
}
</style>

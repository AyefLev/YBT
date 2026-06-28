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
      <div class="brand-line">
        <span class="brand-mark">研</span>
        <div>
          <strong>研备通 AI</strong>
          <small>智能教研工作台</small>
        </div>
      </div>

      <div class="auth-heading">
        <p class="eyebrow">登录</p>
        <h1>进入工作台</h1>
        <p>统一管理课程、章节、知识库、教案、习题和 AI 生成链路。</p>
      </div>

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
    linear-gradient(180deg, rgba(37, 99, 235, 0.08), transparent 42%),
    var(--bg);
}

.auth-card {
  display: grid;
  width: min(100%, 430px);
  gap: 22px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 28px;
  background: var(--surface);
  box-shadow: var(--shadow-md);
}

.brand-line {
  display: flex;
  gap: 12px;
  align-items: center;
  border-bottom: 1px solid var(--line);
  padding-bottom: 18px;
}

.brand-mark {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 10px;
  color: #ffffff;
  background: var(--brand);
  font-weight: 900;
}

.brand-line div {
  display: grid;
  gap: 3px;
}

.brand-line strong {
  color: var(--text);
  font-weight: 850;
}

.brand-line small,
.auth-heading p,
.switch {
  color: var(--muted);
}

.auth-heading {
  display: grid;
  gap: 8px;
}

.auth-heading h1 {
  margin: 0;
  color: var(--text);
  font-size: 1.85rem;
  line-height: 1.15;
}

.auth-heading p {
  margin: 0;
  line-height: 1.65;
}

.switch {
  margin: 0;
}

.switch a {
  color: var(--brand-dark);
  font-weight: 850;
  text-decoration: none;
}

.switch a:hover {
  text-decoration: underline;
}
</style>

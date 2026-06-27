<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const displayName = ref('')
const password = ref('')
const role = ref<'teacher' | 'student'>('teacher')
const applyForTeacherReview = ref(false)
const applicationNote = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.register({
      username: username.value,
      email: email.value,
      display_name: displayName.value,
      password: password.value,
      role: role.value,
      apply_for_teacher_review: role.value === 'teacher' && applyForTeacherReview.value,
      application_note: applicationNote.value,
    })
    await router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '注册失败，请稍后重试'
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card">
      <p class="eyebrow">研备通 AI</p>
      <h1>注册账号</h1>
      <p class="intro">创建教师或学生账号后会自动登录工作台；教师也可以选择提交审核申请。</p>

      <form class="stack" @submit.prevent="submit">
        <label>
          用户名
          <input v-model.trim="username" autocomplete="username" required />
        </label>

        <label>
          邮箱
          <input v-model.trim="email" type="email" autocomplete="email" required />
        </label>

        <label>
          显示名称
          <input v-model.trim="displayName" autocomplete="name" required />
        </label>

        <label>
          密码
          <input v-model="password" type="password" autocomplete="new-password" minlength="8" required />
        </label>

        <label>
          账号类型
          <select v-model="role">
            <option value="teacher">教师</option>
            <option value="student">学生</option>
          </select>
        </label>

        <label v-if="role === 'teacher'" class="checkbox">
          <input v-model="applyForTeacherReview" type="checkbox" />
          作为教师申请提交管理员审核
        </label>

        <label v-if="role === 'teacher' && applyForTeacherReview">
          申请说明
          <textarea v-model.trim="applicationNote" rows="3" placeholder="例如：任教学科、所属机构、申请原因" />
        </label>

        <p v-if="error" class="alert" role="alert">{{ error }}</p>

        <button class="btn-primary" type="submit" :disabled="auth.loading">
          {{ auth.loading ? '正在注册...' : '注册并登录' }}
        </button>
      </form>

      <p class="switch">
        已有账号？
        <RouterLink to="/login">返回登录</RouterLink>
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
  width: min(100%, 470px);
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

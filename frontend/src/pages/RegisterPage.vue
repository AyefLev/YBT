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
      <div class="brand-line">
        <span class="brand-mark">研</span>
        <div>
          <strong>研备通 AI</strong>
          <small>智能教研工作台</small>
        </div>
      </div>

      <div class="auth-heading">
        <p class="eyebrow">注册</p>
        <h1>创建账号</h1>
        <p>教师账号可提交审核申请，审核通过后即可使用教案、习题、资料和班级教学能力。</p>
      </div>

      <form class="stack" @submit.prevent="submit">
        <div class="auth-grid">
          <label>
            用户名
            <input v-model.trim="username" autocomplete="username" required />
          </label>

          <label>
            邮箱
            <input v-model.trim="email" type="email" autocomplete="email" required />
          </label>
        </div>

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
    linear-gradient(180deg, rgba(37, 99, 235, 0.08), transparent 42%),
    var(--bg);
}

.auth-card {
  display: grid;
  width: min(100%, 520px);
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

.brand-line div,
.auth-heading {
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

.auth-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
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

@media (max-width: 620px) {
  .auth-grid {
    grid-template-columns: 1fr;
  }
}
</style>

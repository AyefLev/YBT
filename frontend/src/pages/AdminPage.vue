<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '../api/client'

interface RoleRead {
  id: number
  name: string
  permissions: string[]
}

interface AdminUser {
  id: number
  username: string
  email: string
  display_name: string
  is_active: boolean
  requested_role: string
  account_status: string
  review_note: string
  roles: string[]
  permissions: string[]
}

interface AIProviderConfig {
  role: string
  base_url: string
  model: string
  enabled: boolean
  api_key_configured: boolean
  api_key_preview: string
  updated_at: string | null
}

const roles = ref<RoleRead[]>([])
const users = ref<AdminUser[]>([])
const applications = ref<AdminUser[]>([])
const modelConfigs = ref<AIProviderConfig[]>([])
const modelApiKeys = ref<Record<string, string>>({})
const loading = ref('')
const error = ref('')
const notice = ref('')

const username = ref('')
const email = ref('')
const displayName = ref('')
const password = ref('')
const selectedRoles = ref('student')

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

function roleText(user: AdminUser): string {
  return user.roles.join(' / ') || '未分配'
}

function statusText(status: string): string {
  const labels: Record<string, string> = {
    approved: '已通过',
    pending: '待审核',
    rejected: '已拒绝',
  }
  return labels[status] ?? status
}

function roleList(): string[] {
  return selectedRoles.value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

async function loadAdminData() {
  loading.value = 'load'
  error.value = ''
  try {
    const [roleResult, userResult, applicationResult, modelConfigResult] = await Promise.all([
      api<RoleRead[]>('/api/admin/roles'),
      api<AdminUser[]>('/api/admin/users'),
      api<AdminUser[]>('/api/admin/teacher-applications'),
      api<AIProviderConfig[]>('/api/ai/admin/provider-configs'),
    ])
    roles.value = roleResult
    users.value = userResult
    applications.value = applicationResult
    modelConfigs.value = modelConfigResult
  } catch (err) {
    setError(err, '系统管理数据加载失败')
  } finally {
    loading.value = ''
  }
}

async function loadModelConfigs() {
  modelConfigs.value = await api<AIProviderConfig[]>('/api/ai/admin/provider-configs')
}

async function saveModelConfig(config: AIProviderConfig) {
  loading.value = `model-${config.role}`
  error.value = ''
  try {
    const apiKey = modelApiKeys.value[config.role] || ''
    const updated = await api<AIProviderConfig>(`/api/ai/admin/provider-configs/${config.role}`, {
      method: 'PATCH',
      body: JSON.stringify({
        base_url: config.base_url,
        model: config.model,
        enabled: config.enabled,
        api_key: apiKey || undefined,
      }),
    })
    modelConfigs.value = modelConfigs.value.map((item) =>
      item.role === updated.role ? updated : item,
    )
    modelApiKeys.value = { ...modelApiKeys.value, [config.role]: '' }
    notice.value = '模型配置已保存。'
  } catch (err) {
    setError(err, '保存模型配置失败')
  } finally {
    loading.value = ''
  }
}

function modelRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    generate: '生成模型',
    review: '审核模型',
    revise: '修订模型',
    vision: '视觉模型',
  }
  return labels[role] ?? role
}

async function createUser() {
  loading.value = 'create'
  error.value = ''
  notice.value = ''
  try {
    await api<AdminUser>('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify({
        username: username.value,
        email: email.value,
        password: password.value,
        display_name: displayName.value,
        roles: roleList(),
        requested_role: roleList().includes('teacher') ? 'teacher' : 'student',
      }),
    })
    username.value = ''
    email.value = ''
    displayName.value = ''
    password.value = ''
    selectedRoles.value = 'student'
    notice.value = '用户已创建。'
    await loadAdminData()
  } catch (err) {
    setError(err, '创建用户失败')
  } finally {
    loading.value = ''
  }
}

async function saveRoles(user: AdminUser) {
  loading.value = `roles-${user.id}`
  error.value = ''
  try {
    await api<AdminUser>(`/api/admin/users/${user.id}/roles`, {
      method: 'POST',
      body: JSON.stringify({ roles: user.roles }),
    })
    notice.value = '角色已保存。'
    await loadAdminData()
  } catch (err) {
    setError(err, '保存角色失败')
  } finally {
    loading.value = ''
  }
}

async function toggleActive(user: AdminUser) {
  loading.value = `active-${user.id}`
  error.value = ''
  try {
    await api<AdminUser>(`/api/admin/users/${user.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: !user.is_active }),
    })
    notice.value = user.is_active ? '用户已停用。' : '用户已启用。'
    await loadAdminData()
  } catch (err) {
    setError(err, '更新用户状态失败')
  } finally {
    loading.value = ''
  }
}

async function approveTeacher(user: AdminUser) {
  loading.value = `approve-${user.id}`
  error.value = ''
  try {
    await api<AdminUser>(`/api/admin/teacher-applications/${user.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note: '管理员审核通过' }),
    })
    notice.value = '教师申请已通过。'
    await loadAdminData()
  } catch (err) {
    setError(err, '审批失败')
  } finally {
    loading.value = ''
  }
}

async function rejectTeacher(user: AdminUser) {
  loading.value = `reject-${user.id}`
  error.value = ''
  try {
    await api<AdminUser>(`/api/admin/teacher-applications/${user.id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note: '管理员审核未通过' }),
    })
    notice.value = '教师申请已拒绝。'
    await loadAdminData()
  } catch (err) {
    setError(err, '拒绝申请失败')
  } finally {
    loading.value = ''
  }
}

onMounted(loadAdminData)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">管理</p>
        <h1>系统管理</h1>
        <p>管理员可以管理账号、角色、教师申请和全局教学资源；教师与学生的数据访问由后端权限控制。</p>
      </div>
      <div class="hero-actions">
        <button type="button" class="btn-secondary" :disabled="loading === 'load'" @click="loadAdminData">
          刷新
        </button>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <section class="panel stack">
      <h2>教师申请</h2>
      <p v-if="!applications.length" class="empty-state">暂无待审核教师申请。</p>
      <ul v-else class="clean-list">
        <li v-for="user in applications" :key="user.id">
          <div class="user-row">
            <div>
              <strong>{{ user.display_name }}</strong>
              <small>{{ user.username }} · {{ user.email }} · {{ user.review_note || '无申请说明' }}</small>
            </div>
            <div class="actions">
              <button type="button" class="btn-primary" @click="approveTeacher(user)">通过</button>
              <button type="button" class="btn-danger" @click="rejectTeacher(user)">拒绝</button>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <div class="two-column-grid">
      <form class="panel stack" @submit.prevent="createUser">
        <h2>创建用户</h2>
        <label>
          用户名
          <input v-model.trim="username" required />
        </label>
        <label>
          邮箱
          <input v-model.trim="email" type="email" required />
        </label>
        <label>
          显示名称
          <input v-model.trim="displayName" required />
        </label>
        <label>
          初始密码
          <input v-model="password" type="password" minlength="8" required />
        </label>
        <label>
          角色
          <select v-model="selectedRoles">
            <option value="student">学生</option>
            <option value="teacher">教师</option>
            <option value="teaching_manager">教研管理员</option>
            <option value="admin">管理员</option>
          </select>
        </label>
        <button class="btn-primary" type="submit" :disabled="loading === 'create'">
          {{ loading === 'create' ? '创建中...' : '创建用户' }}
        </button>
      </form>

      <section class="panel stack">
        <h2>角色权限</h2>
        <ul class="clean-list">
          <li v-for="role in roles" :key="role.id">
            <strong>{{ role.name }}</strong>
            <small>{{ role.permissions.join(' / ') || '无权限' }}</small>
          </li>
        </ul>
      </section>
    </div>

    <section class="panel stack">
      <div class="panel-title">
        <h2>模型 API 配置</h2>
        <small>生成 / 审核 / 修订 / 视觉</small>
      </div>
      <p v-if="!modelConfigs.length" class="empty-state">暂无模型配置。</p>
      <ul v-else class="model-config-list">
        <li v-for="config in modelConfigs" :key="config.role">
          <div>
            <strong>{{ modelRoleLabel(config.role) }}</strong>
            <small>
              {{ config.api_key_configured ? `密钥：${config.api_key_preview}` : '未配置密钥' }}
              · {{ config.enabled ? '已启用' : '已停用' }}
            </small>
          </div>
          <label>
            Base URL
            <input v-model.trim="config.base_url" placeholder="https://api.example.com/v1" />
          </label>
          <label>
            模型
            <input v-model.trim="config.model" placeholder="model-name" />
          </label>
          <label>
            新 API Key
            <input v-model.trim="modelApiKeys[config.role]" type="password" placeholder="留空则不修改" />
          </label>
          <label class="checkbox">
            <input v-model="config.enabled" type="checkbox" />
            启用
          </label>
          <button type="button" class="btn-secondary" @click="saveModelConfig(config)">保存</button>
        </li>
      </ul>
    </section>

    <section class="panel stack">
      <div class="panel-title">
        <h2>用户数据库</h2>
        <small>{{ users.length }} 个账号</small>
      </div>
      <p v-if="!users.length" class="empty-state">暂无用户。</p>
      <ul v-else class="clean-list">
        <li v-for="user in users" :key="user.id">
          <div class="user-row">
            <div>
              <strong>{{ user.display_name }}</strong>
              <small>
                {{ user.username }} · {{ user.email }} · {{ roleText(user) }}
                <span class="status-pill" :class="user.account_status">{{ statusText(user.account_status) }}</span>
                <span class="status-pill" :class="user.is_active ? 'success' : 'danger'">
                  {{ user.is_active ? '启用' : '停用' }}
                </span>
              </small>
            </div>
            <div class="role-editor">
              <select v-model="user.roles" multiple>
                <option v-for="role in roles" :key="role.id" :value="role.name">
                  {{ role.name }}
                </option>
              </select>
              <button type="button" class="btn-secondary" @click="saveRoles(user)">保存角色</button>
              <button type="button" class="btn-danger" @click="toggleActive(user)">
                {{ user.is_active ? '停用' : '启用' }}
              </button>
            </div>
          </div>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.user-row {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  justify-content: space-between;
}

.user-row > div:first-child {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.role-editor {
  display: grid;
  min-width: 260px;
  grid-template-columns: minmax(120px, 1fr) auto auto;
  gap: 8px;
  align-items: center;
}

.role-editor select {
  min-height: 76px;
}

.model-config-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.model-config-list li {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) repeat(3, minmax(140px, 1fr)) auto auto;
  gap: 10px;
  align-items: end;
  border-bottom: 1px solid var(--line);
  padding-bottom: 12px;
}

.model-config-list li:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

@media (max-width: 900px) {
  .user-row,
  .role-editor,
  .model-config-list li {
    display: grid;
    grid-template-columns: 1fr;
    min-width: 0;
  }
}
</style>

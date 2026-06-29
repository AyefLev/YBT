<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

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
  prompt_price_per_1k: number
  completion_price_per_1k: number
  currency: string
  enabled: boolean
  api_key_configured: boolean
  api_key_preview: string
  updated_at: string | null
}

const roles = ref<RoleRead[]>([])
const route = useRoute()
const users = ref<AdminUser[]>([])
const applications = ref<AdminUser[]>([])
const modelConfigs = ref<AIProviderConfig[]>([])
const modelApiKeys = ref<Record<string, string>>({})
const loading = ref('')
const error = ref('')
const notice = ref('')
const userSearch = ref('')
const editingUserId = ref<number | null>(null)

const username = ref('')
const email = ref('')
const displayName = ref('')
const password = ref('')
const selectedRoles = ref('student')
const pageMode = computed(() => String(route.meta.pageMode || 'users'))
const showUsersPage = computed(() => pageMode.value === 'users')
const showApiPage = computed(() => pageMode.value === 'api')
const filteredUsers = computed(() => {
  const keyword = userSearch.value.trim().toLowerCase()
  if (!keyword) return users.value
  return users.value.filter((user) =>
    [
      user.display_name,
      user.username,
      user.email,
      user.requested_role,
      user.account_status,
      ...user.roles,
    ]
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
})

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

function roleText(user: AdminUser): string {
  return user.roles.join(' / ') || '未分配'
}

function roleLabel(role: string): string {
  const labels: Record<string, string> = {
    admin: '管理员',
    teaching_manager: '教研管理员',
    teacher: '教师',
    student: '学生',
    pending_teacher: '待审核教师',
    operator: '运维',
  }
  return labels[role] ?? role
}

function roleClass(role: string): string {
  if (role === 'admin') return 'admin'
  if (role === 'teaching_manager') return 'manager'
  if (role === 'teacher' || role === 'pending_teacher') return 'teacher'
  if (role === 'student') return 'student'
  return ''
}

function statusText(status: string): string {
  const labels: Record<string, string> = {
    approved: '已通过',
    pending: '待审核',
    rejected: '已拒绝',
  }
  return labels[status] ?? status
}

function userInitial(user: AdminUser): string {
  const value = user.display_name || user.username || user.email
  return value.slice(0, 1).toUpperCase()
}

function toggleRoleEditor(user: AdminUser) {
  editingUserId.value = editingUserId.value === user.id ? null : user.id
}

function toggleRoleAssignment(user: AdminUser, roleName: string, checked: boolean) {
  const current = new Set(user.roles)
  if (checked) {
    current.add(roleName)
  } else {
    current.delete(roleName)
  }
  user.roles = Array.from(current)
}

function toggleRoleAssignmentFromEvent(user: AdminUser, roleName: string, event: Event) {
  const input = event.target as HTMLInputElement
  toggleRoleAssignment(user, roleName, input.checked)
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
        prompt_price_per_1k: config.prompt_price_per_1k,
        completion_price_per_1k: config.completion_price_per_1k,
        currency: config.currency,
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

async function saveAndEnableModelConfig(config: AIProviderConfig) {
  config.enabled = true
  await saveModelConfig(config)
}

async function disableModelConfig(config: AIProviderConfig) {
  config.enabled = false
  await saveModelConfig(config)
}

function modelConfigStatusText(config: AIProviderConfig): string {
  if (config.enabled) return '正在用于系统调用'
  if (config.api_key_configured || modelApiKeys.value[config.role]) return '已保存但未启用'
  return '未配置'
}

function modelConfigStatusClass(config: AIProviderConfig): string {
  if (config.enabled) return 'success'
  if (config.api_key_configured || modelApiKeys.value[config.role]) return 'warning'
  return 'danger'
}

function modelRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    generate: '生成模型',
    review: '审核模型',
    revise: '修订模型',
    vision: '视觉模型',
    embedding: '向量模型',
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
    editingUserId.value = null
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
        <h1>{{ showApiPage ? 'API 管理' : '用户管理' }}</h1>
        <p>{{ showApiPage ? '维护生成、审核、视觉和向量模型 API，并配置费用估算参数。' : '管理账号、角色和教师申请；教师与学生的数据访问由后端权限控制。' }}</p>
      </div>
      <div class="hero-actions">
        <button type="button" class="btn-secondary" :disabled="loading === 'load'" @click="loadAdminData">
          刷新
        </button>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <section v-if="showUsersPage" class="panel stack">
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

    <div v-if="showUsersPage" class="two-column-grid">
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

    <section v-if="showApiPage" class="panel stack">
      <div class="panel-title">
        <h2>模型 API 配置</h2>
        <small>只有“正在用于系统调用”的配置会覆盖 .env；未启用时系统健康检查会显示 .env 中的模型。</small>
      </div>
      <p v-if="!modelConfigs.length" class="empty-state">暂无模型配置。</p>
      <ul v-else class="model-config-list">
        <li v-for="config in modelConfigs" :key="config.role">
          <div class="model-config-heading">
            <strong>{{ modelRoleLabel(config.role) }}</strong>
            <span class="status-pill" :class="modelConfigStatusClass(config)">
              {{ modelConfigStatusText(config) }}
            </span>
            <small>
              {{ config.api_key_configured ? `密钥：${config.api_key_preview}` : '未配置密钥' }}
              · {{ config.enabled ? '系统会使用此配置' : '当前会回退到环境变量配置' }}
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
            输入单价/千token
            <input v-model.number="config.prompt_price_per_1k" type="number" min="0" step="0.0001" />
          </label>
          <label>
            输出单价/千token
            <input v-model.number="config.completion_price_per_1k" type="number" min="0" step="0.0001" />
          </label>
          <label>
            币种
            <input v-model.trim="config.currency" placeholder="CNY" />
          </label>
          <label>
            新 API Key
            <input v-model.trim="modelApiKeys[config.role]" type="password" placeholder="留空则不修改" />
          </label>
          <label class="checkbox activation-toggle">
            <input v-model="config.enabled" type="checkbox" />
            用于系统调用
          </label>
          <div class="model-config-actions">
            <button type="button" class="btn-primary" @click="saveAndEnableModelConfig(config)">
              保存并启用
            </button>
            <button type="button" class="btn-secondary" @click="saveModelConfig(config)">
              仅保存
            </button>
            <button v-if="config.enabled" type="button" class="btn-danger" @click="disableModelConfig(config)">
              停用
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="showUsersPage" class="panel stack">
      <div class="panel-title">
        <h2>用户数据库</h2>
        <small>{{ filteredUsers.length }} / {{ users.length }} 个账号</small>
      </div>
      <div class="user-toolbar">
        <label>
          搜索用户
          <input v-model.trim="userSearch" placeholder="用户名、邮箱、角色或状态" />
        </label>
      </div>
      <p v-if="!filteredUsers.length" class="empty-state">暂无匹配用户。</p>
      <div v-else class="user-table-wrap">
        <table class="user-table">
          <thead>
            <tr>
              <th>用户</th>
              <th>ID</th>
              <th>角色</th>
              <th>账号状态</th>
              <th>申请类型</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="user in filteredUsers" :key="user.id">
              <tr>
                <td>
                  <div class="user-identity">
                    <span class="user-avatar">{{ userInitial(user) }}</span>
                    <div>
                      <strong>{{ user.display_name }}</strong>
                      <small>{{ user.username }} · {{ user.email }}</small>
                    </div>
                  </div>
                </td>
                <td>{{ user.id }}</td>
                <td>
                  <div class="role-pills" :title="roleText(user)">
                    <span v-for="role in user.roles" :key="role" class="role-pill" :class="roleClass(role)">
                      {{ roleLabel(role) }}
                    </span>
                    <span v-if="!user.roles.length" class="role-pill">未分配</span>
                  </div>
                </td>
                <td>
                  <div class="status-cell">
                    <span class="status-dot" :class="{ off: !user.is_active }" />
                    <span>{{ user.is_active ? '启用' : '停用' }}</span>
                    <span class="status-pill" :class="user.account_status">{{ statusText(user.account_status) }}</span>
                  </div>
                </td>
                <td>{{ roleLabel(user.requested_role) }}</td>
                <td>
                  <div class="user-actions">
                    <button type="button" class="btn-secondary compact-button" @click="toggleRoleEditor(user)">
                      {{ editingUserId === user.id ? '收起' : '角色' }}
                    </button>
                    <button
                      type="button"
                      class="compact-button"
                      :class="user.is_active ? 'btn-danger' : 'btn-secondary'"
                      @click="toggleActive(user)"
                    >
                      {{ user.is_active ? '停用' : '启用' }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="editingUserId === user.id" class="role-edit-row">
                <td colspan="6">
                  <div class="inline-role-editor">
                    <div>
                      <strong>编辑角色</strong>
                      <small>{{ user.username }} 当前角色：{{ roleText(user) }}</small>
                    </div>
                    <div class="role-checkbox-grid">
                      <label v-for="role in roles" :key="role.id" class="role-checkbox">
                        <input
                          type="checkbox"
                          :checked="user.roles.includes(role.name)"
                          @change="toggleRoleAssignmentFromEvent(user, role.name, $event)"
                        />
                        <span>{{ roleLabel(role.name) }}</span>
                        <small>{{ role.name }}</small>
                      </label>
                    </div>
                    <div class="inline-role-actions">
                      <button type="button" class="btn-primary" :disabled="loading === `roles-${user.id}`" @click="saveRoles(user)">
                        {{ loading === `roles-${user.id}` ? '保存中...' : '保存角色' }}
                      </button>
                      <button type="button" class="btn-secondary" @click="editingUserId = null">
                        取消
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
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

.user-toolbar {
  display: grid;
  max-width: 360px;
}

.user-table-wrap {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.user-table {
  width: 100%;
  min-width: 860px;
  border-collapse: collapse;
  background: #ffffff;
}

.user-table th,
.user-table td {
  border-bottom: 1px solid var(--line);
  padding: 12px 14px;
  text-align: left;
  vertical-align: middle;
}

.user-table th {
  color: var(--muted);
  background: var(--surface-soft);
  font-size: 0.88rem;
  font-weight: 900;
}

.user-table tr:last-child td {
  border-bottom: 0;
}

.user-identity {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.user-avatar {
  display: inline-grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  color: var(--brand-ink);
  background: var(--brand-soft);
  font-weight: 900;
}

.user-identity div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.user-identity strong,
.user-identity small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-pills,
.status-cell,
.user-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
}

.role-pill {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  color: #334155;
  background: #e2e8f0;
  font-size: 0.78rem;
  font-weight: 850;
  line-height: 1.2;
}

.role-pill.admin {
  color: #5b21b6;
  background: #ede9fe;
}

.role-pill.manager {
  color: #0f766e;
  background: #ccfbf1;
}

.role-pill.teacher {
  color: #1d4ed8;
  background: #dbeafe;
}

.role-pill.student {
  color: #166534;
  background: #dcfce7;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
}

.status-dot.off {
  background: #ef4444;
}

.compact-button {
  min-height: 34px;
  padding: 7px 10px;
  white-space: nowrap;
}

.role-edit-row td {
  background: var(--surface-soft);
}

.inline-role-editor {
  display: grid;
  gap: 12px;
}

.inline-role-editor > div:first-child {
  display: grid;
  gap: 4px;
}

.role-checkbox-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.role-checkbox {
  display: grid;
  grid-template-columns: auto minmax(0, 0.45fr) minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 10px;
  background: #ffffff;
}

.role-checkbox input {
  width: auto;
}

.role-checkbox span,
.role-checkbox small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inline-role-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
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
  grid-template-columns: minmax(180px, 0.75fr) repeat(3, minmax(150px, 1fr));
  gap: 12px;
  align-items: start;
  border-bottom: 1px solid var(--line);
  padding-bottom: 16px;
}

.model-config-list li:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.model-config-heading {
  display: grid;
  gap: 7px;
  align-content: start;
}

.model-config-heading .status-pill {
  justify-self: start;
}

.activation-toggle {
  align-self: end;
  min-height: 42px;
}

.model-config-actions {
  display: flex;
  grid-column: 1 / -1;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  border-top: 1px dashed var(--line);
  padding-top: 10px;
}

@media (max-width: 900px) {
  .user-row,
  .role-editor,
  .model-config-list li {
    display: grid;
    grid-template-columns: 1fr;
    min-width: 0;
  }

  .role-checkbox-grid {
    grid-template-columns: 1fr;
  }
}
</style>

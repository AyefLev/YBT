<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const SIDEBAR_COLLAPSED_KEY = 'workbench-sidebar-collapsed'
const sidebarCollapsed = ref(
  typeof localStorage !== 'undefined' && localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true',
)
const collapsedGroups = ref<Set<string>>(new Set())

const userName = computed(() => auth.user?.display_name || auth.user?.username || '用户')

const userRoleText = computed(() => {
  if (auth.user?.roles.includes('admin')) return '管理员'
  if (auth.user?.roles.includes('teaching_manager')) return '教管'
  if (auth.user?.roles.includes('student')) return '学生'
  if (auth.user?.account_status === 'pending') return '待审核教师'
  return '教师'
})

function hasPermission(permission: string): boolean {
  return auth.user?.permissions.includes(permission) ?? false
}

function hasAnyPermission(...permissions: string[]): boolean {
  return permissions.some((permission) => hasPermission(permission))
}

interface NavChild {
  label: string
  to: string
  show: boolean
}

interface NavGroup {
  label: string
  to?: string
  show: boolean
  children?: NavChild[]
}

const navGroups = computed<NavGroup[]>(() =>
  [
    { label: '工作台', to: '/dashboard', show: true },
    {
      label: '教案',
      show: hasAnyPermission('lesson:create', 'lesson:view_all'),
      children: [
        { label: '生成教案', to: '/dashboard/lesson/generate', show: hasPermission('lesson:create') },
        { label: '已有教案', to: '/dashboard/lesson/records', show: hasAnyPermission('lesson:create', 'lesson:view_all') },
      ],
    },
    {
      label: '练习题',
      show: hasAnyPermission('exercise:create', 'exercise:view_all'),
      children: [
        { label: '生成练习', to: '/dashboard/exercise/generate', show: hasPermission('exercise:create') },
        { label: '已有练习', to: '/dashboard/exercise/records', show: hasAnyPermission('exercise:create', 'exercise:view_all') },
        { label: '题库管理', to: '/dashboard/questions', show: hasAnyPermission('exercise:create', 'question:view_all') },
      ],
    },
    {
      label: '资料课程',
      show: hasAnyPermission('material:upload', 'material:view_all', 'material:view_public', 'course:create', 'course:view_all'),
      children: [
        { label: '资料列表', to: '/dashboard/materials/library', show: hasAnyPermission('material:upload', 'material:view_all', 'material:view_public') },
        { label: '上传资料', to: '/dashboard/materials/upload', show: hasPermission('material:upload') },
        { label: '课程体系', to: '/dashboard/courses', show: hasAnyPermission('course:create', 'course:view_all') },
      ],
    },
    {
      label: '班级教学',
      show: hasAnyPermission('class:manage', 'class:join', 'class:view_all'),
      children: [
        { label: '班级与作业', to: '/dashboard/classrooms', show: hasAnyPermission('class:manage', 'class:join', 'class:view_all') },
      ],
    },
    {
      label: '审核运维',
      show: hasAnyPermission('review:manage', 'lesson:create', 'log:view'),
      children: [
        { label: '教研审核', to: '/dashboard/reviews', show: hasPermission('review:manage') },
        { label: '内容检查', to: '/dashboard/compliance', show: hasPermission('lesson:create') },
        { label: '运行总览', to: '/dashboard/observability', show: hasPermission('log:view') },
        { label: 'Token 与费用', to: '/dashboard/observability/token', show: hasPermission('log:view') },
        { label: '系统检查', to: '/dashboard/health', show: hasPermission('log:view') },
      ],
    },
    {
      label: '系统管理',
      show: hasAnyPermission('admin:user_manage', 'admin:content_manage'),
      children: [
        { label: '用户管理', to: '/dashboard/admin/users', show: hasPermission('admin:user_manage') },
        { label: 'API 管理', to: '/dashboard/admin/api', show: hasPermission('admin:content_manage') },
      ],
    },
    {
      label: '资源库',
      to: '/dashboard/resources',
      show: hasAnyPermission('lesson:create', 'exercise:create', 'material:upload', 'material:view_public', 'course:create', 'question:view_all'),
    },
  ]
    .map((group) => ({
      ...group,
      children: group.children?.filter((child) => child.show),
    }))
    .filter((group) => group.show && (!group.children || group.children.length)),
)

async function logout() {
  auth.logout()
  await router.push('/login')
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(sidebarCollapsed.value))
  }
}

function isGroupOpen(group: NavGroup): boolean {
  if (!group.children?.length) return false
  if (collapsedGroups.value.has(group.label)) return false
  return true
}

function toggleGroup(group: NavGroup) {
  const next = new Set(collapsedGroups.value)
  if (next.has(group.label)) {
    next.delete(group.label)
  } else {
    next.add(group.label)
  }
  collapsedGroups.value = next
}

function groupActive(group: NavGroup): boolean {
  if (group.to && route.path === group.to) return true
  return group.children?.some((child) => route.path === child.to || route.path.startsWith(`${child.to}/`)) ?? false
}
</script>

<template>
  <div class="workbench" :class="{ collapsed: sidebarCollapsed }">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">研</span>
        <div class="brand-text">
          <strong>研备通 AI</strong>
          <span>智能教研平台</span>
        </div>
        <button type="button" class="collapse-toggle" @click="toggleSidebar" :title="sidebarCollapsed ? '展开' : '收起'">
          <svg v-if="!sidebarCollapsed" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
        </button>
      </div>

      <nav aria-label="工作台导航">
        <template v-for="group in navGroups" :key="group.label">
          <RouterLink
            v-if="group.to"
            :to="group.to"
            class="nav-link"
            :class="{ active: route.path === group.to }"
          >
            <span class="nav-icon" aria-hidden="true"></span>
            <span class="nav-full">{{ group.label }}</span>
            <span class="nav-short">{{ group.label.slice(0, 1) }}</span>
          </RouterLink>
          <div v-else class="nav-section">
            <button
              type="button"
              class="nav-parent"
              :class="{ active: groupActive(group) }"
              @click="toggleGroup(group)"
            >
              <span class="nav-full">{{ group.label }}</span>
              <span class="nav-short">{{ group.label.slice(0, 1) }}</span>
              <span class="nav-arrow" :class="{ open: isGroupOpen(group) }">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </span>
            </button>
            <div class="nav-children-wrapper" :class="{ open: isGroupOpen(group) }">
              <div class="nav-children">
                <RouterLink
                  v-for="child in group.children"
                  :key="child.to"
                  :to="child.to"
                  class="nav-child"
                >
                  <span class="nav-full">{{ child.label }}</span>
                  <span class="nav-short">{{ child.label.slice(0, 1) }}</span>
                </RouterLink>
              </div>
            </div>
          </div>
        </template>
      </nav>

      <div class="account">
        <div class="account-info">
          <div class="avatar">{{ userName.slice(0, 1).toUpperCase() }}</div>
          <div class="account-details">
            <strong>{{ userName }}</strong>
            <small>{{ userRoleText }}</small>
          </div>
        </div>
        <button type="button" class="btn-logout" @click="logout" title="退出登录">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
        </button>
      </div>
    </aside>

    <button
      v-if="sidebarCollapsed"
      type="button"
      class="sidebar-reopen"
      aria-label="展开侧边栏"
      @click="toggleSidebar"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
    </button>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.workbench {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 280px minmax(0, 1fr);
  background: #f8fafc;
  transition: grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.workbench.collapsed {
  grid-template-columns: 0 minmax(0, 1fr);
}

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  height: 100vh;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid #e2e8f0;
  background: #ffffff;
  overflow: hidden;
  padding: 24px 20px;
  box-shadow: 4px 0 24px rgba(15, 23, 42, 0.02);
  transition: padding 0.3s ease, opacity 0.3s ease;
  z-index: 40;
}

.brand {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 32px;
  gap: 12px;
  align-items: center;
  margin-bottom: 32px;
}

.collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #64748b;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.collapse-toggle:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  color: #ffffff;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  font-size: 1.1rem;
  font-weight: 800;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.brand-text strong {
  color: #0f172a;
  font-size: 1.1rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-text span {
  color: #64748b;
  font-size: 0.75rem;
}

nav {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-gutter: stable;
}

nav::-webkit-scrollbar {
  width: 4px;
}
nav::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-link,
.nav-parent {
  display: flex;
  width: 100%;
  align-items: center;
  border-radius: 10px;
  padding: 10px 14px;
  color: #475569;
  background: transparent;
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  transition: all 0.2s ease;
  cursor: pointer;
  border: none;
  text-align: left;
}

.nav-short {
  display: none;
}

.nav-arrow {
  margin-left: auto;
  color: #94a3b8;
  display: flex;
  align-items: center;
  transition: transform 0.3s ease;
}

.nav-arrow.open {
  transform: rotate(180deg);
}

.nav-children-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s ease;
}

.nav-children-wrapper.open {
  grid-template-rows: 1fr;
}

.nav-children {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 14px;
  margin-left: 20px;
  border-left: 1px solid #e2e8f0;
  margin-top: 4px;
  margin-bottom: 4px;
}

.nav-child {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 8px;
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s ease;
  position: relative;
}

.nav-child::before {
  content: '';
  position: absolute;
  left: -1px;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 0;
  background: #2563eb;
  transition: height 0.2s ease;
}

.nav-link:hover,
.nav-parent:hover,
.nav-child:hover {
  background: #f8fafc;
  color: #0f172a;
}

.nav-child:hover::before {
  height: 12px;
}

.nav-parent.active,
.nav-link.active,
.nav-child.router-link-active,
.nav-link.exact.router-link-exact-active {
  color: #2563eb;
  background: #eff6ff;
}

.nav-child.router-link-active::before {
  height: 100%;
}

.account {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
  margin-top: auto;
  border-top: 1px solid #e2e8f0;
  padding-top: 20px;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
}

.account-details {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.account-details strong {
  color: #0f172a;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.account-details small {
  color: #64748b;
  font-size: 0.75rem;
}

.btn-logout {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-logout:hover {
  background: #fee2e2;
  color: #ef4444;
}

.content {
  min-width: 0;
  padding: 32px 40px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.sidebar-reopen {
  position: fixed;
  top: 24px;
  left: 20px;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  color: #0f172a;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
  cursor: pointer;
  transition: all 0.2s ease;
}

.sidebar-reopen:hover {
  background: #f8fafc;
  color: #2563eb;
  transform: scale(1.05);
}

.workbench.collapsed .sidebar {
  padding: 0;
  opacity: 0;
  pointer-events: none;
}

@media (max-width: 1024px) {
  .workbench {
    grid-template-columns: 240px minmax(0, 1fr);
  }
  .content {
    padding: 24px;
  }
}

@media (max-width: 860px) {
  .workbench, .workbench.collapsed {
    display: flex;
    flex-direction: column;
  }

  .sidebar {
    position: static;
    height: auto;
    padding: 20px;
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
    opacity: 1;
    pointer-events: auto;
  }

  nav {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
    overflow-y: visible;
  }

  .nav-section, .nav-link {
    width: auto;
  }

  .nav-children-wrapper {
    display: none; /* Simplify mobile view */
  }

  .brand {
    grid-template-columns: 40px minmax(0, 1fr) auto;
    margin-bottom: 20px;
  }

  .collapse-toggle, .sidebar-reopen {
    display: none;
  }
}
</style>

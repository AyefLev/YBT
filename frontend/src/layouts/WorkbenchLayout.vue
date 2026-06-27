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
        <div>
          <strong>研备通 AI</strong>
          <span>成人考研机构智能教研平台</span>
        </div>
        <button type="button" class="collapse-toggle" @click="toggleSidebar">
          {{ sidebarCollapsed ? '展开' : '收起' }}
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
            <span class="nav-full">{{ group.label }}</span>
            <span class="nav-short">{{ group.label.slice(0, 2) }}</span>
          </RouterLink>
          <div v-else class="nav-section">
            <button
              type="button"
              class="nav-parent"
              :class="{ active: groupActive(group) }"
              @click="toggleGroup(group)"
            >
              <span class="nav-full">{{ group.label }}</span>
              <span class="nav-short">{{ group.label.slice(0, 2) }}</span>
              <span class="nav-arrow">{{ isGroupOpen(group) ? '⌄' : '›' }}</span>
            </button>
            <div v-if="isGroupOpen(group)" class="nav-children">
              <RouterLink
                v-for="child in group.children"
                :key="child.to"
                :to="child.to"
                class="nav-child"
              >
                <span class="nav-dot" aria-hidden="true" />
                <span class="nav-full">{{ child.label }}</span>
                <span class="nav-short">{{ child.label.slice(0, 2) }}</span>
              </RouterLink>
            </div>
          </div>
        </template>
      </nav>

      <div class="account">
        <span>当前账号</span>
        <strong>{{ userName }}</strong>
        <small>{{ userRoleText }}</small>
        <button type="button" @click="logout">退出登录</button>
      </div>
    </aside>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.workbench {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 260px minmax(0, 1fr);
  background:
    linear-gradient(180deg, rgba(37, 99, 235, 0.06), transparent 340px),
    var(--bg);
}

.workbench.collapsed {
  grid-template-columns: 88px minmax(0, 1fr);
}

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  height: 100vh;
  flex-direction: column;
  border-right: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.94);
  padding: 22px 18px;
}

.brand {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  margin-bottom: 26px;
}

.collapse-toggle {
  grid-column: 1 / -1;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 9px;
  color: var(--muted);
  background: #ffffff;
  font-weight: 900;
}

.logo {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
  background: var(--brand);
  font-weight: 900;
}

.brand div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.brand strong {
  color: var(--text);
  font-size: 1.15rem;
}

.brand span:last-child,
.account span {
  color: var(--muted);
  font-size: 0.86rem;
}

nav {
  display: grid;
  gap: 6px;
}

.nav-section {
  display: grid;
  gap: 4px;
}

.nav-link,
.nav-parent,
.nav-child {
  display: flex;
  width: 100%;
  gap: 10px;
  align-items: center;
  border-radius: 8px;
  padding: 10px 12px;
  color: #334155;
  background: transparent;
  font-weight: 800;
  text-decoration: none;
}

.nav-parent {
  border: 0;
  text-align: left;
}

.nav-short {
  display: none;
}

.nav-arrow {
  margin-left: auto;
  color: var(--muted);
}

.nav-children {
  display: grid;
  gap: 3px;
  padding-left: 12px;
}

.nav-child {
  padding: 8px 10px;
  color: #475569;
  font-size: 0.94rem;
}

.nav-dot {
  width: 6px;
  height: 6px;
  flex: none;
  border-radius: 999px;
  background: #94a3b8;
}

.nav-link:hover,
.nav-parent:hover,
.nav-child:hover {
  background: #f1f5f9;
}

.nav-parent.active,
.nav-link.active,
.nav-child.router-link-active,
.nav-link.exact.router-link-exact-active {
  color: var(--brand-dark);
  background: var(--brand-soft);
}

.account {
  display: grid;
  gap: 8px;
  margin-top: auto;
  border-top: 1px solid var(--line);
  padding-top: 16px;
}

.account strong {
  color: var(--text);
}

.account button {
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  padding: 10px 12px;
  color: #334155;
  background: #ffffff;
  font-weight: 800;
}

.content {
  min-width: 0;
  padding: 30px 32px;
}

.workbench.collapsed .sidebar {
  padding: 18px 12px;
}

.workbench.collapsed .brand {
  grid-template-columns: 1fr;
  justify-items: center;
}

.workbench.collapsed .brand div,
.workbench.collapsed .account span,
.workbench.collapsed .account strong,
.workbench.collapsed .account small,
.workbench.collapsed .nav-full,
.workbench.collapsed .nav-arrow,
.workbench.collapsed .nav-dot {
  display: none;
}

.workbench.collapsed .nav-short {
  display: inline;
}

.workbench.collapsed .nav-link,
.workbench.collapsed .nav-parent,
.workbench.collapsed .nav-child,
.workbench.collapsed .account button,
.workbench.collapsed .collapse-toggle {
  justify-content: center;
  text-align: center;
}

@media (max-width: 860px) {
  .workbench {
    display: block;
  }

  .workbench.collapsed {
    display: block;
  }

  .sidebar {
    position: static;
    height: auto;
    padding: 16px;
  }

  nav {
    display: flex;
    flex-wrap: wrap;
  }

  .nav-link,
  .nav-parent,
  .nav-child {
    padding: 8px 10px;
  }

  .account {
    grid-template-columns: 1fr auto;
    align-items: center;
    margin-top: 14px;
  }

  .account span {
    display: none;
  }

  .brand {
    grid-template-columns: 42px minmax(0, 1fr) auto;
  }

  .collapse-toggle {
    grid-column: auto;
  }

  .workbench.collapsed .brand {
    grid-template-columns: 42px minmax(0, 1fr) auto;
    justify-items: stretch;
  }

  .workbench.collapsed .brand div,
  .workbench.collapsed .nav-full,
  .workbench.collapsed .nav-arrow,
  .workbench.collapsed .nav-dot {
    display: initial;
  }

  .workbench.collapsed .nav-short {
    display: none;
  }

  .content {
    padding: 20px;
  }
}
</style>

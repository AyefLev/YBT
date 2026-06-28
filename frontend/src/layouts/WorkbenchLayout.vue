<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { buildWorkbenchNavigation, type WorkbenchNavGroup } from '../navigation/workbenchNavigation'
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

const userInitial = computed(() => userName.value.slice(0, 1).toUpperCase())

function hasPermission(permission: string): boolean {
  return auth.user?.permissions.includes(permission) ?? false
}

function hasAnyPermission(...permissions: string[]): boolean {
  return permissions.some((permission) => hasPermission(permission))
}

function hasRole(role: string): boolean {
  return auth.user?.roles.includes(role) ?? false
}

const navGroups = computed(() => buildWorkbenchNavigation({ hasPermission, hasAnyPermission, hasRole }))

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

function isGroupOpen(group: WorkbenchNavGroup): boolean {
  if (!group.children?.length) return false
  if (collapsedGroups.value.has(group.label)) return false
  return true
}

function toggleGroup(group: WorkbenchNavGroup) {
  const next = new Set(collapsedGroups.value)
  if (next.has(group.label)) {
    next.delete(group.label)
  } else {
    next.add(group.label)
  }
  collapsedGroups.value = next
}

function groupActive(group: WorkbenchNavGroup): boolean {
  if (group.to && route.path === group.to) return true
  return group.children?.some((child) => route.path === child.to || route.path.startsWith(`${child.to}/`)) ?? false
}

function navGlyph(label: string): string {
  const glyphs: Record<string, string> = {
    工作台: '台',
    教案: '案',
    练习题: '题',
    资料课程: '资',
    班级教学: '班',
    教研审核: '审',
    系统运维: '运',
    系统管理: '管',
    资源库: '库',
  }
  return glyphs[label] ?? label.slice(0, 1)
}
</script>

<template>
  <div class="workbench" :class="{ collapsed: sidebarCollapsed }">
    <aside class="sidebar" aria-label="工作台侧边栏">
      <div class="brand">
        <span class="logo" aria-hidden="true">研</span>
        <div class="brand-text">
          <strong>研备通 AI</strong>
          <span>智能教研工作台</span>
        </div>
        <button
          type="button"
          class="collapse-toggle"
          :aria-label="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          @click="toggleSidebar"
        >
          <span aria-hidden="true">{{ sidebarCollapsed ? '›' : '‹' }}</span>
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
            <span class="nav-glyph" aria-hidden="true">{{ navGlyph(group.label) }}</span>
            <span class="nav-full">{{ group.label }}</span>
          </RouterLink>

          <div v-else class="nav-section">
            <button
              type="button"
              class="nav-parent"
              :class="{ active: groupActive(group) }"
              @click="toggleGroup(group)"
            >
              <span class="nav-glyph" aria-hidden="true">{{ navGlyph(group.label) }}</span>
              <span class="nav-full">{{ group.label }}</span>
              <span class="nav-arrow" :class="{ open: isGroupOpen(group) }" aria-hidden="true">⌄</span>
            </button>
            <div class="nav-children-wrapper" :class="{ open: isGroupOpen(group) }">
              <div class="nav-children">
                <RouterLink
                  v-for="child in group.children"
                  :key="child.to"
                  :to="child.to"
                  class="nav-child"
                >
                  <span class="nav-child-marker" aria-hidden="true" />
                  <span class="nav-full">{{ child.label }}</span>
                </RouterLink>
              </div>
            </div>
          </div>
        </template>
      </nav>

      <div class="account">
        <div class="avatar" aria-hidden="true">{{ userInitial }}</div>
        <div class="account-details">
          <strong>{{ userName }}</strong>
          <small>{{ userRoleText }}</small>
        </div>
        <button type="button" class="btn-logout" title="退出登录" aria-label="退出登录" @click="logout">
          退
        </button>
      </div>
    </aside>

    <button
      v-if="sidebarCollapsed"
      type="button"
      class="sidebar-reopen"
      aria-label="展开侧边栏"
      title="展开侧边栏"
      @click="toggleSidebar"
    >
      ›
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
  grid-template-columns: 268px minmax(0, 1fr);
  background: var(--bg);
  transition: grid-template-columns 0.22s ease;
}

.workbench.collapsed {
  grid-template-columns: 0 minmax(0, 1fr);
}

.sidebar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  height: 100vh;
  min-width: 0;
  flex-direction: column;
  border-right: 1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.96)),
    var(--surface);
  overflow: hidden;
  padding: 20px 16px;
}

.brand {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 34px;
  gap: 11px;
  align-items: center;
  border-bottom: 1px solid var(--line);
  margin-bottom: 16px;
  padding-bottom: 16px;
}

.logo {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 10px;
  color: #ffffff;
  background: var(--brand);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.18);
  font-weight: 900;
}

.brand-text {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.brand-text strong {
  overflow: hidden;
  color: var(--text);
  font-size: 1.02rem;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brand-text span {
  overflow: hidden;
  color: var(--muted);
  font-size: 0.78rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collapse-toggle,
.sidebar-reopen,
.btn-logout {
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  color: var(--muted-strong);
  background: var(--surface);
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease,
    transform 0.08s ease;
}

.collapse-toggle {
  width: 34px;
  height: 34px;
  font-size: 1.3rem;
}

.collapse-toggle:hover,
.sidebar-reopen:hover,
.btn-logout:hover {
  border-color: var(--line-strong);
  color: var(--brand-dark);
  background: var(--brand-soft);
}

nav {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-gutter: stable;
}

nav::-webkit-scrollbar {
  width: 5px;
}

nav::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #cbd5e1;
}

.nav-section {
  display: grid;
  gap: 3px;
}

.nav-link,
.nav-parent,
.nav-child {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  border: 0;
  border-radius: var(--radius-md);
  color: var(--muted-strong);
  background: transparent;
  font-weight: 760;
  text-align: left;
  text-decoration: none;
  transition:
    background 0.16s ease,
    color 0.16s ease;
}

.nav-link,
.nav-parent {
  gap: 10px;
  padding: 10px 11px;
}

.nav-glyph {
  display: grid;
  width: 24px;
  height: 24px;
  flex: none;
  place-items: center;
  border-radius: 7px;
  color: var(--muted-strong);
  background: var(--surface-muted);
  font-size: 0.78rem;
  font-weight: 900;
}

.nav-full {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-arrow {
  margin-left: auto;
  color: #94a3b8;
  font-weight: 900;
  transition: transform 0.16s ease;
}

.nav-arrow.open {
  transform: rotate(180deg);
}

.nav-children-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.18s ease;
}

.nav-children-wrapper.open {
  grid-template-rows: 1fr;
}

.nav-children {
  display: grid;
  gap: 2px;
  overflow: hidden;
  border-left: 1px solid var(--line);
  margin: 2px 0 5px 22px;
  padding-left: 10px;
}

.nav-child {
  gap: 8px;
  padding: 8px 10px;
  font-size: 0.92rem;
}

.nav-child-marker {
  width: 5px;
  height: 5px;
  flex: none;
  border-radius: 999px;
  background: #cbd5e1;
}

.nav-link:hover,
.nav-parent:hover,
.nav-child:hover {
  color: var(--text);
  background: var(--surface-muted);
}

.nav-parent.active,
.nav-link.active,
.nav-child.router-link-active,
.nav-link.router-link-exact-active {
  color: var(--brand-ink);
  background: var(--brand-soft);
}

.nav-parent.active .nav-glyph,
.nav-link.active .nav-glyph {
  color: #ffffff;
  background: var(--brand);
}

.nav-child.router-link-active .nav-child-marker {
  background: var(--brand);
}

.account {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 34px;
  gap: 10px;
  align-items: center;
  border-top: 1px solid var(--line);
  margin-top: 16px;
  padding-top: 16px;
}

.avatar {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 999px;
  color: var(--brand-ink);
  background: var(--brand-soft);
  font-weight: 900;
}

.account-details {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.account-details strong,
.account-details small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-details strong {
  color: var(--text);
  font-size: 0.92rem;
}

.account-details small {
  color: var(--muted);
  font-size: 0.76rem;
}

.btn-logout {
  width: 34px;
  height: 34px;
  font-size: 0.82rem;
  font-weight: 900;
}

.content {
  width: 100%;
  max-width: var(--content-max);
  min-width: 0;
  margin: 0 auto;
  padding: 30px 34px 42px;
}

.sidebar-reopen {
  position: fixed;
  top: 20px;
  left: 18px;
  z-index: 40;
  width: 40px;
  height: 40px;
  box-shadow: var(--shadow-md);
  font-size: 1.45rem;
}

.workbench.collapsed .sidebar {
  border-right: 0;
  opacity: 0;
  padding: 0;
  pointer-events: none;
}

.workbench.collapsed .content {
  padding-left: 76px;
}

@media (max-width: 1080px) {
  .workbench {
    grid-template-columns: 244px minmax(0, 1fr);
  }

  .content {
    padding: 24px;
  }
}

@media (max-width: 860px) {
  .workbench,
  .workbench.collapsed {
    display: block;
  }

  .sidebar {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--line);
    opacity: 1;
    padding: 16px;
    pointer-events: auto;
  }

  .brand {
    grid-template-columns: 40px minmax(0, 1fr);
  }

  .collapse-toggle,
  .sidebar-reopen {
    display: none;
  }

  nav {
    max-height: 48vh;
  }

  .content,
  .workbench.collapsed .content {
    padding: 20px;
  }
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const userName = computed(() => auth.user?.display_name || auth.user?.username || '教师')

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

const navItems = computed(() =>
  [
    { label: '工作台', to: '/dashboard', show: true },
    { label: '备课资源', to: '/dashboard/lesson', show: hasAnyPermission('lesson:create', 'lesson:view_all') },
    { label: '习题资源', to: '/dashboard/exercise', show: hasAnyPermission('exercise:create', 'exercise:view_all') },
    { label: '机构知识库', to: '/dashboard/materials', show: hasAnyPermission('material:upload', 'material:view_all') },
    { label: '课程体系', to: '/dashboard/courses', show: hasAnyPermission('course:create', 'course:view_all') },
    {
      label: '班级与作业',
      to: '/dashboard/classrooms',
      show: hasAnyPermission('class:manage', 'class:join', 'class:view_all'),
    },
    { label: '题库管理', to: '/dashboard/questions', show: hasAnyPermission('exercise:create', 'question:view_all') },
    { label: '教研审核', to: '/dashboard/reviews', show: hasPermission('review:manage') },
    { label: '合规检查', to: '/dashboard/compliance', show: hasPermission('lesson:create') },
    { label: '观测日志', to: '/dashboard/observability', show: hasPermission('log:view') },
    { label: '演示检查', to: '/dashboard/health', show: true },
    { label: '资源库', to: '/dashboard/resources', show: true },
    { label: '系统管理', to: '/dashboard/admin', show: hasPermission('admin:user_manage') },
  ].filter((item) => item.show),
)

async function logout() {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="workbench">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">研</span>
        <div>
          <strong>研备通 AI</strong>
          <span>成人考研机构智能教研平台</span>
        </div>
      </div>

      <nav aria-label="工作台导航">
        <span class="nav-group">教师流程</span>
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :class="{ exact: item.to === '/dashboard' }"
        >
          {{ item.label }}
        </RouterLink>
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
.account span,
.nav-group {
  color: var(--muted);
  font-size: 0.86rem;
}

nav {
  display: grid;
  gap: 6px;
}

.nav-group {
  margin: 4px 0 6px;
  font-weight: 800;
}

nav a {
  border-radius: 8px;
  padding: 10px 12px;
  color: #334155;
  font-weight: 800;
  text-decoration: none;
}

nav a:hover {
  background: #f1f5f9;
}

nav a.router-link-active,
nav a.exact.router-link-exact-active {
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

@media (max-width: 860px) {
  .workbench {
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

  .nav-group {
    width: 100%;
  }

  nav a {
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

  .content {
    padding: 20px;
  }
}
</style>

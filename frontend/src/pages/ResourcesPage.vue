<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

function hasPermission(permission: string): boolean {
  return auth.user?.permissions.includes(permission) ?? false
}

const resources = computed(() =>
  [
    {
      title: '我的班级',
      description: '查看已加入班级、作业与提交情况。',
      to: '/dashboard/classrooms',
      show: hasPermission('class:join') || hasPermission('class:manage') || hasPermission('class:view_all'),
    },
    {
      title: '公共资料库',
      description: '查看可公开使用的课程资料和知识库片段。',
      to: '/dashboard/materials',
      show: hasPermission('material:view_public') || hasPermission('material:upload') || hasPermission('material:view_all'),
    },
    {
      title: '教案',
      description: '生成和维护教案，保存版本并导出文档。',
      to: '/dashboard/lesson',
      show: hasPermission('lesson:create') || hasPermission('lesson:view_all'),
    },
    {
      title: '练习题',
      description: '按课程节点生成练习，保存后可进入题库。',
      to: '/dashboard/exercise',
      show: hasPermission('exercise:create') || hasPermission('exercise:view_all'),
    },
    {
      title: '课程体系',
      description: '维护课程、章节、课次与知识点结构。',
      to: '/dashboard/courses',
      show: hasPermission('course:create') || hasPermission('course:view_all'),
    },
    {
      title: '题库管理',
      description: '沉淀可审核、可导出的机构题库资产。',
      to: '/dashboard/questions',
      show: hasPermission('exercise:create') || hasPermission('question:view_all'),
    },
    {
      title: '内容检查',
      description: '检查教案、习题和材料中的风险词与修改建议。',
      to: '/dashboard/compliance',
      show: hasPermission('lesson:create'),
    },
  ].filter((resource) => resource.show),
)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">资源</p>
        <h1>资源库</h1>
        <p>汇总当前账号可用的资源入口，只显示与你的角色权限匹配的内容。</p>
      </div>
    </header>

    <div class="resource-grid">
      <RouterLink v-for="resource in resources" :key="resource.to" :to="resource.to" class="panel card">
        <strong>{{ resource.title }}</strong>
        <span>{{ resource.description }}</span>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.resource-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.card {
  display: grid;
  gap: 8px;
  color: inherit;
  text-decoration: none;
}

.card:hover {
  border-color: #93c5fd;
}

.card strong {
  color: var(--text);
  font-size: 1.05rem;
}

.card span {
  color: var(--muted);
  line-height: 1.7;
}

@media (max-width: 900px) {
  .resource-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .resource-grid {
    grid-template-columns: 1fr;
  }
}
</style>

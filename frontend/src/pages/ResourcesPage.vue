<script setup lang="ts">
import { RouterLink } from 'vue-router'

const resources = [
  {
    title: '备课资源',
    description: '从教学目标生成教案，保存版本并导出 DOCX。',
    to: '/dashboard/lesson',
  },
  {
    title: '习题资源',
    description: '按知识点生成练习题，保留历史版本用于复用。',
    to: '/dashboard/exercise',
  },
  {
    title: '机构知识库',
    description: '上传教材和讲义，检索相关片段辅助生成。',
    to: '/dashboard/materials',
  },
  {
    title: '合规审核',
    description: '检查教案、习题和材料中的风险词与修改建议。',
    to: '/dashboard/compliance',
  },
  {
    title: '课程体系',
    description: '维护课程、章节、课次与知识点结构。',
    to: '/dashboard/courses',
  },
  {
    title: '题库管理',
    description: '沉淀可审核、可导出的机构题库资产。',
    to: '/dashboard/questions',
  },
]
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">资源</p>
        <h1>资源库</h1>
        <p>汇总当前系统可用的教研资源入口，方便演示时快速进入不同业务能力。</p>
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

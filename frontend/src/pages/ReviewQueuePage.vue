<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '../api/client'

interface Reviewable {
  resource_type: string
  resource_id: number
  title: string
  owner_id: number
  status: string
  subject: string | null
  created_at: string
  updated_at: string
}

const items = ref<Reviewable[]>([])
const comment = ref('')
const loading = ref('')
const error = ref('')
const notice = ref('')

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

function resourceLabel(type: string): string {
  const labels: Record<string, string> = {
    lesson: '备课',
    question: '题目',
    exercise: '习题',
  }
  return labels[type] ?? type
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: '草稿',
    pending_review: '待审核',
    approved: '已通过',
    rejected: '已退回',
  }
  return labels[status] ?? status
}

async function loadPending() {
  loading.value = 'load'
  error.value = ''
  try {
    items.value = await api<Reviewable[]>('/api/reviews/pending')
  } catch (err) {
    setError(err, '审核队列加载失败')
  } finally {
    loading.value = ''
  }
}

async function review(item: Reviewable, action: 'approve' | 'reject') {
  loading.value = `${action}-${item.resource_type}-${item.resource_id}`
  error.value = ''
  try {
    await api(`/api/reviews/${item.resource_type}/${item.resource_id}/${action}`, {
      method: 'POST',
      body: JSON.stringify({ comment: comment.value }),
    })
    notice.value = `${resourceLabel(item.resource_type)} ${item.resource_id} 已${action === 'approve' ? '通过' : '退回'}`
    comment.value = ''
    await loadPending()
  } catch (err) {
    setError(err, action === 'approve' ? '审核通过失败' : '审核退回失败')
  } finally {
    loading.value = ''
  }
}

onMounted(loadPending)
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">教研审核</p>
        <h1>审核队列</h1>
        <p>审核教师提交的教案和题库题目，让机构内容在发布前经过人工把关。</p>
      </div>
      <button type="button" class="btn-secondary" @click="loadPending">刷新队列</button>
    </header>

    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <section class="panel stack">
      <label>
        审核意见
        <textarea v-model.trim="comment" rows="3" placeholder="通过或退回时记录审核意见" />
      </label>
      <p v-if="!items.length" class="empty-state">暂无待审核内容。</p>
      <ul v-else class="review-list">
        <li v-for="item in items" :key="`${item.resource_type}-${item.resource_id}`">
          <div class="stack">
            <strong>{{ resourceLabel(item.resource_type) }} {{ item.resource_id }} · {{ item.title }}</strong>
            <small>
              {{ item.subject || '未填写学科' }} · 提交人 {{ item.owner_id }}
              <span class="status-pill" :class="item.status">{{ statusLabel(item.status) }}</span>
            </small>
          </div>
          <div class="actions">
            <button type="button" class="btn-primary" @click="review(item, 'approve')">通过</button>
            <button type="button" class="btn-danger" @click="review(item, 'reject')">退回</button>
          </div>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.review-list {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.review-list li {
  display: flex;
  gap: 14px;
  justify-content: space-between;
  border-bottom: 1px solid #edf1f7;
  padding-bottom: 14px;
}

.review-list li:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

@media (max-width: 760px) {
  .review-list li {
    display: grid;
  }
}
</style>

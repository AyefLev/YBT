<script setup lang="ts">
import { computed, ref } from 'vue'

import { filterMaterialsForContext, type TeachingContextIds } from '../pages/teachingContext'

export interface MaterialOption {
  id: number
  title: string
  resource_scope: string
  parse_status: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
}

const props = defineProps<{
  materials: MaterialOption[]
  modelValue: number[]
  contextIds: TeachingContextIds
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

const mode = ref<'context' | 'all'>('context')

const visibleMaterials = computed(() =>
  mode.value === 'context'
    ? filterMaterialsForContext(props.materials, props.contextIds)
    : props.materials,
)

function checked(materialId: number): boolean {
  return props.modelValue.includes(materialId)
}

function toggle(materialId: number, enabled: boolean) {
  if (props.disabled) return
  const next = new Set(props.modelValue)
  if (enabled) {
    next.add(materialId)
  } else {
    next.delete(materialId)
  }
  emit('update:modelValue', Array.from(next).sort((left, right) => left - right))
}

function scopeLabel(scope: string): string {
  return scope === 'public' ? '公共资源' : '个人资源'
}
</script>

<template>
  <section class="material-picker">
    <div class="picker-header">
      <strong>选择知识库资料</strong>
      <div class="segmented">
        <button type="button" :class="{ active: mode === 'context' }" @click="mode = 'context'">
          当前节点
        </button>
        <button type="button" :class="{ active: mode === 'all' }" @click="mode = 'all'">
          全部资料
        </button>
      </div>
    </div>

    <p v-if="!visibleMaterials.length" class="empty-state">暂无可选资料，可先上传到当前课程节点。</p>
    <div v-else class="material-options">
      <label v-for="material in visibleMaterials" :key="material.id" class="material-option">
        <input
          type="checkbox"
          :disabled="disabled"
          :checked="checked(material.id)"
          @change="toggle(material.id, ($event.target as HTMLInputElement).checked)"
        />
        <span>
          <strong>#{{ material.id }} {{ material.title }}</strong>
          <small>
            {{ scopeLabel(material.resource_scope) }} · {{ material.parse_status }}
            <template v-if="material.course_id"> · 课程 {{ material.course_id }}</template>
            <template v-if="material.chapter_id"> · 章节 {{ material.chapter_id }}</template>
            <template v-if="material.session_id"> · 课次 {{ material.session_id }}</template>
            <template v-if="material.knowledge_point_id"> · 知识点 {{ material.knowledge_point_id }}</template>
          </small>
        </span>
      </label>
    </div>
  </section>
</template>

<style scoped>
.material-picker {
  display: grid;
  gap: 10px;
}

.picker-header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.segmented {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.segmented button {
  border: 0;
  padding: 7px 10px;
  color: var(--muted);
  background: #ffffff;
  font-weight: 800;
}

.segmented button.active {
  color: var(--brand-dark);
  background: var(--brand-soft);
}

.material-options {
  display: grid;
  max-height: 260px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.material-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  border-bottom: 1px solid var(--line);
  padding: 10px;
}

.material-option:last-child {
  border-bottom: 0;
}

.material-option span {
  display: grid;
  gap: 4px;
}

.material-option small {
  color: var(--muted);
}

@media (max-width: 720px) {
  .picker-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>

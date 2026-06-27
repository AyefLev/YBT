<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

const html = computed(() => renderMarkdown(props.content || ''))

function renderMarkdown(source: string): string {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks: string[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    if (!line.trim()) {
      index += 1
      continue
    }

    if (line.trim().startsWith('```')) {
      const code: string[] = []
      index += 1
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        code.push(lines[index])
        index += 1
      }
      blocks.push(`<pre class="md-code"><code>${escapeHtml(code.join('\n'))}</code></pre>`)
      index += 1
      continue
    }

    const tableBlock = readTable(lines, index)
    if (tableBlock) {
      blocks.push(tableBlock.html)
      index = tableBlock.nextIndex
      continue
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      const level = heading[1].length + 2
      blocks.push(`<h${level}>${renderInline(heading[2])}</h${level}>`)
      index += 1
      continue
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = []
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(`<li>${renderInline(lines[index].replace(/^\s*[-*]\s+/, ''))}</li>`)
        index += 1
      }
      blocks.push(`<ul>${items.join('')}</ul>`)
      continue
    }

    if (/^\s*\d+[.、]\s+/.test(line)) {
      const items: string[] = []
      while (index < lines.length && /^\s*\d+[.、]\s+/.test(lines[index])) {
        items.push(`<li>${renderInline(lines[index].replace(/^\s*\d+[.、]\s+/, ''))}</li>`)
        index += 1
      }
      blocks.push(`<ol>${items.join('')}</ol>`)
      continue
    }

    if (/^\s*>/.test(line)) {
      const quotes: string[] = []
      while (index < lines.length && /^\s*>/.test(lines[index])) {
        quotes.push(renderInline(lines[index].replace(/^\s*>\s?/, '')))
        index += 1
      }
      blocks.push(`<blockquote>${quotes.join('<br>')}</blockquote>`)
      continue
    }

    const paragraph: string[] = []
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].trim().startsWith('```') &&
      !/^(#{1,3})\s+/.test(lines[index]) &&
      !/^\s*[-*]\s+/.test(lines[index]) &&
      !/^\s*\d+[.、]\s+/.test(lines[index]) &&
      !/^\s*>/.test(lines[index])
    ) {
      paragraph.push(lines[index])
      index += 1
    }
    blocks.push(`<p>${paragraph.map(renderInline).join('<br>')}</p>`)
  }

  return blocks.join('')
}

function readTable(lines: string[], startIndex: number): { html: string; nextIndex: number } | null {
  if (!lines[startIndex].includes('|') || startIndex + 1 >= lines.length) return null
  if (!/^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[startIndex + 1])) return null

  const headers = splitTableRow(lines[startIndex])
  const rows: string[][] = []
  let index = startIndex + 2
  while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
    rows.push(splitTableRow(lines[index]))
    index += 1
  }
  const headerHtml = headers.map((cell) => `<th>${renderInline(cell)}</th>`).join('')
  const rowHtml = rows
    .map((row) => `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join('')}</tr>`)
    .join('')
  return {
    html: `<div class="md-table-wrap"><table><thead><tr>${headerHtml}</tr></thead><tbody>${rowHtml}</tbody></table></div>`,
    nextIndex: index,
  }
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function renderInline(value: string): string {
  let text = escapeHtml(value)
  const code: string[] = []
  text = text.replace(/`([^`]+)`/g, (_, content: string) => {
    const token = `@@CODE${code.length}@@`
    code.push(`<code>${content}</code>`)
    return token
  })
  text = text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
  code.forEach((replacement, index) => {
    text = text.replace(`@@CODE${index}@@`, replacement)
  })
  return text
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
</script>

<template>
  <article class="markdown-preview" v-html="html" />
</template>

<style scoped>
.markdown-preview {
  display: grid;
  gap: 10px;
  color: var(--text);
  line-height: 1.75;
}

.markdown-preview :deep(h3),
.markdown-preview :deep(h4),
.markdown-preview :deep(h5),
.markdown-preview :deep(p),
.markdown-preview :deep(ul),
.markdown-preview :deep(ol),
.markdown-preview :deep(blockquote),
.markdown-preview :deep(pre) {
  margin: 0;
}

.markdown-preview :deep(h3),
.markdown-preview :deep(h4),
.markdown-preview :deep(h5) {
  color: var(--text);
}

.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  display: grid;
  gap: 6px;
  padding-left: 1.3rem;
}

.markdown-preview :deep(blockquote) {
  border-left: 4px solid #bfdbfe;
  padding: 8px 12px;
  color: #1e3a8a;
  background: #eff6ff;
}

.markdown-preview :deep(code) {
  border-radius: 6px;
  padding: 2px 5px;
  background: #e2e8f0;
}

.markdown-preview :deep(.md-code) {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  background: #0f172a;
}

.markdown-preview :deep(.md-code code) {
  padding: 0;
  color: #e2e8f0;
  background: transparent;
}

.markdown-preview :deep(.md-table-wrap) {
  overflow: auto;
}

.markdown-preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
  min-width: 360px;
}

.markdown-preview :deep(th),
.markdown-preview :deep(td) {
  border: 1px solid var(--line);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.markdown-preview :deep(th) {
  background: var(--surface-soft);
}
</style>

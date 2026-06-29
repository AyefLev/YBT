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
  const math: string[] = []
  text = text.replace(/`([^`]+)`/g, (_, content: string) => {
    const token = `@@CODE${code.length}@@`
    code.push(`<code>${content}</code>`)
    return token
  })
  text = renderMathTokens(text, math)
  text = text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
  math.forEach((replacement, index) => {
    text = text.replace(`@@MATH${index}@@`, replacement)
  })
  code.forEach((replacement, index) => {
    text = text.replace(`@@CODE${index}@@`, replacement)
  })
  return text
}

function renderMathTokens(text: string, math: string[]): string {
  const addMath = (content: string, display = false): string => {
    const token = `@@MATH${math.length}@@`
    math.push(
      `<span class="${display ? 'math-block' : 'math-inline'}">${latexToHtml(content)}</span>`,
    )
    return token
  }

  text = text.replace(/\\{1,2}\[([\s\S]*?)\\{1,2}\]/g, (_, content: string) => addMath(content, true))
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, content: string) => addMath(content, true))
  text = text.replace(/\\{1,2}\(([\s\S]*?)\\{1,2}\)/g, (_, content: string) => addMath(content))
  text = text.replace(/\$([^$\n]+)\$/g, (_, content: string) => addMath(content))
  return text
}

function latexToHtml(source: string): string {
  let text = collapseLatexSlashes(source.trim())
  text = replaceLatexFractions(text)
  text = replaceLatexRoots(text)
  text = unwrapLatexTextCommands(text)

  const replacements: Array<[RegExp, string]> = [
    [/\\rightarrow/g, '→'],
    [/\\leftarrow/g, '←'],
    [/\\times/g, '×'],
    [/\\cdot/g, '·'],
    [/\\div/g, '÷'],
    [/\\leq/g, '≤'],
    [/\\geq/g, '≥'],
    [/\\neq/g, '≠'],
    [/\\approx/g, '≈'],
    [/\\equiv/g, '≡'],
    [/\\pm/g, '±'],
    [/\\infty/g, '∞'],
    [/\\alpha/g, 'α'],
    [/\\beta/g, 'β'],
    [/\\gamma/g, 'γ'],
    [/\\delta/g, 'δ'],
    [/\\epsilon/g, 'ε'],
    [/\\theta/g, 'θ'],
    [/\\lambda/g, 'λ'],
    [/\\mu/g, 'μ'],
    [/\\pi/g, 'π'],
    [/\\rho/g, 'ρ'],
    [/\\sigma/g, 'σ'],
    [/\\varphi/g, 'φ'],
    [/\\phi/g, 'φ'],
    [/\\omega/g, 'ω'],
    [/\\sum/g, 'Σ'],
    [/\\prod/g, 'Π'],
    [/\\int/g, '∫'],
    [/\\lim/g, 'lim'],
    [/\\sin/g, 'sin'],
    [/\\cos/g, 'cos'],
    [/\\tan/g, 'tan'],
    [/\\ln/g, 'ln'],
    [/\\log/g, 'log'],
    [/\\to/g, '→'],
    [/\\forall/g, '∀'],
    [/\\exists/g, '∃'],
    [/\\in/g, '∈'],
    [/\\left/g, ''],
    [/\\right/g, ''],
    [/\\displaystyle/g, ''],
    [/\\[,;:]/g, ' '],
    [/\\!/g, ''],
  ]
  replacements.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement)
  })

  text = text
    .replace(/\\begin\{cases\}/g, '<span class="math-cases">')
    .replace(/\\end\{cases\}/g, '</span>')
    .replace(/\\begin\{[bpv]?matrix\}/g, '[')
    .replace(/\\end\{[bpv]?matrix\}/g, ']')
    .replace(/&amp;/g, ' ')
    .replace(/&/g, ' ')
    .replace(/\\\\/g, '<br>')

  text = replaceScripts(text, '^', 'sup')
  text = replaceScripts(text, '_', 'sub')
  text = text
    .replace(/\\([A-Za-z]+)/g, '$1')
    .replace(/\\([{}()[\]])/g, '$1')
    .replace(/\\/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  return text
}

function collapseLatexSlashes(value: string): string {
  return value.replace(/\\{2,}(?=[A-Za-z()[\]{}])/g, '\\')
}

function unwrapLatexTextCommands(value: string): string {
  return ['mathrm', 'operatorname', 'text', 'mathbf', 'mathit', 'mathcal'].reduce(
    (current, command) => current.replace(new RegExp(`\\\\${command}\\{([^{}]+)\\}`, 'g'), '$1'),
    value,
  )
}

function replaceLatexRoots(value: string): string {
  return value
    .replace(/\\sqrt\[([^{}\[\]]+)\]\{([^{}]+)\}/g, '$1√($2)')
    .replace(/\\sqrt\{([^{}]+)\}/g, '√($1)')
}

function replaceLatexFractions(value: string): string {
  let output = ''
  let index = 0
  while (index < value.length) {
    if (value.startsWith('\\frac', index)) {
      const numerator = readBracedGroup(value, index + '\\frac'.length)
      const denominator = numerator ? readBracedGroup(value, numerator.nextIndex) : null
      if (numerator && denominator) {
        output += `<span class="math-frac"><span>${latexToHtml(numerator.content)}</span><span>${latexToHtml(denominator.content)}</span></span>`
        index = denominator.nextIndex
        continue
      }
    }
    output += value[index]
    index += 1
  }
  return output
}

function readBracedGroup(value: string, start: number): { content: string; nextIndex: number } | null {
  let index = start
  while (index < value.length && /\s/.test(value[index])) index += 1
  if (value[index] !== '{') return null

  let depth = 0
  const contentStart = index + 1
  while (index < value.length) {
    if (value[index] === '{') depth += 1
    if (value[index] === '}') {
      depth -= 1
      if (depth === 0) {
        return { content: value.slice(contentStart, index), nextIndex: index + 1 }
      }
    }
    index += 1
  }
  return null
}

function replaceScripts(value: string, marker: '^' | '_', tag: 'sup' | 'sub'): string {
  const escapedMarker = marker === '^' ? '\\^' : '_'
  value = value.replace(new RegExp(`${escapedMarker}\\{([^{}]+)\\}`, 'g'), (_, content: string) => {
    return `<${tag}>${latexToHtml(content)}</${tag}>`
  })
  value = value.replace(new RegExp(`${escapedMarker}([A-Za-z0-9α-ωΑ-Ω∞])`, 'g'), `<${tag}>$1</${tag}>`)
  return value
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

.markdown-preview :deep(.math-inline),
.markdown-preview :deep(.math-block) {
  font-family: "Cambria Math", "Times New Roman", "Noto Serif CJK SC", serif;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.markdown-preview :deep(.math-inline) {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  border-radius: 6px;
  padding: 0 3px;
  background: rgba(219, 234, 254, 0.55);
}

.markdown-preview :deep(.math-block) {
  display: flex;
  justify-content: center;
  margin: 6px 0;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 10px 12px;
  background: #f8fbff;
  text-align: center;
}

.markdown-preview :deep(.math-frac) {
  display: inline-grid;
  grid-template-rows: auto auto;
  min-width: 22px;
  margin: 0 2px;
  vertical-align: middle;
  text-align: center;
  line-height: 1.15;
}

.markdown-preview :deep(.math-frac > span:first-child) {
  border-bottom: 1px solid currentColor;
  padding: 0 4px 2px;
}

.markdown-preview :deep(.math-frac > span:last-child) {
  padding: 2px 4px 0;
}

.markdown-preview :deep(.math-cases) {
  display: inline-grid;
  gap: 3px;
  border-left: 2px solid currentColor;
  padding-left: 8px;
  text-align: left;
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

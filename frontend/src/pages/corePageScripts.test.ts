import { readFileSync } from 'node:fs'

import { describe, expect, it } from 'vitest'

const pageRequirements = [
  {
    file: new URL('./LessonPage.vue', import.meta.url),
    bindings: [
      'const form = reactive(',
      'async function generateLesson(',
      'async function saveLesson(',
    ],
  },
  {
    file: new URL('./ExercisePage.vue', import.meta.url),
    bindings: [
      'const form = reactive(',
      'async function generateExercise(',
      'async function saveExercise(',
    ],
  },
]

describe('core generation pages', () => {
  it.each(pageRequirements)(
    'keeps the script bindings required by $file',
    ({ file, bindings }) => {
      const source = readFileSync(file, 'utf8')

      expect(source).toContain('<script setup lang="ts">')
      for (const binding of bindings) {
        expect(source).toContain(binding)
      }
    },
  )
})

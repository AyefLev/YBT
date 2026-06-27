import { ref } from 'vue'
import { describe, expect, test } from 'vitest'

import { clearSelectionDependentState } from './workbenchSelection'

describe('workbench selection state', () => {
  test('clears stale versions and generated details for different content', () => {
    const state = {
      versions: ref([{ id: 1 }]),
      compliance: ref({ risk_level: 'low' }),
      references: ref([{ id: 1 }]),
      generatedContent: ref('generated content'),
    }

    clearSelectionDependentState(state, 'saved content')

    expect(state.versions.value).toEqual([])
    expect(state.compliance.value).toBeNull()
    expect(state.references.value).toEqual([])
    expect(state.generatedContent.value).toBe('')
  })

  test('keeps generated details when the selected content still matches them', () => {
    const compliance = { risk_level: 'low' }
    const references = [{ id: 1 }]
    const state = {
      versions: ref([{ id: 1 }]),
      compliance: ref(compliance),
      references: ref(references),
      generatedContent: ref('generated content'),
    }

    clearSelectionDependentState(state, 'generated content')

    expect(state.versions.value).toEqual([])
    expect(state.compliance.value).toEqual(compliance)
    expect(state.references.value).toEqual(references)
    expect(state.generatedContent.value).toBe('generated content')
  })
})

import { beforeEach, describe, expect, it } from 'vitest'

import {
  hasMeaningfulGenerationDraft,
  loadMeaningfulGenerationDraft,
  saveGenerationDraft,
  type GenerationDraft,
} from './generationDraft'

interface DraftForm extends Record<string, unknown> {
  title: string
  course_id: number
  use_materials: boolean
  reference_count: number
}

const blankForm: DraftForm = {
  title: 'New lesson',
  course_id: 0,
  use_materials: false,
  reference_count: 5,
}

function draft(overrides: Partial<GenerationDraft<DraftForm>> = {}): GenerationDraft<DraftForm> {
  return {
    form: { ...blankForm },
    content: '',
    selectedMaterialIds: [],
    generatedContent: '',
    compliance: null,
    review: null,
    references: [],
    providerStatus: null,
    status: 'editing',
    savedAt: new Date(0).toISOString(),
    ...overrides,
  }
}

describe('generation draft rules', () => {
  beforeEach(() => {
    const storage = new Map<string, string>()
    Object.defineProperty(globalThis, 'sessionStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => storage.set(key, value),
        removeItem: (key: string) => storage.delete(key),
        clear: () => storage.clear(),
      },
    })
    sessionStorage.clear()
  })

  it('does not treat an untouched generation page as a meaningful draft', () => {
    expect(hasMeaningfulGenerationDraft(draft(), blankForm)).toBe(false)
  })

  it('treats edited content and selected materials as meaningful drafts', () => {
    expect(hasMeaningfulGenerationDraft(draft({ content: 'Draft body' }), blankForm)).toBe(true)
    expect(hasMeaningfulGenerationDraft(draft({ selectedMaterialIds: [1] }), blankForm)).toBe(true)
  })

  it('loads only meaningful saved drafts', () => {
    saveGenerationDraft('draft:blank', draft())
    saveGenerationDraft('draft:generated', draft({ generatedContent: 'Generated body', status: 'generated' }))

    expect(loadMeaningfulGenerationDraft<DraftForm>('draft:blank', blankForm)).toBeNull()
    expect(loadMeaningfulGenerationDraft<DraftForm>('draft:generated', blankForm)?.generatedContent).toBe(
      'Generated body',
    )
  })
})

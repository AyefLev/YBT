export interface GenerationDraft<TForm extends Record<string, unknown>> {
  form: TForm
  content: string
  selectedMaterialIds: number[]
  generatedContent: string
  compliance: unknown
  review: unknown
  references: unknown[]
  providerStatus?: unknown
  status: 'editing' | 'generating' | 'generated'
  savedAt: string
}

export function draftStorageKey(scope: string, userId: number | null | undefined): string {
  return `ybt:generation-draft:${scope}:user:${userId ?? 'anonymous'}`
}

export function saveGenerationDraft<TForm extends Record<string, unknown>>(
  key: string,
  draft: Omit<GenerationDraft<TForm>, 'savedAt'>,
): void {
  if (typeof sessionStorage === 'undefined') return
  sessionStorage.setItem(
    key,
    JSON.stringify({
      ...draft,
      savedAt: new Date().toISOString(),
    }),
  )
}

export function loadGenerationDraft<TForm extends Record<string, unknown>>(
  key: string,
): GenerationDraft<TForm> | null {
  if (typeof sessionStorage === 'undefined') return null
  const raw = sessionStorage.getItem(key)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as GenerationDraft<TForm>
    if (!parsed || typeof parsed !== 'object' || !parsed.form) return null
    return parsed
  } catch {
    return null
  }
}

export function loadMeaningfulGenerationDraft<TForm extends Record<string, unknown>>(
  key: string,
  baselineForm: TForm,
): GenerationDraft<TForm> | null {
  const draft = loadGenerationDraft<TForm>(key)
  if (!draft) return null
  return hasMeaningfulGenerationDraft(draft, baselineForm) ? draft : null
}

export function hasMeaningfulGenerationDraft<TForm extends Record<string, unknown>>(
  draft: Omit<GenerationDraft<TForm>, 'savedAt'> | GenerationDraft<TForm>,
  baselineForm: TForm,
): boolean {
  if (draft.status === 'generating' || draft.status === 'generated') return true
  if (draft.content.trim() || draft.generatedContent.trim()) return true
  if (draft.selectedMaterialIds.length > 0 || draft.references.length > 0) return true
  if (hasValue(draft.compliance) || hasValue(draft.review) || hasValue(draft.providerStatus)) return true
  return normalizedJson(draft.form) !== normalizedJson(baselineForm)
}

export function clearGenerationDraft(key: string): void {
  if (typeof sessionStorage === 'undefined') return
  sessionStorage.removeItem(key)
}

function hasValue(value: unknown): boolean {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value).length > 0
  return true
}

function normalizedJson(value: unknown): string {
  return JSON.stringify(sortValue(value))
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, entry]) => [key, sortValue(entry)]),
  )
}

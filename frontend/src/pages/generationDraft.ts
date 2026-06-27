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

export function clearGenerationDraft(key: string): void {
  if (typeof sessionStorage === 'undefined') return
  sessionStorage.removeItem(key)
}

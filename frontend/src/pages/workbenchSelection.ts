import type { Ref } from 'vue'

interface SelectionDependentState<TVersion, TCompliance, TReference> {
  versions: Ref<TVersion[]>
  compliance: Ref<TCompliance | null>
  references: Ref<TReference[]>
  generatedContent: Ref<string>
}

export function clearSelectionDependentState<TVersion, TCompliance, TReference>(
  state: SelectionDependentState<TVersion, TCompliance, TReference>,
  nextContent: string,
) {
  state.versions.value = []

  if (state.generatedContent.value === nextContent) {
    return
  }

  state.compliance.value = null
  state.references.value = []
  state.generatedContent.value = ''
}

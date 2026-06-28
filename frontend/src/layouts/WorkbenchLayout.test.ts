import { readFileSync } from 'node:fs'

import { compileScript, parse } from '@vue/compiler-sfc'
import { describe, expect, test } from 'vitest'

describe('WorkbenchLayout', () => {
  test('defines every binding required to render the authenticated workbench', () => {
    const filename = new URL('./WorkbenchLayout.vue', import.meta.url)
    const source = readFileSync(filename, 'utf8')
    const { descriptor, errors } = parse(source, { filename: filename.pathname })

    expect(errors).toEqual([])
    expect(descriptor.scriptSetup).not.toBeNull()

    const bindings = compileScript(descriptor, { id: 'workbench-layout' }).bindings ?? {}
    expect(Object.keys(bindings)).toEqual(
      expect.arrayContaining([
        'sidebarCollapsed',
        'navGroups',
        'route',
        'userName',
        'userRoleText',
        'toggleSidebar',
        'toggleGroup',
        'isGroupOpen',
        'groupActive',
        'logout',
      ]),
    )
  })
})

import { describe, expect, it } from 'vitest'

import { buildWorkbenchNavigation } from './workbenchNavigation'

describe('buildWorkbenchNavigation', () => {
  it('groups lesson and exercise routes for teachers', () => {
    const groups = buildWorkbenchNavigation({
      hasPermission: (permission) => ['lesson:create', 'exercise:create'].includes(permission),
      hasAnyPermission: (...permissions) =>
        permissions.some((permission) => ['lesson:create', 'exercise:create'].includes(permission)),
    })

    expect(groups.map((group) => group.label)).toContain('教案')
    expect(groups.find((group) => group.label === '教案')?.children?.map((child) => child.to)).toEqual([
      '/dashboard/lesson/generate',
      '/dashboard/lesson/records',
    ])
    expect(groups.find((group) => group.label === '练习题')?.children?.map((child) => child.to)).toEqual([
      '/dashboard/exercise/generate',
      '/dashboard/exercise/records',
      '/dashboard/questions',
    ])
  })

  it('hides upload route when the user can only view public materials', () => {
    const groups = buildWorkbenchNavigation({
      hasPermission: (permission) => permission === 'material:view_public',
      hasAnyPermission: (...permissions) => permissions.includes('material:view_public'),
    })

    const materials = groups.find((group) => group.label === '资料课程')
    expect(materials?.children?.map((child) => child.to)).toEqual(['/dashboard/materials/library'])
  })
})

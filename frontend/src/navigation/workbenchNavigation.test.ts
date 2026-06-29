import { describe, expect, it } from 'vitest'

import { buildWorkbenchNavigation } from './workbenchNavigation'

function accessFor(permissions: string[], roles: string[] = []) {
  return {
    hasPermission: (permission: string) => permissions.includes(permission),
    hasAnyPermission: (...values: string[]) => values.some((permission) => permissions.includes(permission)),
    hasRole: (role: string) => roles.includes(role),
  }
}

describe('buildWorkbenchNavigation', () => {
  it('groups lesson and exercise routes for teachers', () => {
    const groups = buildWorkbenchNavigation(accessFor(['lesson:create', 'exercise:create'], ['teacher']))

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
    const groups = buildWorkbenchNavigation(accessFor(['material:view_public'], ['student']))

    const materials = groups.find((group) => group.label === '资料课程')
    expect(materials?.children?.map((child) => child.to)).toEqual(['/dashboard/materials/library'])
  })

  it('keeps system admins out of teaching navigation even with stale teaching permissions', () => {
    const groups = buildWorkbenchNavigation(
      accessFor(
        [
          'lesson:create',
          'exercise:create',
          'material:upload',
          'course:create',
          'class:manage',
          'review:manage',
          'log:view',
          'admin:user_manage',
          'admin:content_manage',
        ],
        ['admin'],
      ),
    )

    expect(groups.map((group) => group.label)).toEqual(['工作台', '系统运维', '系统管理'])
    expect(groups.find((group) => group.label === '系统管理')?.children?.map((child) => child.to)).toEqual([
      '/dashboard/admin/users',
      '/dashboard/admin/api',
      '/dashboard/admin/database',
    ])
  })

  it('keeps teaching managers out of system operations even with stale log permission', () => {
    const groups = buildWorkbenchNavigation(
      accessFor(['course:view_all', 'course:manage_all', 'review:manage', 'log:view'], ['teaching_manager']),
    )

    expect(groups.map((group) => group.label)).toContain('资料课程')
    expect(groups.map((group) => group.label)).toContain('教研审核')
    expect(groups.map((group) => group.label)).not.toContain('系统运维')
  })
})

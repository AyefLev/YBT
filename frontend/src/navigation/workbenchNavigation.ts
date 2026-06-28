export interface WorkbenchNavChild {
  label: string
  to: string
}

export interface WorkbenchNavGroup {
  label: string
  to?: string
  children?: WorkbenchNavChild[]
}

export interface WorkbenchNavigationAccess {
  hasPermission(permission: string): boolean
  hasAnyPermission(...permissions: string[]): boolean
  hasRole(role: string): boolean
}

interface DraftNavChild extends WorkbenchNavChild {
  show: boolean
}

interface DraftNavGroup extends WorkbenchNavGroup {
  show: boolean
  children?: DraftNavChild[]
}

export function buildWorkbenchNavigation(access: WorkbenchNavigationAccess): WorkbenchNavGroup[] {
  const { hasPermission, hasAnyPermission, hasRole } = access
  const isSystemAdmin = hasRole('admin')
  const canUseTeachingWorkbench = !isSystemAdmin
  const groups: DraftNavGroup[] = [
    { label: '工作台', to: '/dashboard', show: true },
    {
      label: '教案',
      show: canUseTeachingWorkbench && hasAnyPermission('lesson:create', 'lesson:view_all'),
      children: [
        { label: '生成教案', to: '/dashboard/lesson/generate', show: hasPermission('lesson:create') },
        { label: '已有教案', to: '/dashboard/lesson/records', show: hasAnyPermission('lesson:create', 'lesson:view_all') },
      ],
    },
    {
      label: '练习题',
      show: canUseTeachingWorkbench && hasAnyPermission('exercise:create', 'exercise:view_all'),
      children: [
        { label: '生成练习', to: '/dashboard/exercise/generate', show: hasPermission('exercise:create') },
        { label: '已有练习', to: '/dashboard/exercise/records', show: hasAnyPermission('exercise:create', 'exercise:view_all') },
        { label: '题库管理', to: '/dashboard/questions', show: hasAnyPermission('exercise:create', 'question:view_all') },
      ],
    },
    {
      label: '资料课程',
      show: canUseTeachingWorkbench && hasAnyPermission('material:upload', 'material:view_all', 'material:view_public', 'course:create', 'course:view_all'),
      children: [
        { label: '资料列表', to: '/dashboard/materials/library', show: hasAnyPermission('material:upload', 'material:view_all', 'material:view_public') },
        { label: '上传资料', to: '/dashboard/materials/upload', show: hasPermission('material:upload') },
        { label: '课程体系', to: '/dashboard/courses', show: hasAnyPermission('course:create', 'course:view_all') },
      ],
    },
    {
      label: '班级教学',
      show: canUseTeachingWorkbench && hasAnyPermission('class:manage', 'class:join', 'class:view_all'),
      children: [
        { label: '班级与作业', to: '/dashboard/classrooms', show: hasAnyPermission('class:manage', 'class:join', 'class:view_all') },
      ],
    },
    {
      label: '教研审核',
      show: canUseTeachingWorkbench && hasPermission('review:manage'),
      children: [
        { label: '教研审核', to: '/dashboard/reviews', show: hasPermission('review:manage') },
        { label: '内容检查', to: '/dashboard/compliance', show: hasPermission('review:manage') },
      ],
    },
    {
      label: '系统运维',
      show: hasPermission('log:view'),
      children: [
        { label: '运行总览', to: '/dashboard/observability', show: hasPermission('log:view') },
        { label: 'Token 与费用', to: '/dashboard/observability/token', show: hasPermission('log:view') },
        { label: '系统检查', to: '/dashboard/health', show: hasPermission('log:view') },
      ],
    },
    {
      label: '系统管理',
      show: hasAnyPermission('admin:user_manage', 'admin:content_manage'),
      children: [
        { label: '用户管理', to: '/dashboard/admin/users', show: hasPermission('admin:user_manage') },
        { label: 'API 管理', to: '/dashboard/admin/api', show: hasPermission('admin:content_manage') },
      ],
    },
    {
      label: '资源库',
      to: '/dashboard/resources',
      show: canUseTeachingWorkbench && hasAnyPermission('lesson:create', 'exercise:create', 'material:upload', 'material:view_public', 'course:create', 'question:view_all'),
    },
  ]

  return groups
    .map((group) => ({
      ...group,
      children: group.children?.filter((child) => child.show).map(({ show: _show, ...child }) => child),
    }))
    .filter((group) => group.show && (!group.children || group.children.length))
    .map(({ show: _show, ...group }) => group)
}

import { describe, expect, test } from 'vitest'

import { filterMaterialsForContext, lessonDefaultsFromContext } from './teachingContext'

describe('teaching context helpers', () => {
  test('filters materials linked to the selected course node', () => {
    const materials = [
      { id: 1, title: '课次材料', course_id: 1, chapter_id: 2, session_id: 3, knowledge_point_id: null },
      { id: 2, title: '课程材料', course_id: 1, chapter_id: null, session_id: null, knowledge_point_id: null },
      { id: 3, title: '其他课程', course_id: 9, chapter_id: null, session_id: null, knowledge_point_id: null },
    ]

    expect(
      filterMaterialsForContext(materials, {
        course_id: 1,
        chapter_id: 2,
        session_id: 3,
        knowledge_point_id: 0,
      }).map((item) => item.id),
    ).toEqual([1, 2])
  })

  test('derives lesson defaults from selected course detail', () => {
    const defaults = lessonDefaultsFromContext(
      {
        subject: '高数',
        chapters: [
          {
            id: 2,
            title: '导数',
            summary: '',
            sessions: [
              { id: 3, title: '导数定义', duration_minutes: 60, teaching_goal: '掌握导数定义' },
            ],
          },
        ],
        knowledge_points: [
          {
            id: 4,
            name: '导数定义',
            description: '理解极限定义',
            difficulty: 'basic',
            chapter_id: 2,
            session_id: 3,
          },
        ],
      },
      { chapter_id: 2, session_id: 3, knowledge_point_id: 4 },
    )

    expect(defaults.chapter).toBe('导数')
    expect(defaults.duration_minutes).toBe(60)
    expect(defaults.teaching_goal).toContain('掌握导数定义')
    expect(defaults.teaching_goal).toContain('理解极限定义')
  })
})

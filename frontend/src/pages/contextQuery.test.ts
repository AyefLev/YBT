import { describe, expect, test } from 'vitest'

import { buildTeachingContextQuery, parseTeachingContextQuery } from './contextQuery'

describe('teaching context query', () => {
  test('parses positive numeric query values and ignores invalid values', () => {
    const parsed = parseTeachingContextQuery({
      course_id: '1',
      chapter_id: '2',
      session_id: 'bad',
      knowledge_point_id: '-4',
      lesson_id: '5',
      exercise_id: '6',
    })

    expect(parsed).toEqual({
      course_id: 1,
      chapter_id: 2,
      session_id: 0,
      knowledge_point_id: 0,
      lesson_id: 5,
      exercise_id: 6,
    })
  })

  test('builds query with only positive ids', () => {
    expect(
      buildTeachingContextQuery({
        course_id: 1,
        chapter_id: 0,
        session_id: 3,
        knowledge_point_id: null,
        lesson_id: undefined,
        exercise_id: 8,
      }),
    ).toEqual({ course_id: '1', session_id: '3', exercise_id: '8' })
  })
})

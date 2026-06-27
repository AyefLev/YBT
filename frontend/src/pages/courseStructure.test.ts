import { describe, expect, test } from 'vitest'

import { buildCourseAssetTree, type CourseAssetDetail } from './courseStructure'

describe('course asset tree', () => {
  test('places knowledge points under their linked sessions and chapters', () => {
    const detail: CourseAssetDetail = {
      chapters: [
        {
          id: 1,
          title: '第一章',
          summary: '',
          order_index: 1,
          sessions: [
            {
              id: 10,
              title: '第 1 课',
              duration_minutes: 45,
              teaching_goal: '',
              order_index: 1,
            },
          ],
        },
      ],
      knowledge_points: [
        {
          id: 100,
          name: '矩阵乘法定义',
          description: '',
          difficulty: 'basic',
          chapter_id: 1,
          session_id: 10,
        },
        {
          id: 101,
          name: '章节总览',
          description: '',
          difficulty: 'medium',
          chapter_id: 1,
          session_id: null,
        },
        {
          id: 102,
          name: '公共知识点',
          description: '',
          difficulty: 'advanced',
          chapter_id: null,
          session_id: null,
        },
      ],
    }

    const tree = buildCourseAssetTree(detail)

    expect(tree.chapters[0].sessions[0].knowledgePoints.map((point) => point.name)).toEqual([
      '矩阵乘法定义',
    ])
    expect(tree.chapters[0].knowledgePoints.map((point) => point.name)).toEqual(['章节总览'])
    expect(tree.unassignedKnowledgePoints.map((point) => point.name)).toEqual(['公共知识点'])
  })
})

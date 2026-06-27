import type { LocationQueryRaw } from 'vue-router'

export interface TeachingContextQuery {
  course_id: number
  chapter_id: number
  session_id: number
  knowledge_point_id: number
  lesson_id: number
  exercise_id: number
}

export function parseTeachingContextQuery(query: Record<string, unknown>): TeachingContextQuery {
  return {
    course_id: positiveNumber(query.course_id),
    chapter_id: positiveNumber(query.chapter_id),
    session_id: positiveNumber(query.session_id),
    knowledge_point_id: positiveNumber(query.knowledge_point_id),
    lesson_id: positiveNumber(query.lesson_id),
    exercise_id: positiveNumber(query.exercise_id),
  }
}

export function buildTeachingContextQuery(
  values: Partial<Record<keyof TeachingContextQuery, number | null | undefined>>,
): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  for (const [key, value] of Object.entries(values)) {
    if (typeof value === 'number' && value > 0) {
      query[key] = String(value)
    }
  }
  return query
}

function positiveNumber(value: unknown): number {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0
}

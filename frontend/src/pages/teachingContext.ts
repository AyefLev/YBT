export interface TeachingContextIds {
  course_id?: number | null
  chapter_id?: number | null
  session_id?: number | null
  knowledge_point_id?: number | null
}

export interface ScopedMaterial {
  id: number
  title: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
}

export interface TeachingContextChapter {
  id: number
  title: string
  summary: string
  sessions: TeachingContextSession[]
}

export interface TeachingContextSession {
  id: number
  title: string
  duration_minutes: number
  teaching_goal: string
}

export interface TeachingContextKnowledgePoint {
  id: number
  name: string
  description: string
  difficulty: string
  chapter_id: number | null
  session_id: number | null
}

export interface TeachingContextCourseDetail {
  subject: string
  chapters: TeachingContextChapter[]
  knowledge_points: TeachingContextKnowledgePoint[]
}

export interface LessonContextDefaults {
  chapter: string
  duration_minutes: number
  teaching_goal: string
  knowledge_point: string
}

export function filterMaterialsForContext<T extends ScopedMaterial>(
  materials: T[],
  context: TeachingContextIds,
): T[] {
  if (!context.course_id) return materials
  return materials.filter((material) => {
    if (material.course_id !== context.course_id) return false
    if (context.knowledge_point_id && material.knowledge_point_id === context.knowledge_point_id) {
      return true
    }
    if (context.session_id && material.session_id === context.session_id) return true
    if (context.chapter_id && material.chapter_id === context.chapter_id && !material.session_id) {
      return true
    }
    return !material.chapter_id && !material.session_id && !material.knowledge_point_id
  })
}

export function lessonDefaultsFromContext(
  course: TeachingContextCourseDetail,
  context: TeachingContextIds,
): LessonContextDefaults {
  const chapter = course.chapters.find((item) => item.id === context.chapter_id) ?? null
  const session =
    chapter?.sessions.find((item) => item.id === context.session_id) ??
    course.chapters.flatMap((item) => item.sessions).find((item) => item.id === context.session_id) ??
    null
  const point =
    course.knowledge_points.find((item) => item.id === context.knowledge_point_id) ?? null
  const goalParts = [session?.teaching_goal, point?.description].filter(Boolean)

  return {
    chapter: chapter?.title || session?.title || '',
    duration_minutes: session?.duration_minutes || 45,
    teaching_goal: goalParts.join('\n'),
    knowledge_point: point?.name || '',
  }
}

export interface CourseAssetSession {
  id: number
  title: string
  duration_minutes: number
  teaching_goal: string
  order_index: number
}

export interface CourseAssetChapter {
  id: number
  title: string
  summary: string
  order_index: number
  sessions: CourseAssetSession[]
}

export interface CourseAssetKnowledgePoint {
  id: number
  name: string
  description: string
  difficulty: string
  chapter_id: number | null
  session_id: number | null
}

export interface CourseAssetDetail {
  chapters: CourseAssetChapter[]
  knowledge_points: CourseAssetKnowledgePoint[]
}

export interface CourseAssetTreeSession extends CourseAssetSession {
  knowledgePoints: CourseAssetKnowledgePoint[]
}

export interface CourseAssetTreeChapter extends Omit<CourseAssetChapter, 'sessions'> {
  sessions: CourseAssetTreeSession[]
  knowledgePoints: CourseAssetKnowledgePoint[]
}

export interface CourseAssetTree {
  chapters: CourseAssetTreeChapter[]
  unassignedKnowledgePoints: CourseAssetKnowledgePoint[]
}

export function buildCourseAssetTree(detail: CourseAssetDetail): CourseAssetTree {
  const pointsBySession = new Map<number, CourseAssetKnowledgePoint[]>()
  const pointsByChapter = new Map<number, CourseAssetKnowledgePoint[]>()
  const unassignedKnowledgePoints: CourseAssetKnowledgePoint[] = []

  for (const point of detail.knowledge_points) {
    if (point.session_id) {
      appendToMap(pointsBySession, point.session_id, point)
    } else if (point.chapter_id) {
      appendToMap(pointsByChapter, point.chapter_id, point)
    } else {
      unassignedKnowledgePoints.push(point)
    }
  }

  return {
    chapters: detail.chapters.map((chapter) => ({
      ...chapter,
      sessions: chapter.sessions.map((session) => ({
        ...session,
        knowledgePoints: pointsBySession.get(session.id) ?? [],
      })),
      knowledgePoints: pointsByChapter.get(chapter.id) ?? [],
    })),
    unassignedKnowledgePoints,
  }
}

function appendToMap<TKey, TValue>(map: Map<TKey, TValue[]>, key: TKey, value: TValue) {
  const existing = map.get(key)
  if (existing) {
    existing.push(value)
  } else {
    map.set(key, [value])
  }
}

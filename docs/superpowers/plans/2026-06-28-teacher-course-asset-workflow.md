# Teacher Course Asset Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a teacher-centered full workflow from course tree context to materials, lesson generation, exercise generation, question-bank drafting, and classroom assignment publishing.

**Architecture:** Reuse the existing FastAPI course/material/lesson/exercise/classroom models and add only small backend validation around assignment publishing. Put most workflow improvements in focused Vue utilities/components: query context parsing, teaching context defaults, material selection, course-tree actions, and collapsible workbench navigation.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Vue 3, TypeScript, Vue Router, Vitest, Vite, Docker Compose.

---

## File Structure

- `backend/app/classrooms/service.py`: validate `exercise_id` when creating assignments.
- `backend/tests/test_classrooms_permissions.py`: backend regression tests for exercise-backed assignment publishing.
- `frontend/src/pages/contextQuery.ts`: parse/build course workflow query params.
- `frontend/src/pages/contextQuery.test.ts`: Vitest coverage for query behavior.
- `frontend/src/pages/teachingContext.ts`: derive defaults and scoped asset/material filters from a selected course tree.
- `frontend/src/pages/teachingContext.test.ts`: Vitest coverage for defaults and filters.
- `frontend/src/components/MaterialPicker.vue`: reusable material multi-select for lesson and exercise pages.
- `frontend/src/layouts/WorkbenchLayout.vue`: collapsible sidebar.
- `frontend/src/pages/CoursesPage.vue`: quick actions from course tree nodes.
- `frontend/src/pages/MaterialsPage.vue`: consume context query and prefill upload scope.
- `frontend/src/pages/LessonPage.vue`: consume context query, use `MaterialPicker`, add PPT generation action.
- `frontend/src/pages/ExercisePage.vue`: consume context query, use `MaterialPicker`, default lesson/material selection.
- `frontend/src/pages/ClassroomsPage.vue`: choose a saved exercise when publishing assignments.

## Task 1: Backend Assignment Exercise Validation

**Files:**
- Modify: `backend/app/classrooms/service.py`
- Test: `backend/tests/test_classrooms_permissions.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `backend/tests/test_classrooms_permissions.py`:

```python
def test_teacher_can_publish_assignment_from_own_course_exercise(client):
    teacher_headers = _auth_headers(client, username="teacher_publish_exercise")
    course = client.post(
        "/api/courses",
        headers=teacher_headers,
        json={"title": "高数强化", "subject": "数学", "exam_type": "考研"},
    ).json()
    classroom = client.post(
        "/api/classrooms",
        headers=teacher_headers,
        json={"name": "高数班", "course_id": course["id"]},
    ).json()
    exercise = client.post(
        "/api/exercises",
        headers=teacher_headers,
        json={
            "course_id": course["id"],
            "title": "导数练习",
            "subject": "高数",
            "knowledge_point": "导数",
            "question_type": "选择题",
            "difficulty": "medium",
            "content": "题干：求导\n答案：A",
        },
    ).json()

    response = client.post(
        f"/api/classrooms/{classroom['id']}/assignments",
        headers=teacher_headers,
        json={"title": "导数作业", "exercise_id": exercise["id"]},
    )

    assert response.status_code == 201
    assert response.json()["exercise_id"] == exercise["id"]


def test_teacher_cannot_publish_assignment_from_other_course_exercise(client):
    teacher_headers = _auth_headers(client, username="teacher_publish_mismatch")
    first_course = client.post(
        "/api/courses",
        headers=teacher_headers,
        json={"title": "高数", "subject": "数学", "exam_type": "考研"},
    ).json()
    second_course = client.post(
        "/api/courses",
        headers=teacher_headers,
        json={"title": "英语", "subject": "英语", "exam_type": "考研"},
    ).json()
    classroom = client.post(
        "/api/classrooms",
        headers=teacher_headers,
        json={"name": "高数班", "course_id": first_course["id"]},
    ).json()
    exercise = client.post(
        "/api/exercises",
        headers=teacher_headers,
        json={
            "course_id": second_course["id"],
            "title": "阅读练习",
            "subject": "英语",
            "knowledge_point": "阅读",
            "question_type": "选择题",
            "difficulty": "medium",
            "content": "题干：阅读\n答案：A",
        },
    ).json()

    response = client.post(
        f"/api/classrooms/{classroom['id']}/assignments",
        headers=teacher_headers,
        json={"title": "错误作业", "exercise_id": exercise["id"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Exercise does not belong to classroom course"
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_classrooms_permissions.py::test_teacher_can_publish_assignment_from_own_course_exercise tests\test_classrooms_permissions.py::test_teacher_cannot_publish_assignment_from_other_course_exercise -q --basetemp .pytest-tmp
```

Expected: the mismatch test fails because `create_assignment()` does not validate exercise course scope yet.

- [ ] **Step 3: Implement minimal validation**

In `backend/app/classrooms/service.py`, import `Exercise`:

```python
from app.exercises.models import Exercise
```

Before constructing `Assignment` in `create_assignment()`, add:

```python
    if payload.exercise_id is not None:
        exercise = db.get(Exercise, payload.exercise_id)
        if exercise is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
        if (
            "exercise:view_all" not in classroom.teacher.permission_codes
            and exercise.owner_id != classroom.teacher_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
        if classroom.course_id is not None and exercise.course_id not in {None, classroom.course_id}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exercise does not belong to classroom course",
            )
```

If `classroom.teacher` is not loaded, use `classroom.teacher_id` and skip permission-code access; owner check is enough for teacher-created assignment in this path.

- [ ] **Step 4: Run tests and verify GREEN**

Run the same two tests. Expected: both pass.

## Task 2: Context Query Utilities

**Files:**
- Create: `frontend/src/pages/contextQuery.ts`
- Create: `frontend/src/pages/contextQuery.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/pages/contextQuery.test.ts`:

```ts
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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
cd frontend
npm.cmd test -- src/pages/contextQuery.test.ts
```

Expected: fails because `contextQuery.ts` does not exist.

- [ ] **Step 3: Implement utility**

Create `frontend/src/pages/contextQuery.ts`:

```ts
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

export function buildTeachingContextQuery(values: Partial<Record<keyof TeachingContextQuery, number | null | undefined>>): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  for (const [key, value] of Object.entries(values)) {
    if (typeof value === 'number' && value > 0) query[key] = String(value)
  }
  return query
}

function positiveNumber(value: unknown): number {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0
}
```

- [ ] **Step 4: Run tests and verify GREEN**

Run `npm.cmd test -- src/pages/contextQuery.test.ts`. Expected: pass.

## Task 3: Teaching Context Filters

**Files:**
- Create: `frontend/src/pages/teachingContext.ts`
- Create: `frontend/src/pages/teachingContext.test.ts`

- [ ] **Step 1: Write failing tests**

Create tests that verify current-node material filtering and default knowledge point names:

```ts
import { describe, expect, test } from 'vitest'

import { filterMaterialsForContext, lessonDefaultsFromContext } from './teachingContext'

describe('teaching context helpers', () => {
  test('filters materials linked to the selected course node', () => {
    const materials = [
      { id: 1, title: '课次材料', course_id: 1, chapter_id: 2, session_id: 3, knowledge_point_id: null },
      { id: 2, title: '课程材料', course_id: 1, chapter_id: null, session_id: null, knowledge_point_id: null },
      { id: 3, title: '其他课程', course_id: 9, chapter_id: null, session_id: null, knowledge_point_id: null },
    ]

    expect(filterMaterialsForContext(materials, { course_id: 1, chapter_id: 2, session_id: 3, knowledge_point_id: 0 }).map((item) => item.id)).toEqual([1, 2])
  })

  test('derives lesson defaults from selected course detail', () => {
    const defaults = lessonDefaultsFromContext(
      {
        subject: '高数',
        chapters: [{ id: 2, title: '导数', summary: '', sessions: [{ id: 3, title: '导数定义', duration_minutes: 60, teaching_goal: '掌握导数定义' }] }],
        knowledge_points: [{ id: 4, name: '导数定义', description: '理解极限定义', difficulty: 'basic', chapter_id: 2, session_id: 3 }],
      },
      { chapter_id: 2, session_id: 3, knowledge_point_id: 4 },
    )

    expect(defaults.chapter).toBe('导数')
    expect(defaults.duration_minutes).toBe(60)
    expect(defaults.teaching_goal).toContain('掌握导数定义')
  })
})
```

- [ ] **Step 2: Run tests and verify RED**

Run `npm.cmd test -- src/pages/teachingContext.test.ts`. Expected: fails because helper file does not exist.

- [ ] **Step 3: Implement helpers**

Create helpers with minimal structural interfaces and exported functions:

```ts
export interface TeachingContextIds {
  course_id?: number
  chapter_id?: number
  session_id?: number
  knowledge_point_id?: number
}

export interface ScopedMaterial {
  id: number
  title: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
}

export function filterMaterialsForContext<T extends ScopedMaterial>(materials: T[], context: TeachingContextIds): T[] {
  if (!context.course_id) return materials
  return materials.filter((material) => {
    if (material.course_id !== context.course_id) return false
    if (context.knowledge_point_id && material.knowledge_point_id === context.knowledge_point_id) return true
    if (context.session_id && material.session_id === context.session_id) return true
    if (context.chapter_id && material.chapter_id === context.chapter_id && !material.session_id) return true
    return !material.chapter_id && !material.session_id && !material.knowledge_point_id
  })
}
```

Also add `lessonDefaultsFromContext()` using chapter/session/knowledge point lookup.

- [ ] **Step 4: Run tests and verify GREEN**

Run `npm.cmd test -- src/pages/teachingContext.test.ts`. Expected: pass.

## Task 4: Reusable MaterialPicker

**Files:**
- Create: `frontend/src/components/MaterialPicker.vue`
- Modify: `frontend/src/pages/LessonPage.vue`
- Modify: `frontend/src/pages/ExercisePage.vue`

- [ ] **Step 1: Add component**

Create a component with props:

```ts
interface MaterialOption {
  id: number
  title: string
  resource_scope: string
  parse_status: string
  course_id: number | null
  chapter_id: number | null
  session_id: number | null
  knowledge_point_id: number | null
}
```

It accepts `materials`, `modelValue`, and `contextIds`, emits `update:modelValue`, and shows “当前节点资料 / 全部可用资料” segmented buttons.

- [ ] **Step 2: Wire LessonPage**

In `LessonPage.vue`, replace manual `material_ids` input as the primary UI with:

```vue
<MaterialPicker
  v-model="selectedMaterialIds"
  :materials="materials"
  :context-ids="contextIds"
/>
```

Keep the manual ID input under an “高级设置” block and sync it from `selectedMaterialIds`.

- [ ] **Step 3: Wire ExercisePage**

Use the same `MaterialPicker` and pass selected ids to generation and save payloads.

- [ ] **Step 4: Verify**

Run:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

Expected: TypeScript build passes.

## Task 5: Course Tree Quick Actions

**Files:**
- Modify: `frontend/src/pages/CoursesPage.vue`
- Modify: `frontend/src/pages/courseStructure.ts`
- Test: `frontend/src/pages/courseStructure.test.ts`

- [ ] **Step 1: Write failing test for action query**

Extend `courseStructure.test.ts` with:

```ts
import { buildTeachingContextQuery } from './contextQuery'

test('builds context query for a course session action', () => {
  expect(buildTeachingContextQuery({ course_id: 1, chapter_id: 2, session_id: 3 })).toEqual({
    course_id: '1',
    chapter_id: '2',
    session_id: '3',
  })
})
```

- [ ] **Step 2: Run RED**

Run `npm.cmd test -- src/pages/courseStructure.test.ts`. Expected: fails until `contextQuery.ts` exists from Task 2.

- [ ] **Step 3: Add quick action buttons**

In each session and knowledge point block, add buttons/links:

```vue
<RouterLink :to="{ path: '/dashboard/materials', query: buildTeachingContextQuery({...}) }">上传资料</RouterLink>
<RouterLink :to="{ path: '/dashboard/lesson', query: buildTeachingContextQuery({...}) }">生成教案</RouterLink>
<RouterLink :to="{ path: '/dashboard/exercise', query: buildTeachingContextQuery({...}) }">生成习题</RouterLink>
<RouterLink :to="{ path: '/dashboard/classrooms', query: buildTeachingContextQuery({...}) }">发布作业</RouterLink>
```

- [ ] **Step 4: Verify**

Run `npm.cmd run build`. Expected: pass.

## Task 6: Query Context in Materials, Lesson, and Exercise Pages

**Files:**
- Modify: `frontend/src/pages/MaterialsPage.vue`
- Modify: `frontend/src/pages/LessonPage.vue`
- Modify: `frontend/src/pages/ExercisePage.vue`

- [ ] **Step 1: MaterialsPage**

On mount, parse `useRoute().query`, prefill `course_id/chapter_id/session_id/knowledge_point_id`, and after upload show a return link if `return_to` exists.

- [ ] **Step 2: LessonPage**

On mount, parse query, load selected course detail, apply defaults:

```ts
form.course_id = context.course_id
form.chapter_id = context.chapter_id
form.session_id = context.session_id
form.knowledge_point_id = context.knowledge_point_id
```

Then derive default `chapter`, `duration_minutes`, and `teaching_goal` from `lessonDefaultsFromContext()`.

- [ ] **Step 3: ExercisePage**

On mount, parse query, load selected course detail, default `lesson_id` to query `lesson_id` or latest lesson matching current session.

- [ ] **Step 4: Verify**

Run:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

Expected: pass.

## Task 7: Lesson PPT Action

**Files:**
- Modify: `frontend/src/pages/LessonPage.vue`

- [ ] **Step 1: Add API action**

After a lesson is saved and selected, show “生成 PPT” button:

```ts
async function generatePresentation() {
  if (!selectedLessonId.value) return
  presentationMessage.value = ''
  const result = await api<{ lesson_id: number; queued: boolean; message: string }>(
    `/api/presentations/lesson/${selectedLessonId.value}/generate`,
    { method: 'POST', body: JSON.stringify({ template_name: 'default' }) },
  )
  presentationMessage.value = result.message
}
```

- [ ] **Step 2: Verify**

Run `npm.cmd run build`. Expected: pass.

## Task 8: Exercise-Backed Assignment Publishing

**Files:**
- Modify: `frontend/src/pages/ClassroomsPage.vue`

- [ ] **Step 1: Load exercises**

Load `/api/exercises` on mount and keep an `exercises` ref.

- [ ] **Step 2: Filter exercises by selected classroom**

Add computed:

```ts
const publishableExercises = computed(() =>
  exercises.value.filter((exercise) => !selectedClass.value?.course_id || exercise.course_id === selectedClass.value.course_id),
)
```

- [ ] **Step 3: Add select to publish form**

Add a select for `exercise_id`; when changed, auto-fill assignment title and instructions from exercise title/content summary.

- [ ] **Step 4: Submit exercise_id**

Include `exercise_id: selectedExerciseId.value || null` in the assignment payload.

- [ ] **Step 5: Verify**

Run `npm.cmd run build`. Expected: pass.

## Task 9: Collapsible Workbench Sidebar

**Files:**
- Modify: `frontend/src/layouts/WorkbenchLayout.vue`

- [ ] **Step 1: Add state**

Add:

```ts
const SIDEBAR_COLLAPSED_KEY = 'workbench-sidebar-collapsed'
const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true')

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(sidebarCollapsed.value))
}
```

- [ ] **Step 2: Add button and classes**

Bind class:

```vue
<div class="workbench" :class="{ collapsed: sidebarCollapsed }">
```

Add a button in the sidebar header with text `收起` / `展开`.

- [ ] **Step 3: CSS**

Add a collapsed grid width around `88px`; hide secondary labels and account details when collapsed. Preserve mobile layout under `860px`.

- [ ] **Step 4: Verify**

Run `npm.cmd run build`. Expected: pass.

## Task 10: Final Verification and Push

**Files:**
- No source edits unless verification finds failures.

- [ ] **Step 1: Backend targeted tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_classrooms_permissions.py tests\test_courses.py tests\test_lessons.py tests\test_exercises_exports.py -q --basetemp .pytest-tmp
```

- [ ] **Step 2: Frontend tests and build**

Run:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

- [ ] **Step 3: Docker config**

Run:

```powershell
cd ..
docker compose config
```

Do not paste expanded secret values into public docs.

- [ ] **Step 4: Remote safety check**

Run:

```powershell
git fetch origin main
git status --short --branch
git log --oneline --decorate --graph --all -n 12
```

If remote `main` has commits and local branch has no base, integrate without force-push.

- [ ] **Step 5: Commit and push**

Stage only intended source, tests, spec, and plan files. Commit:

```powershell
git add backend frontend docs README.md docker-compose.yml infra .dockerignore .gitignore
git commit -m "feat: connect teacher course asset workflow"
git push origin main
```

If authentication fails, keep the local commit and report the exact push failure.

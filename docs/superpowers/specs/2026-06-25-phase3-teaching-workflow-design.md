# Phase 3 Teaching Workflow Design

Date: 2026-06-25

## Goal

Phase 3 upgrades Yanbeitong AI from an AI-assisted content generator into a minimal institutional teaching-research workflow system.

The goal is to demonstrate the market-facing difference identified in the research report:

> General-purpose LLMs can generate one-off lesson plans or exercises. Yanbeitong AI should manage an institution's reusable course structure, question bank, review workflow, and delivery artifacts.

This phase should produce a working institutional loop:

1. Build a course structure.
2. Attach materials and generated content to that structure.
3. Save generated exercises as reusable question-bank items.
4. Submit lesson plans and questions for teaching-research review.
5. Approve or reject content with review comments.
6. Export approved course or practice artifacts.

## Product Positioning

Phase 3 supports the positioning:

> Adult postgraduate entrance exam and continuing-education institutions use Yanbeitong AI to standardize teaching-research production, not just generate temporary text.

The product should make these benefits visible:

- Institutional course assets become structured and reusable.
- AI-generated questions become managed question-bank records.
- Teaching managers can review and approve content before use.
- Teachers can reuse approved course and question assets.
- Exports become closer to real institutional delivery documents.

## Scope

### 1. Course Structure Management

Add a lightweight course hierarchy:

- Course
- Chapter
- Lesson session
- Knowledge point

This hierarchy should be institution-friendly but not over-modeled.

#### Course

Represents a sellable or teachable course line, such as:

- 考研英语一基础班
- 考研数学强化班
- 专升本英语冲刺班

Fields:

- `id`
- `owner_id`
- `title`
- `subject`
- `exam_type`
- `description`
- `status`: `draft`, `active`, `archived`
- `created_at`
- `updated_at`

#### Chapter

Represents a unit inside a course.

Fields:

- `id`
- `course_id`
- `title`
- `summary`
- `order_index`
- `created_at`
- `updated_at`

#### Lesson Session

Represents a teachable class session under a chapter.

Fields:

- `id`
- `course_id`
- `chapter_id`
- `title`
- `duration_minutes`
- `teaching_goal`
- `order_index`
- `lesson_id`: optional link to an existing generated/saved lesson plan
- `created_at`
- `updated_at`

#### Knowledge Point

Represents a reusable teaching concept.

Fields:

- `id`
- `course_id`
- `chapter_id`: optional
- `session_id`: optional
- `name`
- `description`
- `difficulty`: `basic`, `medium`, `advanced`
- `created_at`
- `updated_at`

Rules:

- A course can exist without chapters.
- A chapter must belong to a course.
- A lesson session must belong to a course and chapter.
- A knowledge point must belong to a course and can optionally link to a chapter or session.
- Deleting a course should not silently delete saved lesson plans or exercises. It can delete only the course hierarchy records, while linked content remains owned by the user.

### 2. Course Asset Links

Materials and generated content should be attachable to the course hierarchy.

Initial link types:

- Course material link
- Course lesson link
- Course exercise/question link

For Phase 3, implement these conservatively:

- Materials can be linked to course/chapter/session/knowledge point.
- Existing lessons can be linked to sessions.
- Question-bank items can be linked to course/chapter/session/knowledge point.

This avoids rewriting existing material, lesson, and exercise modules.

### 3. Question Bank

Add a structured question bank separate from the free-form saved exercise document.

Why:

- Current exercise generation returns one large text block.
- Institutions need reusable individual questions.
- Question-bank records support search, review, reuse, and export.

Fields:

- `id`
- `owner_id`
- `course_id`: optional
- `chapter_id`: optional
- `session_id`: optional
- `knowledge_point_id`: optional
- `source_exercise_id`: optional
- `source_material_id`: optional
- `title`
- `subject`
- `question_type`
- `difficulty`
- `stem`
- `options_json`: list of options for objective questions
- `answer`
- `analysis`
- `tags_json`
- `status`: `draft`, `pending_review`, `approved`, `rejected`
- `reviewer_id`: optional
- `review_comment`
- `reviewed_at`
- `created_at`
- `updated_at`

Supported first-version question types:

- `single_choice`
- `multiple_choice`
- `fill_blank`
- `short_answer`
- `true_false`

The system does not need perfect automatic parsing from generated exercise text in Phase 3. It should support:

- Creating question-bank items manually.
- Creating question-bank items from a structured form.
- Optionally "save selected generated exercise as question-bank draft" when the frontend has enough text.

### 4. Teaching-Research Review Workflow

Add a shared review model for content that needs teaching-research approval.

Reviewable resource types:

- `lesson`
- `question`

Review statuses:

- `draft`
- `pending_review`
- `approved`
- `rejected`

Review actions:

- Submit for review.
- Approve.
- Reject with comment.
- Return to draft after rejection.

Permissions:

- Teachers can create and edit their own drafts.
- Teachers can submit their own lessons/questions for review.
- Teaching managers and admins can review.
- Review actions should be logged.

Recommended permission codes:

- Existing teacher content creation permissions remain usable.
- Add `review:manage` for approval/rejection.
- Add this permission to `admin` and `teaching_manager`.

Audit fields:

- reviewer id
- review comment
- reviewed at
- status transition

### 5. Lightweight Template Export

Phase 3 should not build a template designer.

Instead, add fixed-format exports that demonstrate institutional delivery:

- Course outline DOCX
- Lesson session package DOCX
- Question practice package DOCX

Initial export requirements:

#### Course Outline Export

Includes:

- course title
- subject
- exam type
- description
- chapters
- sessions
- knowledge points

#### Practice Package Export

Includes:

- course/chapter/session metadata if selected
- question list
- answers
- analysis

This creates a visible customer-facing artifact without building a complex template system.

### 6. Frontend Experience

Add pages or page sections for:

- Course management
- Course detail
- Question bank
- Review queue

Recommended navigation:

- 知识库
- 课程体系
- 题库
- 教研审核
- 备课
- 习题
- 日志/管理

#### Course Page

Capabilities:

- list courses
- create/edit/archive course
- view course detail
- manage chapters
- manage sessions
- manage knowledge points
- link materials
- link saved lesson plans

#### Question Bank Page

Capabilities:

- list questions
- create/edit question
- filter by course, knowledge point, type, difficulty, status
- submit question for review
- export selected questions

#### Review Queue Page

Capabilities:

- list pending lessons and questions
- open detail
- approve
- reject with comment

### 7. API Surface

Suggested endpoints:

#### Courses

- `GET /api/courses`
- `POST /api/courses`
- `GET /api/courses/{course_id}`
- `PATCH /api/courses/{course_id}`
- `DELETE /api/courses/{course_id}` or archive-only endpoint

#### Chapters

- `POST /api/courses/{course_id}/chapters`
- `PATCH /api/chapters/{chapter_id}`
- `DELETE /api/chapters/{chapter_id}`

#### Sessions

- `POST /api/chapters/{chapter_id}/sessions`
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`

#### Knowledge Points

- `POST /api/courses/{course_id}/knowledge-points`
- `PATCH /api/knowledge-points/{knowledge_point_id}`
- `DELETE /api/knowledge-points/{knowledge_point_id}`

#### Course Asset Links

- `POST /api/courses/{course_id}/materials/{material_id}`
- `DELETE /api/courses/{course_id}/materials/{material_id}`
- `POST /api/sessions/{session_id}/lessons/{lesson_id}`

#### Question Bank

- `GET /api/questions`
- `POST /api/questions`
- `GET /api/questions/{question_id}`
- `PATCH /api/questions/{question_id}`
- `DELETE /api/questions/{question_id}`
- `POST /api/questions/{question_id}/submit-review`

#### Review

- `GET /api/reviews/pending`
- `POST /api/reviews/{resource_type}/{resource_id}/approve`
- `POST /api/reviews/{resource_type}/{resource_id}/reject`
- `POST /api/reviews/{resource_type}/{resource_id}/return-draft`

#### Exports

- `POST /api/exports/course/{course_id}/outline-docx`
- `POST /api/exports/questions/docx`

### 8. Data Model Boundaries

Keep Phase 3 bounded:

- Do not introduce multi-tenant organization tables yet.
- Do not rewrite existing lesson/exercise versioning.
- Do not introduce a vector database.
- Do not add student accounts or student learning records.
- Do not add billing or subscription controls.

The data model should extend the current owner-scoped model.

Each new record should have `owner_id` or be reachable through an owner-owned parent.

### 9. Integration With Existing Features

#### Knowledge Base

Materials remain the source of institutional content.

Phase 3 adds links from materials to course hierarchy. It does not need to alter parsing.

#### Lesson Generation

Generated lesson content can be saved as before.

Phase 3 adds:

- optional linking saved lesson to a lesson session
- review status for saved lesson
- submit/approve/reject workflow

#### Exercise Generation

Generated exercise content remains available as a full document.

Phase 3 adds:

- question-bank creation from structured form
- no automatic parsing of free-form exercise text into individual questions

#### Logs

Operation logs should record:

- course create/update/archive
- question create/update/delete
- review submit/approve/reject
- export course outline/practice package

### 10. Error Handling

Expected behaviors:

- Cross-user access returns 404, consistent with existing lesson/exercise ownership behavior.
- Review actions on missing resources return 404.
- Review actions on invalid status transitions return 400.
- Approving/rejecting without `review:manage` returns 403.
- Deleting a parent hierarchy node with children should either:
  - return 400 with a clear message, or
  - perform explicit cascade only for hierarchy records.

Recommendation:

- Course deletion should be archive-first.
- Chapter/session/knowledge point deletion should be blocked when linked questions or lessons exist.

### 11. Testing Strategy

Backend tests:

- course CRUD and ownership scoping
- chapter/session/knowledge point creation and ordering
- material and lesson linking
- question-bank CRUD and filters
- review permission enforcement
- valid and invalid review transitions
- DOCX export records and content
- operation logs for key workflow actions

Frontend tests:

- navigation includes new pages
- API client handles new endpoints where helper logic exists
- component-level tests only if the repo already supports them; otherwise use build verification

Manual demo tests:

1. Create a course.
2. Add chapter, session, and knowledge point.
3. Upload/link a material.
4. Generate/save a lesson and link it to a session.
5. Create question-bank items.
6. Submit one question for review.
7. Log in as teaching manager/admin and approve it.
8. Export a question practice package.

### 12. Demo Narrative

The Phase 3 demo should tell this story:

1. A training institution creates a course line.
2. The institution uploads its materials and links them to course units.
3. Teachers generate lesson plans and question drafts.
4. Generated items become reusable assets instead of disposable text.
5. A teaching manager reviews and approves the content.
6. The institution exports standardized teaching artifacts.

This story directly addresses the market concern:

> The system is not competing with a general-purpose chatbot on text generation. It is managing the institutional teaching-research workflow around AI-generated and human-curated content.

## Non-Goals

Phase 3 will not include:

- student accounts
- student homework submission
- wrong-question analytics
- class-level learning dashboards
- multi-tenant organizations
- payment plans or quota billing
- complex visual template designer
- OCR/image understanding
- vector database retrieval

These are explicitly out of scope for Phase 3 and should only be considered after the institutional teaching workflow is stable.

## Success Criteria

Phase 3 is successful when:

- A user can build a course hierarchy.
- Materials, lessons, and questions can be associated with that hierarchy.
- Individual question-bank items can be created, filtered, reviewed, and exported.
- Lesson and question review statuses are visible and enforceable.
- Teaching managers/admins can approve or reject content.
- The demo clearly shows how the system creates reusable institutional assets.

## Risks

### Scope Creep

Course, question bank, review, export, and dashboards can each become large products. Phase 3 must keep to the minimal institutional workflow.

Mitigation:

- No student-side features.
- No template designer.
- No advanced question parsing.
- No multi-tenant organization model.

### Data Model Complexity

Course hierarchy and existing lesson/exercise records can become tangled.

Mitigation:

- Use link tables instead of rewriting existing lesson/exercise models.
- Keep owner-scoped access rules.
- Avoid hard deletes when linked content exists.

### Review Workflow Ambiguity

Lessons and questions are different resources but need similar review behavior.

Mitigation:

- Use shared status values and shared service functions.
- Keep API routes explicit by resource type.

### Frontend Complexity

Adding too many screens can overwhelm the current MVP UI.

Mitigation:

- Add focused pages: course detail, question bank, review queue.
- Avoid complex drag-and-drop or tree editors.
- Use simple forms and tables.

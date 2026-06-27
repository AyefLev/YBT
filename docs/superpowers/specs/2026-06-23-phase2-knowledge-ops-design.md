# Phase 2 Knowledge Ops Design

## Goal

Upgrade the Yanbeitong MVP from a synchronous demo app into a stronger teaching-research system that can demonstrate:

- Managed institutional knowledge base.
- Better document parsing and provenance.
- Multi-AI generation review to reduce hallucination risk.
- Asynchronous work execution.
- Observable job/model/operation logs.
- API-first backend surface.
- Docker-based startup for classroom demonstration.

## Scope

### 1. Knowledge Base Management

Materials become managed resources instead of upload-only records.

Required API surface:

- `GET /api/materials`: list current user's materials.
- `GET /api/materials/{id}`: get one material.
- `GET /api/materials/{id}/chunks`: inspect parsed chunks.
- `DELETE /api/materials/{id}`: delete material and chunks.
- `POST /api/materials/{id}/reparse`: enqueue parsing again.
- `POST /api/materials/upload`: accept metadata and file upload.

Material metadata:

- `title`
- `subject`
- `purpose`
- `tags`
- `file_name`
- `file_type`
- `parse_status`
- `parse_error`
- `chunk_count`
- timestamps

Search results should show where a result came from, including material id, title, and page or slide provenance when available.

### 2. Document Parsing

Parsing remains local and deterministic for MVP reliability, but supports a broader file surface:

- Text and Markdown: paragraph-aware chunking.
- DOCX: paragraph extraction.
- PDF: page-aware extraction when parser dependencies are installed.
- PPTX: slide-aware extraction when parser dependencies are installed.

The parser records:

- chunk index
- content
- page number for PDFs
- slide number for PPTX
- approximate token count
- parse error when parsing fails

Unsupported or empty files should not crash the app. They should move the material into `empty` or `failed` status with a visible reason.

### 3. Multi-AI Collaboration

Use a lightweight Generate -> Review -> Revise model flow.

For Phase 2, this can run on the same provider and even the same model, but the software must treat the roles as independently configurable:

- generator model
- reviewer model
- reviser model

Suggested environment variables:

- `LLM_GENERATE_MODEL`
- `LLM_REVIEW_MODEL`
- `LLM_REVISE_MODEL`
- `LLM_MULTI_AGENT_REVIEW`

Generated lesson plans and exercises should return a review object with:

- review status
- reviewer model
- warnings
- suggestions
- revised content when enabled and needed

The first production behavior should be conservative: generate content, review it, and only revise when the review reports material issues. If the real API fails and mock fallback is enabled, the multi-AI review also falls back to deterministic mock output.

### 4. Asynchronous Execution

Long work should not block the request path.

Phase 2 uses the local FastAPI background execution model backed by worker threads. This avoids Redis/Celery operational overhead while still satisfying the "threaded async work" requirement for classroom demonstration.

Initial async jobs:

- material parsing after upload
- material reparsing

Job states:

- `pending`
- `running`
- `succeeded`
- `failed`

Material parse states:

- `pending`
- `parsing`
- `parsed`
- `empty`
- `failed`

### 5. Observability Logs

Add first-class observability around operations, model calls, and background jobs.

Existing operation/model logs remain useful. Phase 2 adds job logs:

- job type
- status
- resource type and resource id
- user id
- details
- error message
- start/end/duration

Required API surface:

- `GET /api/logs/jobs`

This gives the demo a visible answer to: "How do we know what happened when the system parsed, generated, reviewed, or failed?"

### 6. API-First System

The backend should be demonstrable from Swagger UI at `/docs`, not only through the frontend.

The Phase 2 API should make these workflows testable:

- login
- upload material
- inspect parse status
- inspect chunks
- search knowledge base
- generate lesson/exercise
- see model review
- inspect operation/model/job logs

### 7. Docker Startup

Add container startup as the default demo path:

- backend container
- frontend container
- shared local data volume
- environment-based AI config

Expected demo command:

```powershell
docker compose up --build
```

Expected exposed services:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Non-Goals

- No vector database in Phase 2.
- No Celery/Redis unless local threaded jobs prove insufficient.
- No OCR or image understanding requirement yet.
- No mandatory multi-provider setup; multi-AI roles are configurable and can initially use one compatible OpenAI-style provider.

## Risks

- Background parsing means upload responses may return before chunks are ready. The frontend must show clear pending/parsing states.
- Optional PDF/PPTX dependencies may not be installed in every environment. Parser failures must be observable.
- Multi-AI review can increase API cost and latency. It must be switchable by environment variable.


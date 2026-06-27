# Phase 2 Knowledge Ops Implementation Plan

## Commit 1: Design and Plan

- Add Phase 2 design document.
- Add this implementation plan.

Verification:

- `git status --short`

## Commit 2: Backend Tests

Write failing tests before implementation for:

- material metadata upload
- material list/detail/chunk APIs
- delete and reparse APIs
- parse error visibility
- search result provenance
- job logs API
- multi-AI review response on lesson/exercise generation

Target files:

- `backend/tests/test_materials.py`
- `backend/tests/test_retrieval.py`
- `backend/tests/test_logs.py`
- `backend/tests/test_lessons.py`
- `backend/tests/test_exercises.py`

Verification:

- Run targeted pytest commands and confirm the new assertions fail for the expected missing behavior.

## Commit 3: Backend Implementation

Implement:

- material metadata columns and SQLite compatibility migration
- material CRUD and chunk APIs
- parser refactor with status/error/provenance support
- threaded background parse/reparse execution
- job log model, schemas, service, API
- retrieval result material title/source fields
- multi-AI Generate -> Review -> optional Revise service support
- response schemas for AI review

Verification:

- `python -m pytest -v`

## Commit 4: Frontend Knowledge Base and Review UI

Implement:

- material metadata upload form
- material list with status, tags, chunk count, errors
- delete/reparse actions
- chunk inspection
- search results with source title and page/slide
- lesson/exercise review display

Verification:

- frontend tests if present
- `npm.cmd run build`

## Commit 5: Dockerization

Implement:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- root `docker-compose.yml`
- `.dockerignore`
- Vite proxy target env support
- README demo instructions

Verification:

- configuration review
- if Docker is available, run `docker compose config`
- otherwise document that Docker runtime verification was not executed

## Final Verification

Run:

- backend tests
- frontend build
- docker compose config when Docker is installed
- `git status --short`

Final response should include:

- what changed
- how to run locally
- how to run with Docker
- where to configure real AI API keys
- tests run and any limitations


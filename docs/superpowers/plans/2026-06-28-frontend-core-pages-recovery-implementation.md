# Frontend Core Pages Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the lesson and exercise page scripts without losing the redesigned templates, make the frontend production build pass, and standardize embedding configuration on `text-embedding-v4`.

**Architecture:** Recover the known-good `<script setup>` blocks from parent commit `8fd45e9` and prepend them to the current templates. Use a source-structure regression test to prevent another script-only deletion, then use TypeScript build errors to make only the compatibility adaptations required by the redesigned templates.

**Tech Stack:** Vue 3, TypeScript, Vitest, Vite, Docker Compose, Nginx, FastAPI

---

## File map

- Create `frontend/src/pages/corePageScripts.test.ts`: regression guard for the two Vue SFC script blocks.
- Modify `frontend/src/pages/LessonPage.vue`: restore lesson-generation state and handlers.
- Modify `frontend/src/pages/ExercisePage.vue`: restore exercise-generation state and handlers.
- Modify `docker-compose.yml`: set Compose embedding model to `text-embedding-v4`.
- Modify `backend/.env.example`: document `text-embedding-v4`.
- Modify `README.md`: document the same model selection.

### Task 1: Add the failing regression test

**Files:**
- Create: `frontend/src/pages/corePageScripts.test.ts`
- Test: `frontend/src/pages/corePageScripts.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { readFileSync } from 'node:fs'

import { describe, expect, it } from 'vitest'

const pageRequirements = [
  {
    file: new URL('./LessonPage.vue', import.meta.url),
    bindings: ['const form = reactive(', 'async function generateLesson(', 'async function saveLesson('],
  },
  {
    file: new URL('./ExercisePage.vue', import.meta.url),
    bindings: ['const form = reactive(', 'async function generateExercise(', 'async function saveExercise('],
  },
]

describe('core generation pages', () => {
  it.each(pageRequirements)('keeps the script bindings required by $file', ({ file, bindings }) => {
    const source = readFileSync(file, 'utf8')

    expect(source).toContain('<script setup lang="ts">')
    for (const binding of bindings) {
      expect(source).toContain(binding)
    }
  })
})
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
docker compose exec -T frontend npm test -- src/pages/corePageScripts.test.ts
```

Expected: two failures because neither SFC contains `<script setup lang="ts">`.

- [ ] **Step 3: Commit the red test**

Stage only `frontend/src/pages/corePageScripts.test.ts` and commit it without including existing unrelated worktree changes.

### Task 2: Restore the known-good script blocks

**Files:**
- Modify: `frontend/src/pages/LessonPage.vue`
- Modify: `frontend/src/pages/ExercisePage.vue`
- Test: `frontend/src/pages/corePageScripts.test.ts`

- [ ] **Step 1: Extract each parent script block**

Read each file at revision `8fd45e9`, retain everything from the first line through the first `</script>`, and prepend that text plus one blank line to the current file.

- [ ] **Step 2: Run the focused regression test**

Run:

```powershell
docker compose exec -T frontend npm test -- src/pages/corePageScripts.test.ts
```

Expected: both parameterized cases pass.

- [ ] **Step 3: Run the TypeScript production build**

Run:

```powershell
docker compose exec -T frontend npm run build
```

Expected: either exit 0 or a short list of bindings introduced by the redesigned templates but absent from the parent scripts.

- [ ] **Step 4: Make only required compatibility adaptations**

For every remaining `TS2339`, map the current template binding to the equivalent parent-script state or add a computed property/thin handler with the exact name used by the template. Do not change API payloads or backend contracts.

- [ ] **Step 5: Re-run focused test and build**

Expected: regression test passes and `npm run build` exits 0.

- [ ] **Step 6: Commit the page recovery**

Stage only the two Vue pages and commit them.

### Task 3: Standardize embedding configuration

**Files:**
- Modify: `docker-compose.yml`
- Modify: `backend/.env.example`
- Modify: `README.md`

- [ ] **Step 1: Replace model defaults**

Change every user-facing/default `EMBEDDING_MODEL=local-hash-embedding-v1` or YAML equivalent to `text-embedding-v4`. Keep `EMBEDDING_DIMENSIONS=128` in Compose so it remains compatible with the existing Qdrant collection.

- [ ] **Step 2: Verify no reranker or old default remains**

Run:

```powershell
rg -n "gte-rerank|local-hash-embedding-v1|text-embedding-v4" docker-compose.yml backend/.env.example README.md
```

Expected: `text-embedding-v4` appears in all three files; neither unwanted model appears.

- [ ] **Step 3: Commit the configuration change**

Stage only the three configuration/documentation files and commit them.

### Task 4: Full frontend verification

**Files:**
- Test: all files under `frontend/src/**/*.test.ts`

- [ ] **Step 1: Run all unit tests**

Run:

```powershell
docker compose exec -T frontend npm test
```

Expected: all test files pass with zero failures.

- [ ] **Step 2: Run the production build**

Run:

```powershell
docker compose exec -T frontend npm run build
```

Expected: `vue-tsc --noEmit && vite build` exits 0 and emits `dist/`.

- [ ] **Step 3: Inspect the final diff**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; existing `WorkbenchLayout` changes remain present and uncommitted unless already committed independently.

### Task 5: Docker and browser verification

**Files:**
- Runtime verification only

- [ ] **Step 1: Rebuild affected services**

Run:

```powershell
docker compose up -d --build frontend backend worker gateway
```

Expected: Compose rebuilds/recreates affected containers without startup failure.

- [ ] **Step 2: Verify service health**

Run:

```powershell
docker compose ps
```

Expected: backend, frontend, worker, gateway, PostgreSQL, Redis and Qdrant are running; backend is healthy.

- [ ] **Step 3: Verify browser behavior**

Log in through `http://localhost:8080/login`, visit:

- `/dashboard/lesson/generate`
- `/dashboard/lesson/records`
- `/dashboard/exercise/generate`
- `/dashboard/exercise/records`

Expected: generation pages contain their complete forms and record pages render their management content.

- [ ] **Step 4: Verify embedding capability**

Request `GET http://localhost:8080/api/ai/capabilities`.

Expected: `embedding_model` is `text-embedding-v4`.

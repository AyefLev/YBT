# Phase 3 Demo Script

1. Start the system from containers:

   ```powershell
   docker compose up --build
   ```

2. Open the gateway entry at `http://localhost:8080`.
3. Log in as a teacher, or register a teacher account.
4. Open `Course System`, create a course, then add one chapter, one session, and one knowledge point.
5. Export the course outline DOCX from the course detail panel.
6. Open `Question Bank`, create a structured question, and submit it for review.
7. Log in as an admin or assign a user the `teaching_manager` role.
8. Open `Teaching Review`, approve or reject the submitted question.
9. Return a rejected question to draft from the review API if needed.
10. Export the current question list as a DOCX practice package.
11. Open Swagger UI at `http://localhost:8080/docs` and show:
    - `/api/courses`
    - `/api/questions`
    - `/api/reviews/pending`
    - `/api/exports/course/{course_id}/outline-docx`
    - `/api/exports/questions/docx`

Demo message:

Yanbeitong AI is not only a text generator. It turns AI-generated and human-curated content into reusable institutional course assets, question-bank records, reviewable teaching-research resources, and standardized delivery documents.

Architecture message:

All external traffic enters through the API gateway. The FastAPI container handles synchronous API orchestration, Redis carries cache and background task queues, Qdrant stores material chunk vectors for semantic knowledge retrieval, and worker containers consume asynchronous module jobs such as material parsing, vector indexing, exports, and future PPT generation.

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pptx import Presentation as PptxPresentation
from pptx.util import Pt
from sqlalchemy.orm import Session

from app.ai.schemas import AIResult
from app.ai.service import generate_text
from app.auth.models import User
from app.core.config import get_settings
from app.exports.models import ExportRecord
from app.lessons.models import Lesson
from app.presentations.schemas import (
    PresentationGenerateRequest,
    PresentationGenerateResponse,
    PresentationSlideRead,
)


def generate_lesson_presentation_file(
    db: Session,
    *,
    lesson: Lesson,
    payload: PresentationGenerateRequest,
    current_user: User,
) -> PresentationGenerateResponse:
    target_count = payload.slide_count or 6
    prompt = _build_presentation_prompt(lesson, payload=payload, target_count=target_count)
    provider_status: AIResult | None = generate_text(
        db,
        "presentation",
        prompt,
        user_id=current_user.id,
    )
    slides = _parse_slides(provider_status.content, target_count=target_count)
    if not slides:
        slides = _fallback_slides(lesson, target_count=target_count)

    file_path = _write_pptx(lesson=lesson, slides=slides)
    try:
        record = ExportRecord(
            resource_type="presentation",
            resource_id=lesson.id,
            file_path=str(file_path),
            exported_by=current_user.id,
        )
        db.add(record)
        db.flush()
    except Exception:
        _remove_file(file_path)
        raise

    return PresentationGenerateResponse(
        lesson_id=lesson.id,
        status="generated",
        queued=False,
        message="PPT generated.",
        slides=slides,
        provider_status=provider_status,
        export_id=record.id,
        download_url=f"/api/presentations/exports/{record.id}/pptx",
        filename=file_path.name,
    )


def _build_presentation_prompt(
    lesson: Lesson,
    *,
    payload: PresentationGenerateRequest,
    target_count: int,
) -> str:
    return "\n".join(
        [
            "Create a teaching PowerPoint outline as strict JSON.",
            f"slide_count={target_count}",
            f"title={lesson.title}",
            f"subject={lesson.subject}",
            f"chapter={lesson.chapter}",
            f"duration_minutes={lesson.duration_minutes}",
            f"style={payload.style or 'default'}",
            f"include_exercises={payload.include_exercises}",
            f"description={payload.description or 'Let the model choose the best slide plan.'}",
            "Return only JSON in this shape:",
            '{"slides":[{"title":"...","bullets":["..."],"speaker_notes":"...","visual_prompt":"..."}]}',
            "Keep each slide focused and suitable for classroom teaching.",
            "Lesson content:",
            lesson.current_content[:8000],
        ]
    )


def _parse_slides(raw: str, *, target_count: int) -> list[PresentationSlideRead]:
    payload = _load_json_payload(raw)
    if payload is None:
        return []
    raw_slides = payload.get("slides") if isinstance(payload, dict) else payload
    if not isinstance(raw_slides, list):
        return []

    slides: list[PresentationSlideRead] = []
    for index, item in enumerate(raw_slides[:target_count], start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or f"Slide {index}").strip()
        bullets_value = item.get("bullets") or []
        if isinstance(bullets_value, str):
            bullets = [line.strip(" -*\t") for line in bullets_value.splitlines() if line.strip()]
        elif isinstance(bullets_value, list):
            bullets = [str(value).strip() for value in bullets_value if str(value).strip()]
        else:
            bullets = []
        slides.append(
            PresentationSlideRead(
                slide_no=len(slides) + 1,
                title=title[:120],
                bullets=bullets[:8],
                speaker_notes=str(item.get("speaker_notes") or "").strip()[:1200],
                visual_prompt=str(item.get("visual_prompt") or "").strip()[:600],
            )
        )
    return slides


def _load_json_payload(raw: str) -> object | None:
    raw = raw.strip()
    if not raw:
        return None
    candidates = [raw]
    object_start = raw.find("{")
    object_end = raw.rfind("}")
    if object_start >= 0 and object_end > object_start:
        candidates.append(raw[object_start : object_end + 1])
    array_start = raw.find("[")
    array_end = raw.rfind("]")
    if array_start >= 0 and array_end > array_start:
        candidates.append(raw[array_start : array_end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _fallback_slides(lesson: Lesson, *, target_count: int) -> list[PresentationSlideRead]:
    lines = [line.strip(" #*-") for line in lesson.current_content.splitlines() if line.strip()]
    if not lines:
        lines = [lesson.current_content.strip() or lesson.title]

    slides: list[PresentationSlideRead] = [
        PresentationSlideRead(
            slide_no=1,
            title=lesson.title,
            bullets=[
                f"Subject: {lesson.subject}",
                f"Chapter: {lesson.chapter}",
                f"Duration: {lesson.duration_minutes} minutes",
            ],
            speaker_notes="Open with lesson goals and expected outcomes.",
            visual_prompt="Clean title slide for a classroom lesson.",
        )
    ]
    remaining = max(0, target_count - 1)
    chunk_size = max(1, len(lines) // max(1, remaining))
    for index in range(remaining):
        chunk = lines[index * chunk_size : (index + 1) * chunk_size] or lines[:3]
        slides.append(
            PresentationSlideRead(
                slide_no=len(slides) + 1,
                title=chunk[0][:80] if chunk else f"Lesson Point {index + 1}",
                bullets=chunk[:5],
                speaker_notes="Explain this part with examples and quick checks.",
                visual_prompt="Simple teaching diagram related to the slide bullets.",
            )
        )
    return slides[:target_count]


def _write_pptx(*, lesson: Lesson, slides: list[PresentationSlideRead]) -> Path:
    export_dir = get_settings().export_dir
    export_dir.mkdir(parents=True, exist_ok=True)
    file_path = _presentation_file_path(export_dir, lesson)

    deck = PptxPresentation()
    for slide_data in slides:
        slide = deck.slides.add_slide(deck.slide_layouts[1])
        slide.shapes.title.text = slide_data.title
        text_frame = slide.placeholders[1].text_frame
        text_frame.clear()
        if slide_data.bullets:
            for index, bullet in enumerate(slide_data.bullets):
                paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
                paragraph.text = bullet
                paragraph.level = 0
                for run in paragraph.runs:
                    run.font.size = Pt(20)
        else:
            text_frame.text = "Key point"

        if slide_data.visual_prompt:
            paragraph = text_frame.add_paragraph()
            paragraph.text = f"Visual: {slide_data.visual_prompt}"
            paragraph.level = 0
            for run in paragraph.runs:
                run.font.size = Pt(14)

        if slide_data.speaker_notes:
            slide.notes_slide.notes_text_frame.text = slide_data.speaker_notes

    deck.save(file_path)
    return file_path


def _presentation_file_path(export_dir: Path, lesson: Lesson) -> Path:
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", lesson.title).strip("-") or "lesson"
    for _ in range(10):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        candidate = export_dir / f"presentation-{lesson.id}-{safe_title}-{timestamp}-{uuid4().hex}.pptx"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not allocate a unique presentation filename")


def _remove_file(file_path: Path) -> None:
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass

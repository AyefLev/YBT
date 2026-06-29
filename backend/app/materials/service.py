from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.models import User
from app.ai.service import analyze_image
from app.cache.service import get_cache
from app.core.config import get_settings
from app.core.database import get_session_local
from app.courses.models import Chapter, Course, KnowledgePoint, LessonSession
from app.logs.models import JobLog
from app.materials.models import Material, MaterialChunk
from app.materials.parsers import MaterialNeedsVisionError, SUPPORTED_SUFFIXES, ParsedText, parse_material
from app.materials.schemas import MaterialParseStatusRead
from app.materials.vision import render_pdf_pages_for_vision
from app.retrieval.vector_store import (
    delete_material_vectors,
    index_material_vectors,
    is_vector_store_configured,
)
from app.tasks.queue import enqueue_task

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 80
CHUNK_STRATEGIES = {"fixed", "paragraph", "parent_child"}
_PARSE_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="material-parser")


class VisionMaterialParseUnavailable(RuntimeError):
    pass


def create_material_record_from_upload(
    db: Session,
    *,
    title: str,
    subject: str = "",
    purpose: str = "",
    resource_scope: str = "personal",
    course_id: int | None = None,
    chapter_id: int | None = None,
    session_id: int | None = None,
    knowledge_point_id: int | None = None,
    chunk_strategy: str = "fixed",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    tags: str | list[str] | None = None,
    upload: UploadFile,
    uploader: User,
) -> Material:
    original_name = Path(upload.filename or "material").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {suffix or 'none'}",
        )

    _validate_teaching_scope(
        db,
        current_user=uploader,
        course_id=course_id,
        chapter_id=chapter_id,
        session_id=session_id,
        knowledge_point_id=knowledge_point_id,
    )
    normalized_chunk_size = _normalize_chunk_size(chunk_size)
    saved_path = _save_upload(upload, suffix)
    material = Material(
        title=title,
        subject=subject or "",
        purpose=purpose or "",
        resource_scope=_normalize_resource_scope(resource_scope),
        course_id=course_id,
        chapter_id=chapter_id,
        session_id=session_id,
        knowledge_point_id=knowledge_point_id,
        chunk_strategy=_normalize_chunk_strategy(chunk_strategy),
        chunk_size=normalized_chunk_size,
        chunk_overlap=_normalize_chunk_overlap(chunk_overlap, normalized_chunk_size),
        tags_json=_encode_tags(tags),
        file_name=original_name,
        file_type=suffix,
        file_path=str(saved_path),
        uploader_id=uploader.id,
        parse_status="pending",
        parse_error=None,
    )
    db.add(material)
    db.flush()
    return material


def schedule_material_parse(material_id: int, *, wait_seconds: float | None = None):
    write_material_parse_status_cache(
        material_id=material_id,
        status="pending",
        detail="Material parse job queued",
    )

    if enqueue_task("material.parse", {"material_id": material_id}, queue="materials"):
        return None

    future = _PARSE_EXECUTOR.submit(parse_material_job, material_id)
    timeout = get_settings().material_parse_wait_seconds if wait_seconds is None else wait_seconds
    if timeout > 0:
        try:
            future.result(timeout=timeout)
        except TimeoutError:
            pass
    return future


def schedule_material_vector_index(material_id: int) -> None:
    if not is_vector_store_configured():
        return

    write_material_parse_status_cache(
        material_id=material_id,
        status="parsed",
        detail="Material parsed; vector index job queued",
    )
    try:
        if enqueue_task(
            "material.index_vectors",
            {"material_id": material_id},
            queue="materials",
        ):
            return
    except Exception:
        return
    index_material_vectors_job(material_id)


def parse_material_job(material_id: int) -> None:
    should_index_vectors = False
    session_local = get_session_local()
    with session_local() as db:
        material = db.get(Material, material_id)
        if material is None:
            return

        started_at = datetime.now(timezone.utc)
        started = perf_counter()
        job_log = JobLog(
            job_type="material_parse",
            status="running",
            resource_type="material",
            resource_id=material.id,
            user_id=material.uploader_id,
            detail=f"Parsing {material.file_name}",
            started_at=started_at,
        )
        db.add(job_log)
        material.parse_status = "parsing"
        material.parse_error = None
        write_material_parse_status_cache(
            material_id=material.id,
            status="parsing",
            detail=f"Parsing {material.file_name}",
        )
        db.flush()

        try:
            try:
                parsed_texts = parse_material(Path(material.file_path), material.file_type)
            except MaterialNeedsVisionError as exc:
                parsed_texts = _parse_pdf_with_vision(
                    db,
                    material=material,
                    reason=str(exc),
                )
            _replace_chunks(db, material=material, parsed_texts=parsed_texts)
            chunk_count = len(material.chunks)
            should_index_vectors = chunk_count > 0
            material.parse_status = "parsed" if chunk_count else "empty"
            material.parse_error = None
            job_log.status = "succeeded"
            job_log.detail = f"Parsed {chunk_count} chunks"
            write_material_parse_status_cache(
                material_id=material.id,
                status=material.parse_status,
                detail=job_log.detail,
            )
        except VisionMaterialParseUnavailable as exc:
            material.parse_status = "needs_vision"
            material.parse_error = str(exc) or exc.__class__.__name__
            job_log.status = "needs_vision"
            job_log.error_message = material.parse_error
            write_material_parse_status_cache(
                material_id=material.id,
                status="needs_vision",
                detail=f"{material.file_name} 需要视觉模型解析",
                error_message=material.parse_error,
            )
        except Exception as exc:
            material.parse_status = "failed"
            material.parse_error = str(exc) or exc.__class__.__name__
            job_log.status = "failed"
            job_log.error_message = material.parse_error
            write_material_parse_status_cache(
                material_id=material.id,
                status="failed",
                detail=f"Failed to parse {material.file_name}",
                error_message=material.parse_error,
            )
        finally:
            finished_at = datetime.now(timezone.utc)
            job_log.finished_at = finished_at
            job_log.duration_ms = max(0, int((perf_counter() - started) * 1000))
            db.commit()

    if should_index_vectors:
        schedule_material_vector_index(material_id)


def index_material_vectors_job(material_id: int) -> None:
    session_local = get_session_local()
    with session_local() as db:
        material = db.get(Material, material_id)
        if material is None:
            return

        started_at = datetime.now(timezone.utc)
        started = perf_counter()
        job_log = JobLog(
            job_type="material_vector_index",
            status="running",
            resource_type="material",
            resource_id=material.id,
            user_id=material.uploader_id,
            detail=f"Indexing vectors for {material.file_name}",
            started_at=started_at,
        )
        db.add(job_log)
        db.flush()

        try:
            result = index_material_vectors(db, material=material)
            job_log.status = "succeeded" if result.enabled else "skipped"
            job_log.detail = result.message
            write_material_parse_status_cache(
                material_id=material.id,
                status=material.parse_status,
                detail=result.message,
            )
        except Exception as exc:
            job_log.status = "failed"
            job_log.error_message = str(exc) or exc.__class__.__name__
            write_material_parse_status_cache(
                material_id=material.id,
                status=material.parse_status,
                detail="Material parsed; vector indexing failed",
                error_message=job_log.error_message,
            )
        finally:
            finished_at = datetime.now(timezone.utc)
            job_log.finished_at = finished_at
            job_log.duration_ms = max(0, int((perf_counter() - started) * 1000))
            db.commit()


def _parse_pdf_with_vision(
    db: Session,
    *,
    material: Material,
    reason: str,
) -> list[ParsedText]:
    if material.file_type != ".pdf":
        raise VisionMaterialParseUnavailable(reason)
    try:
        rendered_pages = render_pdf_pages_for_vision(Path(material.file_path))
    except Exception as exc:
        raise VisionMaterialParseUnavailable(
            f"{reason} 当前无法渲染 PDF 页面或视觉解析依赖不可用，请启用视觉模型解析后重新解析。"
        ) from exc

    if not rendered_pages:
        raise VisionMaterialParseUnavailable(f"{reason} 未能渲染出可供视觉模型识别的页面。")

    parsed: list[ParsedText] = []
    for page in rendered_pages:
        try:
            result = analyze_image(
                db,
                image_bytes=page.image_bytes,
                mime_type=page.mime_type,
                prompt=_vision_pdf_prompt(material, page.page_no),
                user_id=material.uploader_id,
            )
        except Exception as exc:
            raise VisionMaterialParseUnavailable(
                f"{reason} 视觉模型解析第 {page.page_no} 页失败：{exc}"
            ) from exc
        content = result.content.strip()
        if content:
            parsed.append(ParsedText(content=content, page_no=page.page_no))

    if not parsed:
        raise VisionMaterialParseUnavailable(f"{reason} 视觉模型未返回可用文本。")
    return parsed


def _vision_pdf_prompt(material: Material, page_no: int) -> str:
    return (
        "请识别这页考研教学资料并输出可写入知识库的中文纯文本。\n"
        "要求：\n"
        "1. 面向考研备课和习题生成，保留题干、条件、答案、解析、公式和图表含义。\n"
        "2. 数学公式用 LaTeX 或清晰文本表达，不要输出无意义乱码。\n"
        "3. 不要描述页面截图本身，不要输出 Markdown 标题。\n"
        "4. 如果某处无法识别，请写“[此处无法识别]”，不要猜造内容。\n\n"
        f"资料标题：{material.title}\n"
        f"学科：{material.subject or '未标注'}\n"
        f"页码：{page_no}"
    )


def get_owned_material(db: Session, *, material_id: int, current_user: User) -> Material | None:
    statement = select(Material).where(Material.id == material_id)
    if "material:view_all" not in current_user.permission_codes and "material:manage_all" not in current_user.permission_codes:
        statement = statement.where(
            or_(
                Material.uploader_id == current_user.id,
                Material.resource_scope == "public",
            )
        )
    return db.scalar(statement)


def list_owned_materials(db: Session, *, current_user: User) -> list[Material]:
    statement = select(Material).order_by(Material.created_at.desc(), Material.id.desc())
    if "material:view_all" not in current_user.permission_codes and "material:manage_all" not in current_user.permission_codes:
        statement = statement.where(
            or_(
                Material.uploader_id == current_user.id,
                Material.resource_scope == "public",
            )
        )
    return list(
        db.scalars(statement).all()
    )


def can_manage_material(material: Material, *, current_user: User) -> bool:
    return (
        "material:manage_all" in current_user.permission_codes
        or material.uploader_id == current_user.id
    )


def list_material_chunks(db: Session, *, material: Material) -> list[MaterialChunk]:
    return list(
        db.scalars(
            select(MaterialChunk)
            .where(MaterialChunk.material_id == material.id)
            .order_by(MaterialChunk.chunk_index, MaterialChunk.id)
        ).all()
    )


def delete_material(db: Session, *, material: Material) -> None:
    path = Path(material.file_path)
    delete_material_vectors(material_id=material.id)
    db.delete(material)
    db.flush()
    path.unlink(missing_ok=True)


def mark_material_for_reparse(db: Session, *, material: Material) -> Material:
    _replace_chunks(db, material=material, parsed_texts=[])
    delete_material_vectors(material_id=material.id)
    material.parse_status = "pending"
    material.parse_error = None
    write_material_parse_status_cache(
        material_id=material.id,
        status="pending",
        detail="Material queued for reparse",
    )
    db.flush()
    return material


def material_chunk_count(material: Material) -> int:
    return len(material.chunks)


def material_tags(material: Material) -> list[str]:
    return _decode_tags(material.tags_json)


def material_parse_status(material: Material) -> MaterialParseStatusRead:
    cache_key = _material_parse_status_cache_key(material.id)
    cached = get_cache().get(cache_key)
    if cached:
        try:
            payload = json.loads(cached)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            return MaterialParseStatusRead(
                material_id=material.id,
                status=str(payload.get("status") or material.parse_status),
                detail=str(payload.get("detail") or ""),
                error_message=payload.get("error_message") or None,
                cache_hit=True,
            )

    return MaterialParseStatusRead(
        material_id=material.id,
        status=material.parse_status,
        detail=material.parse_error or "",
        error_message=material.parse_error,
        cache_hit=False,
    )


def write_material_parse_status_cache(
    *,
    material_id: int,
    status: str,
    detail: str,
    error_message: str | None = None,
) -> None:
    get_cache().set(
        _material_parse_status_cache_key(material_id),
        json.dumps(
            {
                "material_id": material_id,
                "status": status,
                "detail": detail,
                "error_message": error_message or "",
            },
            ensure_ascii=False,
        ),
        ttl_seconds=600,
    )


def _material_parse_status_cache_key(material_id: int) -> str:
    return f"material:{material_id}:parse_status"


def _replace_chunks(
    db: Session,
    *,
    material: Material,
    parsed_texts: list[ParsedText],
) -> None:
    db.query(MaterialChunk).filter(MaterialChunk.material_id == material.id).delete()
    material.chunks.clear()

    chunk_index = 0
    for parsed in parsed_texts:
        for content in _split_text(
            parsed.content,
            strategy=material.chunk_strategy,
            chunk_size=material.chunk_size,
            chunk_overlap=material.chunk_overlap,
        ):
            chunk = MaterialChunk(
                material_id=material.id,
                chunk_index=chunk_index,
                content=content,
                page_no=parsed.page_no,
                slide_no=parsed.slide_no,
                token_count=len(content),
                future_vector_id=None,
                future_embedding_model=None,
            )
            db.add(chunk)
            material.chunks.append(chunk)
            chunk_index += 1
    db.flush()


def _save_upload(upload: UploadFile, suffix: str) -> Path:
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / f"{uuid4().hex}{suffix}"
    with saved_path.open("wb") as target:
        while content := upload.file.read(1024 * 1024):
            target.write(content)
    return saved_path


def _split_text(
    text: str,
    *,
    strategy: str = "fixed",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    text = text.replace("\x00", "")
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    normalized = "\n".join(paragraphs).strip()
    if not normalized:
        return []

    strategy = _normalize_chunk_strategy(strategy)
    chunk_size = _normalize_chunk_size(chunk_size)
    chunk_overlap = _normalize_chunk_overlap(chunk_overlap, chunk_size)
    if strategy == "paragraph":
        return paragraphs
    if strategy == "parent_child":
        return _split_parent_child(paragraphs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    return _split_with_overlap(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def _split_parent_child(
    paragraphs: list[str],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    parents: list[str] = []
    current: list[str] = []
    for paragraph in paragraphs:
        is_heading = len(paragraph) <= 80 and (
            paragraph.startswith(("#", "第"))
            or paragraph.endswith(("章", "节", "课", "：", ":"))
        )
        if is_heading and current:
            parents.append("\n".join(current))
            current = [paragraph]
        else:
            current.append(paragraph)
    if current:
        parents.append("\n".join(current))

    chunks: list[str] = []
    for parent in parents:
        chunks.extend(_split_with_overlap(parent, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return chunks


def _split_with_overlap(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _normalize_chunk_strategy(value: str) -> str:
    normalized = (value or "fixed").strip().lower()
    if normalized not in CHUNK_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chunk_strategy must be fixed, paragraph, or parent_child",
        )
    return normalized


def _normalize_chunk_size(value: int) -> int:
    if value < 200 or value > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chunk_size must be between 200 and 4000",
        )
    return value


def _normalize_chunk_overlap(value: int, chunk_size: int) -> int:
    if value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chunk_overlap must be greater than or equal to 0",
        )
    return min(value, max(0, chunk_size // 2))


def _encode_tags(tags: str | list[str] | None) -> str:
    if tags is None:
        values: list[str] = []
    elif isinstance(tags, str):
        values = [tag.strip() for tag in tags.split(",") if tag.strip()]
    else:
        values = [str(tag).strip() for tag in tags if str(tag).strip()]
    return json.dumps(values, ensure_ascii=False)


def _decode_tags(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return [tag.strip() for tag in value.split(",") if tag.strip()]
    if not isinstance(decoded, list):
        return []
    return [str(tag) for tag in decoded if str(tag).strip()]


def _normalize_resource_scope(value: str) -> str:
    normalized = (value or "personal").strip().lower()
    if normalized not in {"personal", "public"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resource_scope must be personal or public",
        )
    return normalized


def _validate_teaching_scope(
    db: Session,
    *,
    current_user: User,
    course_id: int | None,
    chapter_id: int | None,
    session_id: int | None,
    knowledge_point_id: int | None,
) -> None:
    resolved_course_id = course_id
    if course_id is not None:
        course_query = select(Course).where(Course.id == course_id)
        if "course:manage_all" not in current_user.permission_codes:
            course_query = course_query.where(Course.owner_id == current_user.id)
        if db.scalar(course_query) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if chapter_id is not None:
        chapter_query = (
            select(Chapter)
            .join(Course, Chapter.course_id == Course.id)
            .where(Chapter.id == chapter_id)
        )
        if "course:manage_all" not in current_user.permission_codes:
            chapter_query = chapter_query.where(Course.owner_id == current_user.id)
        chapter = db.scalar(chapter_query)
        if chapter is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
        resolved_course_id = _ensure_same_course(resolved_course_id, chapter.course_id)

    if session_id is not None:
        session_query = (
            select(LessonSession)
            .join(Course, LessonSession.course_id == Course.id)
            .where(LessonSession.id == session_id)
        )
        if "course:manage_all" not in current_user.permission_codes:
            session_query = session_query.where(Course.owner_id == current_user.id)
        session = db.scalar(session_query)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        resolved_course_id = _ensure_same_course(resolved_course_id, session.course_id)
        if chapter_id is not None and session.chapter_id != chapter_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session does not belong to chapter")

    if knowledge_point_id is not None:
        point_query = (
            select(KnowledgePoint)
            .join(Course, KnowledgePoint.course_id == Course.id)
            .where(KnowledgePoint.id == knowledge_point_id)
        )
        if "course:manage_all" not in current_user.permission_codes:
            point_query = point_query.where(Course.owner_id == current_user.id)
        point = db.scalar(point_query)
        if point is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge point not found")
        resolved_course_id = _ensure_same_course(resolved_course_id, point.course_id)
    if resolved_course_id is not None:
        course_query = select(Course).where(Course.id == resolved_course_id)
        if "course:manage_all" not in current_user.permission_codes:
            course_query = course_query.where(Course.owner_id == current_user.id)
        if db.scalar(course_query) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")


def _ensure_same_course(current_course_id: int | None, linked_course_id: int) -> int:
    if current_course_id is not None and current_course_id != linked_course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linked teaching resources must belong to the same course",
        )
    return linked_course_id

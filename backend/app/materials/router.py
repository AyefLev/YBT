from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_any_permission, require_permission
from app.materials.models import Material, MaterialChunk
from app.materials.schemas import MaterialChunkRead, MaterialParseStatusRead, MaterialRead
from app.materials.service import (
    can_manage_material,
    create_material_record_from_upload,
    delete_material,
    get_owned_material,
    list_material_chunks,
    list_owned_materials,
    mark_material_for_reparse,
    material_chunk_count,
    material_parse_status,
    material_tags,
    schedule_material_parse,
)

router = APIRouter(prefix="/api/materials", tags=["materials"])


def material_to_read(material: Material) -> MaterialRead:
    uploader = getattr(material, "uploader", None)
    return MaterialRead(
        id=material.id,
        title=material.title,
        subject=material.subject,
        purpose=material.purpose,
        resource_scope=material.resource_scope,
        course_id=material.course_id,
        chapter_id=material.chapter_id,
        session_id=material.session_id,
        knowledge_point_id=material.knowledge_point_id,
        chunk_strategy=material.chunk_strategy,
        chunk_size=material.chunk_size,
        chunk_overlap=material.chunk_overlap,
        tags=material_tags(material),
        file_name=material.file_name,
        file_type=material.file_type,
        file_path=material.file_path,
        uploader_id=material.uploader_id,
        uploader_name=getattr(uploader, "display_name", "") or "",
        uploader_username=getattr(uploader, "username", "") or "",
        parse_status=material.parse_status,
        parse_error=material.parse_error,
        created_at=material.created_at,
        chunk_count=material_chunk_count(material),
    )


def chunk_to_read(chunk: MaterialChunk) -> MaterialChunkRead:
    return MaterialChunkRead.model_validate(chunk)


def _material_or_404(db: Session, material_id: int, current_user: User) -> Material:
    material = get_owned_material(db, material_id=material_id, current_user=current_user)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return material


def _manageable_material_or_404(db: Session, material_id: int, current_user: User) -> Material:
    material = _material_or_404(db, material_id, current_user)
    if not can_manage_material(material, current_user=current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to manage this material",
        )
    return material


@router.get("", response_model=list[MaterialRead])
def list_materials(
    current_user: User = Depends(require_any_permission("material:upload", "material:view_all", "material:view_public")),
    db: Session = Depends(get_db),
) -> list[MaterialRead]:
    return [
        material_to_read(material)
        for material in list_owned_materials(db, current_user=current_user)
    ]


@router.post("/upload", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def upload_material(
    title: str = Form(...),
    subject: str = Form(""),
    purpose: str = Form(""),
    resource_scope: str = Form("personal"),
    course_id: int | None = Form(None),
    chapter_id: int | None = Form(None),
    session_id: int | None = Form(None),
    knowledge_point_id: int | None = Form(None),
    chunk_strategy: str = Form("fixed"),
    chunk_size: int = Form(800),
    chunk_overlap: int = Form(80),
    tags: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("material:upload")),
    db: Session = Depends(get_db),
) -> MaterialRead:
    if resource_scope.strip().lower() == "public" and "material:publish_public" not in current_user.permission_codes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only public material publishers can publish public materials",
        )
    material = create_material_record_from_upload(
        db,
        title=title,
        subject=subject,
        purpose=purpose,
        resource_scope=resource_scope,
        course_id=course_id,
        chapter_id=chapter_id,
        session_id=session_id,
        knowledge_point_id=knowledge_point_id,
        chunk_strategy=chunk_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        tags=tags,
        upload=file,
        uploader=current_user,
    )
    db.commit()
    schedule_material_parse(material.id)
    db.refresh(material)
    return material_to_read(material)


@router.get("/{material_id}", response_model=MaterialRead)
def get_material(
    material_id: int,
    current_user: User = Depends(require_any_permission("material:upload", "material:view_all", "material:view_public")),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material = _material_or_404(db, material_id, current_user)
    return material_to_read(material)


@router.get("/{material_id}/parse-status", response_model=MaterialParseStatusRead)
def get_material_parse_status(
    material_id: int,
    current_user: User = Depends(require_any_permission("material:upload", "material:view_all", "material:view_public")),
    db: Session = Depends(get_db),
) -> MaterialParseStatusRead:
    material = _material_or_404(db, material_id, current_user)
    return material_parse_status(material)


@router.get("/{material_id}/chunks", response_model=list[MaterialChunkRead])
def get_material_chunks(
    material_id: int,
    current_user: User = Depends(require_any_permission("material:upload", "material:view_all", "material:view_public")),
    db: Session = Depends(get_db),
) -> list[MaterialChunkRead]:
    material = _material_or_404(db, material_id, current_user)
    return [chunk_to_read(chunk) for chunk in list_material_chunks(db, material=material)]


@router.post("/{material_id}/reparse", response_model=MaterialRead, status_code=status.HTTP_202_ACCEPTED)
def reparse_material(
    material_id: int,
    current_user: User = Depends(require_permission("material:upload")),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material = _manageable_material_or_404(db, material_id, current_user)
    mark_material_for_reparse(db, material=material)
    db.commit()
    schedule_material_parse(material.id)
    db.refresh(material)
    return material_to_read(material)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_material(
    material_id: int,
    current_user: User = Depends(require_permission("material:upload")),
    db: Session = Depends(get_db),
) -> None:
    material = _manageable_material_or_404(db, material_id, current_user)
    delete_material(db, material=material)
    db.commit()

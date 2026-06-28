import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.config_schemas import AIProviderConfigRead, AIProviderConfigUpdate
from app.ai.config_service import (
    ai_provider_config_to_read,
    list_ai_provider_configs,
    upsert_ai_provider_config,
)
from app.ai.schemas import ModelCapabilityResponse, ModelConnectivityResponse, VisionAnalysisResponse
from app.ai.service import analyze_image, check_model_connectivity, _provider_config_for_role
from app.auth.models import User
from app.cache.service import get_cache
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_any_permission, require_permission

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/capabilities", response_model=ModelCapabilityResponse)
def get_model_capabilities(db: Session = Depends(get_db)) -> ModelCapabilityResponse:
    settings = get_settings()
    cache = get_cache()
    cached = cache.get("ai:capabilities")
    if cached:
        try:
            return ModelCapabilityResponse.model_validate_json(cached)
        except ValidationError:
            cache.delete("ai:capabilities")

    generate_config = _provider_config_for_role(settings, "generate", db=db)
    review_config = _provider_config_for_role(settings, "review", db=db)
    revise_config = _provider_config_for_role(settings, "revise", db=db)
    vision_config = _provider_config_for_role(settings, "vision", db=db)
    embedding_config = _provider_config_for_role(settings, "embedding", db=db)
    capabilities = ModelCapabilityResponse(
        text_model=generate_config.model,
        text_configured=bool(generate_config.api_key),
        generate_model=generate_config.model,
        generate_configured=bool(generate_config.api_key),
        review_model=review_config.model,
        review_configured=bool(review_config.api_key),
        revise_model=revise_config.model,
        revise_configured=bool(revise_config.api_key),
        vision_model=vision_config.model,
        vision_configured=bool(vision_config.api_key and vision_config.model),
        embedding_model=embedding_config.model,
        embedding_configured=bool(embedding_config.model),
        mock_on_failure=settings.llm_mock_on_failure,
        multi_agent_review=settings.llm_multi_agent_review,
    )
    cache.set("ai:capabilities", json.dumps(capabilities.model_dump()), ttl_seconds=30)
    return capabilities


@router.get("/connectivity", response_model=ModelConnectivityResponse)
def get_model_connectivity(
    probe: bool = False,
    db: Session = Depends(get_db),
) -> ModelConnectivityResponse:
    return ModelConnectivityResponse(
        probe_enabled=probe,
        checks=[
            check_model_connectivity("generate", db=db, probe=probe),
            check_model_connectivity("review", db=db, probe=probe),
            check_model_connectivity("revise", db=db, probe=probe),
            check_model_connectivity("vision", db=db, probe=probe),
            check_model_connectivity("embedding", db=db, probe=probe),
        ],
    )


@router.post("/vision/analyze", response_model=VisionAnalysisResponse)
def analyze_vision_image(
    prompt: str = Form("Describe this image for teaching use."),
    file: UploadFile = File(...),
    current_user: User = Depends(
        require_any_permission(
            "lesson:create",
            "exercise:create",
            "material:upload",
        )
    ),
    db: Session = Depends(get_db),
) -> VisionAnalysisResponse:
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image uploads are supported")

    image_bytes = file.file.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")
    if len(image_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image file is too large")

    try:
        result = analyze_image(
            db,
            image_bytes=image_bytes,
            mime_type=content_type,
            prompt=prompt,
            user_id=current_user.id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return VisionAnalysisResponse(content=result.content, provider_status=result)


@router.get("/admin/provider-configs", response_model=list[AIProviderConfigRead])
def get_provider_configs(
    _=Depends(require_permission("admin:content_manage")),
    db: Session = Depends(get_db),
) -> list[AIProviderConfigRead]:
    return list_ai_provider_configs(db)


@router.patch("/admin/provider-configs/{role}", response_model=AIProviderConfigRead)
def update_provider_config(
    role: str,
    payload: AIProviderConfigUpdate,
    _=Depends(require_permission("admin:content_manage")),
    db: Session = Depends(get_db),
) -> AIProviderConfigRead:
    try:
        config = upsert_ai_provider_config(db, role=role, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    get_cache().delete("ai:capabilities")
    return ai_provider_config_to_read(config)

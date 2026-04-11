from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.plan_rate_limit import require_plan_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.services.analytics_service import record_usage_event
from app.services.s3_service import create_presigned_upload

router = APIRouter(prefix="/files", tags=["files"])


class PresignUploadRequest(BaseModel):
    filename: str
    content_type: str


@router.post("/presign-upload")
async def presign_upload(
    payload: PresignUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _plan_limit=Depends(require_plan_rate_limit()),
):
    try:
        data = create_presigned_upload(payload.filename, payload.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await record_usage_event(db, current_user.id, "files.presign")
    await db.commit()
    return data

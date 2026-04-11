from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.organization import OrganizationRole
from app.models.user import User
from app.services.analytics_service import record_usage_event
from app.services.audit_service import log_audit
from app.services.notification_service import create_notification
from app.services.org_service import (
    add_member,
    create_organization,
    list_org_members,
    list_user_organizations,
    remove_member,
)

router = APIRouter(prefix="/orgs", tags=["orgs"])


class CreateOrgRequest(BaseModel):
    name: str


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.member


@router.post("")
async def create_org(
    payload: CreateOrgRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    org = await create_organization(db, current_user, payload.name)
    await record_usage_event(db, current_user.id, "org.create")
    await log_audit(db, current_user.id, "org.create", "organization", org.id, {"name": org.name})
    await db.commit()
    return {"id": org.id, "name": org.name, "slug": org.slug}


@router.get("")
async def list_orgs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    orgs = await list_user_organizations(db, current_user.id)
    return [{"id": org.id, "name": org.name, "slug": org.slug} for org in orgs]


@router.get("/{org_id}/members")
async def members(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    memberships = await list_org_members(db, org_id)
    return [
        {
            "id": membership.id,
            "organization_id": membership.organization_id,
            "user_id": membership.user_id,
            "role": membership.role,
            "is_active": membership.is_active,
        }
        for membership in memberships
    ]


@router.post("/{org_id}/members")
async def invite_member(
    org_id: str,
    payload: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    membership = await add_member(db, org_id, payload.email, payload.role)
    if not membership:
        raise HTTPException(status_code=404, detail="User with that email was not found")
    await create_notification(
        db,
        membership.user_id,
        "Added to organization",
        f"You were added to org {org_id} as {payload.role.value}.",
        "org_invite",
    )
    await log_audit(
        db,
        current_user.id,
        "org.member.add",
        "organization",
        org_id,
        {"email": payload.email, "role": payload.role.value},
    )
    await record_usage_event(db, current_user.id, "org.member.add")
    await db.commit()
    return {"message": "Member added", "membership_id": membership.id}


@router.delete("/{org_id}/members/{user_id}")
async def delete_member(
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    removed = await remove_member(db, org_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Membership not found")
    await log_audit(db, current_user.id, "org.member.remove", "organization", org_id, {"user_id": user_id})
    await db.commit()
    return {"message": "Member removed"}

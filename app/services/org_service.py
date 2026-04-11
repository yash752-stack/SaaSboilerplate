from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User


def _slugify(name: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in name).split())


async def create_organization(db: AsyncSession, user: User, name: str) -> Organization:
    org = Organization(name=name, slug=_slugify(name), created_by=user.id)
    db.add(org)
    await db.flush()

    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=OrganizationRole.owner,
    )
    db.add(membership)
    await db.flush()
    return org


async def list_user_organizations(db: AsyncSession, user_id: str) -> list[Organization]:
    result = await db.execute(
        select(Organization)
        .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
        .where(OrganizationMembership.user_id == user_id, OrganizationMembership.is_active == True)
        .order_by(Organization.created_at.desc())
    )
    return list(result.scalars().all())


async def list_org_members(db: AsyncSession, organization_id: str) -> list[OrganizationMembership]:
    result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(OrganizationMembership.created_at.asc())
    )
    return list(result.scalars().all())


async def add_member(
    db: AsyncSession,
    organization_id: str,
    email: str,
    role: OrganizationRole = OrganizationRole.member,
) -> OrganizationMembership | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None

    existing = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
    )
    membership = existing.scalar_one_or_none()
    if membership:
        membership.role = role
        membership.is_active = True
        db.add(membership)
        await db.flush()
        return membership

    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.id,
        role=role,
    )
    db.add(membership)
    await db.flush()
    return membership


async def remove_member(db: AsyncSession, organization_id: str, user_id: str) -> bool:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return False
    membership.is_active = False
    db.add(membership)
    await db.flush()
    return True

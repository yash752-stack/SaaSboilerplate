from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User


def _slugify(name: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in name).split())


async def _generate_unique_slug(db: AsyncSession, name: str) -> str:
    base_slug = _slugify(name) or "organization"
    slug = base_slug
    suffix = 2

    while True:
        result = await db.execute(select(Organization.id).where(Organization.slug == slug))
        existing = result.scalar_one_or_none()
        if not existing:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


async def create_organization(db: AsyncSession, user: User, name: str) -> Organization:
    org = Organization(name=name, slug=await _generate_unique_slug(db, name), created_by=user.id)
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
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_active == True,
        )
        .order_by(OrganizationMembership.created_at.asc())
    )
    return list(result.scalars().all())


async def get_organization_by_id(db: AsyncSession, organization_id: str) -> Organization | None:
    result = await db.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_org_membership(
    db: AsyncSession,
    organization_id: str,
    user_id: str,
) -> OrganizationMembership | None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.is_active == True,
        )
    )
    return result.scalar_one_or_none()


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


async def remove_member(db: AsyncSession, organization_id: str, user_id: str) -> str:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.is_active == True,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return "not_found"

    if membership.role == OrganizationRole.owner:
        owner_count = (
            await db.execute(
                select(OrganizationMembership)
                .where(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.role == OrganizationRole.owner,
                    OrganizationMembership.is_active == True,
                )
            )
        ).scalars().all()
        if len(owner_count) <= 1:
            return "last_owner"

    membership.is_active = False
    db.add(membership)
    await db.flush()
    return "removed"

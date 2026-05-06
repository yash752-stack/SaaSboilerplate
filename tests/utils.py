from uuid import uuid4


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid4().hex[:10]}@example.com"

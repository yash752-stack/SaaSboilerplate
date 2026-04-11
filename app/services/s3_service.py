from datetime import datetime
from urllib.parse import urlencode

from app.core.config import settings


def create_presigned_upload(
    filename: str,
    content_type: str,
    expires_in: int = 900,
) -> dict:
    if content_type not in settings.ALLOWED_UPLOAD_TYPES:
        raise ValueError("Unsupported file type")

    key = f"uploads/{datetime.utcnow():%Y/%m/%d}/{filename}"
    if settings.S3_BUCKET:
        import boto3

        client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        return {"upload_url": url, "file_key": key}

    local_url = f"{settings.BACKEND_BASE_URL}/mock-upload?{urlencode({'key': key, 'expires_in': expires_in})}"
    return {"upload_url": local_url, "file_key": key}

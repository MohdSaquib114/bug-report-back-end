import os
import uuid
from dataclasses import dataclass

from app.errors import AppError

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    _BOTO_AVAILABLE = True
except ImportError:  # pragma: no cover - boto3 is a declared dependency
    _BOTO_AVAILABLE = False


class StorageError(AppError):
    status_code = 502


@dataclass(frozen=True)
class StoredObject:
    key: str
    url: str


_EXT_BY_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "application/pdf": ".pdf",
}


def _ext_from_filename(filename: str | None) -> str:
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""


class StorageService:
    """Uploads attachment bytes to an S3-compatible bucket (Neon bucket).

    Enabled when ``S3_BUCKET`` is set. Credentials are resolved by boto3 from
    the environment (``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``),
    ``~/.aws`` or the usual provider chain. ``S3_ENDPOINT_URL`` can point at an
    S3-compatible endpoint (e.g. the Neon endpoint); leave it unset for AWS S3.
    """

    def __init__(self) -> None:
        self.region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-2"
        self.bucket = os.getenv("S3_BUCKET")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL") or None
        self.public_base_url = os.getenv("S3_PUBLIC_BASE_URL") or None
        self.expires_in = int(os.getenv("S3_PRESIGN_EXPIRES", "604800"))
        self._client = None

    @property
    def configured(self) -> bool:
        return bool(_BOTO_AVAILABLE and self.bucket)

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
            )
        return self._client

    def _build_key(self, prefix: str, content_type: str, filename: str | None) -> str:
        ext = _EXT_BY_TYPE.get(content_type) or _ext_from_filename(filename)
        return "{0}/{1}{2}".format(prefix.strip("/"), uuid.uuid4().hex, ext)

    def upload(
        self,
        *,
        data: bytes,
        content_type: str,
        prefix: str,
        filename: str | None = None,
    ) -> StoredObject:
        if not self.configured:
            raise StorageError("Attachment storage is not configured")

        key = self._build_key(prefix, content_type, filename)
        try:
            self._get_client().put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Failed to upload attachment: {0}".format(exc)) from exc

        return StoredObject(key=key, url=self.generate_url(key))

    def generate_url(self, key: str) -> str:
        if self.public_base_url:
            return "{0}/{1}".format(self.public_base_url.rstrip("/"), key)
        try:
            return self._get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=self.expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Failed to generate attachment URL: {0}".format(exc)) from exc

    def delete(self, key: str) -> None:
        if not self.configured:
            return
        try:
            self._get_client().delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Failed to delete attachment: {0}".format(exc)) from exc


_storage: StorageService | None = None


def get_storage() -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage


def reset_storage() -> None:
    """Testing helper: force re-read of environment on next access."""
    global _storage
    _storage = None
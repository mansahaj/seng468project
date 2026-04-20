import os
from io import BytesIO

from minio import Minio
from minio.error import S3Error


def get_minio_client() -> Minio:
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ROOT_USER", "seng468minio")
    secret_key = os.getenv(
        "MINIO_ROOT_PASSWORD",
        "Seng468MinioPassword_2026_ChangeMe!",
    )
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def get_bucket_name() -> str:
    return os.getenv("MINIO_BUCKET", "documents")


def ensure_bucket_exists() -> None:
    client = get_minio_client()
    bucket_name = get_bucket_name()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_pdf_object(
    object_name: str,
    content: bytes,
    content_type: str = "application/pdf",
) -> None:
    ensure_bucket_exists()
    client = get_minio_client()
    client.put_object(
        get_bucket_name(),
        object_name,
        BytesIO(content),
        length=len(content),
        content_type=content_type,
    )


def download_object_bytes(object_name: str) -> bytes:
    ensure_bucket_exists()
    client = get_minio_client()
    response = client.get_object(get_bucket_name(), object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_object(object_name: str) -> None:
    ensure_bucket_exists()
    client = get_minio_client()
    try:
        client.remove_object(get_bucket_name(), object_name)
    except S3Error as exc:
        if exc.code != "NoSuchKey":
            raise

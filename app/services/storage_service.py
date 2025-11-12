"""Storage service for S3/MinIO operations."""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional
from datetime import timedelta
from app.config import settings


class StorageService:
    """Service for S3/MinIO operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for uploading a file (PUT)."""
        try:
            url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise Exception(f"Error generating upload URL: {str(e)}")

    def generate_download_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for downloading a file (GET)."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise Exception(f"Error generating download URL: {str(e)}")

    def upload_file(self, file_path: str, key: str, content_type: Optional[str] = None) -> bool:
        """Upload a file to S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.s3_client.upload_file(file_path, self.bucket_name, key, ExtraArgs=extra_args)
            return True
        except ClientError as e:
            raise Exception(f"Error uploading file: {str(e)}")

    def upload_fileobj(self, file_obj, key: str, content_type: Optional[str] = None) -> bool:
        """Upload a file-like object to S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.s3_client.upload_fileobj(file_obj, self.bucket_name, key, ExtraArgs=extra_args)
            return True
        except ClientError as e:
            raise Exception(f"Error uploading file: {str(e)}")

    def delete_file(self, key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            raise Exception(f"Error deleting file: {str(e)}")

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False


# Global instance
storage_service = StorageService()


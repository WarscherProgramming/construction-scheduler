from collections.abc import Iterable, Iterator
from io import RawIOBase
from urllib.parse import urlparse

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.client import Config
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from app.core.config import AttachmentConfig
from app.storage.attachment import (
    AttachmentObjectMissing,
    AttachmentStorage,
    AttachmentStorageAuthenticationError,
    AttachmentStorageConfigurationError,
    AttachmentStorageConnectionError,
    AttachmentStorageError,
    AttachmentStorageThrottledError,
    AttachmentStorageTimeoutError,
    AttachmentStreamTooLarge,
    validate_storage_key,
)
from app.storage.provider import StorageObjectMetadata


TRANSFER_CHUNK_SIZE = 8 * 1024 * 1024
NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}
AUTHENTICATION_CODES = {
    "401",
    "403",
    "AccessDenied",
    "ExpiredToken",
    "InvalidAccessKeyId",
    "SignatureDoesNotMatch",
}
THROTTLING_CODES = {
    "429",
    "RequestLimitExceeded",
    "SlowDown",
    "Throttling",
    "ThrottlingException",
}
CONFIGURATION_CODES = {
    "InvalidBucketName",
    "NoSuchBucket",
    "PermanentRedirect",
}


class IterableStream(RawIOBase):
    def __init__(self, chunks: Iterable[bytes]):
        self._chunks = iter(chunks)
        self._buffer = bytearray()
        self._finished = False

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if self._finished and not self._buffer:
            return b""

        target_size = TRANSFER_CHUNK_SIZE if size is None or size < 0 else size
        while len(self._buffer) < target_size and not self._finished:
            try:
                chunk = next(self._chunks)
            except StopIteration:
                self._finished = True
                break
            if chunk:
                self._buffer.extend(chunk)

        result = bytes(self._buffer[:target_size])
        del self._buffer[:target_size]
        return result


class S3BodyIterator:
    def __init__(self, body, chunk_size: int):
        self.body = body
        self.chunk_size = chunk_size
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        if self.closed:
            raise StopIteration
        try:
            chunk = self.body.read(self.chunk_size)
        except Exception as error:
            self.close()
            raise classify_s3_error(error) from error
        if not chunk:
            self.close()
            raise StopIteration
        return chunk

    def close(self) -> None:
        if not self.closed:
            try:
                self.body.close()
            except Exception:
                pass
            finally:
                self.closed = True

    def __del__(self):
        self.close()


def classify_s3_error(error: Exception) -> AttachmentStorageError:
    if isinstance(error, (ConnectTimeoutError, ReadTimeoutError)):
        return AttachmentStorageTimeoutError(
            "Attachment storage request timed out"
        )
    if isinstance(
        error,
        (EndpointConnectionError, ConnectionClosedError),
    ):
        return AttachmentStorageConnectionError(
            "Attachment storage connection failed"
        )
    if isinstance(error, ClientError):
        response = error.response or {}
        code = str(response.get("Error", {}).get("Code", ""))
        status_code = response.get(
            "ResponseMetadata",
            {},
        ).get("HTTPStatusCode")

        if code in CONFIGURATION_CODES:
            return AttachmentStorageConfigurationError(
                "Attachment storage is not configured correctly"
            )
        if code in NOT_FOUND_CODES or status_code == 404:
            return AttachmentObjectMissing(
                "Attachment object is missing"
            )
        if (
            code in AUTHENTICATION_CODES
            or status_code in {401, 403}
        ):
            return AttachmentStorageAuthenticationError(
                "Attachment storage authentication failed"
            )
        if code in THROTTLING_CODES or status_code == 429:
            return AttachmentStorageThrottledError(
                "Attachment storage request was throttled"
            )
        translated = AttachmentStorageError(
            "Attachment storage provider failed"
        )
        if isinstance(status_code, int) and status_code < 500:
            translated.retryable = False
        return translated

    return AttachmentStorageError(
        "Attachment storage provider failed"
    )


def validate_s3_config(config: AttachmentConfig) -> None:
    required = {
        "ATTACHMENT_S3_BUCKET": config.s3_bucket,
        "ATTACHMENT_S3_REGION": config.s3_region,
        "ATTACHMENT_S3_ACCESS_KEY_ID": config.s3_access_key_id,
        "ATTACHMENT_S3_SECRET_ACCESS_KEY": (
            config.s3_secret_access_key
        ),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise AttachmentStorageConfigurationError(
            f"Required setting {missing[0]} is not configured"
        )
    if config.s3_addressing_style not in {"auto", "path", "virtual"}:
        raise AttachmentStorageConfigurationError(
            "ATTACHMENT_S3_ADDRESSING_STYLE is invalid"
        )
    if config.s3_endpoint_url:
        endpoint = urlparse(config.s3_endpoint_url)
        if endpoint.scheme not in {"http", "https"} or not endpoint.netloc:
            raise AttachmentStorageConfigurationError(
                "ATTACHMENT_S3_ENDPOINT_URL is invalid"
            )
        if config.s3_secure_transport and endpoint.scheme != "https":
            raise AttachmentStorageConfigurationError(
                "ATTACHMENT_S3_ENDPOINT_URL must use HTTPS"
            )


def build_s3_client(config: AttachmentConfig):
    validate_s3_config(config)
    session = boto3.session.Session(
        aws_access_key_id=config.s3_access_key_id,
        aws_secret_access_key=config.s3_secret_access_key,
        aws_session_token=config.s3_session_token,
        region_name=config.s3_region,
    )
    return session.client(
        "s3",
        endpoint_url=config.s3_endpoint_url,
        use_ssl=config.s3_secure_transport,
        config=Config(
            connect_timeout=config.s3_connect_timeout,
            read_timeout=config.s3_read_timeout,
            retries={
                "max_attempts": config.s3_max_retries,
                "mode": "standard",
            },
            s3={"addressing_style": config.s3_addressing_style},
        ),
    )


class S3CompatibleProvider(AttachmentStorage):
    provider_name = "s3"

    def __init__(
        self,
        client,
        bucket: str,
        key_prefix: str = "",
    ):
        self.client = client
        self.bucket = bucket
        self.key_prefix = key_prefix
        self.transfer_config = TransferConfig(
            multipart_threshold=TRANSFER_CHUNK_SIZE,
            multipart_chunksize=TRANSFER_CHUNK_SIZE,
            use_threads=False,
        )

    def _key_for(self, storage_key: str) -> str:
        validate_storage_key(storage_key)
        if self.key_prefix:
            return f"{self.key_prefix}/{storage_key}"
        return storage_key

    def put_stream(
        self,
        storage_key: str,
        chunks: Iterable[bytes],
        *,
        content_type: str | None = None,
    ) -> None:
        extra_args = {"ChecksumAlgorithm": "SHA256"}
        if content_type:
            extra_args["ContentType"] = content_type
        try:
            self.client.upload_fileobj(
                IterableStream(chunks),
                self.bucket,
                self._key_for(storage_key),
                ExtraArgs=extra_args,
                Config=self.transfer_config,
            )
        except AttachmentStreamTooLarge:
            raise
        except Exception as error:
            raise classify_s3_error(error) from error

    def open_stream(
        self,
        storage_key: str,
        chunk_size: int,
    ) -> Iterator[bytes]:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=self._key_for(storage_key),
            )
        except Exception as error:
            raise classify_s3_error(error) from error

        return S3BodyIterator(response["Body"], chunk_size)

    def delete(self, storage_key: str) -> bool:
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=self._key_for(storage_key),
            )
            return True
        except Exception as error:
            translated = classify_s3_error(error)
            if isinstance(translated, AttachmentObjectMissing):
                return False
            raise translated from error

    def exists(self, storage_key: str) -> bool:
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=self._key_for(storage_key),
            )
            return True
        except Exception as error:
            translated = classify_s3_error(error)
            if isinstance(translated, AttachmentObjectMissing):
                return False
            raise translated from error

    def metadata(self, storage_key: str) -> StorageObjectMetadata:
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=self._key_for(storage_key),
            )
        except Exception as error:
            raise classify_s3_error(error) from error

        return StorageObjectMetadata(
            size_bytes=int(response.get("ContentLength", 0)),
            content_type=response.get("ContentType"),
            etag=str(response.get("ETag", "")).strip('"') or None,
        )

    def generate_download_url(
        self,
        storage_key: str,
        *,
        expires_seconds: int = 300,
    ) -> str:
        if not 1 <= expires_seconds <= 3600:
            raise AttachmentStorageError(
                "Download URL expiry must be from 1 to 3600 seconds"
            )
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": self._key_for(storage_key),
                },
                ExpiresIn=expires_seconds,
            )
        except Exception as error:
            raise classify_s3_error(error) from error

    def copy(self, source_key: str, destination_key: str) -> None:
        try:
            self.client.copy_object(
                Bucket=self.bucket,
                CopySource={
                    "Bucket": self.bucket,
                    "Key": self._key_for(source_key),
                },
                Key=self._key_for(destination_key),
            )
        except Exception as error:
            raise classify_s3_error(error) from error

    def health_check(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


S3AttachmentStorage = S3CompatibleProvider


def build_s3_storage(
    config: AttachmentConfig,
    *,
    client=None,
) -> S3CompatibleProvider:
    validate_s3_config(config)
    return S3CompatibleProvider(
        client or build_s3_client(config),
        config.s3_bucket or "",
        config.s3_key_prefix,
    )

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from app.core.config import (
    DEFAULT_ATTACHMENT_MIME_TYPES,
    AttachmentConfig,
    normalize_attachment_key_prefix,
)
from app.storage.attachment import (
    AttachmentObjectMissing,
    AttachmentStorageAuthenticationError,
    AttachmentStorageConfigurationError,
    AttachmentStorageConnectionError,
    AttachmentStorageThrottledError,
    AttachmentStorageTimeoutError,
    AttachmentStreamTooLarge,
    LocalAttachmentStorage,
    MemoryAttachmentStorage,
)
from app.storage.factory import build_attachment_storage
from app.storage.s3 import (
    S3AttachmentStorage,
    build_s3_client,
    build_s3_storage,
    classify_s3_error,
)


STORAGE_KEY = "a" * 32


def make_config(**overrides):
    values = {
        "storage_provider": "s3",
        "local_storage_root": Path("unused"),
        "max_upload_size": 1024,
        "upload_chunk_size": 4,
        "permitted_mime_types": DEFAULT_ATTACHMENT_MIME_TYPES,
        "s3_bucket": "private-bucket",
        "s3_region": "us-west-2",
        "s3_endpoint_url": "https://objects.example.test",
        "s3_access_key_id": "access-id",
        "s3_secret_access_key": "top-secret",
        "s3_addressing_style": "path",
        "s3_key_prefix": "fieldflow/files",
    }
    values.update(overrides)
    return AttachmentConfig(**values)


def client_error(code, status_code):
    return ClientError(
        {
            "Error": {"Code": code, "Message": "provider detail"},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        "Operation",
    )


class FakeBody:
    def __init__(self, content):
        self.content = content
        self.offset = 0
        self.read_sizes = []
        self.closed = False

    def read(self, size):
        self.read_sizes.append(size)
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self):
        self.closed = True


class FakeS3Client:
    def __init__(self):
        self.upload = None
        self.body = FakeBody(b"streamed-download")
        self.deleted = []
        self.heads = []
        self.copies = []
        self.presigned = []
        self.bucket_checks = []
        self.delete_error = None
        self.head_error = None

    def upload_fileobj(
        self,
        file_object,
        bucket,
        key,
        *,
        ExtraArgs,
        Config,
    ):
        chunks = []
        while chunk := file_object.read(5):
            chunks.append(chunk)
        self.upload = {
            "bucket": bucket,
            "key": key,
            "content": b"".join(chunks),
            "extra_args": ExtraArgs,
            "config": Config,
        }

    def get_object(self, *, Bucket, Key):
        return {"Body": self.body}

    def delete_object(self, *, Bucket, Key):
        if self.delete_error:
            raise self.delete_error
        self.deleted.append((Bucket, Key))

    def head_object(self, *, Bucket, Key):
        if self.head_error:
            raise self.head_error
        self.heads.append((Bucket, Key))
        return {
            "ContentLength": 17,
            "ContentType": "application/pdf",
            "ETag": '"checksum-etag"',
        }

    def generate_presigned_url(
        self,
        operation,
        *,
        Params,
        ExpiresIn,
    ):
        self.presigned.append((operation, Params, ExpiresIn))
        return "https://objects.example.test/signed"

    def copy_object(self, *, Bucket, CopySource, Key):
        self.copies.append((Bucket, CopySource, Key))

    def head_bucket(self, *, Bucket):
        self.bucket_checks.append(Bucket)


class AttachmentS3Tests(unittest.TestCase):
    def test_local_and_memory_providers_remain_available(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_root = Path(temporary_directory) / "attachments"
            local = build_attachment_storage(
                make_config(
                    storage_provider="local",
                    local_storage_root=local_root,
                )
            )
            memory = build_attachment_storage(
                make_config(storage_provider="memory")
            )

            self.assertIsInstance(local, LocalAttachmentStorage)
            self.assertTrue(local_root.is_dir())
            self.assertIsInstance(memory, MemoryAttachmentStorage)

    def test_invalid_provider_and_missing_s3_configuration_are_safe(self):
        with self.assertRaises(
            AttachmentStorageConfigurationError
        ) as invalid_context:
            build_attachment_storage(
                make_config(storage_provider="other")
            )
        with self.assertRaises(
            AttachmentStorageConfigurationError
        ) as missing_context:
            build_s3_storage(
                make_config(
                    s3_bucket=None,
                    s3_access_key_id=None,
                    s3_secret_access_key="must-not-appear",
                ),
                client=FakeS3Client(),
            )

        combined = (
            str(invalid_context.exception)
            + str(missing_context.exception)
        )
        self.assertNotIn("must-not-appear", combined)
        self.assertNotIn("private-bucket", combined)

    def test_key_prefix_normalization_rejects_namespace_escape(self):
        self.assertEqual(
            normalize_attachment_key_prefix("/fieldflow//files/"),
            "fieldflow/files",
        )
        for invalid in ("../files", "fieldflow\\files", "./files"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(RuntimeError):
                    normalize_attachment_key_prefix(invalid)

    def test_build_client_applies_endpoint_transport_and_retry_options(self):
        session = Mock()
        with patch(
            "app.storage.s3.boto3.session.Session",
            return_value=session,
        ) as session_constructor:
            build_s3_client(make_config())

        session_constructor.assert_called_once_with(
            aws_access_key_id="access-id",
            aws_secret_access_key="top-secret",
            aws_session_token=None,
            region_name="us-west-2",
        )
        call = session.client.call_args
        self.assertEqual(call.args, ("s3",))
        self.assertEqual(
            call.kwargs["endpoint_url"],
            "https://objects.example.test",
        )
        self.assertTrue(call.kwargs["use_ssl"])
        self.assertEqual(
            call.kwargs["config"].s3["addressing_style"],
            "path",
        )
        self.assertEqual(
            call.kwargs["config"].retries["max_attempts"],
            3,
        )

    def test_injected_client_avoids_sdk_client_construction(self):
        fake_client = FakeS3Client()
        with patch(
            "app.storage.s3.build_s3_client"
        ) as client_builder:
            storage = build_s3_storage(
                make_config(),
                client=fake_client,
            )

        self.assertIs(storage.client, fake_client)
        client_builder.assert_not_called()

    def test_streamed_upload_uses_private_metadata_and_prefix(self):
        client = FakeS3Client()
        storage = S3AttachmentStorage(
            client,
            "private-bucket",
            "fieldflow/files",
        )

        storage.put_stream(
            STORAGE_KEY,
            (chunk for chunk in (b"abc", b"def", b"ghi")),
            content_type="application/pdf",
        )

        self.assertEqual(client.upload["content"], b"abcdefghi")
        self.assertEqual(
            client.upload["key"],
            f"fieldflow/files/{STORAGE_KEY}",
        )
        self.assertEqual(
            client.upload["extra_args"]["ContentType"],
            "application/pdf",
        )
        self.assertEqual(
            client.upload["extra_args"]["ChecksumAlgorithm"],
            "SHA256",
        )
        self.assertNotIn("ACL", client.upload["extra_args"])

    def test_upload_preserves_stream_validation_errors(self):
        client = FakeS3Client()
        storage = S3AttachmentStorage(client, "private-bucket")

        def chunks():
            yield b"first"
            raise AttachmentStreamTooLarge("too large")

        with self.assertRaises(AttachmentStreamTooLarge):
            storage.put_stream(STORAGE_KEY, chunks())

    def test_streamed_download_closes_response_body(self):
        client = FakeS3Client()
        storage = S3AttachmentStorage(client, "private-bucket")

        content = b"".join(storage.open_stream(STORAGE_KEY, 4))

        self.assertEqual(content, b"streamed-download")
        self.assertTrue(client.body.closed)
        self.assertTrue(all(size == 4 for size in client.body.read_sizes))

    def test_delete_and_exists_apply_prefix_and_are_idempotent(self):
        client = FakeS3Client()
        storage = S3AttachmentStorage(
            client,
            "private-bucket",
            "prefix",
        )

        self.assertTrue(storage.exists(STORAGE_KEY))
        self.assertTrue(storage.delete(STORAGE_KEY))
        client.head_error = client_error("NoSuchKey", 404)
        client.delete_error = client_error("NoSuchKey", 404)

        self.assertFalse(storage.exists(STORAGE_KEY))
        self.assertFalse(storage.delete(STORAGE_KEY))
        expected = ("private-bucket", f"prefix/{STORAGE_KEY}")
        self.assertIn(expected, client.heads)
        self.assertIn(expected, client.deleted)

    def test_generic_provider_metadata_signed_url_copy_and_health(self):
        client = FakeS3Client()
        storage = S3AttachmentStorage(
            client,
            "private-bucket",
            "prefix",
        )
        destination = "b" * 32

        metadata = storage.metadata(STORAGE_KEY)
        signed_url = storage.generate_download_url(
            STORAGE_KEY,
            expires_seconds=120,
        )
        storage.copy(STORAGE_KEY, destination)

        self.assertEqual(metadata.size_bytes, 17)
        self.assertEqual(metadata.content_type, "application/pdf")
        self.assertEqual(metadata.etag, "checksum-etag")
        self.assertEqual(
            signed_url,
            "https://objects.example.test/signed",
        )
        self.assertEqual(
            client.presigned,
            [
                (
                    "get_object",
                    {
                        "Bucket": "private-bucket",
                        "Key": f"prefix/{STORAGE_KEY}",
                    },
                    120,
                )
            ],
        )
        self.assertEqual(
            client.copies,
            [
                (
                    "private-bucket",
                    {
                        "Bucket": "private-bucket",
                        "Key": f"prefix/{STORAGE_KEY}",
                    },
                    f"prefix/{destination}",
                )
            ],
        )
        self.assertTrue(storage.health_check())
        self.assertEqual(client.bucket_checks, ["private-bucket"])

    def test_provider_errors_are_classified(self):
        cases = (
            (
                client_error("NoSuchKey", 404),
                AttachmentObjectMissing,
            ),
            (
                client_error("AccessDenied", 403),
                AttachmentStorageAuthenticationError,
            ),
            (
                ReadTimeoutError(endpoint_url="https://example.test"),
                AttachmentStorageTimeoutError,
            ),
            (
                EndpointConnectionError(
                    endpoint_url="https://example.test"
                ),
                AttachmentStorageConnectionError,
            ),
            (
                client_error("SlowDown", 429),
                AttachmentStorageThrottledError,
            ),
            (
                client_error("NoSuchBucket", 404),
                AttachmentStorageConfigurationError,
            ),
        )
        for error, expected_type in cases:
            with self.subTest(expected_type=expected_type.__name__):
                self.assertIsInstance(
                    classify_s3_error(error),
                    expected_type,
                )


if __name__ == "__main__":
    unittest.main()

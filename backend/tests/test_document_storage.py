from pathlib import Path
import tempfile
import unittest

from app.storage.provider import (
    LocalStorageProvider,
    MemoryStorageProvider,
    StorageObjectMissing,
    StorageProviderError,
)


class StorageProviderContractTests(unittest.TestCase):
    def exercise_provider(self, provider):
        source = "documents/ab/cd/abcdef0123456789"
        copied = "documents/ab/cd/copied0123456789"
        moved = "documents/ab/cd/moved00123456789"

        self.assertTrue(provider.health_check())
        provider.upload(
            source,
            (chunk for chunk in (b"field", b"flow")),
            content_type="text/plain",
        )
        self.assertTrue(provider.exists(source))
        self.assertEqual(b"".join(provider.download(source, 3)), b"fieldflow")
        self.assertEqual(provider.metadata(source).size_bytes, 9)
        self.assertIsNone(
            provider.generate_download_url(source, expires_seconds=60)
        )

        provider.copy(source, copied)
        self.assertEqual(b"".join(provider.download(copied, 20)), b"fieldflow")
        provider.move(copied, moved)
        self.assertFalse(provider.exists(copied))
        self.assertTrue(provider.exists(moved))
        self.assertTrue(provider.delete(source))
        self.assertFalse(provider.delete(source))
        with self.assertRaises(StorageObjectMissing):
            list(provider.download(source, 4))

    def test_memory_provider_contract(self):
        self.exercise_provider(MemoryStorageProvider())

    def test_local_provider_contract_uses_opaque_nested_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = LocalStorageProvider(Path(directory))
            self.exercise_provider(provider)
            self.assertTrue(
                (
                    Path(directory)
                    / "documents"
                    / "ab"
                    / "cd"
                    / "moved00123456789"
                ).is_file()
            )

    def test_providers_reject_unsafe_keys(self):
        provider = MemoryStorageProvider()
        for key in (
            "../secret",
            "documents/../../secret",
            "/absolute/path",
            "documents/user@example.com/file",
        ):
            with self.subTest(key=key):
                with self.assertRaises(StorageProviderError):
                    provider.upload(key, (b"content",))


if __name__ == "__main__":
    unittest.main()

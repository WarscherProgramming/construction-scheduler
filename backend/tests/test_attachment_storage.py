from pathlib import Path
import tempfile
import unittest

from app.storage.attachment import (
    AttachmentObjectMissing,
    AttachmentStorageError,
    LocalAttachmentStorage,
)


STORAGE_KEY = "0123456789abcdef0123456789abcdef"


class LocalAttachmentStorageTests(unittest.TestCase):
    def test_put_open_exists_and_idempotent_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalAttachmentStorage(Path(directory))
            storage.put_stream(STORAGE_KEY, [b"first", b"-second"])

            self.assertTrue(storage.exists(STORAGE_KEY))
            self.assertEqual(
                b"".join(storage.open_stream(STORAGE_KEY, 3)),
                b"first-second",
            )
            self.assertTrue(storage.delete(STORAGE_KEY))
            self.assertFalse(storage.delete(STORAGE_KEY))

    def test_partial_write_is_removed_when_stream_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalAttachmentStorage(Path(directory))

            def failing_chunks():
                yield b"partial"
                raise ValueError("stream failed")

            with self.assertRaises(ValueError):
                storage.put_stream(STORAGE_KEY, failing_chunks())

            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_existing_storage_key_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalAttachmentStorage(Path(directory))
            storage.put_stream(STORAGE_KEY, [b"original"])

            with self.assertRaises(AttachmentStorageError):
                storage.put_stream(STORAGE_KEY, [b"replacement"])

            self.assertEqual(
                b"".join(storage.open_stream(STORAGE_KEY, 16)),
                b"original",
            )

    def test_missing_objects_and_unsafe_keys_fail_without_path_leaks(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalAttachmentStorage(Path(directory))

            with self.assertRaises(AttachmentObjectMissing):
                storage.open_stream(STORAGE_KEY, 8)
            with self.assertRaises(AttachmentStorageError):
                storage.put_stream("../outside", [b"unsafe"])

            self.assertFalse((Path(directory).parent / "outside").exists())


if __name__ == "__main__":
    unittest.main()

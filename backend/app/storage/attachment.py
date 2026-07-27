from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path
import re


STORAGE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class AttachmentStorageError(Exception):
    """Stable boundary for provider-specific storage failures."""

    category = "unknown"
    retryable = True


class AttachmentObjectMissing(AttachmentStorageError):
    """The metadata exists but its stored object does not."""

    category = "not_found"
    retryable = False


class AttachmentStorageAuthenticationError(AttachmentStorageError):
    category = "authentication"
    retryable = False


class AttachmentStorageTimeoutError(AttachmentStorageError):
    category = "timeout"


class AttachmentStorageConnectionError(AttachmentStorageError):
    category = "connection"


class AttachmentStorageThrottledError(AttachmentStorageError):
    category = "throttled"


class AttachmentStorageConfigurationError(AttachmentStorageError):
    category = "configuration"
    retryable = False


class AttachmentStreamTooLarge(AttachmentStorageError):
    category = "validation"
    retryable = False


class AttachmentStorage(ABC):
    provider_name: str

    @abstractmethod
    def put_stream(
        self,
        storage_key: str,
        chunks: Iterable[bytes],
        *,
        content_type: str | None = None,
    ) -> None:
        """Persist every chunk under an opaque key."""

    @abstractmethod
    def open_stream(
        self,
        storage_key: str,
        chunk_size: int,
    ) -> Iterator[bytes]:
        """Return an iterator that reads the object in bounded chunks."""

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete an object, returning whether it existed."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Return whether an object currently exists."""


def validate_storage_key(storage_key: str) -> None:
    if not STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise AttachmentStorageError("Invalid storage key")


class LocalAttachmentStorage(AttachmentStorage):
    provider_name = "local"

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()

    def _path_for(self, storage_key: str) -> Path:
        validate_storage_key(storage_key)
        return self.root / storage_key

    def put_stream(
        self,
        storage_key: str,
        chunks: Iterable[bytes],
        *,
        content_type: str | None = None,
    ) -> None:
        destination = self._path_for(storage_key)

        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                for chunk in chunks:
                    if chunk:
                        handle.write(chunk)
        except AttachmentStorageError:
            destination.unlink(missing_ok=True)
            raise
        except FileExistsError as error:
            raise AttachmentStorageError(
                "Attachment key already exists"
            ) from error
        except OSError as error:
            destination.unlink(missing_ok=True)
            raise AttachmentStorageError(
                "Unable to store attachment"
            ) from error
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def open_stream(
        self,
        storage_key: str,
        chunk_size: int,
    ) -> Iterator[bytes]:
        source = self._path_for(storage_key)
        if not source.is_file():
            raise AttachmentObjectMissing("Attachment object is missing")

        def read_chunks() -> Iterator[bytes]:
            try:
                with source.open("rb") as handle:
                    while chunk := handle.read(chunk_size):
                        yield chunk
            except OSError as error:
                raise AttachmentStorageError(
                    "Unable to read attachment"
                ) from error

        return read_chunks()

    def delete(self, storage_key: str) -> bool:
        target = self._path_for(storage_key)
        try:
            target.unlink()
            return True
        except FileNotFoundError:
            return False
        except OSError as error:
            raise AttachmentStorageError(
                "Unable to delete attachment"
            ) from error

    def exists(self, storage_key: str) -> bool:
        return self._path_for(storage_key).is_file()


class MemoryAttachmentStorage(AttachmentStorage):
    provider_name = "memory"

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_stream(
        self,
        storage_key: str,
        chunks: Iterable[bytes],
        *,
        content_type: str | None = None,
    ) -> None:
        validate_storage_key(storage_key)
        if storage_key in self.objects:
            raise AttachmentStorageError(
                "Attachment key already exists"
            )
        content = bytearray()
        for chunk in chunks:
            if chunk:
                content.extend(chunk)
        self.objects[storage_key] = bytes(content)

    def open_stream(
        self,
        storage_key: str,
        chunk_size: int,
    ) -> Iterator[bytes]:
        validate_storage_key(storage_key)
        if storage_key not in self.objects:
            raise AttachmentObjectMissing("Attachment object is missing")

        content = self.objects[storage_key]
        return (
            content[offset : offset + chunk_size]
            for offset in range(0, len(content), chunk_size)
        )

    def delete(self, storage_key: str) -> bool:
        validate_storage_key(storage_key)
        return self.objects.pop(storage_key, None) is not None

    def exists(self, storage_key: str) -> bool:
        validate_storage_key(storage_key)
        return storage_key in self.objects

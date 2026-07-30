from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
import re
import shutil


STORAGE_KEY_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]{2,128}(?:/[A-Za-z0-9_-]{2,128}){0,8}$"
)


class StorageProviderError(Exception):
    """Stable boundary for provider-specific storage failures."""

    category = "unknown"
    retryable = True


class StorageObjectMissing(StorageProviderError):
    category = "not_found"
    retryable = False


class StorageAuthenticationError(StorageProviderError):
    category = "authentication"
    retryable = False


class StorageTimeoutError(StorageProviderError):
    category = "timeout"


class StorageConnectionError(StorageProviderError):
    category = "connection"


class StorageThrottledError(StorageProviderError):
    category = "throttled"


class StorageConfigurationError(StorageProviderError):
    category = "configuration"
    retryable = False


class StorageStreamTooLarge(StorageProviderError):
    category = "validation"
    retryable = False


@dataclass(frozen=True)
class StorageObjectMetadata:
    size_bytes: int
    content_type: str | None = None
    etag: str | None = None


class StorageProvider(ABC):
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

    def upload(
        self,
        storage_key: str,
        chunks: Iterable[bytes],
        *,
        content_type: str | None = None,
    ) -> None:
        self.put_stream(
            storage_key,
            chunks,
            content_type=content_type,
        )

    @abstractmethod
    def open_stream(
        self,
        storage_key: str,
        chunk_size: int,
    ) -> Iterator[bytes]:
        """Return an iterator that reads the object in bounded chunks."""

    def download(
        self,
        storage_key: str,
        chunk_size: int,
    ) -> Iterator[bytes]:
        return self.open_stream(storage_key, chunk_size)

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete an object, returning whether it existed."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Return whether an object currently exists."""

    @abstractmethod
    def metadata(self, storage_key: str) -> StorageObjectMetadata:
        """Return safe provider metadata for an object."""

    @abstractmethod
    def generate_download_url(
        self,
        storage_key: str,
        *,
        expires_seconds: int = 300,
    ) -> str | None:
        """Return a temporary provider URL, or None when unsupported."""

    @abstractmethod
    def copy(self, source_key: str, destination_key: str) -> None:
        """Copy an object without exposing provider paths."""

    def move(self, source_key: str, destination_key: str) -> None:
        self.copy(source_key, destination_key)
        try:
            self.delete(source_key)
        except StorageProviderError:
            try:
                self.delete(destination_key)
            except StorageProviderError:
                pass
            raise

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the configured provider is reachable."""


def validate_storage_key(storage_key: str) -> None:
    if not STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise StorageProviderError("Invalid storage key")


class LocalStorageProvider(StorageProvider):
    provider_name = "local"

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()

    def _path_for(self, storage_key: str) -> Path:
        validate_storage_key(storage_key)
        return self.root.joinpath(*storage_key.split("/"))

    def put_stream(
        self,
        storage_key: str,
        chunks: Iterable[bytes],
        *,
        content_type: str | None = None,
    ) -> None:
        destination = self._path_for(storage_key)

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                for chunk in chunks:
                    if chunk:
                        handle.write(chunk)
        except StorageProviderError:
            destination.unlink(missing_ok=True)
            raise
        except FileExistsError as error:
            raise StorageProviderError(
                "Storage key already exists"
            ) from error
        except OSError as error:
            destination.unlink(missing_ok=True)
            raise StorageProviderError(
                "Unable to store object"
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
            raise StorageObjectMissing("Stored object is missing")

        def read_chunks() -> Iterator[bytes]:
            try:
                with source.open("rb") as handle:
                    while chunk := handle.read(chunk_size):
                        yield chunk
            except OSError as error:
                raise StorageProviderError(
                    "Unable to read object"
                ) from error

        return read_chunks()

    def delete(self, storage_key: str) -> bool:
        target = self._path_for(storage_key)
        try:
            target.unlink()
            self._remove_empty_parents(target.parent)
            return True
        except FileNotFoundError:
            return False
        except OSError as error:
            raise StorageProviderError(
                "Unable to delete object"
            ) from error

    def exists(self, storage_key: str) -> bool:
        return self._path_for(storage_key).is_file()

    def metadata(self, storage_key: str) -> StorageObjectMetadata:
        source = self._path_for(storage_key)
        try:
            stat = source.stat()
        except FileNotFoundError as error:
            raise StorageObjectMissing("Stored object is missing") from error
        except OSError as error:
            raise StorageProviderError(
                "Unable to inspect object"
            ) from error
        if not source.is_file():
            raise StorageObjectMissing("Stored object is missing")
        return StorageObjectMetadata(size_bytes=stat.st_size)

    def generate_download_url(
        self,
        storage_key: str,
        *,
        expires_seconds: int = 300,
    ) -> None:
        validate_storage_key(storage_key)
        return None

    def copy(self, source_key: str, destination_key: str) -> None:
        source = self._path_for(source_key)
        destination = self._path_for(destination_key)
        if not source.is_file():
            raise StorageObjectMissing("Stored object is missing")
        if destination.exists():
            raise StorageProviderError("Storage key already exists")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as source_handle:
                with destination.open("xb") as destination_handle:
                    shutil.copyfileobj(source_handle, destination_handle)
        except FileExistsError as error:
            raise StorageProviderError(
                "Storage key already exists"
            ) from error
        except OSError as error:
            destination.unlink(missing_ok=True)
            raise StorageProviderError(
                "Unable to copy object"
            ) from error

    def move(self, source_key: str, destination_key: str) -> None:
        source = self._path_for(source_key)
        destination = self._path_for(destination_key)
        if not source.is_file():
            raise StorageObjectMissing("Stored object is missing")
        if destination.exists():
            raise StorageProviderError("Storage key already exists")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.replace(destination)
            self._remove_empty_parents(source.parent)
        except OSError as error:
            raise StorageProviderError(
                "Unable to move object"
            ) from error

    def health_check(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        return self.root.is_dir()

    def _remove_empty_parents(self, directory: Path) -> None:
        while directory != self.root:
            try:
                directory.rmdir()
            except OSError:
                return
            directory = directory.parent


class MemoryStorageProvider(StorageProvider):
    provider_name = "memory"

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str | None] = {}

    def put_stream(
        self,
        storage_key: str,
        chunks: Iterable[bytes],
        *,
        content_type: str | None = None,
    ) -> None:
        validate_storage_key(storage_key)
        if storage_key in self.objects:
            raise StorageProviderError("Storage key already exists")
        content = bytearray()
        for chunk in chunks:
            if chunk:
                content.extend(chunk)
        self.objects[storage_key] = bytes(content)
        self.content_types[storage_key] = content_type

    def open_stream(
        self,
        storage_key: str,
        chunk_size: int,
    ) -> Iterator[bytes]:
        validate_storage_key(storage_key)
        if storage_key not in self.objects:
            raise StorageObjectMissing("Stored object is missing")

        content = self.objects[storage_key]
        return (
            content[offset : offset + chunk_size]
            for offset in range(0, len(content), chunk_size)
        )

    def delete(self, storage_key: str) -> bool:
        validate_storage_key(storage_key)
        self.content_types.pop(storage_key, None)
        return self.objects.pop(storage_key, None) is not None

    def exists(self, storage_key: str) -> bool:
        validate_storage_key(storage_key)
        return storage_key in self.objects

    def metadata(self, storage_key: str) -> StorageObjectMetadata:
        validate_storage_key(storage_key)
        if storage_key not in self.objects:
            raise StorageObjectMissing("Stored object is missing")
        return StorageObjectMetadata(
            size_bytes=len(self.objects[storage_key]),
            content_type=self.content_types.get(storage_key),
        )

    def generate_download_url(
        self,
        storage_key: str,
        *,
        expires_seconds: int = 300,
    ) -> None:
        validate_storage_key(storage_key)
        return None

    def copy(self, source_key: str, destination_key: str) -> None:
        validate_storage_key(source_key)
        validate_storage_key(destination_key)
        if source_key not in self.objects:
            raise StorageObjectMissing("Stored object is missing")
        if destination_key in self.objects:
            raise StorageProviderError("Storage key already exists")
        self.objects[destination_key] = self.objects[source_key]
        self.content_types[destination_key] = self.content_types.get(source_key)

    def health_check(self) -> bool:
        return True

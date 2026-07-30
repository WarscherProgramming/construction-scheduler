"""Compatibility exports for the original attachment storage API."""

from app.storage.provider import (
    LocalStorageProvider,
    MemoryStorageProvider,
    StorageAuthenticationError,
    StorageConfigurationError,
    StorageConnectionError,
    StorageObjectMissing,
    StorageProvider,
    StorageProviderError,
    StorageStreamTooLarge,
    StorageThrottledError,
    StorageTimeoutError,
    validate_storage_key,
)


AttachmentStorage = StorageProvider
AttachmentStorageError = StorageProviderError
AttachmentObjectMissing = StorageObjectMissing
AttachmentStorageAuthenticationError = StorageAuthenticationError
AttachmentStorageTimeoutError = StorageTimeoutError
AttachmentStorageConnectionError = StorageConnectionError
AttachmentStorageThrottledError = StorageThrottledError
AttachmentStorageConfigurationError = StorageConfigurationError
AttachmentStreamTooLarge = StorageStreamTooLarge
LocalAttachmentStorage = LocalStorageProvider
MemoryAttachmentStorage = MemoryStorageProvider


__all__ = [
    "AttachmentObjectMissing",
    "AttachmentStorage",
    "AttachmentStorageAuthenticationError",
    "AttachmentStorageConfigurationError",
    "AttachmentStorageConnectionError",
    "AttachmentStorageError",
    "AttachmentStorageThrottledError",
    "AttachmentStorageTimeoutError",
    "AttachmentStreamTooLarge",
    "LocalAttachmentStorage",
    "MemoryAttachmentStorage",
    "validate_storage_key",
]

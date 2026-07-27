from dataclasses import replace
from pathlib import Path

from app.core.config import AttachmentConfig
from app.storage.attachment import (
    AttachmentStorage,
    AttachmentStorageConfigurationError,
    LocalAttachmentStorage,
    MemoryAttachmentStorage,
)
from app.storage.s3 import build_s3_storage


def build_attachment_storage(
    config: AttachmentConfig,
    *,
    client=None,
) -> AttachmentStorage:
    provider = config.storage_provider
    if provider == "local":
        root = Path(config.local_storage_root)
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise AttachmentStorageConfigurationError(
                "Attachment local storage root is unavailable"
            ) from error
        if not root.is_dir():
            raise AttachmentStorageConfigurationError(
                "Attachment local storage root is invalid"
            )
        return LocalAttachmentStorage(root)
    if provider == "memory":
        return MemoryAttachmentStorage()
    if provider == "s3":
        return build_s3_storage(config, client=client)

    raise AttachmentStorageConfigurationError(
        "Unsupported attachment storage provider"
    )


def build_storage_resolver(config: AttachmentConfig):
    storages: dict[str, AttachmentStorage] = {}

    def resolve(provider: str) -> AttachmentStorage:
        if provider not in storages:
            provider_config = replace(
                config,
                storage_provider=provider,
            )
            storages[provider] = build_attachment_storage(
                provider_config
            )
        return storages[provider]

    return resolve

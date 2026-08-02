from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL.Image import Image


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float | None = None


class OCRProviderError(Exception):
    code = "ocr_failed"
    retryable = False


class OCRUnavailableError(OCRProviderError):
    code = "ocr_unavailable"


class OCRTimeoutError(OCRProviderError):
    code = "ocr_timeout"
    retryable = True


class OCRProvider(ABC):
    provider_name: str

    @property
    @abstractmethod
    def available(self) -> bool:
        """Return whether this provider can process images."""

    @abstractmethod
    def extract_text(
        self,
        image: Image,
        *,
        language: str,
        timeout_seconds: int,
    ) -> OCRResult:
        """Extract plain text from one already bounded image."""


class DisabledOCRProvider(OCRProvider):
    provider_name = "disabled"

    @property
    def available(self) -> bool:
        return False

    def extract_text(
        self,
        image: Image,
        *,
        language: str,
        timeout_seconds: int,
    ) -> OCRResult:
        raise OCRUnavailableError("OCR is not configured")

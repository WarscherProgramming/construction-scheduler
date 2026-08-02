from dataclasses import dataclass
from io import BytesIO
import time
import unicodedata
import warnings

from PIL import Image, ImageOps
import pypdfium2 as pdfium

from app.core.config import DocumentExtractionConfig
from app.extraction.ocr import (
    OCRProvider,
    OCRProviderError,
    OCRUnavailableError,
)


EXTRACTOR_VERSION = (
    f"pypdfium2-{pdfium.PYPDFIUM_INFO.version}:fieldflow-1"
)
SUPPORTED_EXTRACTION_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)


class ExtractionError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    extraction_method: str
    confidence: float | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    pages: tuple[ExtractedPage, ...]
    page_count: int
    pages_processed: int
    extraction_method: str
    status: str
    warning_codes: tuple[str, ...]

    @property
    def character_count(self) -> int:
        return sum(len(page.text) for page in self.pages)

    @property
    def searchable(self) -> bool:
        return any(page.text.strip() for page in self.pages)


def normalize_extracted_text(text: str, maximum: int) -> tuple[str, bool]:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    output: list[str] = []
    previous_space = False
    previous_newline = False
    for character in normalized.replace("\r\n", "\n").replace("\r", "\n"):
        if character == "\n":
            if output and not previous_newline:
                output.append("\n")
            previous_space = False
            previous_newline = True
            continue
        if character == "\t" or character.isspace():
            if output and not previous_space and not previous_newline:
                output.append(" ")
            previous_space = True
            continue
        if character == "\x00" or unicodedata.category(character).startswith("C"):
            continue
        output.append(character)
        previous_space = False
        previous_newline = False

    value = "".join(output).strip()
    truncated = len(value) > maximum
    return value[:maximum], truncated


def _meaningful_character_count(text: str) -> int:
    return sum(character.isalnum() for character in text)


def _check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise ExtractionError(
            "parser_timeout",
            "Document extraction exceeded the configured time limit",
            retryable=True,
        )


def _validate_image_bounds(
    image: Image.Image,
    config: DocumentExtractionConfig,
) -> None:
    width, height = image.size
    if (
        width <= 0
        or height <= 0
        or width > config.ocr_max_dimension
        or height > config.ocr_max_dimension
        or width * height > config.ocr_max_pixels
    ):
        raise ExtractionError(
            "image_limit_exceeded",
            "Document image exceeds the configured processing limits",
        )


def _is_blank_image(image: Image.Image) -> bool:
    grayscale = image.convert("L")
    try:
        low, high = grayscale.getextrema()
        return high - low <= 2 and high >= 245
    finally:
        grayscale.close()


def _ocr_page(
    image: Image.Image,
    provider: OCRProvider,
    config: DocumentExtractionConfig,
) -> tuple[str, float | None, bool]:
    if not config.ocr_enabled or not provider.available:
        raise OCRUnavailableError("OCR is not configured")
    result = provider.extract_text(
        image,
        language=config.ocr_language,
        timeout_seconds=config.ocr_page_timeout_seconds,
    )
    text, truncated = normalize_extracted_text(
        result.text,
        config.max_chars_per_page,
    )
    confidence = result.confidence
    if confidence is not None:
        confidence = max(0.0, min(100.0, float(confidence)))
    return text, confidence, truncated


def _combine_page_text(
    embedded: str,
    ocr_text: str,
    maximum: int,
) -> tuple[str, bool]:
    if embedded and ocr_text:
        return normalize_extracted_text(f"{embedded}\n{ocr_text}", maximum)
    return normalize_extracted_text(embedded or ocr_text, maximum)


def _document_method(pages: list[ExtractedPage]) -> str:
    methods = {
        page.extraction_method
        for page in pages
        if page.text.strip()
    }
    if not methods:
        return "metadata_only"
    if methods == {"embedded_text"}:
        return "embedded_text"
    if methods == {"ocr"}:
        return "ocr"
    return "mixed"


def _extract_pdf(
    content: bytes,
    provider: OCRProvider,
    config: DocumentExtractionConfig,
    deadline: float,
) -> ExtractedDocument:
    try:
        pdf = pdfium.PdfDocument(content)
    except Exception as error:
        message = str(error).lower()
        code = "encrypted_pdf" if "password" in message else "corrupt_file"
        safe_message = (
            "Encrypted PDFs are not supported"
            if code == "encrypted_pdf"
            else "The PDF could not be read"
        )
        raise ExtractionError(code, safe_message) from error

    pages: list[ExtractedPage] = []
    warnings: list[str] = []
    ocr_pages = 0
    total_characters = 0
    try:
        page_count = len(pdf)
        if page_count > config.max_pages:
            raise ExtractionError(
                "page_limit_exceeded",
                "Document exceeds the configured page limit",
            )

        for page_index in range(page_count):
            _check_deadline(deadline)
            page = pdf[page_index]
            embedded = ""
            embedded_truncated = False
            try:
                text_page = page.get_textpage()
                try:
                    embedded, embedded_truncated = normalize_extracted_text(
                        text_page.get_text_range(),
                        config.max_chars_per_page,
                    )
                finally:
                    text_page.close()

                meaningful = (
                    _meaningful_character_count(embedded)
                    >= config.embedded_text_threshold
                )
                if meaningful:
                    page_text = embedded
                    method = "embedded_text"
                    confidence = None
                else:
                    width_points, height_points = page.get_size()
                    scale = config.ocr_dpi / 72
                    width = max(1, round(width_points * scale))
                    height = max(1, round(height_points * scale))
                    if (
                        width > config.ocr_max_dimension
                        or height > config.ocr_max_dimension
                        or width * height > config.ocr_max_pixels
                    ):
                        raise ExtractionError(
                            "image_limit_exceeded",
                            "PDF page exceeds the configured processing limits",
                        )
                    bitmap = page.render(scale=scale)
                    image = bitmap.to_pil()
                    try:
                        if _is_blank_image(image):
                            page_text = embedded
                            method = "embedded_text"
                            confidence = None
                        elif ocr_pages >= config.ocr_max_pages:
                            page_text = embedded
                            method = "embedded_text"
                            confidence = None
                            warnings.append("ocr_page_limit_exceeded")
                        else:
                            ocr_pages += 1
                            try:
                                (
                                    ocr_text,
                                    confidence,
                                    ocr_truncated,
                                ) = _ocr_page(image, provider, config)
                            except OCRUnavailableError:
                                page_text = embedded
                                method = "embedded_text"
                                confidence = None
                                warnings.append("ocr_unavailable")
                            except OCRProviderError as error:
                                page_text = embedded
                                method = "embedded_text"
                                confidence = None
                                warnings.append(error.code)
                            else:
                                page_text, combined_truncated = _combine_page_text(
                                    embedded,
                                    ocr_text,
                                    config.max_chars_per_page,
                                )
                                embedded_truncated = (
                                    embedded_truncated
                                    or ocr_truncated
                                    or combined_truncated
                                )
                                method = "mixed" if embedded else "ocr"
                                _check_deadline(deadline)
                    finally:
                        image.close()
                        bitmap.close()
            finally:
                page.close()

            remaining = config.max_chars_per_document - total_characters
            if remaining <= 0:
                page_text = ""
                warnings.append("text_limit_exceeded")
            elif len(page_text) > remaining:
                page_text = page_text[:remaining]
                warnings.append("text_limit_exceeded")
            if embedded_truncated:
                warnings.append("text_limit_exceeded")
            total_characters += len(page_text)
            pages.append(
                ExtractedPage(
                    page_number=page_index + 1,
                    text=page_text,
                    extraction_method=method,
                    confidence=confidence,
                )
            )
    finally:
        pdf.close()

    warning_codes = tuple(dict.fromkeys(warnings))
    method = _document_method(pages)
    searchable = any(page.text.strip() for page in pages)
    if searchable:
        status = "completed_with_warnings" if warning_codes else "completed"
    elif warning_codes:
        status = "unavailable"
        method = "unavailable"
    else:
        status = "completed"
    return ExtractedDocument(
        pages=tuple(pages),
        page_count=len(pages),
        pages_processed=len(pages),
        extraction_method=method,
        status=status,
        warning_codes=warning_codes,
    )


def _extract_raster(
    content: bytes,
    provider: OCRProvider,
    config: DocumentExtractionConfig,
    deadline: float,
) -> ExtractedDocument:
    _check_deadline(deadline)
    image = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(content))
            _validate_image_bounds(image, config)
            image.load()
    except ExtractionError:
        if image is not None:
            image.close()
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ) as error:
        if image is not None:
            image.close()
        raise ExtractionError(
            "corrupt_file",
            "The image could not be read safely",
        ) from error

    try:
        oriented = ImageOps.exif_transpose(image)
        try:
            _validate_image_bounds(oriented, config)
            if _is_blank_image(oriented):
                return ExtractedDocument(
                    pages=(ExtractedPage(1, "", "metadata_only"),),
                    page_count=1,
                    pages_processed=1,
                    extraction_method="metadata_only",
                    status="completed",
                    warning_codes=(),
                )
            try:
                text, confidence, truncated = _ocr_page(
                    oriented,
                    provider,
                    config,
                )
                _check_deadline(deadline)
            except OCRUnavailableError:
                return ExtractedDocument(
                    pages=(),
                    page_count=1,
                    pages_processed=0,
                    extraction_method="unavailable",
                    status="unavailable",
                    warning_codes=("ocr_unavailable",),
                )
            except OCRProviderError as error:
                raise ExtractionError(
                    error.code,
                    "OCR could not process the document",
                    retryable=error.retryable,
                ) from error
        finally:
            if oriented is not image:
                oriented.close()
    finally:
        image.close()

    truncated = truncated or len(text) > config.max_chars_per_document
    text = text[: config.max_chars_per_document]
    return ExtractedDocument(
        pages=(ExtractedPage(1, text, "ocr", confidence),),
        page_count=1,
        pages_processed=1,
        extraction_method="ocr" if text else "metadata_only",
        status="completed_with_warnings" if truncated else "completed",
        warning_codes=("text_limit_exceeded",) if truncated else (),
    )


def extract_document_content(
    content: bytes,
    mime_type: str,
    provider: OCRProvider,
    config: DocumentExtractionConfig,
) -> ExtractedDocument:
    if mime_type not in SUPPORTED_EXTRACTION_MIME_TYPES:
        raise ExtractionError(
            "unsupported_type",
            "This document type supports metadata search only",
        )
    deadline = time.monotonic() + config.extraction_timeout_seconds
    if mime_type == "application/pdf":
        return _extract_pdf(content, provider, config, deadline)
    return _extract_raster(content, provider, config, deadline)

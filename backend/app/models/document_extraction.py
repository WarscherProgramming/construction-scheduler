from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


SEARCH_VECTOR_TYPE = Text().with_variant(TSVECTOR(), "postgresql")


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', "
            "'completed_with_warnings', 'failed', 'unavailable', "
            "'cancelled')",
            name="ck_document_extractions_status",
        ),
        CheckConstraint(
            "extraction_method IN ('embedded_text', 'ocr', 'mixed', "
            "'metadata_only', 'unavailable')",
            name="ck_document_extractions_method",
        ),
        CheckConstraint(
            "page_count >= 0",
            name="ck_document_extractions_page_count_nonnegative",
        ),
        CheckConstraint(
            "pages_processed >= 0 AND pages_processed <= page_count",
            name="ck_document_extractions_pages_processed",
        ),
        CheckConstraint(
            "text_character_count >= 0",
            name="ck_document_extractions_character_count_nonnegative",
        ),
        UniqueConstraint(
            "document_id",
            name="uq_document_extractions_document",
        ),
        Index(
            "ix_document_extractions_project_status",
            "project_id",
            "status",
            "searchable",
            "updated_at",
            "id",
        ),
        Index(
            "ix_document_extractions_project_document",
            "project_id",
            "document_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    extraction_method = Column(
        String(32),
        nullable=False,
        default="unavailable",
        server_default="unavailable",
    )
    page_count = Column(Integer, nullable=False, default=0, server_default="0")
    pages_processed = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    text_character_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    searchable = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    language = Column(String(16), nullable=False, default="eng", server_default="eng")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(50), nullable=True)
    failure_message = Column(String(300), nullable=True)
    warning_codes = Column(String(300), nullable=True)
    extractor_version = Column(String(100), nullable=False)
    source_checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class DocumentPageText(Base):
    __tablename__ = "document_page_texts"
    __table_args__ = (
        CheckConstraint(
            "page_number >= 1",
            name="ck_document_page_texts_page_positive",
        ),
        CheckConstraint(
            "extraction_method IN ('embedded_text', 'ocr', 'mixed', "
            "'metadata_only', 'unavailable')",
            name="ck_document_page_texts_method",
        ),
        CheckConstraint(
            "character_count >= 0",
            name="ck_document_page_texts_character_count_nonnegative",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
            name="ck_document_page_texts_confidence_range",
        ),
        UniqueConstraint(
            "extraction_id",
            "page_number",
            name="uq_document_page_texts_extraction_page",
        ),
        Index(
            "ix_document_page_texts_project_document",
            "project_id",
            "document_id",
            "page_number",
            "id",
        ),
        Index(
            "ix_document_page_texts_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    extraction_id = Column(
        Integer,
        ForeignKey("document_extractions.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    search_vector = Column(SEARCH_VECTOR_TYPE, nullable=True)
    extraction_method = Column(String(32), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=True)
    character_count = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class DocumentExtractionJob(Base):
    __tablename__ = "document_extraction_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', "
            "'cancelled')",
            name="ck_document_extraction_jobs_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_document_extraction_jobs_attempt_nonnegative",
        ),
        Index(
            "uq_document_extraction_jobs_active_document",
            "document_id",
            "source_checksum",
            unique=True,
            sqlite_where=text("status IN ('pending', 'processing')"),
            postgresql_where=text("status IN ('pending', 'processing')"),
        ),
        Index(
            "ix_document_extraction_jobs_pending",
            "status",
            "available_at",
            "created_at",
            "id",
        ),
        Index(
            "ix_document_extraction_jobs_lease",
            "status",
            "lease_expires_at",
        ),
        Index(
            "ix_document_extraction_jobs_project_document",
            "project_id",
            "document_id",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    available_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    lease_token = Column(String(64), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_error_code = Column(String(50), nullable=True)
    last_error_message = Column(String(300), nullable=True)
    source_checksum = Column(String(64), nullable=False)
    extractor_version = Column(String(100), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )

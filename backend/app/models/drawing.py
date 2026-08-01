from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
)

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DrawingSet(Base):
    __tablename__ = "drawing_sets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_drawing_sets_status",
        ),
        Index(
            "uq_drawing_sets_active_name",
            "project_id",
            "name",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_drawing_sets_project_listing",
            "project_id",
            "deleted_at",
            "updated_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    issue_date = Column(String(10), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class DrawingSheet(Base):
    __tablename__ = "drawing_sheets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'void', 'archived')",
            name="ck_drawing_sheets_status",
        ),
        UniqueConstraint(
            "drawing_set_id",
            "normalized_sheet_number",
            name="uq_drawing_sheets_set_normalized_number",
        ),
        Index(
            "ix_drawing_sheets_project_register",
            "project_id",
            "deleted_at",
            "drawing_set_id",
            "discipline",
            "status",
            "sort_key",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    drawing_set_id = Column(
        Integer,
        ForeignKey("drawing_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sheet_number = Column(String(100), nullable=False)
    normalized_sheet_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    discipline = Column(String(10), nullable=False)
    description = Column(Text, nullable=True)
    sort_key = Column(String(500), nullable=False)
    # Application-managed because a database FK would create a circular
    # dependency with DrawingRevision.drawing_sheet_id.
    current_revision_id = Column(Integer, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class DrawingRevision(Base):
    __tablename__ = "drawing_revisions"
    __table_args__ = (
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_drawing_revisions_sequence_positive",
        ),
        UniqueConstraint(
            "document_id",
            name="uq_drawing_revisions_document",
        ),
        UniqueConstraint(
            "drawing_sheet_id",
            "normalized_revision_code",
            name="uq_drawing_revisions_sheet_code",
        ),
        UniqueConstraint(
            "drawing_sheet_id",
            "sequence_number",
            name="uq_drawing_revisions_sheet_sequence",
        ),
        Index(
            "uq_drawing_revisions_current_sheet",
            "drawing_sheet_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
            postgresql_where=text("is_current = true"),
        ),
        Index(
            "ix_drawing_revisions_sheet_history",
            "drawing_sheet_id",
            "sequence_number",
            "id",
        ),
        Index(
            "ix_drawing_revisions_project_document",
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
    drawing_sheet_id = Column(
        Integer,
        ForeignKey("drawing_sheets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_code = Column(String(50), nullable=False)
    normalized_revision_code = Column(String(50), nullable=False)
    revision_date = Column(String(10), nullable=False)
    description = Column(Text, nullable=True)
    sequence_number = Column(Integer, nullable=False)
    is_current = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    superseded_by_revision_id = Column(
        Integer,
        ForeignKey("drawing_revisions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class DrawingIssue(Base):
    __tablename__ = "drawing_issues"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'issued', 'void')",
            name="ck_drawing_issues_status",
        ),
        CheckConstraint(
            "purpose IN ('bid', 'permit', 'construction', 'addendum', "
            "'bulletin', 'record', 'as_built', 'other')",
            name="ck_drawing_issues_purpose",
        ),
        UniqueConstraint(
            "drawing_set_id",
            "issue_number",
            name="uq_drawing_issues_set_number",
        ),
        Index(
            "ix_drawing_issues_set_listing",
            "drawing_set_id",
            "deleted_at",
            "issue_date",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    drawing_set_id = Column(
        Integer,
        ForeignKey("drawing_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    issue_number = Column(String(100), nullable=False)
    issue_date = Column(String(10), nullable=False)
    purpose = Column(String(20), nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    issued_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class DrawingIssueRevision(Base):
    __tablename__ = "drawing_issue_revisions"
    __table_args__ = (
        Index(
            "ix_drawing_issue_revisions_revision",
            "drawing_revision_id",
            "drawing_issue_id",
        ),
    )

    drawing_issue_id = Column(
        Integer,
        ForeignKey("drawing_issues.id", ondelete="CASCADE"),
        primary_key=True,
    )
    drawing_revision_id = Column(
        Integer,
        ForeignKey("drawing_revisions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.db.database import Base
from app.models.attachment import Attachment  # noqa: F401
from app.models.attachment_cleanup import AttachmentCleanupJob  # noqa: F401
from app.models.change_order import (  # noqa: F401
    ChangeOrder,
    ChangeOrderNumberSequence,
)
from app.models.daily_log import DailyLog  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.document_extraction import (  # noqa: F401
    DocumentExtraction,
    DocumentExtractionJob,
    DocumentPageText,
)
from app.models.drawing import (  # noqa: F401
    DrawingIssue,
    DrawingIssueRevision,
    DrawingRevision,
    DrawingSet,
    DrawingSheet,
)
from app.models.entity_relationship import EntityRelationship  # noqa: F401
from app.models.folder import Folder  # noqa: F401
from app.models.inspection import Inspection  # noqa: F401
from app.models.look_ahead import LookAheadItem, LookAheadPlan  # noqa: F401
from app.models.resource_planning import (  # noqa: F401
    Crew,
    EquipmentResource,
    ResourceAvailability,
    TaskResourceAssignment,
)
from app.models.note_delay import NoteDelay  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_schedule_settings import (  # noqa: F401
    ProjectScheduleSettings,
)
from app.models.project_company import ProjectCompany  # noqa: F401
from app.models.punch_item import PunchItem, PunchItemNumberSequence  # noqa: F401
from app.models.rfi import RFI, RFINumberSequence  # noqa: F401
from app.models.schedule_baseline import (  # noqa: F401
    ScheduleBaseline,
    ScheduleBaselineTask,
    ScheduleBaselineTaskDependency,
)
from app.models.refresh_session import RefreshSession  # noqa: F401
from app.models.submittal import Submittal, SubmittalNumberSequence  # noqa: F401
from app.models.task import Task, TaskDependency  # noqa: F401
from app.models.template import (  # noqa: F401
    ScheduleTemplate,
    ScheduleTemplateTask,
    ScheduleTemplateTaskDependency,
)
from app.models.user import User  # noqa: F401

load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

database_url = os.getenv("DATABASE_URL")
if database_url is None or not database_url.strip():
    raise RuntimeError("Required environment variable DATABASE_URL is not set")

# ConfigParser treats percent signs as interpolation markers.
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


from fastapi import FastAPI
from app.api.routes_task import router as task_router
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.template import ScheduleTemplate, ScheduleTemplateTask
from app.models.inspection import Inspection
from app.models.daily_log import DailyLog
from app.models.note_delay import NoteDelay
from app.models.change_order import ChangeOrder
from app.api.routes_project import router as project_router
from app.api.routes_template import router as template_router
from app.api.routes_export import router as export_router
from app.api.routes_auth import router as auth_router
from app.api.routes_daily_log import router as daily_log_router
from app.api.routes_inspection import router as inspection_router
from app.api.routes_note_delay import router as note_delay_router
from app.api.routes_change_order import router as change_order_router


Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(task_router)
app.include_router(project_router)
app.include_router(template_router)
app.include_router(export_router)
app.include_router(auth_router)
app.include_router(daily_log_router)
app.include_router(inspection_router)
app.include_router(note_delay_router)
app.include_router(change_order_router)

@app.get("/")
def root():
    return {"message": "Scheduler API is running!"}
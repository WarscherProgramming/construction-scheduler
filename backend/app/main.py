
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ALLOWED_ORIGINS

from app.api.routes_task import router as task_router
from app.api.routes_project import router as project_router
from app.api.routes_template import router as template_router
from app.api.routes_export import router as export_router
from app.api.routes_auth import router as auth_router
from app.api.routes_daily_log import router as daily_log_router
from app.api.routes_inspection import router as inspection_router
from app.api.routes_note_delay import router as note_delay_router
from app.api.routes_change_order import router as change_order_router
from app.api.routes_project_company import router as project_company_router

app = FastAPI(
    title="FieldFlow API",
    version="1.0.0",
)

# ----------------------------------------------------
# CORS
# ----------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# Routes
# ----------------------------------------------------

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(task_router)
app.include_router(template_router)
app.include_router(export_router)
app.include_router(daily_log_router)
app.include_router(inspection_router)
app.include_router(note_delay_router)
app.include_router(change_order_router)
app.include_router(project_company_router)

# ----------------------------------------------------
# Health Check
# ----------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "FieldFlow API is running",
        "version": "1.0.0",
    }


from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import ALLOWED_ORIGINS, APP_DEBUG, MAX_REQUEST_BODY_BYTES
from app.middleware.security import (
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
)

from app.api.routes_task import router as task_router
from app.api.routes_project import router as project_router
from app.api.routes_template import router as template_router
from app.api.routes_export import router as export_router
from app.api.routes_auth import router as auth_router
from app.api.routes_attachment import router as attachment_router
from app.api.routes_daily_log import router as daily_log_router
from app.api.routes_inspection import router as inspection_router
from app.api.routes_note_delay import router as note_delay_router
from app.api.routes_change_order import router as change_order_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_document import router as document_router
from app.api.routes_document_search import router as document_search_router
from app.api.routes_drawing import router as drawing_router
from app.api.routes_relationship import router as relationship_router
from app.api.routes_project_company import router as project_company_router
from app.api.routes_punch_item import router as punch_item_router
from app.api.routes_rfi import router as rfi_router
from app.api.routes_schedule_settings import router as schedule_settings_router
from app.api.routes_schedule_baseline import router as schedule_baseline_router
from app.api.routes_submittal import router as submittal_router
from app.api.routes_look_ahead import router as look_ahead_router
from app.api.routes_resources import router as resources_router
from app.api.routes_schedule_health import router as schedule_health_router
from app.api.routes_preconstruction import router as preconstruction_router

app = FastAPI(
    title="FieldFlow API",
    version="1.0.0",
    debug=APP_DEBUG,
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    safe_errors = [
        {
            "type": item["type"],
            "loc": item["loc"],
            "msg": item["msg"],
        }
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": safe_errors})


# ----------------------------------------------------
# Middleware
# ----------------------------------------------------

# Starlette places the most recently added middleware outermost. The resulting
# request order is security headers -> CORS -> body limit -> route handling.
app.add_middleware(
    RequestBodyLimitMiddleware,
    max_body_bytes=MAX_REQUEST_BODY_BYTES,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

# ----------------------------------------------------
# Routes
# ----------------------------------------------------

app.include_router(auth_router)
app.include_router(attachment_router)
app.include_router(project_router)
app.include_router(task_router)
app.include_router(template_router)
app.include_router(export_router)
app.include_router(daily_log_router)
app.include_router(inspection_router)
app.include_router(note_delay_router)
app.include_router(change_order_router)
app.include_router(dashboard_router)
app.include_router(document_router)
app.include_router(document_search_router)
app.include_router(drawing_router)
app.include_router(relationship_router)
app.include_router(project_company_router)
app.include_router(punch_item_router)
app.include_router(rfi_router)
app.include_router(schedule_settings_router)
app.include_router(schedule_baseline_router)
app.include_router(submittal_router)
app.include_router(look_ahead_router)
app.include_router(resources_router)
app.include_router(schedule_health_router)
app.include_router(preconstruction_router)

# ----------------------------------------------------
# Health Check
# ----------------------------------------------------

@app.get("/")
def root():
    return {"status": "online"}

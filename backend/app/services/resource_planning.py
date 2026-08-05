from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.domain.scheduling import is_workday
from app.models.project_company import ProjectCompany
from app.models.resource_planning import (
    Crew,
    EquipmentResource,
    ResourceAvailability,
    TaskResourceAssignment,
)
from app.models.task import Task
from app.services.project_schedule_settings import get_project_schedule_settings
from app.services.resource_resolver import (
    ResourceType,
    ensure_active,
    get_project_resource,
    resource_definition,
    typed_reference,
)
from app.services.task_scheduling import schedule_metadata, task_response_rows


MAX_RESOURCE_LIST = 200
MAX_LOADING_DAYS = 90
MAX_LOADING_CONFLICTS = 100
MAX_CONTRIBUTING_TASKS_PER_CONFLICT = 5


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _commit(db: Session, duplicate_detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=duplicate_detail) from error
    except Exception:
        db.rollback()
        raise


def _company(db: Session, project_id: int, company_id: int | None) -> ProjectCompany | None:
    if company_id is None:
        return None
    company = db.query(ProjectCompany).filter(
        ProjectCompany.id == company_id,
        ProjectCompany.project_id == project_id,
    ).first()
    if company is None:
        raise HTTPException(status_code=422, detail="Company does not belong to this project")
    return company


def _company_summary(company: ProjectCompany | None) -> dict | None:
    if company is None:
        return None
    return {"id": company.id, "name": company.name, "trade": company.trade}


def _crew_response(crew: Crew, company: ProjectCompany | None = None) -> dict:
    return {
        "id": crew.id,
        "project_id": crew.project_id,
        "name": crew.name,
        "trade": crew.trade,
        "company": _company_summary(company),
        "description": crew.description,
        "default_capacity": crew.default_capacity,
        "capacity_unit": crew.capacity_unit,
        "status": crew.status,
        "created_by": crew.created_by,
        "created_at": crew.created_at,
        "updated_at": crew.updated_at,
        "archived_at": crew.archived_at,
    }


def create_crew(db: Session, *, project_id: int, created_by: int, values: dict) -> dict:
    company = _company(db, project_id, values.get("company_id"))
    crew = Crew(
        project_id=project_id,
        created_by=created_by,
        normalized_name=values["name"].casefold(),
        capacity_unit="workers",
        **values,
    )
    db.add(crew)
    _commit(db, "A crew with this name already exists")
    db.refresh(crew)
    return _crew_response(crew, company)


def list_crews(
    db: Session, *, project_id: int, status_filter: str, limit: int, offset: int
) -> dict:
    query = db.query(Crew).filter(Crew.project_id == project_id)
    if status_filter != "all":
        query = query.filter(Crew.status == status_filter)
    total = query.count()
    crews = query.order_by(Crew.name, Crew.id).offset(offset).limit(limit).all()
    company_ids = {row.company_id for row in crews if row.company_id is not None}
    companies = (
        db.query(ProjectCompany).filter(
            ProjectCompany.project_id == project_id,
            ProjectCompany.id.in_(company_ids),
        ).all()
        if company_ids else []
    )
    company_map = {row.id: row for row in companies}
    return {
        "crews": [_crew_response(row, company_map.get(row.company_id)) for row in crews],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_crew(db: Session, *, project_id: int, crew_id: int) -> dict:
    crew = get_project_resource(
        db, project_id=project_id, resource_type="crew", resource_id=crew_id
    )
    company = _company(db, project_id, crew.company_id) if crew.company_id else None
    return _crew_response(crew, company)


def update_crew(db: Session, *, project_id: int, crew_id: int, values: dict) -> dict:
    crew = get_project_resource(
        db,
        project_id=project_id,
        resource_type="crew",
        resource_id=crew_id,
        for_update=True,
    )
    ensure_active(crew)
    company = _company(db, project_id, values.get("company_id", crew.company_id))
    if "name" in values:
        crew.normalized_name = values["name"].casefold()
    for field, value in values.items():
        setattr(crew, field, value or None if field in {"trade", "description"} else value)
    crew.updated_at = utc_now()
    _commit(db, "A crew with this name already exists")
    db.refresh(crew)
    return _crew_response(crew, company)


def archive_crew(db: Session, *, project_id: int, crew_id: int) -> dict:
    crew = get_project_resource(
        db,
        project_id=project_id,
        resource_type="crew",
        resource_id=crew_id,
        for_update=True,
    )
    if crew.status != "archived":
        crew.status = "archived"
        crew.archived_at = utc_now()
        crew.updated_at = crew.archived_at
        _commit(db, "Unable to archive crew")
        db.refresh(crew)
    return get_crew(db, project_id=project_id, crew_id=crew.id)


def create_equipment(
    db: Session, *, project_id: int, created_by: int, values: dict
) -> EquipmentResource:
    identifier = values.get("identifier") or None
    equipment = EquipmentResource(
        project_id=project_id,
        created_by=created_by,
        normalized_name=values["name"].casefold(),
        normalized_identifier=identifier.casefold() if identifier else None,
        identifier=identifier,
        capacity_unit="units",
        **{key: value for key, value in values.items() if key != "identifier"},
    )
    db.add(equipment)
    _commit(db, "Equipment name or identifier already exists")
    db.refresh(equipment)
    return equipment


def list_equipment(
    db: Session, *, project_id: int, status_filter: str, limit: int, offset: int
) -> dict:
    query = db.query(EquipmentResource).filter(EquipmentResource.project_id == project_id)
    if status_filter != "all":
        query = query.filter(EquipmentResource.status == status_filter)
    total = query.count()
    equipment = (
        query.order_by(EquipmentResource.name, EquipmentResource.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"equipment": equipment, "total": total, "limit": limit, "offset": offset}


def get_equipment(db: Session, *, project_id: int, equipment_id: int) -> EquipmentResource:
    return get_project_resource(
        db,
        project_id=project_id,
        resource_type="equipment",
        resource_id=equipment_id,
    )


def update_equipment(
    db: Session, *, project_id: int, equipment_id: int, values: dict
) -> EquipmentResource:
    equipment = get_project_resource(
        db,
        project_id=project_id,
        resource_type="equipment",
        resource_id=equipment_id,
        for_update=True,
    )
    ensure_active(equipment)
    if "name" in values:
        equipment.normalized_name = values["name"].casefold()
    if "identifier" in values:
        identifier = values["identifier"] or None
        equipment.normalized_identifier = identifier.casefold() if identifier else None
        values["identifier"] = identifier
    for field, value in values.items():
        setattr(
            equipment,
            field,
            value or None if field in {"description", "identifier"} else value,
        )
    equipment.updated_at = utc_now()
    _commit(db, "Equipment name or identifier already exists")
    db.refresh(equipment)
    return equipment


def archive_equipment(
    db: Session, *, project_id: int, equipment_id: int
) -> EquipmentResource:
    equipment = get_project_resource(
        db,
        project_id=project_id,
        resource_type="equipment",
        resource_id=equipment_id,
        for_update=True,
    )
    if equipment.status != "archived":
        equipment.status = "archived"
        equipment.archived_at = utc_now()
        equipment.updated_at = equipment.archived_at
        _commit(db, "Unable to archive equipment")
        db.refresh(equipment)
    return equipment


def _task_for_assignment(db: Session, project_id: int, task_id: int, *, lock=False) -> Task:
    query = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id)
    if lock:
        query = query.with_for_update()
    task = query.first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.is_milestone:
        raise HTTPException(status_code=422, detail="Milestones cannot receive resources")
    if db.query(Task.id).filter(Task.parent_task_id == task.id).first():
        raise HTTPException(status_code=422, detail="Summary tasks cannot receive resources")
    return task


def _resource_summary(resource, resource_type: ResourceType) -> dict:
    return {
        "id": resource.id,
        "resource_type": resource_type,
        "name": resource.name,
        "detail": resource.trade if resource_type == "crew" else resource.equipment_type,
        "identifier": None if resource_type == "crew" else resource.identifier,
        "status": resource.status,
        "default_capacity": resource.default_capacity,
        "capacity_unit": resource.capacity_unit,
    }


def _assignment_response(assignment: TaskResourceAssignment, resource) -> dict:
    return {
        "id": assignment.id,
        "project_id": assignment.project_id,
        "task_id": assignment.task_id,
        "resource": _resource_summary(resource, assignment.resource_type),
        "allocation_amount": assignment.allocation_amount,
        "allocation_unit": assignment.allocation_unit,
        "notes": assignment.notes,
        "created_by": assignment.created_by,
        "updated_by": assignment.updated_by,
        "created_at": assignment.created_at,
        "updated_at": assignment.updated_at,
    }


def _assignment_resource_maps(db: Session, assignments: list[TaskResourceAssignment]):
    crew_ids = {row.crew_id for row in assignments if row.crew_id is not None}
    equipment_ids = {
        row.equipment_resource_id
        for row in assignments
        if row.equipment_resource_id is not None
    }
    crews = db.query(Crew).filter(Crew.id.in_(crew_ids)).all() if crew_ids else []
    equipment = (
        db.query(EquipmentResource).filter(EquipmentResource.id.in_(equipment_ids)).all()
        if equipment_ids else []
    )
    return {row.id: row for row in crews}, {row.id: row for row in equipment}


def list_task_assignments(db: Session, *, project_id: int, task_id: int) -> dict:
    _task_for_assignment(db, project_id, task_id)
    assignments = db.query(TaskResourceAssignment).filter(
        TaskResourceAssignment.project_id == project_id,
        TaskResourceAssignment.task_id == task_id,
    ).order_by(TaskResourceAssignment.resource_type, TaskResourceAssignment.id).all()
    crews, equipment = _assignment_resource_maps(db, assignments)
    return {
        "assignments": [
            _assignment_response(
                row,
                crews[row.crew_id]
                if row.resource_type == "crew"
                else equipment[row.equipment_resource_id],
            )
            for row in assignments
        ]
    }


def create_assignment(
    db: Session,
    *,
    project_id: int,
    task_id: int,
    created_by: int,
    values: dict,
) -> dict:
    _task_for_assignment(db, project_id, task_id, lock=True)
    resource_type = values.pop("resource_type")
    resource_id = values.pop("resource_id")
    resource = get_project_resource(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        for_update=True,
    )
    ensure_active(resource)
    assignment = TaskResourceAssignment(
        project_id=project_id,
        task_id=task_id,
        created_by=created_by,
        allocation_unit=resource.capacity_unit,
        **typed_reference(resource_type, resource_id),
        **values,
    )
    db.add(assignment)
    _commit(db, "This resource is already assigned to the task")
    db.refresh(assignment)
    return _assignment_response(assignment, resource)


def _get_assignment(
    db: Session, *, project_id: int, task_id: int, assignment_id: int, lock=False
) -> TaskResourceAssignment:
    query = db.query(TaskResourceAssignment).filter(
        TaskResourceAssignment.id == assignment_id,
        TaskResourceAssignment.project_id == project_id,
        TaskResourceAssignment.task_id == task_id,
    )
    if lock:
        query = query.with_for_update()
    assignment = query.first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Resource assignment not found")
    return assignment


def update_assignment(
    db: Session,
    *,
    project_id: int,
    task_id: int,
    assignment_id: int,
    updated_by: int,
    values: dict,
) -> dict:
    _task_for_assignment(db, project_id, task_id, lock=True)
    assignment = _get_assignment(
        db,
        project_id=project_id,
        task_id=task_id,
        assignment_id=assignment_id,
        lock=True,
    )
    resource_id = assignment.crew_id or assignment.equipment_resource_id
    resource = get_project_resource(
        db,
        project_id=project_id,
        resource_type=assignment.resource_type,
        resource_id=resource_id,
    )
    ensure_active(resource)
    for field, value in values.items():
        setattr(assignment, field, value or None if field == "notes" else value)
    assignment.updated_by = updated_by
    assignment.updated_at = utc_now()
    _commit(db, "Unable to update resource assignment")
    db.refresh(assignment)
    return _assignment_response(assignment, resource)


def delete_assignment(
    db: Session, *, project_id: int, task_id: int, assignment_id: int
) -> None:
    _task_for_assignment(db, project_id, task_id, lock=True)
    assignment = _get_assignment(
        db,
        project_id=project_id,
        task_id=task_id,
        assignment_id=assignment_id,
        lock=True,
    )
    db.delete(assignment)
    _commit(db, "Unable to delete resource assignment")


def _availability_query(db: Session, project_id: int, resource_type: ResourceType, resource_id: int):
    reference = resource_definition(resource_type).reference_field
    return db.query(ResourceAvailability).filter(
        ResourceAvailability.project_id == project_id,
        getattr(ResourceAvailability, reference) == resource_id,
    )


def list_availability(
    db: Session,
    *,
    project_id: int,
    resource_type: ResourceType,
    resource_id: int,
    limit: int,
    offset: int,
) -> dict:
    get_project_resource(
        db, project_id=project_id, resource_type=resource_type, resource_id=resource_id
    )
    query = _availability_query(db, project_id, resource_type, resource_id)
    total = query.count()
    rows = (
        query.order_by(ResourceAvailability.start_date, ResourceAvailability.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "availability": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _validate_no_overlap(
    db: Session,
    *,
    project_id: int,
    resource_type: ResourceType,
    resource_id: int,
    start_date: str,
    end_date: str,
    exclude_id: int | None = None,
) -> None:
    query = _availability_query(db, project_id, resource_type, resource_id).filter(
        ResourceAvailability.start_date <= end_date,
        ResourceAvailability.end_date >= start_date,
    )
    if exclude_id is not None:
        query = query.filter(ResourceAvailability.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=409, detail="Availability ranges cannot overlap")


def create_availability(
    db: Session,
    *,
    project_id: int,
    resource_type: ResourceType,
    resource_id: int,
    created_by: int,
    values: dict,
) -> ResourceAvailability:
    resource = get_project_resource(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        for_update=True,
    )
    ensure_active(resource)
    _validate_no_overlap(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=values["start_date"],
        end_date=values["end_date"],
    )
    row = ResourceAvailability(
        project_id=project_id,
        created_by=created_by,
        **typed_reference(resource_type, resource_id),
        **values,
    )
    db.add(row)
    _commit(db, "Availability range already exists")
    db.refresh(row)
    return row


def _get_availability(
    db: Session,
    *,
    project_id: int,
    resource_type: ResourceType,
    resource_id: int,
    availability_id: int,
    lock=False,
) -> ResourceAvailability:
    query = _availability_query(db, project_id, resource_type, resource_id).filter(
        ResourceAvailability.id == availability_id
    )
    if lock:
        query = query.with_for_update()
    row = query.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Availability override not found")
    return row


def update_availability(
    db: Session,
    *,
    project_id: int,
    resource_type: ResourceType,
    resource_id: int,
    availability_id: int,
    updated_by: int,
    values: dict,
) -> ResourceAvailability:
    resource = get_project_resource(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        for_update=True,
    )
    ensure_active(resource)
    row = _get_availability(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        availability_id=availability_id,
        lock=True,
    )
    next_start = values.get("start_date", row.start_date)
    next_end = values.get("end_date", row.end_date)
    if next_end < next_start:
        raise HTTPException(status_code=422, detail="End date cannot be earlier than start date")
    _validate_no_overlap(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=next_start,
        end_date=next_end,
        exclude_id=row.id,
    )
    for field, value in values.items():
        setattr(row, field, value or None if field == "notes" else value)
    row.updated_by = updated_by
    row.updated_at = utc_now()
    _commit(db, "Availability range already exists")
    db.refresh(row)
    return row


def delete_availability(
    db: Session,
    *,
    project_id: int,
    resource_type: ResourceType,
    resource_id: int,
    availability_id: int,
) -> None:
    get_project_resource(
        db, project_id=project_id, resource_type=resource_type, resource_id=resource_id
    )
    row = _get_availability(
        db,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        availability_id=availability_id,
        lock=True,
    )
    db.delete(row)
    _commit(db, "Unable to delete availability override")


def _wbs_by_id(tasks: list[Task]) -> dict[int, str]:
    children: dict[int | None, list[Task]] = defaultdict(list)
    for task in tasks:
        children[task.parent_task_id].append(task)
    result: dict[int, str] = {}

    def visit(parent_id: int | None, prefix: str = "") -> None:
        for index, task in enumerate(children.get(parent_id, []), start=1):
            value = f"{prefix}.{index}" if prefix else str(index)
            result[task.id] = value
            visit(task.id, value)

    visit(None)
    return result


def _task_summary(row: dict, wbs: dict[int, str]) -> dict:
    return {
        "id": row["id"],
        "wbs": wbs.get(row["id"]),
        "name": row["name"],
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "progress_status": row["progress_status"],
        "is_critical": row["is_critical"],
    }


def _dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def get_resource_loading(
    db: Session,
    *,
    project_id: int,
    start_date: str | None,
    end_date: str | None,
    resource_type: ResourceType | None,
    resource_id: int | None,
    company_id: int | None,
    trade: str | None,
    over_allocated_only: bool,
    include_unassigned: bool,
    limit: int,
    offset: int,
    summary_only: bool = False,
) -> dict:
    settings = get_project_schedule_settings(db, project_id)
    data_date = date.fromisoformat(settings.data_date)
    start = date.fromisoformat(start_date) if start_date else data_date
    end = date.fromisoformat(end_date) if end_date else start + timedelta(days=20)
    if end < start:
        raise HTTPException(status_code=422, detail="End date cannot be earlier than start date")
    if (end - start).days + 1 > MAX_LOADING_DAYS:
        raise HTTPException(status_code=422, detail="Resource loading is limited to 90 days")
    if resource_id is not None and resource_type is None:
        raise HTTPException(status_code=422, detail="resource_type is required with resource_id")
    if company_id is not None:
        _company(db, project_id, company_id)

    crews = db.query(Crew).filter(Crew.project_id == project_id).order_by(Crew.name, Crew.id).all()
    equipment = db.query(EquipmentResource).filter(
        EquipmentResource.project_id == project_id
    ).order_by(EquipmentResource.name, EquipmentResource.id).all()
    companies = db.query(ProjectCompany).filter(ProjectCompany.project_id == project_id).all()
    company_map = {row.id: row for row in companies}

    resources: list[tuple[ResourceType, Crew | EquipmentResource]] = []
    if resource_type in (None, "crew"):
        resources.extend(
            ("crew", row)
            for row in crews
            if (resource_id is None or row.id == resource_id)
            and (company_id is None or row.company_id == company_id)
            and (not trade or (row.trade or "").casefold() == trade.casefold())
        )
    if resource_type in (None, "equipment") and company_id is None and not trade:
        resources.extend(
            ("equipment", row)
            for row in equipment
            if resource_id is None or row.id == resource_id
        )

    tasks = db.query(Task).options(joinedload(Task.dependencies)).filter(
        Task.project_id == project_id
    ).order_by(Task.order_index, Task.id).all()
    annotated = schedule_metadata(tasks)
    task_rows = task_response_rows(tasks, annotated=annotated)
    task_map = {row["id"]: row for row in task_rows}
    wbs = _wbs_by_id(tasks)
    summary_ids = {row.parent_task_id for row in tasks if row.parent_task_id is not None}
    assignments = db.query(TaskResourceAssignment).filter(
        TaskResourceAssignment.project_id == project_id
    ).order_by(TaskResourceAssignment.id).all()
    assignments_by_resource: dict[tuple[str, int], list[TaskResourceAssignment]] = defaultdict(list)
    assigned_task_ids = set()
    for assignment in assignments:
        assigned_task_ids.add(assignment.task_id)
        key = (
            assignment.resource_type,
            assignment.crew_id
            if assignment.resource_type == "crew"
            else assignment.equipment_resource_id,
        )
        assignments_by_resource[key].append(assignment)
    availability = db.query(ResourceAvailability).filter(
        ResourceAvailability.project_id == project_id,
        ResourceAvailability.start_date <= end.isoformat(),
        ResourceAvailability.end_date >= start.isoformat(),
    ).all()
    availability_by_resource: dict[tuple[str, int], list[ResourceAvailability]] = defaultdict(list)
    for row in availability:
        key = (
            row.resource_type,
            row.crew_id if row.resource_type == "crew" else row.equipment_resource_id,
        )
        availability_by_resource[key].append(row)

    all_dates = list(_dates(start, end))
    loading_rows = []
    conflicts = []
    matching_resource_count = 0
    labor_overallocated_days = 0
    equipment_overallocated_days = 0
    labor_by_date: dict[str, int] = defaultdict(int)
    equipment_by_type_date: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    look_ahead_end = data_date + timedelta(days=20)
    for current_type, resource in resources:
        key = (current_type, resource.id)
        demand_by_date: dict[str, int] = defaultdict(int)
        tasks_by_date: dict[str, dict[int, dict]] = defaultdict(dict)
        for assignment in assignments_by_resource.get(key, []):
            task = task_map.get(assignment.task_id)
            if (
                task is None
                or task["id"] in summary_ids
                or task["is_milestone"]
                or task["progress_status"] == "completed"
                or not task["start_date"]
                or not task["end_date"]
            ):
                continue
            task_start = date.fromisoformat(task["start_date"])
            task_end = date.fromisoformat(task["end_date"])
            if task["progress_status"] == "in_progress":
                task_start = max(task_start, data_date)
            active_start = max(start, task_start)
            active_end = min(end, task_end)
            if active_end < active_start:
                continue
            for active_date in _dates(active_start, active_end):
                if not is_workday(active_date):
                    continue
                value = active_date.isoformat()
                demand_by_date[value] += assignment.allocation_amount
                tasks_by_date[value][task["id"]] = _task_summary(task, wbs)

        days = []
        resource_conflicts = 0
        unavailable_days = 0
        for current in all_dates:
            value = current.isoformat()
            demand = demand_by_date[value]
            override = next(
                (
                    row
                    for row in availability_by_resource.get(key, [])
                    if row.start_date <= value <= row.end_date
                ),
                None,
            )
            capacity = (
                override.capacity
                if override is not None
                else resource.default_capacity
                if is_workday(current)
                else 0
            )
            overage = max(0, demand - capacity)
            day_status = (
                "unavailable" if demand > 0 and capacity == 0
                else "over_allocated" if overage > 0
                else "within_capacity"
            )
            day = {
                "date": value,
                "demand": demand,
                "capacity": capacity,
                "available_remainder": max(0, capacity - demand),
                "utilization_percent": round(demand / capacity * 100, 1) if capacity else None,
                "overage": overage,
                "status": day_status,
            }
            if not summary_only:
                days.append(day)
            if current_type == "crew":
                labor_by_date[value] += demand
            else:
                equipment_by_type_date[resource.equipment_type][value] += demand
            if day_status != "within_capacity":
                resource_conflicts += 1
                unavailable_days += int(day_status == "unavailable")
                if current_type == "crew":
                    labor_overallocated_days += 1
                else:
                    equipment_overallocated_days += 1
                task_summaries = list(tasks_by_date[value].values())
                conflicts.append(
                    {
                        "date": value,
                        "resource": _resource_summary(resource, current_type),
                        "demand": demand,
                        "capacity": capacity,
                        "overage": overage,
                        "status": day_status,
                        "message": (
                            "This resource is unavailable on this date."
                            if day_status == "unavailable"
                            else f"Demand exceeds capacity by {overage} {resource.capacity_unit}."
                        ),
                        "contributing_tasks": task_summaries[
                            :MAX_CONTRIBUTING_TASKS_PER_CONFLICT
                        ],
                        "contributing_task_count": len(task_summaries),
                        "contributing_tasks_truncated": (
                            len(task_summaries)
                            > MAX_CONTRIBUTING_TASKS_PER_CONFLICT
                        ),
                    }
                )
        row = {
            "resource": _resource_summary(resource, current_type),
            "company": _company_summary(company_map.get(resource.company_id))
            if current_type == "crew" else None,
            "trade": resource.trade if current_type == "crew" else None,
            "days": days,
            "peak_demand": max(demand_by_date.values(), default=0),
            "average_demand": round(
                sum(demand_by_date.values()) / max(1, sum(is_workday(day) for day in all_dates)),
                2,
            ),
            "over_allocated_days": resource_conflicts,
            "unavailable_days": unavailable_days,
        }
        if not over_allocated_only or resource_conflicts:
            matching_resource_count += 1
        if not summary_only and (not over_allocated_only or resource_conflicts):
            loading_rows.append(row)

    executable = [
        row for row in task_rows
        if row["id"] not in summary_ids
        and not row["is_milestone"]
        and row["progress_status"] != "completed"
    ]
    all_unassigned = []
    unscheduled_count = 0
    for task in executable:
        if task["id"] in assigned_task_ids:
            continue
        unscheduled = not task["start_date"] or not task["end_date"]
        if unscheduled:
            unscheduled_count += 1
        else:
            task_start = date.fromisoformat(task["start_date"])
            task_end = date.fromisoformat(task["end_date"])
            if task_end < start or task_start > end:
                continue
        all_unassigned.append(
            {
                **_task_summary(task, wbs),
                "reason": "No planned resource assignment.",
                "unscheduled": unscheduled,
            }
        )
    total_resources = matching_resource_count
    loading_rows = loading_rows[offset:offset + limit]
    conflicts.sort(key=lambda row: (row["date"], row["resource"]["resource_type"], row["resource"]["name"]))
    total_conflicts = len(conflicts)
    unavailable_resource_conflicts = sum(
        row["status"] == "unavailable" for row in conflicts
    )
    look_ahead_over_allocation_count = sum(
        data_date <= date.fromisoformat(row["date"]) <= look_ahead_end
        for row in conflicts
    )
    conflicts = conflicts[:MAX_LOADING_CONFLICTS]
    workday_values = [day.isoformat() for day in all_dates if is_workday(day)]
    return {
        "project_id": project_id,
        "data_date": settings.data_date,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "summary": {
            "active_crews": sum(row.status == "active" for row in crews),
            "active_equipment_resources": sum(row.status == "active" for row in equipment),
            "assigned_tasks": len(assigned_task_ids),
            "unassigned_executable_tasks": len(all_unassigned),
            "unscheduled_tasks": unscheduled_count,
            "over_allocated_resource_days": total_conflicts,
            "labor_overallocated_days": labor_overallocated_days,
            "equipment_overallocated_days": equipment_overallocated_days,
            "unavailable_resource_conflicts": unavailable_resource_conflicts,
            "look_ahead_over_allocation_count": look_ahead_over_allocation_count,
            "peak_labor_demand": max(labor_by_date.values(), default=0),
            "average_labor_demand": round(
                sum(labor_by_date[value] for value in workday_values) / max(1, len(workday_values)),
                2,
            ),
            "equipment_type_peaks": [
                {
                    "equipment_type": equipment_type,
                    "peak_demand": max(values.values(), default=0),
                }
                for equipment_type, values in sorted(equipment_by_type_date.items())
            ],
        },
        "resources": loading_rows,
        "conflicts": conflicts,
        "unassigned_tasks": all_unassigned[:MAX_RESOURCE_LIST] if include_unassigned else [],
        "total_conflicts": total_conflicts,
        "conflict_limit": MAX_LOADING_CONFLICTS,
        "conflicts_truncated": total_conflicts > MAX_LOADING_CONFLICTS,
        "total_resources": total_resources,
        "limit": limit,
        "offset": offset,
    }


def get_resource_health_metrics(db: Session, *, project_id: int) -> dict:
    data = get_resource_loading(
        db,
        project_id=project_id,
        start_date=None,
        end_date=None,
        resource_type=None,
        resource_id=None,
        company_id=None,
        trade=None,
        over_allocated_only=False,
        include_unassigned=False,
        limit=1,
        offset=0,
        summary_only=True,
    )
    return {
        "summary": data["summary"],
        "conflicts": data["conflicts"],
    }

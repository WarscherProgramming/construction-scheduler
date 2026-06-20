# FieldFlow

FieldFlow is a full-stack construction planning and field management
application built with React, FastAPI, PostgreSQL, SQLAlchemy, Vite, Render,
and Vercel.

## Features

- Spreadsheet-style schedule editing with keyboard support
- Finish-to-Start and Start-to-Start dependencies with lag
- Workday scheduling that excludes weekends and federal holidays
- Parent/child task hierarchy and drag-and-drop ordering
- Gantt visualization and PDF schedule export
- Reusable schedule templates
- Project dashboards and operational metrics
- Daily logs, inspections, notes and delays, and change orders
- Project-company management
- Search, filtering, responsive record cards, and accessible navigation

## Project structure

```text
scheduler/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- db/
|   |   |-- domain/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- services/
|   |   `-- main.py
|   |-- alembic/
|   |-- tests/
|   `-- requirements.txt
|-- frontend/
|   |-- public/
|   |-- src/
|   |   |-- auth/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- services/
|   |   |-- utils/
|   |   `-- App.jsx
|   `-- package.json
`-- README.md
```

## Backend setup

From `backend/`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/scheduler_db
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://construction-scheduler-eight.vercel.app
```

Apply migrations and run the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`; interactive documentation is at
`http://127.0.0.1:8000/docs`.

Run backend tests:

```bash
pytest
```

## Frontend setup

From `frontend/`:

```bash
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

Run frontend verification:

```bash
npm run lint
npm test
npm run build
```

Set `VITE_API_URL` in the frontend deployment environment to the deployed
FieldFlow API base URL.

## Deployment

- `backend/render.yaml` defines the Render web service, migrations, health
  check, and production CORS origin.
- The frontend is designed for Vercel and uses hash-based routes so project
  modules remain refresh-safe without additional rewrite rules.

## Potential next features

- Critical-path calculations
- Drag-and-drop Gantt editing
- RFIs and submittals
- Punch lists
- File and document management
- Weather-delay integration
- Resource loading

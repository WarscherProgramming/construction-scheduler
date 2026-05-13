
# Construction Scheduler

A full-stack construction scheduling application inspired by tools like Procore, Primavera P6, and Microsoft Project.

This project was built to manage construction schedules using spreadsheet-style editing, dependency logic, Gantt chart visualization, reusable templates, and PostgreSQL persistence.

---

# Features

## Scheduling Engine
- Spreadsheet-style task editing
- Dynamic row creation
- Finish-to-Start (FS) dependencies
- Start-to-Start (SS) dependencies
- Dependency lag support
  - Examples:
    - `1`
    - `1+3`
    - `1SS`
    - `1SS+4`
- Automatic schedule recalculation
- Workday scheduling
  - Weekends excluded
  - Federal holidays excluded
- Editable manual task start dates

---

## Gantt Chart
- Live Gantt chart rendering
- Dependency highlighting
- Project timeline visualization
- Dynamic task updates

---

## Project Management
- Multiple projects
- Project switching
- PostgreSQL persistence
- Project-specific schedules

---

## Templates
- Save schedules as reusable templates
- Apply templates to projects
- Reuse common construction schedule structures

---

## Exporting
- Export schedules to PDF
- Professional table formatting
- Project-based PDF generation

---

# Tech Stack

## Frontend
- React
- Vite

## Backend
- FastAPI
- SQLAlchemy

## Database
- PostgreSQL

## PDF Generation
- ReportLab

---

# Project Structure

```text
scheduler/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── db/
│   │   ├── models/
│   │   └── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── App.jsx
│   └── package.json
│
└── README.md
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/warscherprogramming/construction-scheduler.git
cd construction-scheduler
```

---

# Backend Setup

## Create Virtual Environment

```bash
python -m venv venv
```

## Activate Virtual Environment

### Windows

```bash
venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## PostgreSQL Setup

Create a PostgreSQL database:

```text
scheduler_db
```

Create a `.env` file inside `backend/`:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/scheduler_db
```

---

## Run Backend

```bash
uvicorn app.main:app --reload
```

Backend runs on:

```text
http://127.0.0.1:8000
```

Swagger Docs:

```text
http://127.0.0.1:8000/docs
```

---

# Frontend Setup

## Install Dependencies

```bash
npm install
```

## Run Frontend

```bash
npm run dev
```

Frontend runs on:

```text
http://localhost:5173
```

---

# Future Improvements

- Critical path calculations
- Drag-and-drop Gantt editing
- User authentication
- Cloud deployment
- Daily logs
- RFIs
- Submittals
- Punch lists
- File/document management
- Weather delays
- Resource loading

---

# Screenshots

_Add screenshots here later._


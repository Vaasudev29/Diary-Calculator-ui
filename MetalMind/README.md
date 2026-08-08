# MetalMind

MetalMind is a beginner-friendly commercial intelligence dashboard for a
**fictional** metals/steel company (ABC Steel Ltd.). It helps you understand
revenue, costs, gross profit, margins, customer and product profitability,
at-risk customers, and cross-sell opportunities — all calculated from demo
CSV data. All data is fictional and for learning purposes only.

## Project structure

```
MetalMind/
├── frontend/   React + Vite user interface (what you see in the browser)
├── backend/    FastAPI server (reads the CSV and does the calculations)
├── data/       Demo CSV files (fictional sales data)
├── docs/       Simple documentation
└── README.md   This file
```

## Required software

- **Node.js 18+** and npm (for the frontend)
- **Python 3.9+** (for the backend)

## Installation

### Backend (one-time setup)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### Frontend (one-time setup)

```powershell
cd frontend
npm install
```

## How to run

You need **two terminals** — one for the backend, one for the frontend.

**Terminal 1 — backend:**

```powershell
cd backend
venv\Scripts\activate
uvicorn main:app --reload
```

The API runs at http://localhost:8000 — check http://localhost:8000/api/health

**Terminal 2 — frontend:**

```powershell
cd frontend
npm run dev
```

The dashboard runs at http://localhost:5173

## Packages used (and why)

**Frontend**

| Package | Why we need it |
| --- | --- |
| react, react-dom | Build the user interface |
| recharts | Draw the dashboard charts |
| lucide-react | Simple icons |

**Backend**

| Package | Why we need it |
| --- | --- |
| fastapi | Create the API endpoints |
| uvicorn | Run the FastAPI server |
| pandas | Read and calculate from the CSV data |
| python-multipart | Support CSV file uploads (Phase 16) |

## Status

Phase 1 complete: project structure, frontend scaffold, and backend health
endpoint. Demo data and business calculations come in the next phases.

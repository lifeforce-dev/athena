# Athena - Cash Flow Projection

Project and visualize recurring cash flows over time.

## Quick Start

### Backend

```bash
# Create a virtual environment and install
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -e ".[dev]"

# Copy the example config and edit with your own data
cp data.example.json data.json

# Run the API server
uvicorn app.main:app --reload
```

The API is at `http://localhost:8000` and docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`.

### CLI

```bash
# Project cash flow to a target date
athena --config data.json --as-of 2026-06-30

# With a custom start date and verbose recurrence info
athena --config data.json --as-of 2026-06-30 --from-date 2026-02-01 --verbose
```

### Tests

```bash
pytest -v
```

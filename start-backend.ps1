# Start Backend (FastAPI)
# Run from project root
Write-Host "Starting FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Cyan
Push-Location backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location

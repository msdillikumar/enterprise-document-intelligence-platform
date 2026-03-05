# Start Streamlit Dashboard
# Run from project root
Write-Host "Starting Streamlit Dashboard on http://localhost:8501 ..." -ForegroundColor Cyan
Push-Location streamlit_app
streamlit run app.py
Pop-Location

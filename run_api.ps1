Set-Location "$PSScriptRoot\backend\app"
python -m uvicorn main:app --reload --port 8000

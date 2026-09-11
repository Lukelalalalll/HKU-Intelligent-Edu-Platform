$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if (!(Test-Path .\venv\Scripts\python.exe)) { python -m venv .\venv }
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Start-Process -WindowStyle Hidden .\venv\Scripts\python.exe -ArgumentList '-m uvicorn app.main:app --reload --port 8000'
Start-Process -WindowStyle Hidden .\venv\Scripts\python.exe -ArgumentList '-m app.workers.worker'
Set-Location ..\frontend
npm install
npm run dev

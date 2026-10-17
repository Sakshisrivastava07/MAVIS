# Windows helper: open local servers in separate PowerShell windows.
$Root = Split-Path -Parent $PSScriptRoot
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$Root'; .\.venv\Scripts\python.exe -m http.server 5500 --directory web"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$Root'; .\.venv\Scripts\python.exe -m uvicorn api.server:app --host 127.0.0.1 --port 8001"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$Root'; .\.venv\Scripts\python.exe agent\agent.py dev"
Write-Host 'Start LiveKit and Speaches first (see README). Web, token API, and agent terminals are opening.'

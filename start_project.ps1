$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host 'Starting TechCorp AI backend on http://127.0.0.1:8001' -ForegroundColor Cyan
Start-Process -FilePath 'python' -ArgumentList 'scripts/serve_model.py --host 127.0.0.1 --port 8001' -WorkingDirectory $root

Start-Sleep -Seconds 2
Write-Host 'Starting web UI on http://127.0.0.1:5500' -ForegroundColor Cyan
Start-Process -FilePath 'python' -ArgumentList '-m http.server 5500 --directory webapp' -WorkingDirectory $root

Write-Host 'Project started. Open http://127.0.0.1:5500' -ForegroundColor Green

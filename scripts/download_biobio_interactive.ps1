$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
Write-Host 'Acceso Earthdata para observaciones reales de Concepción/Penco.'
Write-Host 'Introduce tus credenciales solo aquí. La contraseña no aparece ni se guarda.'
& '.\.venv\Scripts\python.exe' scripts/download_scenes.py --candidates catalog/concepcion_penco_candidates.json --target work/raw/concepcion_penco
if ($LASTEXITCODE -ne 0) { throw 'Descarga no completada; no se publica como dato verificado.' }
& '.\.venv\Scripts\python.exe' scripts/verify_downloads.py --scenes catalog/concepcion_penco_candidates.json --raw work/raw/concepcion_penco --output catalog/concepcion_penco_verified.json
if ($LASTEXITCODE -ne 0) { throw 'Verificación no completada.' }
& '.\.venv\Scripts\python.exe' scripts/prepare.py --raw work/raw/concepcion_penco --output data/concepcion_penco --catalog catalog/concepcion_penco_scenes.json
if ($LASTEXITCODE -ne 0) { throw 'Preparación no completada.' }
Write-Host 'Descarga, checksum oficial y preparación terminados.' -ForegroundColor Green

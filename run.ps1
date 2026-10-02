$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv-local\Scripts\python.exe')) {
    throw 'Run: uv venv .venv-local; uv pip install --python .venv-local\Scripts\python.exe -r backend\requirements-dev.txt'
}
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    throw 'Run: cd frontend; npm install; npm run build'
}
$serverArgs = @('-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000', '--workers', '1')
if (Test-Path -LiteralPath '.env') {
    $serverArgs += @('--env-file', '.env')
}
& '.\.venv-local\Scripts\python.exe' @serverArgs

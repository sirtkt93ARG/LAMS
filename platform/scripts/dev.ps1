# Levanta todo en Windows: API, servicio LTI, LMS simulado y web, cada uno en su ventana.
# Uso (desde la carpeta platform):   .\scripts\dev.ps1        (modo desarrollo)
#                                     .\scripts\dev.ps1 -Prod  (sin atajos de desarrollo: entra solo por el LMS simulado)
param([switch]$Prod)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "No se encontró .venv. Creala con: python -m venv .venv" }
& $py -m pip install -e ".[api,lti]" -q
if (-not (Test-Path "data\bank_demo.jsonl")) { & $py scripts\generate_bank.py }
& $py scripts\gen_lti_keys.py
if (-not (Test-Path "web\.env.local")) { Copy-Item "web\.env.example" "web\.env.local" }

$env:PYTHONPATH = "$root\src"
$env:SESSION_SECRET = "dev-session-secret-cambiar-0123456789abcdef"
$env:LTI_HANDOFF_SECRET = "dev-handoff-secret-cambiar-0123456789abcdef"
$env:LTI_SECRET_KEY = "dev-flask-secret"
$env:PSEUDONYM_SECRET = "dev-pseudonym-secret-cambiar-0123456789abcdef"
$env:LTI_CONFIG = "$root\lti_service\configs\lti.mock.json"
$env:WEB_URL = "http://localhost:3000"
$env:TOOL_BASE = "http://localhost:8200"
$env:LTI_SERVICE_URL = "http://localhost:8200"
if ($Prod) {
  Remove-Item Env:MATHEVAL_DEV -ErrorAction SilentlyContinue
  & $py scripts\seed_reviews.py
  $env:NEXT_PUBLIC_DEV = "0"
} else {
  $env:MATHEVAL_DEV = "1"
  $env:NEXT_PUBLIC_DEV = "1"
}
function Launch($title, $cmd) {
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location '$root'; $cmd"
}
Launch "API 8000" "& '$py' -m uvicorn api.app.main:app --port 8000"
Launch "LTI 8200" "& '$py' -m flask --app lti_service.app run --port 8200"
Launch "LMS simulado 8300" "& '$py' -m flask --app tools.mock_lms.app run --port 8300"
Launch "Web 3000" "Set-Location '$root\web'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
Write-Host ""
Write-Host "Se abrieron 4 ventanas. Cuando la web diga 'Ready':"
Write-Host "  Web:               http://localhost:3000"
Write-Host "  Aula simulada:     http://localhost:8300   (prueba del ingreso por LTI)"
Write-Host "  Prueba automática: $py scripts\smoke_http.py"

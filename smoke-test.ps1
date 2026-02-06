param(
  [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-Equal {
  param(
    [string]$Label,
    $Actual,
    $Expected
  )

  if ($Actual -ne $Expected) {
    throw "$Label falhou. Esperado: $Expected | Obtido: $Actual"
  }

  Write-Host "[ok] $Label = $Actual" -ForegroundColor Green
}

Write-Step "Smoke HTTP checks (FastAPI TestClient)"
$smokePayload = @'
from fastapi.testclient import TestClient
from visiontag.api import app
import json

client = TestClient(app)
checks = [
    ("/", 200),
    ("/docs", 200),
    ("/api/v1/health", 200),
    ("/api/v1/labels", 200),
]

results = []
for path, expected in checks:
    response = client.get(path)
    results.append(
        {
            "path": path,
            "status": response.status_code,
            "expected": expected,
            "ok": response.status_code == expected,
        }
    )

health = client.get("/api/v1/health").json()

print(
    json.dumps(
        {
            "checks": results,
            "health": health,
        },
        ensure_ascii=False,
    )
)
'@ | python -

$smoke = $smokePayload | ConvertFrom-Json
foreach ($check in $smoke.checks) {
  if (-not $check.ok) {
    throw "GET $($check.path) retornou $($check.status) (esperado: $($check.expected))."
  }
  Write-Host "[ok] GET $($check.path) => $($check.status)" -ForegroundColor Green
}

Assert-Equal -Label "health.status" -Actual $smoke.health.status -Expected "ok"
Write-Host "[info] health.version = $($smoke.health.version)"
Write-Host "[info] health.model_loaded = $($smoke.health.model_loaded)"

Write-Step "JavaScript syntax checks"
if (Get-Command node -ErrorAction SilentlyContinue) {
  $jsFiles = @(
    "visiontag/static/js/app.js",
    "visiontag/static/js/ui.js",
    "visiontag/static/js/api.js",
    "visiontag/static/js/experience.js"
  )

  foreach ($file in $jsFiles) {
    if (Test-Path $file) {
      node --check $file | Out-Null
      Write-Host "[ok] node --check $file" -ForegroundColor Green
    }
  }
} else {
  Write-Warning "Node.js não encontrado. Checks de JavaScript foram ignorados."
}

if (-not $SkipPytest) {
  Write-Step "Pytest"
  python -m pytest -q
} else {
  Write-Host "[info] pytest ignorado por parâmetro -SkipPytest"
}

Write-Step "Smoke test concluído com sucesso"

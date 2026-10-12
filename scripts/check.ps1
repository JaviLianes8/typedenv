# Local quality gate. Run before every commit. No CI runs in the cloud.
$ErrorActionPreference = "Stop"

function Step([string]$command) {
    Write-Host "> $command"
    Invoke-Expression $command
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Step "ruff format --check ."
Step "ruff check ."
Step "mypy --strict src"
Step "mypy tests"
Step "pytest"

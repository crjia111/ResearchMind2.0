# Local launcher for a native Windows checkout. For WSL, run bash start_linux.sh in WSL.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv: https://docs.astral.sh/uv/'
}
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    & uv sync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& ./.venv/Scripts/python.exe -m services.launcher @args
exit $LASTEXITCODE

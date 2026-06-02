# Thin wrapper around the aiprval CLI. Creates the venv on first run, then
# delegates to `python cli.py all`. For finer control use the CLI directly:
#   analysis/.venv/Scripts/python analysis/cli.py <command> [options]
param([string]$Dataset = "synthetic", [switch]$Quick, [switch]$SkipSim)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root "analysis/.venv/Scripts/python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Creating analysis venv..."
    # Prefer the Windows `py` launcher (native Python) over a bare `python`,
    # which on some setups resolves to a non-native (e.g. MSYS2) interpreter
    # that builds a POSIX-layout venv without Scripts/python.exe.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv (Join-Path $root "analysis/.venv")
    } else {
        & python -m venv (Join-Path $root "analysis/.venv")
    }
    & $py -m pip install --quiet -r (Join-Path $root "analysis/requirements.txt")
}

$cliArgs = @("cli.py", "all", "--dataset", $Dataset)
if ($Quick) { $cliArgs += "--quick" }
if ($SkipSim) { $cliArgs += "--skip-sim" }

Push-Location (Join-Path $root "analysis")
& $py @cliArgs
$code = $LASTEXITCODE
Pop-Location
exit $code

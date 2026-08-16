[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PythonExecutable,
    [Parameter(Mandatory=$true)][string]$BundleRoot,
    [Parameter(Mandatory=$true)][string]$WorkRoot,
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [Parameter(Mandatory=$true)][string]$IsccExecutable,
    [Parameter(Mandatory=$true)][string]$ApplicationPayloadSourceHead,
    [Parameter(Mandatory=$true)][string]$InstallerSourceHead,
    [Parameter(Mandatory=$true)][string]$ReceiptPath,
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pyInstallerVersion = (& $PythonExecutable -I -c 'import PyInstaller; print(PyInstaller.__version__)')
$appVersion = (& $PythonExecutable -I -c 'import pathlib,sys,tomllib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["project"]["version"])' (Join-Path $repository 'pyproject.toml'))
if ($LASTEXITCODE -ne 0 -or $appVersion -notmatch '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$') {
    throw 'Canonical product version could not be resolved.'
}
$arguments = @(
    '-I', '-m', 'pastila_scout.windows_release_orchestration_v1',
    '--repository', $repository,
    '--bundle', $BundleRoot,
    '--work-root', $WorkRoot,
    '--output-root', $OutputRoot,
    '--iscc', $IsccExecutable,
    '--app-version', $appVersion,
    '--application-payload-source-head', $ApplicationPayloadSourceHead,
    '--installer-source-head', $InstallerSourceHead,
    '--receipt', $ReceiptPath,
    '--python-version', (& $PythonExecutable --version).Replace('Python ', ''),
    '--pyinstaller-version', $pyInstallerVersion,
    '--inno-setup-version', (Get-Item -LiteralPath $IsccExecutable).VersionInfo.FileVersion
)
if ($PlanOnly) { $arguments += '--plan-only' }
& $PythonExecutable @arguments
if ($LASTEXITCODE -ne 0) { throw 'Normal release orchestration failed.' }

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
$arguments = @(
    '-I', '-m', 'pastila_scout.windows_release_orchestration_v1',
    '--repository', $repository,
    '--bundle', $BundleRoot,
    '--work-root', $WorkRoot,
    '--output-root', $OutputRoot,
    '--iscc', $IsccExecutable,
    '--app-version', '0.1.0',
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

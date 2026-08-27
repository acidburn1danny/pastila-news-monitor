[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)][string]$BuildMode,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [Parameter(Mandatory = $true)][string]$Wheelhouse,
    [Parameter(Mandatory = $true)][string]$WorkRoot,
    [Parameter(Mandatory = $true)][string]$DistRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExpectedPyInstaller = 'pyinstaller-6.22.0-py3-none-win_amd64.whl'
$ExpectedPyInstallerSha256 = '6E5F3656DE100954BF5DB25536C43E097E46D482843A96D03A0852BF266E4853'
$GuiWrapperText = "from pastila_scout.desktop_v1.entrypoint import main`n`nraise SystemExit(main())`n"
$CliWrapperText = "from pastila_scout.cli import main`n`nraise SystemExit(main())`n"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Fail([string]$Message) {
    throw "Phase 5.5F build rejected: $Message"
}

function Require-Absolute([string]$Name, [string]$Value) {
    $root = if ([string]::IsNullOrWhiteSpace($Value)) { $null } else { [IO.Path]::GetPathRoot($Value) }
    if ([string]::IsNullOrWhiteSpace($Value) -or -not [IO.Path]::IsPathRooted($Value) -or
        [string]::IsNullOrWhiteSpace($root) -or ($root.Length -eq 2 -and $root[1] -eq ':')) {
        Fail "$Name must be an absolute path"
    }
    if (($Value -split '[\\/]') -contains '..') { Fail "$Name must not contain .." }
}

function Resolve-FinalPath([string]$Value) {
    $full = [IO.Path]::GetFullPath($Value).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $cursor = $full
    $suffix = [Collections.Generic.List[string]]::new()
    while (-not (Test-Path -LiteralPath $cursor)) {
        $leaf = Split-Path -Leaf $cursor
        if (-not $leaf) { Fail "cannot resolve output ancestor: $Value" }
        $suffix.Insert(0, $leaf)
        $cursor = Split-Path -Parent $cursor
    }
    $resolved = (Resolve-Path -LiteralPath $cursor).Path.TrimEnd('\')
    foreach ($part in $suffix) { $resolved = Join-Path $resolved $part }
    return $resolved.TrimEnd('\')
}

function Require-NoReparseTraversal([string]$Name, [string]$Value) {
    $cursor = [IO.Path]::GetPathRoot($Value)
    foreach ($part in $Value.Substring($cursor.Length).Split([char[]]'\/', [StringSplitOptions]::RemoveEmptyEntries)) {
        $cursor = Join-Path $cursor $part
        if (-not (Test-Path -LiteralPath $cursor)) { break }
        if ((Get-Item -Force -LiteralPath $cursor).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            Fail "$Name traverses a reparse point"
        }
    }
}

function Is-SameOrNested([string]$Left, [string]$Right) {
    $a = $Left.TrimEnd('\')
    $b = $Right.TrimEnd('\')
    return $a.Equals($b, [StringComparison]::OrdinalIgnoreCase) -or
        $a.StartsWith($b + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $b.StartsWith($a + '\', [StringComparison]::OrdinalIgnoreCase)
}

if ($BuildMode -cne 'stable') { Fail 'BuildMode must be exactly stable' }
if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) { Fail 'PYTHONPATH must be absent' }

foreach ($pair in @(
    @('PythonExecutable', $PythonExecutable), @('Wheelhouse', $Wheelhouse),
    @('WorkRoot', $WorkRoot), @('DistRoot', $DistRoot)
)) { Require-Absolute $pair[0] $pair[1] }

if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) { Fail 'PythonExecutable must be an existing file' }
if (-not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) { Fail 'Wheelhouse must be an existing directory' }
if (Test-Path -LiteralPath $WorkRoot) { Fail 'WorkRoot must not exist' }
if ((Test-Path -LiteralPath $DistRoot) -and @(Get-ChildItem -Force -LiteralPath $DistRoot).Count -ne 0) {
    Fail 'DistRoot must not exist or must be empty'
}

$RepositoryRoot = Resolve-FinalPath (Join-Path $PSScriptRoot '..\..')
$PythonExecutable = Resolve-FinalPath $PythonExecutable
$PythonRoot = Resolve-FinalPath (Split-Path -Parent $PythonExecutable)
$Wheelhouse = Resolve-FinalPath $Wheelhouse
$WorkRoot = Resolve-FinalPath $WorkRoot
$DistRoot = Resolve-FinalPath $DistRoot

foreach ($pair in @(
    @('PythonExecutable', $PythonExecutable), @('Wheelhouse', $Wheelhouse),
    @('WorkRoot', $WorkRoot), @('DistRoot', $DistRoot)
)) { Require-NoReparseTraversal $pair[0] $pair[1] }

if ($WorkRoot -eq [IO.Path]::GetPathRoot($WorkRoot) -or $DistRoot -eq [IO.Path]::GetPathRoot($DistRoot)) {
    Fail 'output roots must not be filesystem roots'
}
$ProfileRoot = Resolve-FinalPath $env:USERPROFILE
if ($WorkRoot.Equals($ProfileRoot, 'OrdinalIgnoreCase') -or $DistRoot.Equals($ProfileRoot, 'OrdinalIgnoreCase')) {
    Fail 'output root must not be the user profile'
}
foreach ($output in @($WorkRoot, $DistRoot)) {
    foreach ($protected in @($RepositoryRoot, $Wheelhouse, $PythonRoot)) {
        if (Is-SameOrNested $output $protected) { Fail 'output and protected input paths must not overlap' }
    }
}
if (Is-SameOrNested $WorkRoot $DistRoot) { Fail 'WorkRoot and DistRoot must not overlap' }

$Icon = Join-Path $RepositoryRoot 'packaging\resources\PastilaScout.ico'
$Notices = Join-Path $RepositoryRoot 'packaging\resources\THIRD-PARTY-NOTICES.txt'
if (-not (Test-Path -LiteralPath $Icon -PathType Leaf)) { Fail 'final owner-approved PastilaScout.ico is required' }
if (-not (Test-Path -LiteralPath $Notices -PathType Leaf)) { Fail 'owner-approved THIRD-PARTY-NOTICES.txt is required' }
$iconBytes = [IO.File]::ReadAllBytes($Icon)
if ($iconBytes.Length -lt 22 -or [BitConverter]::ToUInt16($iconBytes, 0) -ne 0 -or
    [BitConverter]::ToUInt16($iconBytes, 2) -ne 1) { Fail 'PastilaScout.ico has an invalid ICO header' }
$iconCount = [BitConverter]::ToUInt16($iconBytes, 4)
if ($iconCount -lt 1 -or $iconBytes.Length -lt 6 + (16 * $iconCount)) { Fail 'PastilaScout.ico has an invalid directory' }
$payloadEnd = 0
for ($index = 0; $index -lt $iconCount; $index++) {
    $entry = 6 + (16 * $index)
    $length = [BitConverter]::ToUInt32($iconBytes, $entry + 8)
    $offset = [BitConverter]::ToUInt32($iconBytes, $entry + 12)
    if ($length -eq 0 -or $offset -lt 6 + (16 * $iconCount) -or $offset + $length -gt $iconBytes.Length) {
        Fail 'PastilaScout.ico contains an invalid image entry'
    }
    $isPng = $length -ge 8 -and $iconBytes[$offset] -eq 0x89 -and $iconBytes[$offset + 1] -eq 0x50 -and
        $iconBytes[$offset + 2] -eq 0x4E -and $iconBytes[$offset + 3] -eq 0x47 -and
        $iconBytes[$offset + 4] -eq 0x0D -and $iconBytes[$offset + 5] -eq 0x0A -and
        $iconBytes[$offset + 6] -eq 0x1A -and $iconBytes[$offset + 7] -eq 0x0A
    $isDib = $length -ge 40 -and [BitConverter]::ToUInt32($iconBytes, $offset) -ge 40
    if (-not $isPng -and -not $isDib) { Fail 'PastilaScout.ico contains no decodable Windows image entry' }
    $payloadEnd = [Math]::Max($payloadEnd, $offset + $length)
}
if ($payloadEnd -ne $iconBytes.Length) { Fail 'PastilaScout.ico contains trailing non-ICO payload' }
$noticeBytes = [IO.File]::ReadAllBytes($Notices)
if ($noticeBytes.Length -lt 35 -or ($noticeBytes.Length -ge 3 -and $noticeBytes[0] -eq 0xEF -and
    $noticeBytes[1] -eq 0xBB -and $noticeBytes[2] -eq 0xBF) -or $noticeBytes[-1] -ne 0x0A) {
    Fail 'THIRD-PARTY-NOTICES.txt must be UTF-8 without BOM and LF-terminated'
}
$noticeText = $Utf8NoBom.GetString($noticeBytes)
if (-not $noticeText.StartsWith("Pastila Scout Third-Party Notices`n`n", [StringComparison]::Ordinal) -or
    $noticeText -match '(?i)TODO|UNKNOWN|PLACEHOLDER|Your Company') {
    Fail 'THIRD-PARTY-NOTICES.txt has invalid governed content'
}

$TrustKey = Join-Path $RepositoryRoot 'resources\trust\pastila-root-1.pub'
$TrustBootstrap = Join-Path $RepositoryRoot 'resources\trust\bootstrap-root-v1.json'
if ((Get-Item -LiteralPath $TrustKey).Length -ne 32) { Fail 'production trust key must contain exactly 32 raw bytes' }
$bootstrap = Get-Content -Raw -LiteralPath $TrustBootstrap | ConvertFrom-Json
$members = @($bootstrap.PSObject.Properties.Name | Sort-Object)
$expectedMembers = @('algorithm', 'key_id', 'public_key_filename', 'public_key_sha256', 'schema', 'schema_version')
if (Compare-Object $members $expectedMembers) { Fail 'production bootstrap must contain exactly six governed members' }
if ($bootstrap.algorithm -cne 'Ed25519' -or $bootstrap.key_id -cne 'pastila-root-1' -or
    $bootstrap.public_key_filename -cne 'pastila-root-1.pub' -or
    $bootstrap.public_key_sha256 -cne (Get-FileHash -Algorithm SHA256 -LiteralPath $TrustKey).Hash.ToLowerInvariant()) {
    Fail 'production trust resources do not cross-bind exactly'
}

$pythonCheck = @'
import json, platform, struct, sys, tkinter
result = {
    "implementation": platform.python_implementation(),
    "version": list(sys.version_info[:3]),
    "system": platform.system(),
    "machine": platform.machine(),
    "bits": struct.calcsize("P") * 8,
}
tcl = tkinter.Tcl()
result["tcl"] = str(tcl.call("info", "patchlevel"))
result["tk"] = str(tcl.call("package", "require", "Tk"))
print(json.dumps(result, sort_keys=True))
'@
$pythonOutput = @()
$pythonExitCode = $null
try {
    $ErrorActionPreference = 'Continue'
    $pythonOutput = @($pythonCheck | & $PythonExecutable -I - 2>&1)
    $pythonExitCode = $LASTEXITCODE
}
finally { $ErrorActionPreference = 'Stop' }
if ($pythonExitCode -ne 0 -or $pythonOutput.Count -ne 1) {
    Fail 'Python must be Windows AMD64 CPython 3.14 with functional Tcl/Tk'
}
try { $pythonInfo = $pythonOutput[0] | ConvertFrom-Json }
catch { Fail 'Python must be Windows AMD64 CPython 3.14 with functional Tcl/Tk' }
if ($pythonInfo.implementation -ne 'CPython' -or
    $pythonInfo.version[0] -ne 3 -or $pythonInfo.version[1] -ne 14 -or
    $pythonInfo.system -ne 'Windows' -or $pythonInfo.machine -ne 'AMD64' -or
    $pythonInfo.bits -ne 64 -or -not $pythonInfo.tk) {
    Fail 'Python must be Windows AMD64 CPython 3.14 with functional Tcl/Tk'
}

$pyInstallerWheels = @(Get-ChildItem -LiteralPath $Wheelhouse -File -Filter 'pyinstaller-*.whl')
if ($pyInstallerWheels.Count -ne 1 -or $pyInstallerWheels[0].Name -cne $ExpectedPyInstaller) {
    Fail 'wheelhouse must contain the single exact PyInstaller wheel'
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pyInstallerWheels[0].FullName).Hash -cne $ExpectedPyInstallerSha256) {
    Fail 'PyInstaller wheel SHA-256 mismatch'
}

$allWheels = @(Get-ChildItem -LiteralPath $Wheelhouse -File)
if ($allWheels.Count -eq 0 -or @($allWheels | Where-Object Extension -ne '.whl').Count -ne 0) {
    Fail 'every wheelhouse member must be a wheel'
}
$wheelAudit = @'
import email, pathlib, re, sys, zipfile
seen = {}
for wheel in pathlib.Path(sys.argv[1]).iterdir():
    with zipfile.ZipFile(wheel) as archive:
        members = [
            name for name in archive.namelist()
            if name.endswith(".dist-info/METADATA") and name.count("/") == 1
        ]
        if len(members) != 1:
            raise SystemExit(f"wheel must contain exactly one METADATA: {wheel.name}")
        metadata = email.message_from_bytes(archive.read(members[0]))
    name = metadata.get("Name")
    version = metadata.get("Version")
    if not name or not version:
        raise SystemExit(f"wheel lacks Name or Version metadata: {wheel.name}")
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    dist_info = pathlib.PurePosixPath(members[0]).parent.name.removesuffix(".dist-info")
    try:
        dist_info_name, dist_info_version = dist_info.rsplit("-", 1)
        wheel_name, wheel_version = wheel.name.split("-", 2)[:2]
    except ValueError:
        raise SystemExit(f"wheel identity is malformed: {wheel.name}")
    escaped_version = version.replace("-", "_")
    if (re.sub(r"[-_.]+", "-", dist_info_name).lower() != normalized or
            re.sub(r"[-_.]+", "-", wheel_name).lower() != normalized or
            dist_info_version != escaped_version or wheel_version != escaped_version):
        raise SystemExit(f"wheel filename, dist-info, and METADATA identity mismatch: {wheel.name}")
    if normalized in seen:
        raise SystemExit(f"duplicate normalized distribution identity: {normalized}")
    seen[normalized] = wheel.name
    for requirement in metadata.get_all("Requires-Dist", []):
        if re.match(
                r"^\s*[A-Za-z0-9][A-Za-z0-9._-]*(?:\s*\[[^]]*\])?"
                r"\s*@\s*[A-Za-z][A-Za-z0-9+.-]*:", requirement):
            raise SystemExit(f"direct URL requirement is forbidden: {name}")
'@
$wheelAuditOutput = @()
$wheelAuditExitCode = $null
try {
    $ErrorActionPreference = 'Continue'
    $wheelAuditOutput = @($wheelAudit | & $PythonExecutable -I - $Wheelhouse 2>&1)
    $wheelAuditExitCode = $LASTEXITCODE
}
finally { $ErrorActionPreference = 'Stop' }
if ($wheelAuditExitCode -ne 0 -or $wheelAuditOutput.Count -ne 0) {
    Fail 'wheelhouse metadata audit failed'
}
$appWheels = @($allWheels | Where-Object Name -Like 'pastila_news_monitor-*-py3-none-any.whl')
if ($appWheels.Count -ne 1) { Fail 'wheelhouse must contain exactly one application wheel' }

New-Item -ItemType Directory -Path $WorkRoot | Out-Null
try {
    $VenvRoot = Join-Path $WorkRoot 'venv'
    & $PythonExecutable -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) { Fail 'fresh virtual environment creation failed' }
    $VenvPython = Join-Path $VenvRoot 'Scripts\python.exe'
    & $VenvPython -m pip --isolated --version | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail 'fresh environment lacks a functioning local installer' }
    $baseline = @(& $VenvPython -m pip --isolated list --format json | ConvertFrom-Json | ForEach-Object { $_ })

    $ClosureReport = Join-Path $WorkRoot 'closure.json'
    & $VenvPython -m pip --isolated install --dry-run --ignore-installed --no-index --find-links $Wheelhouse `
        --report $ClosureReport $appWheels[0].FullName $pyInstallerWheels[0].FullName | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail 'wheelhouse cannot resolve the complete target closure offline' }
    $closure = Get-Content -Raw -LiteralPath $ClosureReport | ConvertFrom-Json
    $selectedFiles = @($closure.install | ForEach-Object {
        [Uri]::UnescapeDataString(([Uri]$_.download_info.url).Segments[-1])
    } | Sort-Object -Unique)
    $availableFiles = @($allWheels.Name | Sort-Object -Unique)
    $closureDelta = @(Compare-Object $availableFiles $selectedFiles)
    if ($closureDelta.Count -ne 0 -or $selectedFiles.Count -ne $allWheels.Count) {
        Fail 'wheelhouse contains a missing, duplicate, incompatible, unexpected, or unused wheel'
    }

    $wheelArgs = @('--no-index', '--find-links', $Wheelhouse, $appWheels[0].FullName, $pyInstallerWheels[0].FullName)
    & $VenvPython -m pip --isolated install @wheelArgs
    if ($LASTEXITCODE -ne 0) { Fail 'offline wheel installation failed' }
    & $VenvPython -m pip --isolated check
    if ($LASTEXITCODE -ne 0) { Fail 'installed dependency closure is inconsistent' }
    $installed = @(& $VenvPython -m pip --isolated list --format json | ConvertFrom-Json | ForEach-Object { $_ })
    $normalize = { param($name) ($name.ToLowerInvariant() -replace '[-_.]+', '-') }
    $baselineMap = @{}
    foreach ($item in $baseline) { $baselineMap[(& $normalize $item.name)] = $item.version }
    $expectedMap = @{}
    foreach ($item in $closure.install) { $expectedMap[(& $normalize $item.metadata.name)] = $item.metadata.version }
    foreach ($item in $installed) {
        $name = & $normalize $item.name
        if ($baselineMap.ContainsKey($name) -and $baselineMap[$name] -eq $item.version) { continue }
        if (-not $expectedMap.ContainsKey($name) -or $expectedMap[$name] -ne $item.version) {
            Fail 'installed distribution inventory diverges from resolved closure'
        }
        $expectedMap.Remove($name)
    }
    if ($expectedMap.Count -ne 0) { Fail 'installed distribution inventory is incomplete' }
    $isolationCheck = @'
import importlib.metadata, importlib.util, json, pathlib, site, sys
repo = pathlib.Path(sys.argv[1]).resolve()
venv = pathlib.Path(sys.prefix).resolve()
paths = [pathlib.Path(p).resolve() for p in sys.path if p]
pth_files = [p.resolve() for root in site.getsitepackages() for p in pathlib.Path(root).glob("*.pth")]
pth = sorted(str(p) for p in pth_files)
pth_external = []
for file in pth_files:
    for line in file.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or value.startswith("import "):
            continue
        target = (file.parent / value).resolve()
        if target != venv and venv not in target.parents:
            pth_external.append(str(target))
origins = {}
for name in ("pastila_scout", "openai", "httpx"):
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise SystemExit(1)
    origins[name] = pathlib.Path(spec.origin).resolve()
metadata_paths = [pathlib.Path(dist._path).resolve() for dist in importlib.metadata.distributions()]
bad = [str(p) for p in paths if p == repo or repo in p.parents]
bad_origins = [str(p) for p in list(origins.values()) + metadata_paths if p != venv and venv not in p.parents]
print(json.dumps({"origins": {k: str(v) for k, v in origins.items()}, "bad": bad, "bad_origins": bad_origins, "pth": pth, "pth_external": pth_external}, sort_keys=True))
if bad or pth_external or bad_origins:
    raise SystemExit(1)
'@
    $isolationOutput = @()
    $isolationExitCode = $null
    try {
        $ErrorActionPreference = 'Continue'
        $isolationOutput = @($isolationCheck | & $VenvPython -I - $RepositoryRoot 2>&1)
        $isolationExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = 'Stop' }
    if ($isolationExitCode -ne 0 -or $isolationOutput.Count -ne 1) {
        Fail 'installed modules or sys.path leak outside the fresh environment'
    }
    try { $isolation = $isolationOutput[0] | ConvertFrom-Json }
    catch { Fail 'installed modules or sys.path leak outside the fresh environment' }

    $GuiWrapper = Join-Path $WorkRoot 'gui_entry.py'
    $CliWrapper = Join-Path $WorkRoot 'cli_entry.py'
    [IO.File]::WriteAllText($GuiWrapper, $GuiWrapperText, $Utf8NoBom)
    [IO.File]::WriteAllText($CliWrapper, $CliWrapperText, $Utf8NoBom)

    $versionCheck = @'
import importlib.metadata as metadata
print(metadata.version("pastila-news-monitor"))
'@
    $versionOutput = @()
    $versionExitCode = $null
    try {
        $ErrorActionPreference = 'Continue'
        $versionOutput = @($versionCheck | & $VenvPython -I - 2>&1)
        $versionExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = 'Stop' }
    if ($versionExitCode -ne 0 -or $versionOutput.Count -ne 1) {
        Fail 'installed application version must be stable major.minor.patch'
    }
    $version = $versionOutput[0].ToString().Trim()
    if ($version -notmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$' -or $version -eq '0.0.0-dev') {
        Fail 'installed application version must be stable major.minor.patch'
    }
    $parts = $version.Split('.')
    $template = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'version_info.txt.in'))
    $commonVersion = $template.Replace('{FILE_VERSION}', "$($parts[0]), $($parts[1]), $($parts[2]), 0").
        Replace('{PRODUCT_VERSION}', "$($parts[0]), $($parts[1]), $($parts[2]), 0").
        Replace('{CANONICAL_VERSION}', $version)
    $GuiVersionInfo = Join-Path $WorkRoot 'version-info-gui.txt'
    $CliVersionInfo = Join-Path $WorkRoot 'version-info-cli.txt'
    $guiRendered = $commonVersion.Replace('{FILE_DESCRIPTION}', 'Pastila Scout').
        Replace('{INTERNAL_NAME}', 'PastilaScout').Replace('{ORIGINAL_FILENAME}', 'PastilaScout.exe')
    $cliRendered = $commonVersion.Replace('{FILE_DESCRIPTION}', 'Pastila Scout Console').
        Replace('{INTERNAL_NAME}', 'pastila-scout').Replace('{ORIGINAL_FILENAME}', 'pastila-scout.exe')
    [IO.File]::WriteAllText($GuiVersionInfo, $guiRendered, $Utf8NoBom)
    [IO.File]::WriteAllText($CliVersionInfo, $cliRendered, $Utf8NoBom)

    $ResourceRoot = Join-Path $WorkRoot 'resources'
    New-Item -ItemType Directory -Path (Join-Path $ResourceRoot 'config'), (Join-Path $ResourceRoot 'desktop_v1'),
        (Join-Path $ResourceRoot 'resources\trust'),
        (Join-Path $ResourceRoot 'pastila_scout\resources\branding'),
        (Join-Path $ResourceRoot 'pastila_scout\resources\expression_retrieval_v1'),
        (Join-Path $ResourceRoot 'pastila_scout\resources\expression_catalog_v2') | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'config\config.yaml') -Destination (Join-Path $ResourceRoot 'config\config.yaml')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'config\sources.yaml') -Destination (Join-Path $ResourceRoot 'config\sources.yaml')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'src\pastila_scout\desktop_v1\default-settings-v1.json') -Destination (Join-Path $ResourceRoot 'desktop_v1\default-settings-v1.json')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'resources\trust\pastila-root-1.pub') -Destination (Join-Path $ResourceRoot 'resources\trust\pastila-root-1.pub')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'resources\trust\bootstrap-root-v1.json') -Destination (Join-Path $ResourceRoot 'resources\trust\bootstrap-root-v1.json')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'src\pastila_scout\resources\branding\pastila-scout-investigator.png') -Destination (Join-Path $ResourceRoot 'pastila_scout\resources\branding\pastila-scout-investigator.png')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'src\pastila_scout\resources\branding\pastila-scout-investigator-sidebar.png') -Destination (Join-Path $ResourceRoot 'pastila_scout\resources\branding\pastila-scout-investigator-sidebar.png')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'src\pastila_scout\resources\expression_retrieval_v1\catalog.json') -Destination (Join-Path $ResourceRoot 'pastila_scout\resources\expression_retrieval_v1\catalog.json')
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot 'src\pastila_scout\resources\expression_catalog_v2\catalog-overlay.json') -Destination (Join-Path $ResourceRoot 'pastila_scout\resources\expression_catalog_v2\catalog-overlay.json')
    Copy-Item -LiteralPath $Notices -Destination (Join-Path $ResourceRoot 'resources\THIRD-PARTY-NOTICES.txt')

    $env:PASTILA_SPEC_GUI_WRAPPER = $GuiWrapper
    $env:PASTILA_SPEC_CLI_WRAPPER = $CliWrapper
    $env:PASTILA_SPEC_RESOURCE_ROOT = $ResourceRoot
    $env:PASTILA_SPEC_GUI_VERSION_INFO = $GuiVersionInfo
    $env:PASTILA_SPEC_CLI_VERSION_INFO = $CliVersionInfo
    $env:PASTILA_SPEC_ICON = $Icon
    $env:PYTHONPATH = $null
    $Spec = Join-Path $PSScriptRoot 'PastilaScout.spec'
    & $VenvPython -m PyInstaller --clean --noconfirm --workpath (Join-Path $WorkRoot 'pyinstaller-work') --distpath $DistRoot $Spec
    if ($LASTEXITCODE -ne 0) { Fail 'PyInstaller build failed' }
    if (-not (Test-Path -LiteralPath (Join-Path $DistRoot 'app\PastilaScout.exe')) -or
        -not (Test-Path -LiteralPath (Join-Path $DistRoot 'app\pastila-scout.exe'))) {
        Fail 'built output lacks the exact two launchers'
    }
}
finally {
    Remove-Item Env:PASTILA_SPEC_GUI_WRAPPER, Env:PASTILA_SPEC_CLI_WRAPPER,
        Env:PASTILA_SPEC_RESOURCE_ROOT, Env:PASTILA_SPEC_GUI_VERSION_INFO,
        Env:PASTILA_SPEC_CLI_VERSION_INFO, Env:PASTILA_SPEC_ICON -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $WorkRoot) { Remove-Item -LiteralPath $WorkRoot -Recurse -Force }
}

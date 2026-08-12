[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PayloadRoot,
    [Parameter(Mandatory=$true)][string]$PreparationRoot,
    [Parameter(Mandatory=$true)][string]$ToolchainRoot,
    [Parameter(Mandatory=$true)][string]$WorkRoot,
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [ValidateSet('Release','Vm05Instrumented','Vm01aInstrumented')][string]$BuildVariant = 'Release'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$Expected = @{
    Accounting = '655A5253BE353AE8E332BFC12FC77982952762244274D67D3FE898981B6538F4'
    AccountingTag = 'phase-5.6b-current-vm-matrix-accounting-after-r7-r8-r1-verified'
    AccountingCommit = '10f5404a0b290dea1351d82763dd443efc201fda'
    WrapperAuthorityTag = 'phase-5.6b-wrapper-accounting-consumer-refresh-r1-verified'
    Spec = 'D5C5AE513FC763C3E3E2A1B9A4F9ACA0893EC4BC6215AE22C3BF679C5D0F4F0A'
    Accepted = 'A5EF263053DE98B8A71BC8D9DF1C55AA9A67823AA62873560FCD3FAB5F6AF418'
    Jcs = '852361716089EA7205A4149CB52FC4D0837F74A7B2F57154D070660F27E44D13'
    Binding = '818697EBB89AC773B13A3BCA70940F1556FFBD6F16D64D0CCB3CBE3815602FA2'
    Context = 'C27564C7AB79CCF4EB0B85BEEB084A948AD88FFD3AD402C638E4B502FA611ADD'
    Preparation = '21FDD95DDBE6A81C07FC4D350994BE4F458C2593FC809B8D3BD2E4A7F96E1808'
    InnoAuthority = '6058F179761070A96D4C0E6D435F7D6542DB7C565E936F5A3056B6EF75A98C51'
    InnoManifest = '1974DD954157DCAD6FBDE0D46F2BB2207ACDF9F22C3E0AD2B22AA5488D8C0841'
    InnoInventory = '1D1A0306B4A9E9E57B1BD31B13ACAFE30DA6081B4DDDE597021BE9427371F6D7'
    Iscc = '0A8757031B33777E4C9CBFFEE40F11A5062B36D25CBE144C1DB73B6102B80AD7'
}

$RejectedEvidence = @(
    '54409D2B4802DF707BB33EE21F8CCA408DEBAFA369ED961EB6631DAD48AEBEAC',
    'E2D696CD53ACF5607A451FC234F4BB054AB13EA194A2F1AEA7F027363B3D80CA',
    '6478034A97FDA5963B4A3C8969C06AEC26764C1D2FFA7F2575BE3AAE53B6971E',
    'FE17EE0B194D1569891B511096CB4E5A862288E21057D8EDBA7C4B8CBCBFA710'
)

function Fail([string]$Message) { throw "Phase 5.6B validation failed: $Message" }
function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function RequireHash([string]$Path, [string]$Digest) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { Fail "missing file: $Path" }
    if ((Hash $Path) -ne $Digest) { Fail "identity mismatch: $Path" }
}
function Full([string]$Path) { [IO.Path]::GetFullPath($Path).TrimEnd('\') }
function IsInside([string]$Left, [string]$Right) {
    $a=(Full $Left)+'\'; $b=(Full $Right)+'\'
    $a.StartsWith($b,[StringComparison]::OrdinalIgnoreCase) -or $b.StartsWith($a,[StringComparison]::OrdinalIgnoreCase)
}

$repo = Full (Join-Path $PSScriptRoot '..\..')
$payload = Full $PayloadRoot; $prep = Full $PreparationRoot
$toolchain = Full $ToolchainRoot; $work = Full $WorkRoot; $out = Full $OutputRoot
if ((IsInside $payload $repo) -or (IsInside $work $payload) -or (IsInside $out $payload) -or (IsInside $work $out)) { Fail 'source/work/output alias or ancestry overlap' }
if ($BuildVariant -eq 'Vm05Instrumented' -and
    ((Split-Path $work -Leaf) -notmatch '(?i)vm05-instrumented' -or
     (Split-Path $out -Leaf) -notmatch '(?i)vm05-instrumented')) {
    Fail 'VM-05 instrumented work/output roots must be explicitly variant-scoped'
}
if ($BuildVariant -eq 'Vm01aInstrumented' -and
    ((Split-Path $work -Leaf) -notmatch '(?i)vm01a-instrumented' -or
     (Split-Path $out -Leaf) -notmatch '(?i)vm01a-instrumented')) {
    Fail 'VM-01A instrumented work/output roots must be explicitly variant-scoped'
}
$repositoryHead=(git -C $repo rev-parse HEAD).Trim()
$accountingPath=Join-Path $repo 'docs\windows-application\phase-5.6b-current-matrix-accounting-after-r7-r8-r1.json'
RequireHash $accountingPath $Expected.Accounting
$accountingTagType=(git -C $repo cat-file -t $Expected.AccountingTag).Trim()
if ($LASTEXITCODE -ne 0 -or $accountingTagType -ne 'tag') { Fail 'accounting authority tag missing or not annotated' }
$accountingHead=(git -C $repo rev-parse ($Expected.AccountingTag+'^{}')).Trim()
if ($LASTEXITCODE -ne 0 -or $accountingHead -notmatch '^[0-9a-f]{40}$') { Fail 'accounting authority tag cannot be resolved' }
if ($accountingHead -ne $Expected.AccountingCommit) { Fail 'accounting authority tag peel mismatch' }
$wrapperAuthorityTagType=(git -C $repo cat-file -t $Expected.WrapperAuthorityTag).Trim()
if ($LASTEXITCODE -ne 0 -or $wrapperAuthorityTagType -ne 'tag') { Fail 'wrapper authority tag missing or not annotated' }
$wrapperAuthorityHead=(git -C $repo rev-parse ($Expected.WrapperAuthorityTag+'^{}')).Trim()
if ($LASTEXITCODE -ne 0 -or $wrapperAuthorityHead -notmatch '^[0-9a-f]{40}$') { Fail 'wrapper authority tag cannot be resolved' }
git -C $repo merge-base --is-ancestor $accountingHead $wrapperAuthorityHead
if ($LASTEXITCODE -ne 0) { Fail 'accounting authority is not an ancestor of wrapper authority' }
if ($repositoryHead -ne $wrapperAuthorityHead) { Fail 'repository HEAD does not match frozen wrapper authority' }
if (@(git -C $repo status --porcelain --untracked-files=all | Where-Object { $_ -notmatch '^\?\? (packaging/inno/(PastilaScout\.iss|build-installer\.ps1)|tests/packaging/test_inno_installer_v1\.py)$' }).Count) { Fail 'repository contains out-of-scope changes' }
RequireHash (Join-Path $repo 'docs\windows-application\WindowsInstallerSpecificationV1.md') $Expected.Spec

$jcsPath=Join-Path $prep 'inventory\payload-inventory.jcs.json'
$bindingPath=Join-Path $prep 'binding\binding-record.jcs.json'
$contextPath=Join-Path $prep 'binding\preparation-context-record.jcs.json'
$prepInventoryPath=Join-Path $prep 'evidence\preparation-evidence-inventory.jcs.json'
RequireHash $jcsPath $Expected.Jcs; RequireHash $bindingPath $Expected.Binding
RequireHash $contextPath $Expected.Context; RequireHash $prepInventoryPath $Expected.Preparation

# The retained preparation above proves payload authority, but it predates the
# final Phase 5.6B candidate.  A build must also consume the external,
# candidate-bound prospective authorization.  Validate it structurally so a
# historical preparation cannot be substituted and so candidate refreshes do
# not require a self-referential wrapper hash constant.
$prospectiveRoot=Join-Path $prep 'prospective'
$prospectiveContextPath=Join-Path $prospectiveRoot 'prospective-context.jcs.json'
$implementationStartPath=Join-Path $prospectiveRoot 'implementation-start.jcs.json'
$prospectiveInventoryPath=Join-Path $prospectiveRoot 'prospective-preparation-inventory.jcs.json'
$dagPath=Join-Path $prospectiveRoot 'dependency-dag-proof.jcs.json'
foreach($requiredProspective in @($prospectiveContextPath,$implementationStartPath,$prospectiveInventoryPath,$dagPath)) {
    if (-not (Test-Path -LiteralPath $requiredProspective -PathType Leaf)) { Fail "missing prospective authorization: $requiredProspective" }
}
$prospectiveContext=Get-Content -Raw -LiteralPath $prospectiveContextPath | ConvertFrom-Json
if ($prospectiveContext.repository_head -ne $wrapperAuthorityHead -or $prospectiveContext.accounting.sha256 -ne $Expected.Accounting -or $prospectiveContext.accounting.tag -ne $Expected.AccountingTag -or $prospectiveContext.retained_upstream.jcs.sha256 -ne $Expected.Jcs -or $prospectiveContext.retained_upstream.binding.sha256 -ne $Expected.Binding -or $prospectiveContext.retained_upstream.context.sha256 -ne $Expected.Context -or $prospectiveContext.retained_upstream.preparation_inventory.sha256 -ne $Expected.Preparation) { Fail 'prospective context authority mismatch' }
$expectedCandidates=@('packaging/inno/PastilaScout.iss','packaging/inno/build-installer.ps1','tests/packaging/test_inno_installer_v1.py')
if (@($prospectiveContext.candidate_files).Count -ne 3) { Fail 'prospective context candidate cardinality mismatch' }
foreach($candidatePath in $expectedCandidates) {
    $candidate=@($prospectiveContext.candidate_files | Where-Object path -ceq $candidatePath)
    if ($candidate.Count -ne 1) { Fail "prospective context candidate missing: $candidatePath" }
    $repoCandidate=Join-Path $repo ($candidatePath -replace '/','\')
    if ((Hash $repoCandidate) -ne $candidate[0].sha256 -or (Get-Item -LiteralPath $repoCandidate).Length -ne [long]$candidate[0].size) { Fail "prospective candidate mismatch: $candidatePath" }
}
$implementationStart=Get-Content -Raw -LiteralPath $implementationStartPath | ConvertFrom-Json
if ($implementationStart.prospective_context_sha256 -ne (Hash $prospectiveContextPath) -or @($implementationStart.candidate_files).Count -ne 3) { Fail 'implementation-start authority mismatch' }
foreach($candidatePath in $expectedCandidates) {
    $left=@($prospectiveContext.candidate_files | Where-Object path -ceq $candidatePath)[0]
    $right=@($implementationStart.candidate_files | Where-Object path -ceq $candidatePath)
    if ($right.Count -ne 1 -or $right[0].sha256 -ne $left.sha256 -or [long]$right[0].size -ne [long]$left.size) { Fail "implementation-start candidate mismatch: $candidatePath" }
}
$dag=Get-Content -Raw -LiteralPath $dagPath | ConvertFrom-Json
if ($dag.verdict -ne 'ZERO_CYCLES' -or @($dag.cycles).Count -ne 0 -or $dag.fixed_point_hashes -ne $false) { Fail 'prospective DAG is not acyclic' }
$prospectiveInventory=Get-Content -Raw -LiteralPath $prospectiveInventoryPath | ConvertFrom-Json
foreach($rel in @('prospective/dependency-dag-proof.jcs.json','prospective/implementation-start.jcs.json','prospective/prospective-context.jcs.json')) {
    $entry=@($prospectiveInventory.entries | Where-Object path -ceq $rel)
    $prospectiveFile=Join-Path $prep ($rel -replace '/','\')
    if ($entry.Count -ne 1 -or (Hash $prospectiveFile) -ne $entry[0].sha256 -or (Get-Item -LiteralPath $prospectiveFile).Length -ne [long]$entry[0].size) { Fail "prospective preparation inventory mismatch: $rel" }
}
$binding = Get-Content -Raw -LiteralPath $bindingPath | ConvertFrom-Json
$bindingKeys=@($binding.PSObject.Properties.Name | Sort-Object)
$required=@('accepted_output_inventory_sha256','derivation_id','derived_inventory_sha256','derived_inventory_size','independently_derived','payload_directories','payload_entry_count','payload_files','payload_root','phase_5_5f_commit','phase_5_5f_tag') | Sort-Object
if (@(Compare-Object $bindingKeys $required).Count -or $bindingKeys.Count -ne 11) { Fail 'binding record is not the exact frozen 11-member schema' }
if ($binding.accepted_output_inventory_sha256 -ne $Expected.Accepted -or $binding.derived_inventory_sha256 -ne $Expected.Jcs -or $binding.payload_root -ne $payload -or -not $binding.independently_derived) { Fail 'binding record value mismatch' }
$context=Get-Content -Raw -LiteralPath $contextPath | ConvertFrom-Json
if ($context.binding_record_sha256 -ne $Expected.Binding) { Fail 'context does not bind the frozen binding record' }
$joined=Get-Content -Raw -LiteralPath $prepInventoryPath | ConvertFrom-Json
foreach($rel in @('binding/binding-record.jcs.json','binding/preparation-context-record.jcs.json','inventory/payload-inventory.jcs.json')) {
    $entry=@($joined | Where-Object path -eq $rel); if ($entry.Count -ne 1) { Fail "preparation join missing $rel" }
    if ((Hash (Join-Path $prep ($rel -replace '/','\'))) -ne $entry[0].sha256) { Fail "preparation join mismatch $rel" }
}

$authority=Join-Path $toolchain 'evidence\toolchain-authority-record.json'
$manifest=Join-Path $toolchain 'evidence\required-toolchain-manifest.json'
$inventory=Join-Path $toolchain 'evidence\toolchain-inventory.json'
$iscc=Join-Path $toolchain 'toolchain\ISCC.exe'
RequireHash $authority $Expected.InnoAuthority; RequireHash $manifest $Expected.InnoManifest
RequireHash $inventory $Expected.InnoInventory; RequireHash $iscc $Expected.Iscc
if ((Get-Item -LiteralPath $iscc).Length -ne 1456272) { Fail 'ISCC size mismatch' }
$requiredTools=Get-Content -Raw -LiteralPath $manifest | ConvertFrom-Json
foreach($item in $requiredTools) {
    $candidate=Join-Path (Join-Path $toolchain 'toolchain') ($item.path -replace '/','\')
    RequireHash $candidate $item.sha256
    if ((Get-Item -LiteralPath $candidate).Length -ne $item.size) { Fail "toolchain size mismatch: $($item.path)" }
}

$entries=Get-Content -Raw -LiteralPath $jcsPath | ConvertFrom-Json
if ($entries.Count -ne 1035) { Fail 'inventory cardinality mismatch' }
$acceptedPath=Join-Path ([IO.Directory]::GetParent([IO.Directory]::GetParent($payload).FullName).FullName) 'fresh-output-inventory.txt'
RequireHash $acceptedPath $Expected.Accepted
$projected=@{}
foreach($line in @(Get-Content -LiteralPath $acceptedPath)) {
    $parts=$line.Split('|')
    if ($parts.Count -ne 3 -or -not $parts[0] -or $parts[1] -notmatch '^(0|[1-9]\d*)$' -or $parts[2] -notmatch '^[0-9A-F]{64}$') { Fail "accepted inventory schema mismatch: $line" }
    if ($projected.ContainsKey($parts[0])) { Fail "duplicate accepted projection: $($parts[0])" }
    $projected[$parts[0]]=[pscustomobject]@{ size=[long]$parts[1]; sha256=$parts[2] }
}
if ($projected.Count -ne 984) { Fail 'accepted projection cardinality mismatch' }
foreach($entry in @($entries | Where-Object type -eq 'file')) {
    if (-not $projected.ContainsKey($entry.path)) { Fail "accepted projection missing: $($entry.path)" }
    $prior=$projected[$entry.path]
    if ($prior.size -ne $entry.size -or $prior.sha256 -cne $entry.sha256) { Fail "accepted projection value mismatch: $($entry.path)" }
}
$seen=@{}; $files=@(); $directories=0
foreach($entry in $entries) {
    if (@($entry.PSObject.Properties.Name).Count -ne 4) { Fail "inventory schema mismatch: $($entry.path)" }
    $rel=[string]$entry.path
    if (-not $rel -or $rel.Contains('\') -or $rel.StartsWith('/') -or $rel.EndsWith('/') -or $rel -match '(^|/)\.\.?(/|$)') { Fail "unsafe inventory path: $rel" }
    $fold=$rel.ToUpperInvariant(); if ($seen.ContainsKey($fold)) { Fail "duplicate inventory path: $rel" }; $seen[$fold]=$true
    $path=Join-Path $payload ($rel -replace '/','\')
    if ($entry.type -eq 'directory') { if (-not (Test-Path -LiteralPath $path -PathType Container)) { Fail "missing directory: $rel" }; $directories++; continue }
    if ($entry.type -ne 'file' -or -not (Test-Path -LiteralPath $path -PathType Leaf)) { Fail "invalid file: $rel" }
    $item=Get-Item -LiteralPath $path
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $item.Length -ne [long]$entry.size -or (Hash $path) -ne $entry.sha256) { Fail "payload mismatch: $rel" }
    $files += $entry
}
$actual=@(Get-ChildItem -LiteralPath $payload -Recurse -Force); if ($actual.Count -ne 1035 -or $files.Count -ne 984 -or $directories -ne 51) { Fail 'fresh enumeration mismatch' }
$topExe=@(Get-ChildItem -LiteralPath $payload -File -Filter '*.exe')
if ($topExe.Count -ne 2 -or -not ($topExe.Name -ccontains 'PastilaScout.exe') -or -not ($topExe.Name -ccontains 'pastila-scout.exe')) { Fail 'launcher topology mismatch' }
foreach($name in @('THIRD-PARTY-NOTICES.txt','resources\trust\bootstrap-root-v1.json','resources\trust\pastila-root-1.pub')) { if (-not (Test-Path -LiteralPath (Join-Path $payload $name) -PathType Leaf)) { Fail "required payload resource missing: $name" } }
if (@(Get-ChildItem -LiteralPath $payload -Recurse -Force | Where-Object { $_.Name -match '(?i)(private|\.key$|test.?fixture|\.git|pytest|\.db$|\.log$)' }).Count) { Fail 'forbidden payload content detected' }
$version=(& (Join-Path $payload 'pastila-scout.exe') --version).Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$') { Fail 'invalid stable SemVer projection' }

New-Item -ItemType Directory -Force -Path $work,$out | Out-Null
$filesInclude=Join-Path $work 'payload-files.generated.iss'
$verifyInclude=Join-Path $work 'payload-verify.generated.iss'
$fileLines=@(); $verifyLines=@(
    'function FileIsUnlocked(const Path: String): Boolean;',
    'var',
    '  Stream: TFileStream;',
    'begin',
    '  Result := False;',
    '  try',
    '    Stream := TFileStream.Create(Path, fmOpenReadWrite or fmShareExclusive);',
    '    try Result := True; finally Stream.Free; end;',
    '  except',
    '    Result := False;',
    '  end;',
    'end;',
    '',
    'function VerifyInstalledPayloadUnlocked(const Root: String): Boolean;',
    'begin',
    '  Result := False;'
)
foreach($entry in $files) {
    $escaped=($entry.path -replace '/','\').Replace("'","''")
    $verifyLines += "  if not FileIsUnlocked(Root + '\$escaped') then exit;"
}
$verifyLines += @(
    '  Result := True;',
    'end;',
    '',
    'procedure RegisterRestartManagerResources(const SessionHandle: LongWord);',
    'begin'
)
foreach($entry in $files) {
    $escaped=($entry.path -replace '/','\').Replace("'","''")
    $verifyLines += "  RegisterRestartManagerResource(SessionHandle, ExpandConstant('{localappdata}\Programs\PastilaScout\app\$escaped'));"
}
$verifyLines += @('end;','','function VerifyStagedPayload(const Root: String): Boolean;','begin','  Result := False;')
for($fileIndex=0; $fileIndex -lt $files.Count; $fileIndex++) {
    $entry=$files[$fileIndex]
    $rel=$entry.path -replace '/','\'; $dir=Split-Path $rel -Parent; $dest='{app}\{code:StageDirectory}'
    if ($dir) { $dest += '\' + $dir }
    $src=(Join-Path $payload $rel).Replace('"','""')
    $line='Source: "' + $src + '"; DestDir: "' + $dest + '"; Flags: ignoreversion'
    if($fileIndex -eq ($files.Count - 1)) { $line += '; AfterInstall: ActivateStagedPayload' }
    $fileLines += $line
    $escaped=$rel.Replace("'","''")
    $verifyLines += "  { expected size $($entry.size) }; if CompareText(GetSHA256OfFile(Root + '\$escaped'), '$($entry.sha256)') <> 0 then exit;"
}
$verifyLines += @('  Result := True;','end;','','function StageDirectory(Param: String): String;','begin','  Result := StageName;','end;')
[IO.File]::WriteAllLines($filesInclude,$fileLines,(New-Object Text.UTF8Encoding($false)))
[IO.File]::WriteAllLines($verifyInclude,$verifyLines,(New-Object Text.UTF8Encoding($false)))
$icon=Join-Path $repo 'packaging\resources\PastilaScout.ico'
$definition=Join-Path $repo 'packaging\inno\PastilaScout.iss'
$payloadBytes=($files | Measure-Object -Property size -Sum).Sum
$args=@('/Q',('/DPayloadFilesInclude='+$filesInclude),('/DPayloadVerifyInclude='+$verifyInclude),('/DPayloadBytes='+$payloadBytes),('/DAppVersion='+$version),('/DOutputDir='+$out),('/DFrozenIcon='+$icon),$definition)
if ($BuildVariant -eq 'Vm05Instrumented') {
    $args = @('/DPASTILA_VM05_TEST_INSTRUMENTATION=1') + $args
}
if ($BuildVariant -eq 'Vm01aInstrumented') {
    $args = @('/DPASTILA_VM01A_TEST_INSTRUMENTATION=1') + $args
}
$variantRecord=[ordered]@{
    schema='pastila-scout-phase-5.6b-build-variant-v1'
    variant=$BuildVariant
    instrumentation_symbol=if($BuildVariant -eq 'Vm05Instrumented'){'PASTILA_VM05_TEST_INSTRUMENTATION'}elseif($BuildVariant -eq 'Vm01aInstrumented'){'PASTILA_VM01A_TEST_INSTRUMENTATION'}else{$null}
    release_candidate=($BuildVariant -eq 'Release')
    repository_head=(git -C $repo rev-parse HEAD).Trim()
    installer_definition_sha256=(Hash $definition)
    wrapper_sha256=(Hash $PSCommandPath)
    work_root=$work
    output_root=$out
}
[IO.File]::WriteAllText((Join-Path $work 'build-variant.json'),($variantRecord|ConvertTo-Json -Compress),(New-Object Text.UTF8Encoding($false)))
$stdout=Join-Path $work 'iscc.stdout.txt'; $stderr=Join-Path $work 'iscc.stderr.txt'
$process=Start-Process -FilePath $iscc -ArgumentList $args -WorkingDirectory $work -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
if ($process.ExitCode -ne 0) { Fail "ISCC failed with exit $($process.ExitCode); see $stdout and $stderr" }
$outputs=@(Get-ChildItem -LiteralPath $out -File -Filter '*.exe'); if ($outputs.Count -ne 1) { Fail 'installer output cardinality mismatch' }
[pscustomobject]@{ Path=$outputs[0].FullName; Size=$outputs[0].Length; SHA256=(Hash $outputs[0].FullName); Version=$version }

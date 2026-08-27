[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PayloadRoot,
    [Parameter(Mandatory=$true)][string]$AuthorityRoot,
    [Parameter(Mandatory=$true)][string]$WorkRoot,
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [Parameter(Mandatory=$true)][string]$IsccExecutable,
    [Parameter(Mandatory=$true)][string]$SignToolPath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedAuthorityManifestSha256
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) { throw "Clean source installer V1 rejected: $Message" }
function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Full([string]$Path) { [IO.Path]::GetFullPath($Path).TrimEnd('\') }

$repo=Full (Join-Path $PSScriptRoot '..\..')
$payload=Full $PayloadRoot
$authority=Full $AuthorityRoot
$work=Full $WorkRoot
$output=Full $OutputRoot
$manifestPath=Join-Path $authority 'manifest.json'
$sourcePath=Join-Path $authority '03-clean-candidate-source-authority.json'
$inventoryPath=Join-Path $authority '02-clean-payload-inventory.json'
foreach($required in @($manifestPath,$sourcePath,$inventoryPath,$IsccExecutable,$SignToolPath)) {
    if(-not (Test-Path -LiteralPath $required -PathType Leaf)) { Fail "missing input: $required" }
}
if((Hash $manifestPath) -cne $ExpectedAuthorityManifestSha256) { Fail 'authority manifest drift' }
$manifest=Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if($manifest.clean_candidate_source_authority_identity -cne ('sha256:'+(Hash $sourcePath)) -or
   $manifest.clean_payload_inventory_identity -cne ('sha256:'+(Hash $inventoryPath))) { Fail 'authority linkage mismatch' }
$source=Get-Content -Raw -LiteralPath $sourcePath | ConvertFrom-Json
$inventory=Get-Content -Raw -LiteralPath $inventoryPath | ConvertFrom-Json
if($source.dirty_repository_is_authority -ne $false -or $source.worktree_unrelated_changes_excluded -ne $true) { Fail 'dirty repository admitted as authority' }
if((Full $inventory.root) -cne $payload) { Fail 'payload root mismatch' }
if(@($inventory.files).Count -ne [int]$inventory.total_files) { Fail 'payload inventory count mismatch' }
foreach($entry in $inventory.files) {
    $candidate=Join-Path $payload ($entry.path -replace '/','\')
    if(-not (Test-Path -LiteralPath $candidate -PathType Leaf) -or
       (Get-Item -LiteralPath $candidate).Length -ne [long]$entry.bytes -or
       (Hash $candidate) -cne $entry.sha256) { Fail "payload mismatch: $($entry.path)" }
}
$actual=@(Get-ChildItem -LiteralPath $payload -Recurse -File -Force)
if($actual.Count -ne [int]$inventory.total_files) { Fail 'unexpected payload file count' }
if((Test-Path -LiteralPath $work) -or (Test-Path -LiteralPath $output)) { Fail 'work and output roots must be absent' }
New-Item -ItemType Directory -Path $work,$output | Out-Null
$signedPayload=Join-Path $work 'signed-payload'
Copy-Item -LiteralPath $payload -Destination $signedPayload -Recurse
$signingScript=Join-Path $repo 'packaging\signing\invoke-authenticode-v1.ps1'
foreach($launcher in @('PastilaScout.exe','pastila-scout.exe')) {
    & $signingScript -Operation Sign -Path (Join-Path $signedPayload $launcher) -SignToolPath $SignToolPath | Out-Null
    if($LASTEXITCODE -ne 0) { Fail "launcher signing failed: $launcher" }
}

$entries=@(Get-ChildItem -LiteralPath $signedPayload -Recurse -File -Force | Sort-Object FullName | ForEach-Object {
    [pscustomobject]@{ path=$_.FullName.Substring($signedPayload.Length+1).Replace('\','/'); bytes=$_.Length; sha256=(Hash $_.FullName) }
})
$filesInclude=Join-Path $work 'payload-files.generated.iss'
$verifyInclude=Join-Path $work 'payload-verify.generated.iss'
$fileLines=@(); $unlock=@(); $restart=@(); $hashes=@()
for($index=0; $index -lt $entries.Count; $index++) {
    $entry=$entries[$index]; $rel=$entry.path -replace '/','\'; $dir=Split-Path $rel -Parent
    $destination='{app}\{code:StageDirectory}'; if($dir) { $destination+='\'+$dir }
    $sourceFile=(Join-Path $signedPayload $rel).Replace('"','""')
    $line='Source: "'+$sourceFile+'"; DestDir: "'+$destination+'"; Flags: ignoreversion'
    if($index -eq $entries.Count-1) { $line+='; AfterInstall: ActivateStagedPayload' }
    $fileLines+=$line
    $escaped=$rel.Replace("'","''")
    $unlock+="  if not FileIsUnlocked(Root + '\$escaped') then exit;"
    $restart+="  RegisterRestartManagerResource(SessionHandle, ExpandConstant('{localappdata}\Programs\PastilaScout\app\$escaped'));"
    $hashes+="  { expected size $($entry.bytes) }; if CompareText(GetSHA256OfFile(Root + '\$escaped'), '$($entry.sha256)') <> 0 then exit;"
}
$verifyLines=@(
    'function FileIsUnlocked(const Path: String): Boolean;','var','  Stream: TFileStream;','begin',
    '  if not FileExists(Path) then begin Result := True; exit; end;','  Result := False;','  try',
    '    Stream := TFileStream.Create(Path, fmOpenReadWrite or fmShareExclusive);','    try Result := True; finally Stream.Free; end;',
    '  except','    Result := False;','  end;','end;','',
    'function VerifyInstalledPayloadUnlocked(const Root: String): Boolean;','begin','  Result := False;',
    $unlock,'  Result := True;','end;','',
    'procedure RegisterRestartManagerResources(const SessionHandle: LongWord);','begin',$restart,'end;','',
    'function VerifyStagedPayload(const Root: String): Boolean;','begin','  Result := False;',$hashes,'  Result := True;','end;','',
    'function StageDirectory(Param: String): String;','begin','  Result := StageName;','end;'
)
[IO.File]::WriteAllLines($filesInclude,$fileLines,(New-Object Text.UTF8Encoding($false)))
[IO.File]::WriteAllLines($verifyInclude,$verifyLines,(New-Object Text.UTF8Encoding($false)))
$authInclude=Join-Path $work 'authenticode-setup.generated.iss'
[IO.File]::WriteAllText($authInclude,"SignTool=PastilaAcidaAuthenticodeV1 `$f`nSignedUninstaller=yes`n",(New-Object Text.UTF8Encoding($false)))
$signCommand="powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `$q$signingScript`$q -Operation Sign -Path `$f -SignToolPath `$q$SignToolPath`$q"
$payloadBytes=($entries | Measure-Object -Property bytes -Sum).Sum
$definition=Join-Path $repo 'packaging\inno\PastilaScout.iss'
$icon=Join-Path $repo 'packaging\resources\PastilaScout.ico'
$args=@('/Q',('/DPayloadFilesInclude='+$filesInclude),('/DPayloadVerifyInclude='+$verifyInclude),('/DPayloadBytes='+$payloadBytes),'/DAppVersion=1.1.8',('/DOutputDir='+$output),('/DFrozenIcon='+$icon),('/DAuthenticodeSetupInclude='+$authInclude),('/SPastilaAcidaAuthenticodeV1='+$signCommand),$definition)
& $IsccExecutable @args
if($LASTEXITCODE -ne 0) { Fail 'Inno compilation failed' }
$installer=Join-Path $output 'PastilaScout-1.1.8-Setup.exe'
if(-not (Test-Path -LiteralPath $installer -PathType Leaf)) { Fail 'installer output missing' }
& $signingScript -Operation Verify -Path $installer -SignToolPath $SignToolPath | Out-Null
if($LASTEXITCODE -ne 0) { Fail 'installer signature verification failed' }
$receipt=[ordered]@{
    schema='pastilaacida-voice-v2-clean-source-signed-installer-receipt-v1'
    authority_manifest_sha256=(Hash $manifestPath)
    source_authority_sha256=(Hash $sourcePath)
    payload_inventory_sha256=(Hash $inventoryPath)
    signed_payload_file_count=$entries.Count
    signed_gui_sha256=(Hash (Join-Path $signedPayload 'PastilaScout.exe'))
    signed_cli_sha256=(Hash (Join-Path $signedPayload 'pastila-scout.exe'))
    installer_sha256=(Hash $installer)
    signer_thumbprint='604635DF3EB4CAF406D977987B1A6AA764D83612'
    production_activation=[ordered]@{expressions=3;surfaces=3}
}
$receiptPath=Join-Path $output 'signed-installer-receipt-v1.json'
[IO.File]::WriteAllText($receiptPath,($receipt|ConvertTo-Json -Depth 8 -Compress)+"`n",(New-Object Text.UTF8Encoding($false)))
$receipt | ConvertTo-Json -Depth 8

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Sign','Verify')][string]$Operation,
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$SignToolPath,
    [string]$AuthorityPath
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

if(-not $AuthorityPath) { $AuthorityPath=Join-Path $PSScriptRoot '..\windows\signing-authority-v1.json' }

function Fail([string]$Message) { throw "PastilaAcida signing V1 rejected: $Message" }

$target=(Resolve-Path -LiteralPath $Path).Path
$signTool=(Resolve-Path -LiteralPath $SignToolPath).Path
$authorityFile=(Resolve-Path -LiteralPath $AuthorityPath).Path
$authority=Get-Content -Raw -LiteralPath $authorityFile | ConvertFrom-Json
if($authority.schema -cne 'pastilaacida-authenticode-signing-authority-v1' -or
   $authority.signing_mode -cne 'private_signing_required' -or
   $authority.file_digest_algorithm -cne 'SHA256' -or
   $authority.timestamp.status -cne 'NOT_CONFIGURED_PRIVATE_V1') { Fail 'authority is invalid' }
$thumb=[string]$authority.certificate.thumbprint
if($thumb -cnotmatch '^[0-9A-F]{40}$') { Fail 'certificate thumbprint is invalid' }
$repository=(Resolve-Path (Join-Path (Split-Path $authorityFile -Parent) '..\..')).Path
$publicCertificate=(Resolve-Path (Join-Path $repository $authority.certificate.public_certificate)).Path
if((Get-FileHash -Algorithm SHA256 -LiteralPath $publicCertificate).Hash.ToLowerInvariant() -cne
   $authority.certificate.public_certificate_sha256) { Fail 'public certificate identity mismatch' }
$certificates=@(Get-ChildItem Cert:\CurrentUser\My | Where-Object Thumbprint -ceq $thumb)
if($certificates.Count -ne 1) { Fail 'exact certificate is missing or ambiguous' }
$certificate=$certificates[0]
if($certificate.Subject -cne $authority.certificate.subject -or
   $certificate.FriendlyName -cne $authority.certificate.friendly_name -or
   -not $certificate.HasPrivateKey) { Fail 'certificate identity or private-key availability mismatch' }
$eku=@($certificate.Extensions | Where-Object {$_.Oid.Value -eq '2.5.29.37'} | ForEach-Object {$_.Format($false)}) -join ' '
if($eku -notmatch '1\.3\.6\.1\.5\.5\.7\.3\.3') { Fail 'Code Signing EKU is missing' }

if($Operation -eq 'Sign') {
    & $signTool sign /sha1 $thumb /fd SHA256 /v $target
    if($LASTEXITCODE -ne 0) { Fail 'SignTool signing failed' }
}

$signature=Get-AuthenticodeSignature -LiteralPath $target
if($null -eq $signature.SignerCertificate) { Fail 'artifact is unsigned' }
if($signature.SignerCertificate.Thumbprint -cne $thumb) { Fail 'artifact has the wrong signer' }
if($signature.Status -eq 'HashMismatch' -or $signature.Status -eq 'NotSigned') { Fail 'artifact signature integrity failed' }
if($signature.Status -ne 'Valid' -and -not ($authority.verification.allow_private_chain_untrusted -and $signature.Status -eq 'UnknownError')) {
    Fail "artifact signature status is $($signature.Status)"
}

[pscustomobject]@{
    path=$target
    sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    signature_presence=$true
    signature_integrity='VALID'
    chain_trust=if($signature.Status -eq 'Valid'){'TRUSTED_CURRENT_USER'}else{'UNTRUSTED_PRIVATE_ROOT'}
    signer_subject=$signature.SignerCertificate.Subject
    signer_thumbprint=$signature.SignerCertificate.Thumbprint
    file_digest_algorithm='SHA256'
    timestamp_status='NOT_CONFIGURED_PRIVATE_V1'
} | ConvertTo-Json -Compress

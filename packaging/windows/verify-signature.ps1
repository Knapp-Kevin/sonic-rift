<#
.SYNOPSIS
Fails unless a file carries a valid, timestamped MythologIQ Labs signature.

.DESCRIPTION
Runs the release checks from the Windows code signing standard: signtool
verify /pa, a Valid Authenticode status, the expected signer, and a timestamp.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Path,
    [string] $SignToolPath
)

$ErrorActionPreference = 'Stop'

if (-not $SignToolPath) {
    $SignToolPath = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" |
        Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}

& $SignToolPath verify /pa /v $Path
if ($LASTEXITCODE -ne 0) { throw "signtool verify /pa failed for $Path." }

$sig = Get-AuthenticodeSignature $Path
if ($sig.Status -ne 'Valid') { throw "Authenticode status is $($sig.Status), not Valid." }
if ($sig.SignerCertificate.Subject -notmatch '^CN="MythologIQ Labs, LLC"') {
    throw "Unexpected signer: $($sig.SignerCertificate.Subject)"
}
if (-not $sig.TimeStamperCertificate) { throw 'The signature is not timestamped.' }

Write-Host "Verified: $Path"
Write-Host "  Signer:      $($sig.SignerCertificate.Subject)"
Write-Host "  Timestamper: $($sig.TimeStamperCertificate.Subject)"
Write-Host "  SHA-256:     $((Get-FileHash $Path -Algorithm SHA256).Hash)"

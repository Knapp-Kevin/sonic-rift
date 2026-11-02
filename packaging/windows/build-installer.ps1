<#
.SYNOPSIS
Builds the Sonic Rift Windows installer, and signs it when -Sign is given.

.DESCRIPTION
Stages the committed app files (git archive of HEAD, so local edits and
generated environments never ship), adds the launcher and a pinned uv, then
compiles packaging/windows/SonicRift.iss with Inno Setup.

With -Sign, Inno Setup signs the installer and its uninstaller through
SignTool and the Azure Artifact Signing client, using the Azure CLI sign-in
(az login locally, azure/login with OIDC in GitHub Actions). See
MythologIQ-Labs-LLC/Myth-Tech-Forge docs/WINDOWS_CODE_SIGNING_STANDARD.md.

.EXAMPLE
pwsh packaging/windows/build-installer.ps1 -Version 0.1.0
pwsh packaging/windows/build-installer.ps1 -Version 0.1.0 -Sign -SigningClientDir C:\signing\client
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Version,
    [switch] $Sign,
    # Folder holding bin\x64\Azure.CodeSigning.Dlib.dll from the
    # Microsoft.ArtifactSigning.Client NuGet package.
    [string] $SigningClientDir,
    [string] $Iscc,
    [string] $SignToolPath
)

$ErrorActionPreference = 'Stop'

# Pinned uv. Update the version and hash together, from the release's .sha256 file.
$UvVersion = '0.12.22'
$UvSha256 = 'ea1397797a0ca15f63516dd0f49c2dde9776db9be5861cab152ebe8ad199894d'

# What an installed copy needs. Tests, docs and macOS/Linux scripts stay out.
$AppPaths = @(
    'main.py', 'models.json', 'requirements.in', 'requirements.lock.txt', 'uv.toml',
    'run.bat', 'setup_env.bat', 'this_voice_thing', 'engines', 'scripts', 'assets',
    'LICENSE', 'NOTICE', 'LICENSES', 'THIRD_PARTY_NOTICES.md', 'Readme.md', 'CHANGELOG.md'
)

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Build = Join-Path $Root 'build\windows'
$Stage = Join-Path $Build 'stage'
$Dist = Join-Path $Root 'dist'

if ($Version -notmatch '^(\d+)\.(\d+)\.(\d+)') { throw "Version '$Version' must start with MAJOR.MINOR.PATCH." }
$NumericVersion = $Matches[0]

if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force $Stage, $Dist | Out-Null

Write-Host "Staging committed app files from $(git -C $Root rev-parse --short HEAD)..."
$tar = Join-Path $Build 'app.tar'
git -C $Root archive --format=tar --output=$tar HEAD -- @AppPaths
if ($LASTEXITCODE -ne 0) { throw 'git archive failed.' }
# Windows' own bsdtar; a GNU tar earlier on PATH would read C: as a remote host.
& "$env:SystemRoot\System32\tar.exe" -xf $tar -C $Stage
if ($LASTEXITCODE -ne 0) { throw 'Extracting the staged files failed.' }
Remove-Item $tar
Copy-Item (Join-Path $PSScriptRoot 'launch-sonic-rift.cmd') $Stage

Write-Host "Adding uv $UvVersion..."
$uvZip = Join-Path $Build "uv-$UvVersion.zip"
if (-not (Test-Path $uvZip)) {
    Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$UvVersion/uv-x86_64-pc-windows-msvc.zip" -OutFile $uvZip
}
$hash = (Get-FileHash $uvZip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $UvSha256) {
    Remove-Item $uvZip
    throw "uv download hash mismatch: expected $UvSha256, got $hash."
}
$tools = Join-Path $Stage 'tools'
Expand-Archive $uvZip -DestinationPath $tools -Force
Set-Content (Join-Path $tools 'uv-NOTICE.txt') -Encoding utf8 -Value @"
uv $UvVersion by Astral Software Inc., dual-licensed under the MIT License and the
Apache License, Version 2.0. Source and license texts: https://github.com/astral-sh/uv
"@

if (-not $Iscc) {
    $Iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) { throw 'Inno Setup 6 (ISCC.exe) was not found. Pass -Iscc.' }
}

$isccArgs = @(
    "/DAppVersion=$Version", "/DNumericVersion=$NumericVersion",
    "/DStageDir=$Stage", "/DOutputDir=$Dist"
)

if ($Sign) {
    if (-not $SignToolPath) {
        $SignToolPath = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" |
            Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
        if (-not $SignToolPath) { throw 'signtool.exe was not found. Install the Windows SDK or pass -SignToolPath.' }
    }
    if (-not $SigningClientDir) { throw '-Sign needs -SigningClientDir.' }
    $dlib = Join-Path $SigningClientDir 'bin\x64\Azure.CodeSigning.Dlib.dll'
    if (-not (Test-Path $dlib)) { throw "Signing client not found at $dlib." }

    # Only the Azure CLI credential is allowed, so the signer is whoever az is signed in as.
    $metadata = Join-Path $Build 'signing-metadata.json'
    $metadataJson = @{
        Endpoint               = 'https://eus.codesigning.azure.net/'
        CodeSigningAccountName = 'MythologIQ-Labs-Signing'
        CertificateProfileName = 'mythologiq-labs-public-release'
        ExcludeCredentials     = @(
            'ManagedIdentityCredential', 'EnvironmentCredential', 'WorkloadIdentityCredential',
            'SharedTokenCacheCredential', 'VisualStudioCredential', 'VisualStudioCodeCredential',
            'AzurePowerShellCredential', 'AzureDeveloperCliCredential', 'InteractiveBrowserCredential'
        )
    } | ConvertTo-Json
    # No byte-order mark: the signing client can't parse metadata that starts with one,
    # and Windows PowerShell's -Encoding utf8 always writes it.
    [IO.File]::WriteAllText($metadata, $metadataJson)

    # Inno Setup replaces $f with the quoted path of each file it signs, and $q with
    # a quote. Literal quotes inside a native argument don't survive Windows PowerShell.
    $signCommand = "`$q$SignToolPath`$q sign /fd SHA256 /tr http://timestamp.acs.microsoft.com /td SHA256 " +
        "/dlib `$q$dlib`$q /dmdf `$q$metadata`$q `$f"
    $isccArgs += "/Sartifactsigning=$signCommand", '/DSignToolName=artifactsigning'
}

Write-Host "Compiling the installer with $Iscc..."
& $Iscc @isccArgs (Join-Path $PSScriptRoot 'SonicRift.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE." }

$installer = Join-Path $Dist "SonicRift-Setup-$Version.exe"
Write-Host "Built $installer"
$installer

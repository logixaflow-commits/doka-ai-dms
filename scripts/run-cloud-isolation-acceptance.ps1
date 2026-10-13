[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AcceptanceBaseUrl,
    [string]$OutputPath = "docs/Report/cloud-isolation-acceptance.json"
)

$ErrorActionPreference = "Stop"

function ConvertFrom-SecureToken {
    param([Parameter(Mandatory = $true)][Security.SecureString]$SecureToken)

    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$parsed = $null
if (-not [Uri]::TryCreate($AcceptanceBaseUrl, [UriKind]::Absolute, [ref]$parsed) -or $parsed.Scheme -ne "https") {
    throw "AcceptanceBaseUrl must be an absolute HTTPS URL."
}
if ($parsed.Host -eq "doka-ai-dms.logixaflow.workers.dev") {
    throw "Refusing to run two-user isolation against production. Use an isolated acceptance environment that permits both test users."
}

$userASecure = Read-Host "Enter Supabase access token for test user A (hidden input)" -AsSecureString
$userBSecure = Read-Host "Enter Supabase access token for test user B (hidden input)" -AsSecureString
if ($userASecure.Length -eq 0 -or $userBSecure.Length -eq 0) {
    throw "Both test-user access tokens are required."
}

$userA = ConvertFrom-SecureToken -SecureToken $userASecure
$userB = ConvertFrom-SecureToken -SecureToken $userBSecure
if ($userA -eq $userB) {
    $userA = $null
    $userB = $null
    throw "Test user A and B tokens must be different."
}

$fixturePath = Join-Path $env:TEMP ("doka-cloud-50mib-" + [Guid]::NewGuid().ToString("N") + ".bin")
$resolvedOutput = [IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $resolvedOutput
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

try {
    $stream = [IO.File]::Open($fixturePath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $stream.SetLength(52428800)
    }
    finally {
        $stream.Dispose()
    }

    $env:DOKA_CLOUD_BASE_URL = $AcceptanceBaseUrl.TrimEnd("/")
    $env:DOKA_CLOUD_USER_A_TOKEN = $userA
    $env:DOKA_CLOUD_USER_B_TOKEN = $userB

    Write-Host "Running two-user isolation and exact-50-MiB acceptance against the isolated environment."
    Write-Host ("Privacy-safe evidence will be written to: " + $resolvedOutput)
    uv run --with httpx python scripts/cloud_acceptance.py --base-url $env:DOKA_CLOUD_BASE_URL --output $resolvedOutput --fifty-mib-file $fixturePath
    if ($LASTEXITCODE -ne 0) {
        throw ("Cloud isolation acceptance failed. Inspect the privacy-safe evidence file: " + $resolvedOutput)
    }
    Write-Host "Two-user isolation and exact-50-MiB acceptance passed."
}
finally {
    Remove-Item Env:DOKA_CLOUD_USER_A_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:DOKA_CLOUD_USER_B_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:DOKA_CLOUD_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item $fixturePath -Force -ErrorAction SilentlyContinue
    $userA = $null
    $userB = $null
    $userASecure.Dispose()
    $userBSecure.Dispose()
}

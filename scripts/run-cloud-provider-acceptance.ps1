[CmdletBinding()]
param(
    [string]$BaseUrl = "https://doka-ai-dms.logixaflow.workers.dev",
    [ValidateSet("supabase", "b2", "both")]
    [string]$Provider = "both",
    [string]$OutputDirectory = "docs/Report"
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
if (-not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$parsed) -or $parsed.Scheme -ne "https") {
    throw "BaseUrl must be an absolute HTTPS URL."
}

$tokenSecure = Read-Host "Enter the Supabase access token for the authorized Doka test user (input is hidden)" -AsSecureString
if ($tokenSecure.Length -eq 0) {
    throw "An access token is required."
}

$token = ConvertFrom-SecureToken -SecureToken $tokenSecure
$env:DOKA_CLOUD_BASE_URL = $BaseUrl.TrimEnd("/")
$env:DOKA_CLOUD_USER_TOKEN = $token
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

try {
    $providers = if ($Provider -eq "both") { @("b2", "supabase") } else { @($Provider) }
    foreach ($providerName in $providers) {
        $evidencePath = Join-Path $OutputDirectory ("cloud-provider-" + $providerName + "-acceptance.json")
        Write-Host ("Running live " + $providerName + " provider acceptance. Evidence: " + $evidencePath)
        uv run --with httpx python scripts/cloud_provider_acceptance.py --base-url $env:DOKA_CLOUD_BASE_URL --provider $providerName --output $evidencePath
        if ($LASTEXITCODE -ne 0) {
            throw ("Live " + $providerName + " acceptance failed. Check the privacy-safe evidence file: " + $evidencePath)
        }
    }
    Write-Host "All requested provider acceptance runs passed. Evidence files contain no access tokens or signed URLs."
}
finally {
    Remove-Item Env:DOKA_CLOUD_USER_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:DOKA_CLOUD_BASE_URL -ErrorAction SilentlyContinue
    $token = $null
    $tokenSecure.Dispose()
}

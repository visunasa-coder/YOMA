param(
    [string]$ApiToken = $env:SIGNPATH_API_TOKEN,
    [string]$OrganizationId = $env:SIGNPATH_ORGANIZATION_ID,
    [string]$ProjectSlug = $env:SIGNPATH_PROJECT_SLUG,
    [string]$SigningPolicySlug = $env:SIGNPATH_SIGNING_POLICY_SLUG,
    [string]$AppArtifactConfigurationSlug = $env:SIGNPATH_APP_ARTIFACT_CONFIGURATION_SLUG,
    [string]$InstallerArtifactConfigurationSlug = $env:SIGNPATH_INSTALLER_ARTIFACT_CONFIGURATION_SLUG
)

$ErrorActionPreference = 'Stop'

$required = [ordered]@{
    'SIGNPATH_API_TOKEN' = $ApiToken
    'SIGNPATH_ORGANIZATION_ID' = $OrganizationId
    'SIGNPATH_PROJECT_SLUG' = $ProjectSlug
    'SIGNPATH_SIGNING_POLICY_SLUG' = $SigningPolicySlug
    'SIGNPATH_APP_ARTIFACT_CONFIGURATION_SLUG' = $AppArtifactConfigurationSlug
    'SIGNPATH_INSTALLER_ARTIFACT_CONFIGURATION_SLUG' = $InstallerArtifactConfigurationSlug
}

$missing = @($required.GetEnumerator() | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.Value) } | ForEach-Object Key)
if ($missing.Count -gt 0) {
    throw "SignPath production release configuration is incomplete. Missing: $($missing -join ', ')"
}

Write-Output 'SignPath production release configuration is present; approval and provider-side policy remain required.'

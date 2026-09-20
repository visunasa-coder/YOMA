param(
    [Parameter(Mandatory = $true)]
    [string[]]$Path,
    [string]$CertificateThumbprint,
    [switch]$CreateTestCertificate,
    [string]$TimestampServer
)

$ErrorActionPreference = "Stop"

function Get-YomaTestCertificate {
    $existing = Get-ChildItem Cert:\CurrentUser\My |
        Where-Object {
            $_.Subject -eq "CN=YOMA TEST Code Signing" -and
            $_.HasPrivateKey -and
            $_.NotAfter -gt (Get-Date)
        } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1

    if ($existing) { return $existing }

    try {
        return New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject "CN=YOMA TEST Code Signing" `
            -FriendlyName "YOMA TEST ONLY - NOT PRODUCTION TRUSTED" `
            -CertStoreLocation Cert:\CurrentUser\My `
            -HashAlgorithm SHA256 `
            -NotAfter (Get-Date).AddYears(2)
    } catch {
        # Some locked-down developer images do not expose a usable user key
        # store. Keep the test key in memory; never treat it as production
        # trust or persist it outside the YOMA workspace.
        $rsa = [System.Security.Cryptography.RSA]::Create(2048)
        $name = [System.Security.Cryptography.X509Certificates.X500DistinguishedName]::new("CN=YOMA TEST Code Signing")
        $request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
            $name,
            $rsa,
            [System.Security.Cryptography.HashAlgorithmName]::SHA256,
            [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
        )
        $oids = [System.Security.Cryptography.OidCollection]::new()
        [void]$oids.Add([System.Security.Cryptography.Oid]::new("1.3.6.1.5.5.7.3.3"))
        $request.CertificateExtensions.Add(
            [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($oids, $true)
        )
        return $request.CreateSelfSigned((Get-Date).AddMinutes(-5), (Get-Date).AddYears(2))
    }
}

if ($CreateTestCertificate) {
    $certificate = Get-YomaTestCertificate
} elseif ($CertificateThumbprint) {
    $normalized = $CertificateThumbprint.Replace(' ', '')
    $certificate = Get-ChildItem Cert:\CurrentUser\My\$normalized -ErrorAction SilentlyContinue
    if (-not $certificate) {
        $certificate = Get-ChildItem Cert:\LocalMachine\My\$normalized -ErrorAction Stop
    }
    if (-not $certificate.HasPrivateKey) {
        throw "The selected YOMA signing certificate has no private key."
    }
} else {
    throw "Provide -CertificateThumbprint for production signing or -CreateTestCertificate for development signing."
}

if ($certificate.Subject -eq "CN=YOMA TEST Code Signing") {
    Write-Warning "TEST SIGNING ONLY: $($certificate.Thumbprint). This certificate is not production-trusted and will not satisfy enterprise policy unless separately trusted by policy."
}

foreach ($item in $Path) {
    $resolved = Resolve-Path -LiteralPath $item -ErrorAction Stop
    $signatureParameters = @{
        FilePath = $resolved.Path
        Certificate = $certificate
        HashAlgorithm = "SHA256"
    }
    if ($TimestampServer) {
        $signatureParameters.TimestampServer = $TimestampServer
    }
    $result = Set-AuthenticodeSignature @signatureParameters
    $result | Format-List Path,Status,StatusMessage,SignerCertificate
    if (-not $CreateTestCertificate -and $result.Status -ne "Valid") {
        throw "Production signing failed for $($resolved.Path): $($result.StatusMessage)"
    }
}

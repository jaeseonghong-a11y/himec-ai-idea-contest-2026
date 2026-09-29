# Wraps the AutoCAD 2024 bundle, its installer and its Korean guide into one ZIP.
# Mirrors package-team.ps1; outputs to dist2024/ so the 2026 package is untouched.
param(
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must be major.minor.patch' }
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundle = Join-Path $root "dist2024/$Version/Himec.ChangeLoop2024.bundle"
$readme = Join-Path $root 'README_INSTALL_2024_KO.md'
$installer = Join-Path $root 'install-user-2024.ps1'
$zipPath = Join-Path $root "dist2024/Himec.ChangeLoop-AutoCAD2024-v$Version-team.zip"
foreach ($path in @($bundle, $readme, $installer)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing package input: $path" }
}
if (Test-Path -LiteralPath $zipPath) { throw "Output already exists: $zipPath" }

$bundleFiles = @(Get-ChildItem -LiteralPath $bundle -File -Recurse)
$zip = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
try {
    [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $readme, 'README_INSTALL_2024_KO.md') | Out-Null
    [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $installer, 'install-user-2024.ps1') | Out-Null
    $bundleFull = [IO.Path]::GetFullPath($bundle).TrimEnd('\')
    foreach ($file in $bundleFiles) {
        $relative = $file.FullName.Substring($bundleFull.Length).TrimStart('\').Replace('\', '/')
        $entry = 'Himec.ChangeLoop2024.bundle/' + $relative
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $file.FullName, $entry) | Out-Null
    }
}
finally { $zip.Dispose() }

$check = [IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $entries = @($check.Entries | ForEach-Object FullName)
    $required = @(
        'README_INSTALL_2024_KO.md', 'install-user-2024.ps1',
        'Himec.ChangeLoop2024.bundle/PackageContents.xml',
        'Himec.ChangeLoop2024.bundle/Contents/Windows/Himec.AutoCad2024.dll',
        'Himec.ChangeLoop2024.bundle/Contents/Windows/Himec.ChangeCore.dll',
        'Himec.ChangeLoop2024.bundle/Contents/Windows/NAudio.dll',
        'Himec.ChangeLoop2024.bundle/Contents/Windows/NAudio.Core.dll',
        'Himec.ChangeLoop2024.bundle/Contents/Windows/NAudio.WinMM.dll',
        # .NET Framework has no System.Text.Json in the framework itself.
        'Himec.ChangeLoop2024.bundle/Contents/Windows/System.Text.Json.dll'
    )
    foreach ($entry in $required) {
        if ($entries -notcontains $entry) { throw "Missing ZIP entry: $entry" }
    }
    # Derived from the bundle rather than hard-coded: the net48 dependency set is
    # larger than the 2026 one and may change when a package is updated.
    $expected = $bundleFiles.Count + 2
    if ($entries.Count -ne $expected) { throw "Unexpected ZIP file count: $($entries.Count), expected $expected" }
}
finally { $check.Dispose() }

[pscustomobject]@{
    Zip = $zipPath
    Files = $entries.Count
    Bytes = (Get-Item -LiteralPath $zipPath).Length
    Sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
} | Format-List

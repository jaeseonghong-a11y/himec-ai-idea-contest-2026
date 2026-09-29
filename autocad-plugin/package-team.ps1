param(
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must be major.minor.patch' }
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundle = Join-Path $root "dist/$Version/Himec.ChangeLoop.bundle"
$readme = Join-Path $root 'README_INSTALL_KO.md'
$installer = Join-Path $root 'install-user.ps1'
$zipPath = Join-Path $root "dist/Himec.ChangeLoop-AutoCAD2026-v$Version-team.zip"
foreach ($path in @($bundle, $readme, $installer)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing package input: $path" }
}
if (Test-Path -LiteralPath $zipPath) { throw "Output already exists: $zipPath" }

$zip = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
try {
    [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $readme, 'README_INSTALL_KO.md') | Out-Null
    [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $installer, 'install-user.ps1') | Out-Null
    $bundleFull = [IO.Path]::GetFullPath($bundle).TrimEnd('\')
    foreach ($file in Get-ChildItem -LiteralPath $bundle -File -Recurse) {
        $relative = $file.FullName.Substring($bundleFull.Length).TrimStart('\').Replace('\', '/')
        $entry = 'Himec.ChangeLoop.bundle/' + $relative
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $file.FullName, $entry) | Out-Null
    }
}
finally { $zip.Dispose() }

$check = [IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $entries = @($check.Entries | ForEach-Object FullName)
    $required = @(
        'README_INSTALL_KO.md', 'install-user.ps1',
        'Himec.ChangeLoop.bundle/PackageContents.xml',
        'Himec.ChangeLoop.bundle/Contents/Windows/Himec.AutoCad2026.dll',
        'Himec.ChangeLoop.bundle/Contents/Windows/Himec.ChangeCore.dll',
        'Himec.ChangeLoop.bundle/Contents/Windows/NAudio.dll',
        'Himec.ChangeLoop.bundle/Contents/Windows/NAudio.Core.dll',
        'Himec.ChangeLoop.bundle/Contents/Windows/NAudio.WinMM.dll'
    )
    foreach ($entry in $required) {
        if ($entries -notcontains $entry) { throw "Missing ZIP entry: $entry" }
    }
    if ($entries.Count -ne 12) { throw "Unexpected ZIP file count: $($entries.Count)" }
}
finally { $check.Dispose() }

[pscustomobject]@{
    Zip = $zipPath
    Files = $entries.Count
    Bytes = (Get-Item -LiteralPath $zipPath).Length
    Sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
} | Format-List

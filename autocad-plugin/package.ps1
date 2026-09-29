param(
    [string]$Dotnet = "dotnet",
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version must be major.minor.patch" }
$pluginRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = Join-Path $pluginRoot "Himec.AutoCad2026/Himec.AutoCad2026.csproj"
$binaryRoot = Join-Path $pluginRoot "Himec.AutoCad2026/bin/Release/net8.0-windows"
$bundleRoot = Join-Path $pluginRoot "dist/$Version/Himec.ChangeLoop.bundle"
$contentRoot = Join-Path $bundleRoot "Contents/Windows"

if (Test-Path -LiteralPath $bundleRoot) {
    throw "Output already exists: $bundleRoot. Choose a new version; existing packages are not overwritten."
}

& $Dotnet build $project -c Release --nologo
if ($LASTEXITCODE -ne 0) { throw "Build failed." }

New-Item -ItemType Directory -Path $contentRoot -Force | Out-Null
$manifest = [xml](Get-Content -LiteralPath (Join-Path $pluginRoot "packaging/PackageContents.xml") -Raw -Encoding UTF8)
$manifest.ApplicationPackage.SetAttribute("AppVersion", "$Version.0")
$manifest.ApplicationPackage.SetAttribute("ProductCode", ([guid]::NewGuid().ToString('B').ToUpperInvariant()))
$manifest.Save((Join-Path $bundleRoot "PackageContents.xml"))
$required = @("Himec.AutoCad2026.dll", "Himec.ChangeCore.dll", "NAudio.dll", "NAudio.Core.dll", "NAudio.WinMM.dll")
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $binaryRoot $name))) { throw "Missing build output: $name" }
}
Get-ChildItem -LiteralPath $binaryRoot -File | Where-Object { $_.Extension -eq ".dll" } |
    ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $contentRoot $_.Name) }

Write-Output "Bundle: $bundleRoot"
Get-ChildItem -LiteralPath $contentRoot -File | Get-FileHash -Algorithm SHA256 |
    Select-Object @{Name="File";Expression={Split-Path -Leaf $_.Path}}, Hash

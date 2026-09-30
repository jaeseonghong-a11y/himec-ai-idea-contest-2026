# Builds the AutoCAD 2024 (.NET Framework 4.8) bundle.
# The 2026 package.ps1 is left untouched; outputs go to dist2024/ so neither
# version can overwrite the other.
param(
    [string]$Dotnet = "dotnet",
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$AutoCadDir = "C:\Program Files\Autodesk\AutoCAD 2024\"
)

$ErrorActionPreference = "Stop"
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version must be major.minor.patch" }
$pluginRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = Join-Path $pluginRoot "Himec.AutoCad2024/Himec.AutoCad2024.csproj"
$binaryRoot = Join-Path $pluginRoot "Himec.AutoCad2024/bin/Release/net48"
$bundleRoot = Join-Path $pluginRoot "dist2024/$Version/Himec.ChangeLoop2024.bundle"
$contentRoot = Join-Path $bundleRoot "Contents/Windows"

if (Test-Path -LiteralPath $bundleRoot) {
    throw "Output already exists: $bundleRoot. Choose a new version; existing packages are not overwritten."
}
if (-not (Test-Path -LiteralPath (Join-Path $AutoCadDir "AcMgd.dll"))) {
    throw "AutoCAD 2024 managed assemblies not found under $AutoCadDir"
}

# Passed through the environment: a -p: value whose path ends in a backslash would
# escape the closing quote, which silently drops the Autodesk references.
$env:AutoCadDir = $AutoCadDir.TrimEnd('\') + '\'
& $Dotnet build $project -c Release --nologo
if ($LASTEXITCODE -ne 0) { throw "Build failed." }

New-Item -ItemType Directory -Path $contentRoot -Force | Out-Null
$manifest = [xml](Get-Content -LiteralPath (Join-Path $pluginRoot "packaging2024/PackageContents.xml") -Raw -Encoding UTF8)
$manifest.ApplicationPackage.SetAttribute("AppVersion", "$Version.0")
$manifest.ApplicationPackage.SetAttribute("ProductCode", ([guid]::NewGuid().ToString('B').ToUpperInvariant()))
$manifest.Save((Join-Path $bundleRoot "PackageContents.xml"))

# System.Text.Json and its dependencies ship in the bundle because .NET Framework
# does not provide them; the 2026 build gets them from the shared framework.
$required = @(
    "Himec.AutoCad2024.dll", "Himec.ChangeCore.dll",
    "NAudio.dll", "NAudio.Core.dll", "NAudio.WinMM.dll",
    "System.Text.Json.dll", "System.Text.Encodings.Web.dll",
    "System.Memory.dll", "System.Buffers.dll",
    "System.Runtime.CompilerServices.Unsafe.dll",
    "System.Threading.Tasks.Extensions.dll", "System.ValueTuple.dll",
    "Microsoft.Bcl.AsyncInterfaces.dll", "System.Numerics.Vectors.dll"
)
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $binaryRoot $name))) { throw "Missing build output: $name" }
}
Get-ChildItem -LiteralPath $binaryRoot -File | Where-Object { $_.Extension -eq ".dll" } |
    ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $contentRoot $_.Name) }

Write-Output "Bundle: $bundleRoot"
Get-ChildItem -LiteralPath $contentRoot -File | Get-FileHash -Algorithm SHA256 |
    Select-Object @{Name="File";Expression={Split-Path -Leaf $_.Path}}, Hash

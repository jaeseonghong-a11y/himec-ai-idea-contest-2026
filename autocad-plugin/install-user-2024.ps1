# Installs the AutoCAD 2024 bundle for the current user only (no admin rights).
# The 2026 installer (install-user.ps1) is unchanged and targets a different
# folder, so both versions can stay installed side by side.
param(
    [Parameter(Mandatory = $true)][string]$BundlePath,
    [string]$DestinationRoot = (Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Autodesk\ApplicationPlugins')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (Get-Process -Name acad -ErrorAction SilentlyContinue) {
    throw 'AutoCAD가 실행 중입니다. 미저장 도면을 보존하고 AutoCAD를 종료한 뒤 다시 실행하세요.'
}

$source = (Resolve-Path -LiteralPath $BundlePath).Path
if (-not (Test-Path -LiteralPath $source -PathType Container) -or
    -not $source.EndsWith('.bundle', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'BundlePath는 .bundle 폴더여야 합니다.'
}
$manifestPath = Join-Path $source 'PackageContents.xml'
$dllPath = Join-Path $source 'Contents\Windows\Himec.AutoCad2024.dll'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $dllPath -PathType Leaf)) {
    throw '번들에 PackageContents.xml 또는 2024용 플러그인 DLL이 없습니다.'
}
$manifest = [xml](Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8)
if ($manifest.ApplicationPackage.Components.RuntimeRequirements.Platform -ne 'AutoCAD' -or
    $manifest.ApplicationPackage.Components.RuntimeRequirements.SeriesMin -ne 'R24.3') {
    throw '이 설치 스크립트는 AutoCAD 2024(R24.3) 번들만 허용합니다.'
}

$root = [IO.Path]::GetFullPath($DestinationRoot)
New-Item -ItemType Directory -Path $root -Force | Out-Null
$target = Join-Path $root 'Himec.ChangeLoop2024.bundle'
$staging = Join-Path $root ('.himec2024-stage-' + [guid]::NewGuid().ToString('N'))
if ([IO.Path]::GetFullPath($source).TrimEnd('\') -eq [IO.Path]::GetFullPath($target).TrimEnd('\')) {
    throw '설치 원본과 대상이 같습니다. 새 버전의 별도 번들 경로를 지정하세요.'
}
Copy-Item -LiteralPath $source -Destination $staging -Recurse
$backup = $null
try {
    if (Test-Path -LiteralPath $target) {
        $backupRoot = Join-Path $root '.himec-backups'
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        $backup = Join-Path $backupRoot ('Himec.ChangeLoop2024-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
        Move-Item -LiteralPath $target -Destination $backup
    }
    Move-Item -LiteralPath $staging -Destination $target
}
catch {
    if ($backup -and (Test-Path -LiteralPath $backup) -and -not (Test-Path -LiteralPath $target)) {
        Move-Item -LiteralPath $backup -Destination $target
    }
    throw
}

[pscustomobject]@{
    InstalledVersion = $manifest.ApplicationPackage.AppVersion
    InstalledPath = $target
    DllSha256 = (Get-FileHash -LiteralPath (Join-Path $target 'Contents\Windows\Himec.AutoCad2024.dll') -Algorithm SHA256).Hash
    PreviousVersionBackup = $backup
    NextStep = 'AutoCAD 2024를 다시 열고 HIMEC 명령을 시험하세요. SECURELOAD는 낮추지 마세요.'
} | Format-List

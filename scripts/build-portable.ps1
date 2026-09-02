#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidatePattern('^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$')]
    [string]$Version = '1.0.0',

    [switch]$SkipDependencies,
    [switch]$SkipFrontendBuild,
    [switch]$SkipSeed,
    [switch]$SkipPyInstaller,
    [switch]$SkipDesktopBuild,
    [switch]$SkipBranding,
    [switch]$SkipAudit,
    [switch]$SkipArchive,

    [string]$ReleaseRequirements = 'backend\requirements-release.txt',
    [string]$BackendSpec = 'backend\lingguide-backend.spec',
    [string]$SeedScript = 'backend\tools\build_release_seed.py',
    [string]$SeedDirectory,
    [string]$FrontendVisitorDirectory = 'frontend-visitor',
    [string]$FrontendAdminDirectory = 'frontend-admin',
    [string]$DesktopDirectory = 'desktop',
    [string]$DesktopBuildScript = 'build:dir',
    [string]$BackendDistributionDirectory = 'backend\dist\lingguide-backend',
    [string]$DesktopDistributionDirectory = 'desktop\dist\win-unpacked',
    [string]$PythonCommand,
    [string]$NodeCommand = 'node.exe',
    [string]$NpmCommand = 'npm.cmd',
    [string]$OutputRoot = 'release',
    [string]$ReuseDirectory = 'release\.build-cache',
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Resolve-ProjectPath {
    param([Parameter(Mandatory)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $script:ProjectRoot $Path))
}

function Assert-Path {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Description,
        [ValidateSet('Leaf', 'Container')][string]$Type = 'Leaf'
    )
    $pathType = if ($Type -eq 'Leaf') { [Microsoft.PowerShell.Commands.TestPathType]::Leaf } else { [Microsoft.PowerShell.Commands.TestPathType]::Container }
    if (-not (Test-Path -LiteralPath $Path -PathType $pathType)) {
        throw "$Description 不存在：$Path"
    }
}

function Assert-Command {
    param([Parameter(Mandatory)][string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        throw "未找到命令：$Name"
    }
    return $command.Source
}

function Invoke-External {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][string]$Description
    )
    Write-Host "==> $Description"
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$Description 失败，退出码 $LASTEXITCODE。"
        }
    }
    finally {
        Pop-Location
    }
}

function Copy-DirectoryContents {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination,
        [string[]]$ExcludedTopLevelNames = @()
    )
    Assert-Path -Path $Source -Description '复制源目录' -Type Container
    [System.IO.Directory]::CreateDirectory($Destination) | Out-Null
    $excluded = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $ExcludedTopLevelNames | ForEach-Object { [void]$excluded.Add($_) }
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        if ($excluded.Contains($item.Name)) {
            continue
        }
        Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $Destination $item.Name) -Recurse -Force
    }
}

function Expand-Template {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination,
        [Parameter(Mandatory)][hashtable]$Tokens
    )
    $content = [System.IO.File]::ReadAllText($Source, [System.Text.Encoding]::UTF8)
    foreach ($token in $Tokens.GetEnumerator()) {
        $content = $content.Replace("{{$($token.Key)}}", [string]$token.Value)
    }
    [System.IO.File]::WriteAllText($Destination, $content, [System.Text.UTF8Encoding]::new($false))
}

$script:ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$outputRootPath = Resolve-ProjectPath $OutputRoot
$cacheRoot = Resolve-ProjectPath $ReuseDirectory
$portableName = "LingGuide-Portable-$Version-win-x64"
$portableDirectory = Join-Path $outputRootPath $portableName
$archivePath = Join-Path $outputRootPath "$portableName.zip"
$hashPath = "$archivePath.sha256"
$hashListPath = Join-Path $outputRootPath 'SHA256SUMS.txt'
$venvDirectory = Join-Path $cacheRoot 'backend-venv'
$venvPython = Join-Path $venvDirectory 'Scripts\python.exe'
$seedOutput = if ($SeedDirectory) { Resolve-ProjectPath $SeedDirectory } else { Join-Path $cacheRoot 'seed' }

$visitorDirectory = Resolve-ProjectPath $FrontendVisitorDirectory
$adminDirectory = Resolve-ProjectPath $FrontendAdminDirectory
$desktopDirectory = Resolve-ProjectPath $DesktopDirectory
$requirementsPath = Resolve-ProjectPath $ReleaseRequirements
$specPath = Resolve-ProjectPath $BackendSpec
$seedScriptPath = Resolve-ProjectPath $SeedScript
$backendDistribution = Resolve-ProjectPath $BackendDistributionDirectory
$desktopDistribution = Resolve-ProjectPath $DesktopDistributionDirectory
$brandingDirectory = Join-Path $script:ProjectRoot 'release\branding'
$templateDirectory = Join-Path $script:ProjectRoot 'release\templates'

[System.IO.Directory]::CreateDirectory($outputRootPath) | Out-Null
[System.IO.Directory]::CreateDirectory($cacheRoot) | Out-Null

$nodeExecutable = Assert-Command $NodeCommand
$npmExecutable = Assert-Command $NpmCommand
Invoke-External -FilePath $nodeExecutable -Arguments @('--version') -WorkingDirectory $script:ProjectRoot -Description '检查 Node.js'

if ([Environment]::Is64BitOperatingSystem -eq $false) {
    throw '便携版只支持 Windows x64 构建主机。'
}
if (-not $PythonCommand) {
    if (Get-Command 'python' -ErrorAction SilentlyContinue) {
        $PythonCommand = 'python'
    }
    elseif (Get-Command 'py' -ErrorAction SilentlyContinue) {
        $PythonCommand = 'py'
    }
    else {
        throw '未找到 Python（python 或 py）。'
    }
}
$pythonExecutable = Assert-Command $PythonCommand
$pythonPrefixArguments = if ([System.IO.Path]::GetFileNameWithoutExtension($pythonExecutable) -ieq 'py') { @('-3') } else { @() }
Invoke-External -FilePath $pythonExecutable -Arguments ($pythonPrefixArguments + @('--version')) -WorkingDirectory $script:ProjectRoot -Description '检查 Python'

foreach ($frontend in @(
    @{ Name = '游客端'; Path = $visitorDirectory },
    @{ Name = '管理端'; Path = $adminDirectory }
)) {
    Assert-Path -Path (Join-Path $frontend.Path 'package-lock.json') -Description "$($frontend.Name) package-lock.json"
    if (-not $SkipDependencies -and -not $SkipFrontendBuild) {
        Invoke-External -FilePath $npmExecutable -Arguments @('ci', '--no-audit', '--no-fund') -WorkingDirectory $frontend.Path -Description "$($frontend.Name) npm ci"
    }
    if (-not $SkipFrontendBuild) {
        Invoke-External -FilePath $npmExecutable -Arguments @('run', 'build', '--', '--mode', 'portable') -WorkingDirectory $frontend.Path -Description "$($frontend.Name)构建"
    }
    Assert-Path -Path (Join-Path $frontend.Path 'dist\index.html') -Description "$($frontend.Name)构建产物"
}

Assert-Path -Path $requirementsPath -Description '后端发布依赖清单'
Assert-Path -Path $specPath -Description 'PyInstaller spec'
Assert-Path -Path $seedScriptPath -Description '发布种子脚本'

if (-not $SkipDependencies) {
    if (Test-Path -LiteralPath $venvDirectory) {
        Remove-Item -LiteralPath $venvDirectory -Recurse -Force
    }
    Invoke-External -FilePath $pythonExecutable -Arguments ($pythonPrefixArguments + @('-m', 'venv', $venvDirectory)) -WorkingDirectory $script:ProjectRoot -Description '创建隔离后端 venv'
    Assert-Path -Path $venvPython -Description 'venv Python'
    Invoke-External -FilePath $venvPython -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '--requirement', $requirementsPath) -WorkingDirectory $script:ProjectRoot -Description '安装后端发布依赖'
}
else {
    Assert-Path -Path $venvPython -Description '复用的 venv Python'
    Invoke-External -FilePath $venvPython -Arguments @('-m', 'pip', 'check') -WorkingDirectory $script:ProjectRoot -Description '检查复用 venv 依赖'
}
Invoke-External -FilePath $venvPython -Arguments @('-c', 'import PyInstaller; print(PyInstaller.__version__)') -WorkingDirectory $script:ProjectRoot -Description '检查 PyInstaller'

if (-not $SkipSeed) {
    if (Test-Path -LiteralPath $seedOutput) {
        Remove-Item -LiteralPath $seedOutput -Recurse -Force
    }
    [System.IO.Directory]::CreateDirectory($seedOutput) | Out-Null
    Invoke-External -FilePath $venvPython -Arguments @($seedScriptPath, '--output-dir', $seedOutput) -WorkingDirectory (Join-Path $script:ProjectRoot 'backend') -Description '生成只读发布种子'
}
Assert-Path -Path $seedOutput -Description '发布种子产物' -Type Container
if (@(Get-ChildItem -LiteralPath $seedOutput -File -Recurse).Count -eq 0) {
    throw "发布种子目录为空：$seedOutput"
}

if (-not $SkipPyInstaller) {
    Invoke-External -FilePath $venvPython -Arguments @('-m', 'PyInstaller', '--noconfirm', '--clean', $specPath) -WorkingDirectory (Join-Path $script:ProjectRoot 'backend') -Description '构建后端 sidecar'
}
Assert-Path -Path (Join-Path $backendDistribution 'lingguide-backend.exe') -Description '后端 sidecar 构建产物'

if (-not $SkipBranding) {
    & (Join-Path $PSScriptRoot 'generate-branding.ps1') -OutputDirectory $brandingDirectory -Force
}
Assert-Path -Path (Join-Path $brandingDirectory 'lingguide-icon.ico') -Description '品牌 ICO'
Assert-Path -Path (Join-Path $brandingDirectory 'lingguide-icon.png') -Description '品牌 PNG'

Assert-Path -Path (Join-Path $desktopDirectory 'package-lock.json') -Description '桌面端 package-lock.json'
if (-not $SkipDependencies -and -not $SkipDesktopBuild) {
    Invoke-External -FilePath $npmExecutable -Arguments @('ci', '--no-audit', '--no-fund') -WorkingDirectory $desktopDirectory -Description '桌面端 npm ci'
}
if (-not $SkipDesktopBuild) {
    $previousEnvironment = @{}
    $buildEnvironment = [ordered]@{
        LINGGUIDE_BACKEND_SOURCE = $backendDistribution
        LINGGUIDE_VISITOR_SOURCE = (Join-Path $visitorDirectory 'dist')
        LINGGUIDE_ADMIN_SOURCE = (Join-Path $adminDirectory 'dist')
        LINGGUIDE_SEED_SOURCE = $seedOutput
        LINGGUIDE_BRANDING_DIR = $brandingDirectory
    }
    try {
        foreach ($entry in $buildEnvironment.GetEnumerator()) {
            $previousEnvironment[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, 'Process')
            [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
        }
        Invoke-External -FilePath $npmExecutable -Arguments @('run', $DesktopBuildScript) -WorkingDirectory $desktopDirectory -Description '构建桌面端目录包'
    }
    finally {
        foreach ($entry in $previousEnvironment.GetEnumerator()) {
            [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
        }
    }
}
Assert-Path -Path $desktopDistribution -Description '桌面端 win-unpacked 产物' -Type Container

if (Test-Path -LiteralPath $portableDirectory) {
    if (-not $Force) {
        throw "目标发布目录已存在；如需覆盖请使用 -Force：$portableDirectory"
    }
    Remove-Item -LiteralPath $portableDirectory -Recurse -Force
}
[System.IO.Directory]::CreateDirectory($portableDirectory) | Out-Null

# 顶层只接收 electron-builder 的 allowlist；资源目录由下面的显式四类资源重建。
$desktopTopLevelAllowlist = @('LingGuide.exe', 'chrome_100_percent.pak', 'chrome_200_percent.pak', 'd3dcompiler_47.dll', 'ffmpeg.dll', 'icudtl.dat', 'libEGL.dll', 'libGLESv2.dll', 'LICENSE.electron.txt', 'LICENSES.chromium.html', 'resources.pak', 'snapshot_blob.bin', 'v8_context_snapshot.bin', 'vk_swiftshader.dll', 'vk_swiftshader_icd.json', 'vulkan-1.dll')
foreach ($name in $desktopTopLevelAllowlist) {
    $source = Join-Path $desktopDistribution $name
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        Copy-Item -LiteralPath $source -Destination $portableDirectory -Force
    }
}
Assert-Path -Path (Join-Path $portableDirectory 'LingGuide.exe') -Description '组装后的主程序'

$desktopLocales = Join-Path $desktopDistribution 'locales'
if (Test-Path -LiteralPath $desktopLocales -PathType Container) {
    Copy-Item -LiteralPath $desktopLocales -Destination $portableDirectory -Recurse -Force
}

$resourcesDirectory = Join-Path $portableDirectory 'resources'
[System.IO.Directory]::CreateDirectory($resourcesDirectory) | Out-Null
$desktopAppArchive = Join-Path $desktopDistribution 'resources\app.asar'
Assert-Path -Path $desktopAppArchive -Description '桌面端 app.asar'
Copy-Item -LiteralPath $desktopAppArchive -Destination $resourcesDirectory -Force
Copy-DirectoryContents -Source $backendDistribution -Destination (Join-Path $resourcesDirectory 'backend')
Copy-DirectoryContents -Source (Join-Path $visitorDirectory 'dist') -Destination (Join-Path $resourcesDirectory 'web\visitor')
Copy-DirectoryContents -Source (Join-Path $adminDirectory 'dist') -Destination (Join-Path $resourcesDirectory 'web\admin')
Copy-DirectoryContents -Source $seedOutput -Destination (Join-Path $resourcesDirectory 'seed')

$lingGuideData = Join-Path $portableDirectory 'LingGuideData'
[System.IO.Directory]::CreateDirectory($lingGuideData) | Out-Null
[System.IO.File]::WriteAllText(
    (Join-Path $lingGuideData 'README.txt'),
    "此目录保存灵境导游运行数据，请勿删除。`r`n",
    [System.Text.UTF8Encoding]::new($true)
)

$readmeTemplate = Join-Path $templateDirectory 'README.zh-CN.md'
$noticeTemplate = Join-Path $templateDirectory 'THIRD-PARTY-NOTICES.txt'
Assert-Path -Path $readmeTemplate -Description '中文运行说明模板'
Assert-Path -Path $noticeTemplate -Description '第三方声明模板'
$archiveName = "$portableName.zip"
Expand-Template -Source $readmeTemplate -Destination (Join-Path $portableDirectory 'README.zh-CN.md') -Tokens @{
    VERSION = $Version
    BUILD_DATE = [DateTime]::Now.ToString('yyyy-MM-dd')
    ARCHIVE_NAME = $archiveName
}
Copy-Item -LiteralPath $noticeTemplate -Destination (Join-Path $portableDirectory 'THIRD-PARTY-NOTICES.txt') -Force

if (-not $SkipAudit) {
    & (Join-Path $PSScriptRoot 'audit-release.ps1') -ReleaseDirectory $portableDirectory
}

if (-not $SkipArchive) {
    foreach ($path in @($archivePath, $hashPath)) {
        if (Test-Path -LiteralPath $path) {
            if (-not $Force) {
                throw "归档产物已存在；如需覆盖请使用 -Force：$path"
            }
            Remove-Item -LiteralPath $path -Force
        }
    }
    Compress-Archive -LiteralPath $portableDirectory -DestinationPath $archivePath -CompressionLevel Optimal
    $hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $hashLine = "$hash  $archiveName`r`n"
    [System.IO.File]::WriteAllText($hashPath, $hashLine, [System.Text.Encoding]::ASCII)
    [System.IO.File]::WriteAllText($hashListPath, $hashLine, [System.Text.Encoding]::ASCII)
    Write-Host "发布完成：$portableDirectory"
    Write-Host "压缩包：$archivePath"
    Write-Host "SHA256：$hash"
}
else {
    Write-Host "发布目录组装完成（已跳过归档）：$portableDirectory"
}

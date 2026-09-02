#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ReleaseDirectory,

    [long]$MaximumBytes = 500MB,

    [string[]]$RequiredPaths = @(
        'LingGuide.exe',
        'LingGuideData/README.txt',
        'README.zh-CN.md',
        'THIRD-PARTY-NOTICES.txt',
        'icudtl.dat',
        'resources.pak',
        'locales',
        'resources/app.asar',
        'resources/backend/lingguide-backend.exe',
        'resources/backend/_internal',
        'resources/web/visitor/index.html',
        'resources/web/admin/index.html',
        'resources/seed/lingguide.db',
        'resources/seed/faqs.json',
        'resources/seed/manifest.json'
    ),

    [string[]]$AllowedDatabasePaths = @(
        'resources/seed/lingguide.db'
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Convert-ToRelativePath {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Path
    )

    $rootWithSeparator = $Root.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $rootUri = [Uri]::new($rootWithSeparator)
    $pathUri = [Uri]::new($Path)
    return [Uri]::UnescapeDataString($rootUri.MakeRelativeUri($pathUri).ToString()).Replace('\', '/')
}

function Add-AuditFailure {
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.Generic.List[string]]$Failures,
        [Parameter(Mandatory)][string]$Message
    )

    $Failures.Add($Message)
    Write-Error -Message $Message -ErrorAction Continue
}

$root = [System.IO.Path]::GetFullPath($ReleaseDirectory).TrimEnd('\', '/')
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw "发布目录不存在：$root"
}
if ($MaximumBytes -le 0) {
    throw 'MaximumBytes 必须大于 0。'
}

$failures = [System.Collections.Generic.List[string]]::new()
foreach ($requiredPath in $RequiredPaths) {
    $candidate = Join-Path $root ($requiredPath.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    if (-not (Test-Path -LiteralPath $candidate)) {
        Add-AuditFailure -Failures $failures -Message "缺少必需文件或目录：$requiredPath"
    }
}

$files = @(Get-ChildItem -LiteralPath $root -File -Recurse -Force)
$directories = @(Get-ChildItem -LiteralPath $root -Directory -Recurse -Force)
$totalBytes = [long](($files | Measure-Object -Property Length -Sum).Sum)
if ($totalBytes -gt $MaximumBytes) {
    Add-AuditFailure -Failures $failures -Message (
        '发布目录体积 {0:N2} MB 超过门禁 {1:N2} MB。' -f ($totalBytes / 1MB), ($MaximumBytes / 1MB)
    )
}

foreach ($directory in $directories) {
    $relative = Convert-ToRelativePath -Root $root -Path $directory.FullName
    $segments = $relative -split '/'
    if ($segments -contains 'node_modules') {
        Add-AuditFailure -Failures $failures -Message "禁止包含 node_modules：$relative"
    }
    if ($segments | Where-Object { $_ -match '^(?i:logs?)$' }) {
        Add-AuditFailure -Failures $failures -Message "禁止包含日志目录：$relative"
    }
}

$allowedDatabases = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($path in $AllowedDatabasePaths) {
    [void]$allowedDatabases.Add($path.Replace('\', '/').TrimStart('/'))
}

$videoExtensions = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts') | ForEach-Object { [void]$videoExtensions.Add($_) }
$modelExtensions = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@('.onnx', '.pt', '.pth', '.ckpt', '.safetensors', '.gguf', '.ggml', '.tflite', '.pb', '.h5', '.hdf5', '.bin') | ForEach-Object { [void]$modelExtensions.Add($_) }
$databaseExtensions = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@('.db', '.sqlite', '.sqlite3') | ForEach-Object { [void]$databaseExtensions.Add($_) }
$textExtensions = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@(
    '.txt', '.md', '.json', '.jsonl', '.xml', '.html', '.htm', '.css', '.js', '.cjs', '.mjs', '.map',
    '.ts', '.tsx', '.jsx', '.vue', '.py', '.pyi', '.ini', '.cfg', '.conf', '.toml', '.yaml', '.yml',
    '.csv', '.tsv', '.properties', '.license', '.notice', '.pem', '.crt', '.cer', '.bat', '.cmd', '.ps1'
) | ForEach-Object { [void]$textExtensions.Add($_) }

$credentialPatterns = [ordered]@{
    'PEM 私钥' = '-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'
    'AWS Access Key' = '(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])'
    'GitHub Token' = '(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'
    'Bearer Token' = '(?i)\bAuthorization\s*[:=]\s*["'']?Bearer\s+[A-Za-z0-9._~+/-]{16,}'
    'JWT' = '(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])'
    '凭据赋值' = '(?im)^\s*["'']?(?:[A-Z0-9_]*(?:API_?KEY|APP_?SECRET|ACCESS_?TOKEN|ACCESS_?KEY(?:_ID|_SECRET)?|CLIENT_?SECRET|PASSWORD|PASSWD|TOKEN|SECRET)[A-Z0-9_]*)["'']?\s*[:=]\s*["'']?(?!\s*(?:$|change-me\b|not-needed\b|none\b|null\b|example\b|placeholder\b|your[-_ ]|<[^>]+>|\$\{|process\.env|os\.getenv|env\.|settings\.))[A-Za-z0-9+/=_.,:@%!-]{8,}'
}

foreach ($file in $files) {
    $relative = Convert-ToRelativePath -Root $root -Path $file.FullName
    $segments = $relative -split '/'
    $extension = $file.Extension.ToLowerInvariant()

    if ($file.Name -eq '.env' -or $file.Name -like '.env.*') {
        Add-AuditFailure -Failures $failures -Message "禁止包含环境文件：$relative"
    }
    if ($segments -contains 'node_modules') {
        Add-AuditFailure -Failures $failures -Message "禁止包含 node_modules 文件：$relative"
    }
    if ($segments | Where-Object { $_ -match '^(?i:logs?)$' }) {
        Add-AuditFailure -Failures $failures -Message "禁止包含日志文件：$relative"
    }
    if ($extension -in @('.log', '.trace')) {
        Add-AuditFailure -Failures $failures -Message "禁止包含日志/跟踪文件：$relative"
    }
    if ($videoExtensions.Contains($extension)) {
        Add-AuditFailure -Failures $failures -Message "禁止包含视频：$relative"
    }
    $electronRuntimeBinary = $relative -in @('snapshot_blob.bin', 'v8_context_snapshot.bin')
    if ($modelExtensions.Contains($extension) -and -not $electronRuntimeBinary) {
        Add-AuditFailure -Failures $failures -Message "禁止包含模型权重：$relative"
    }
    if ($databaseExtensions.Contains($extension) -and -not $allowedDatabases.Contains($relative)) {
        Add-AuditFailure -Failures $failures -Message "禁止包含未授权数据库：$relative"
    }

    if ($textExtensions.Contains($extension)) {
        if ($file.Length -gt 10MB) {
            $knownLargeText = $relative -eq 'LICENSES.chromium.html' -or $relative.StartsWith('resources/backend/_internal/snownlp/')
            if (-not $knownLargeText) {
                Add-AuditFailure -Failures $failures -Message "未知文本文件超过 10 MB，拒绝凭据扫描：$relative"
            }
            continue
        }
        $content = [System.IO.File]::ReadAllText($file.FullName)
        foreach ($entry in $credentialPatterns.GetEnumerator()) {
            if ([regex]::IsMatch($content, [string]$entry.Value)) {
                Add-AuditFailure -Failures $failures -Message "发现疑似$($entry.Key)：$relative"
            }
        }
    }
}

if ($failures.Count -gt 0) {
    throw "发布审计失败，共 $($failures.Count) 项。"
}

Write-Host ('发布审计通过：{0} 个文件，{1:N2} MB。' -f $files.Count, ($totalBytes / 1MB))

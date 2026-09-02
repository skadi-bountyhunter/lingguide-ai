#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$PortableDirectory,

    [string]$ExecutableName = 'LingGuide.exe',

    [ValidateRange(5, 300)]
    [int]$TimeoutSeconds = 90,

    [ValidateRange(1, 30)]
    [int]$ShutdownTimeoutSeconds = 10,

    [switch]$SkipHttpCheck,

    [switch]$KeepRunning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Read-NewLogText {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][ref]$Position
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return ''
    }
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        if ($Position.Value -gt $stream.Length) {
            $Position.Value = 0L
        }
        [void]$stream.Seek([long]$Position.Value, [System.IO.SeekOrigin]::Begin)
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8, $true, 4096, $true)
        try {
            $text = $reader.ReadToEnd()
            $Position.Value = $stream.Position
            return $text
        }
        finally {
            $reader.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

function Stop-StartedProcess {
    param(
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)][int]$TimeoutSeconds
    )

    $Process.Refresh()
    if ($Process.HasExited) {
        return
    }

    Write-Host "正在优雅关闭启动 PID $($Process.Id)..."
    $closeRequested = $false
    try { $closeRequested = $Process.CloseMainWindow() } catch { $closeRequested = $false }
    if ($closeRequested -and $Process.WaitForExit($TimeoutSeconds * 1000)) {
        return
    }

    $Process.Refresh()
    if (-not $Process.HasExited) {
        Write-Warning "PID $($Process.Id) 未在 ${TimeoutSeconds}s 内退出，将仅终止该启动 PID。"
        Stop-Process -Id $Process.Id -Force -ErrorAction Stop
        [void]$Process.WaitForExit(5000)
    }
}

$root = [System.IO.Path]::GetFullPath($PortableDirectory)
$executable = Join-Path $root $ExecutableName
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "便携版主程序不存在：$executable"
}

$smokeDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("LingGuide-Smoke-{0}" -f [Guid]::NewGuid().ToString('N'))
[System.IO.Directory]::CreateDirectory($smokeDirectory) | Out-Null
$stdoutPath = Join-Path $smokeDirectory 'stdout.log'
$stderrPath = Join-Path $smokeDirectory 'stderr.log'
$desktopLogPath = Join-Path $root 'LingGuideData\logs\desktop.log'
$stdoutPosition = 0L
$stderrPosition = 0L
$desktopLogPosition = if (Test-Path -LiteralPath $desktopLogPath) { (Get-Item -LiteralPath $desktopLogPath).Length } else { 0L }
$combinedLog = ''
$ready = $null
$startedProcess = $null

try {
    $startedProcess = Start-Process -FilePath $executable -WorkingDirectory $root -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    Write-Host "已启动 PID $($startedProcess.Id)，等待 LINGGUIDE_READY 日志..."
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 250
        $startedProcess.Refresh()
        $newText = (Read-NewLogText -Path $stdoutPath -Position ([ref]$stdoutPosition)) + (Read-NewLogText -Path $stderrPath -Position ([ref]$stderrPosition)) + (Read-NewLogText -Path $desktopLogPath -Position ([ref]$desktopLogPosition))
        if ($newText) {
            $combinedLog += $newText
            if ($combinedLog.Length -gt 1MB) {
                $combinedLog = $combinedLog.Substring($combinedLog.Length - 1MB)
            }
            $matches = [regex]::Matches($combinedLog, 'LINGGUIDE_READY\s+(\{[^\r\n]+\})')
            if ($matches.Count -gt 0) {
                try {
                    $ready = $matches[$matches.Count - 1].Groups[1].Value | ConvertFrom-Json -ErrorAction Stop
                }
                catch {
                    throw 'LINGGUIDE_READY 日志后的 JSON 无效。'
                }
                break
            }
        }
        if ($startedProcess.HasExited) {
            throw "主程序在就绪前退出，退出码 $($startedProcess.ExitCode)。日志目录：$smokeDirectory"
        }
    }

    if ($null -eq $ready) {
        throw "等待 LINGGUIDE_READY 超时（${TimeoutSeconds}s）。日志目录：$smokeDirectory"
    }
    $port = 0
    if (-not [int]::TryParse([string]$ready.port, [ref]$port) -or $port -lt 1 -or $port -gt 65535) {
        throw 'LINGGUIDE_READY 缺少合法端口。'
    }

    if (-not $SkipHttpCheck) {
        $healthUri = "http://127.0.0.1:$port/api/health"
        $health = Invoke-RestMethod -Uri $healthUri -Method Get -TimeoutSec 10
        if ([string]$health.status -ne 'healthy') {
            throw "健康检查未返回 healthy：$healthUri"
        }
    }

    $startedProcess.Refresh()
    if ($startedProcess.HasExited) {
        throw "主程序就绪后意外退出，退出码 $($startedProcess.ExitCode)。"
    }
    Write-Host "便携版冒烟通过：PID $($startedProcess.Id)，后端端口 $port。"
}
finally {
    if ($null -ne $startedProcess -and -not $KeepRunning) {
        Stop-StartedProcess -Process $startedProcess -TimeoutSeconds $ShutdownTimeoutSeconds
    }
    if ($null -ne $startedProcess) {
        $startedProcess.Dispose()
    }
    if (Test-Path -LiteralPath $smokeDirectory) {
        Remove-Item -LiteralPath $smokeDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
}

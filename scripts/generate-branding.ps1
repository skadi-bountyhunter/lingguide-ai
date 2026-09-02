#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\release\branding'),
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Save-LingGuidePng {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][int]$Size
    )

    $bitmap = [System.Drawing.Bitmap]::new($Size, $Size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.Clear([System.Drawing.Color]::Transparent)

        $scale = $Size / 512.0
        $background = [System.Drawing.RectangleF]::new(24 * $scale, 24 * $scale, 464 * $scale, 464 * $scale)
        $cornerRadius = 112 * $scale
        $backgroundPath = [System.Drawing.Drawing2D.GraphicsPath]::new()
        try {
            $diameter = 2 * $cornerRadius
            $backgroundPath.AddArc($background.Left, $background.Top, $diameter, $diameter, 180, 90)
            $backgroundPath.AddArc($background.Right - $diameter, $background.Top, $diameter, $diameter, 270, 90)
            $backgroundPath.AddArc($background.Right - $diameter, $background.Bottom - $diameter, $diameter, $diameter, 0, 90)
            $backgroundPath.AddArc($background.Left, $background.Bottom - $diameter, $diameter, $diameter, 90, 90)
            $backgroundPath.CloseFigure()
            $backgroundBrush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
                $background,
                [System.Drawing.ColorTranslator]::FromHtml('#0F766E'),
                [System.Drawing.ColorTranslator]::FromHtml('#064E3B'),
                45.0
            )
            try { $graphics.FillPath($backgroundBrush, $backgroundPath) } finally { $backgroundBrush.Dispose() }
        }
        finally {
            $backgroundPath.Dispose()
        }

        $sunBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#FCD34D'))
        try { $graphics.FillEllipse($sunBrush, 296 * $scale, 90 * $scale, 108 * $scale, 108 * $scale) } finally { $sunBrush.Dispose() }

        $mountains = [System.Drawing.PointF[]]@(
            [System.Drawing.PointF]::new(71 * $scale, 342 * $scale),
            [System.Drawing.PointF]::new(190 * $scale, 180 * $scale),
            [System.Drawing.PointF]::new(257 * $scale, 269 * $scale),
            [System.Drawing.PointF]::new(315 * $scale, 194 * $scale),
            [System.Drawing.PointF]::new(441 * $scale, 342 * $scale),
            [System.Drawing.PointF]::new(441 * $scale, 414 * $scale),
            [System.Drawing.PointF]::new(71 * $scale, 414 * $scale)
        )
        $mountainBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#ECFDF5'))
        try { $graphics.FillPolygon($mountainBrush, $mountains) } finally { $mountainBrush.Dispose() }

        $trail = [System.Drawing.Drawing2D.GraphicsPath]::new()
        try {
            $trail.StartFigure()
            $trail.AddBezier(
                [System.Drawing.PointF]::new(245 * $scale, 438 * $scale),
                [System.Drawing.PointF]::new(237 * $scale, 378 * $scale),
                [System.Drawing.PointF]::new(250 * $scale, 336 * $scale),
                [System.Drawing.PointF]::new(284 * $scale, 312 * $scale)
            )
            $trail.AddBezier(
                [System.Drawing.PointF]::new(284 * $scale, 312 * $scale),
                [System.Drawing.PointF]::new(310 * $scale, 293 * $scale),
                [System.Drawing.PointF]::new(322 * $scale, 266 * $scale),
                [System.Drawing.PointF]::new(321 * $scale, 230 * $scale)
            )
            $trail.AddBezier(
                [System.Drawing.PointF]::new(321 * $scale, 230 * $scale),
                [System.Drawing.PointF]::new(372 * $scale, 277 * $scale),
                [System.Drawing.PointF]::new(387 * $scale, 327 * $scale),
                [System.Drawing.PointF]::new(365 * $scale, 380 * $scale)
            )
            $trail.AddBezier(
                [System.Drawing.PointF]::new(365 * $scale, 380 * $scale),
                [System.Drawing.PointF]::new(353 * $scale, 408 * $scale),
                [System.Drawing.PointF]::new(348 * $scale, 427 * $scale),
                [System.Drawing.PointF]::new(351 * $scale, 438 * $scale)
            )
            $trail.CloseFigure()
            $trailBrush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
                [System.Drawing.RectangleF]::new(238 * $scale, 230 * $scale, 150 * $scale, 208 * $scale),
                [System.Drawing.ColorTranslator]::FromHtml('#FDE68A'),
                [System.Drawing.Color]::White,
                90.0
            )
            try { $graphics.FillPath($trailBrush, $trail) } finally { $trailBrush.Dispose() }
        }
        finally {
            $trail.Dispose()
        }

        $markerBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
        try { $graphics.FillEllipse($markerBrush, 237 * $scale, 238 * $scale, 38 * $scale, 38 * $scale) } finally { $markerBrush.Dispose() }

        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

function Write-IcoFromPng {
    param(
        [Parameter(Mandatory)][string]$PngPath,
        [Parameter(Mandatory)][string]$IcoPath,
        [Parameter(Mandatory)][int]$Size
    )

    $pngBytes = [System.IO.File]::ReadAllBytes($PngPath)
    $stream = [System.IO.File]::Create($IcoPath)
    $writer = [System.IO.BinaryWriter]::new($stream)
    try {
        $encodedSize = if ($Size -ge 256) { 0 } else { $Size }
        $writer.Write([UInt16]0)
        $writer.Write([UInt16]1)
        $writer.Write([UInt16]1)
        $writer.Write([Byte]$encodedSize)
        $writer.Write([Byte]$encodedSize)
        $writer.Write([Byte]0)
        $writer.Write([Byte]0)
        $writer.Write([UInt16]1)
        $writer.Write([UInt16]32)
        $writer.Write([UInt32]$pngBytes.Length)
        $writer.Write([UInt32]22)
        $writer.Write($pngBytes)
    }
    finally {
        $writer.Dispose()
        $stream.Dispose()
    }
}

Add-Type -AssemblyName System.Drawing
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($resolvedOutput) | Out-Null
$pngPath = Join-Path $resolvedOutput 'lingguide-icon.png'
$icoPath = Join-Path $resolvedOutput 'lingguide-icon.ico'
foreach ($path in @($pngPath, $icoPath)) {
    if ((Test-Path -LiteralPath $path) -and -not $Force) {
        throw "目标文件已存在；如需覆盖请使用 -Force：$path"
    }
}

Save-LingGuidePng -Path $pngPath -Size 256
Write-IcoFromPng -PngPath $pngPath -IcoPath $icoPath -Size 256
Write-Host '已生成原创品牌资源。'
Write-Host $pngPath
Write-Host $icoPath

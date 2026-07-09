param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]] $Path,

    [string] $StageRoot = "$env:USERPROFILE\Documents\Image-Line\FL Studio\Audio\Suno Studio",

    [switch] $LaunchFL,

    [string] $FLStudioExe = ""
)

$ErrorActionPreference = "Stop"

function Resolve-FLStudioExecutable {
    param([string] $Override)

    if ($Override -and (Test-Path -LiteralPath $Override -PathType Leaf)) {
        return (Resolve-Path -LiteralPath $Override).Path
    }

    $candidates = @(
        "$env:ProgramFiles\Image-Line\FL Studio 2025\FL64.exe",
        "$env:ProgramFiles\Image-Line\FL Studio 2024\FL64.exe",
        "${env:ProgramFiles(x86)}\Image-Line\FL Studio 2025\FL64.exe",
        "${env:ProgramFiles(x86)}\Image-Line\FL Studio 2024\FL64.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

function Test-SupportedMedia {
    param([string] $FilePath)

    $ext = [System.IO.Path]::GetExtension($FilePath).ToLowerInvariant()
    return @(".wav", ".wave", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma", ".mid", ".midi") -contains $ext
}

$stageDir = New-Item -ItemType Directory -Force -Path $StageRoot
$staged = New-Object System.Collections.Generic.List[string]

foreach ($item in $Path) {
    $resolved = Resolve-Path -LiteralPath $item
    foreach ($source in $resolved) {
        if (-not (Test-Path -LiteralPath $source.Path -PathType Leaf)) {
            throw "Not a file: $($source.Path)"
        }
        if (-not (Test-SupportedMedia -FilePath $source.Path)) {
            throw "Unsupported media type: $($source.Path)"
        }

        $destination = Join-Path $stageDir.FullName ([System.IO.Path]::GetFileName($source.Path))
        Copy-Item -LiteralPath $source.Path -Destination $destination -Force
        $staged.Add((Resolve-Path -LiteralPath $destination).Path)
    }
}

if ($staged.Count -eq 0) {
    throw "No media files were staged."
}

Set-Clipboard -Value ($staged -join [Environment]::NewLine)

$flExe = Resolve-FLStudioExecutable -Override $FLStudioExe
if ($LaunchFL) {
    if (-not $flExe) {
        throw "FL Studio executable was not found. Pass -FLStudioExe to launch it."
    }
    Start-Process -FilePath $flExe -WindowStyle Hidden
}

[PSCustomObject]@{
    stagedFiles = $staged
    stageRoot = $stageDir.FullName
    clipboard = "staged file path(s)"
    flStudioExe = $flExe
    launched = [bool] $LaunchFL
} | ConvertTo-Json -Depth 3

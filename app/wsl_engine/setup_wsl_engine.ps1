param(
    [string]$Distribution = "Ubuntu-24.04"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EngineDir = $ScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $EngineDir "setup_engine.sh") -PathType Leaf)) {
    $EngineDir = Join-Path $ScriptRoot "_internal\wsl_engine"
}
if (-not (Test-Path -LiteralPath (Join-Path $EngineDir "setup_engine.sh") -PathType Leaf)) {
    throw "Bundled WSL engine scripts not found."
}
$EngineParent = Split-Path -Parent $EngineDir
$PipelineDir = Join-Path $EngineParent "retina_pipeline"
if (-not (Test-Path -LiteralPath $PipelineDir -PathType Container)) {
    $ProjectRoot = Split-Path -Parent $EngineParent
    $PipelineDir = Join-Path $ProjectRoot "retina_pipeline"
}
if (-not (Test-Path -LiteralPath $PipelineDir -PathType Container)) {
    throw "Bundled retina_pipeline directory not found."
}

$Wsl = (Get-Command "wsl.exe" -ErrorAction Stop).Source
& $Wsl -d $Distribution -u root -- bash -lc "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv build-essential curl bzip2 ca-certificates"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install WSL system prerequisites."
}

function Convert-ToWslPath([string]$WindowsPath) {
    $Resolved = [System.IO.Path]::GetFullPath($WindowsPath)
    if ($Resolved -match '^([A-Za-z]):\\(.*)$') {
        $Drive = $Matches[1].ToLowerInvariant()
        $Remainder = $Matches[2].Replace('\', '/')
        return "/mnt/$Drive/$Remainder"
    }
    $Mapped = & $Wsl -d $Distribution -- wslpath -a $WindowsPath
    if ($LASTEXITCODE -ne 0 -or -not $Mapped) {
        throw "Unable to map Windows path into WSL: $WindowsPath"
    }
    return ($Mapped | Select-Object -Last 1).Trim()
}

$SetupScript = Convert-ToWslPath (Join-Path $EngineDir "setup_engine.sh")
$PipelineRoot = Convert-ToWslPath $PipelineDir
& $Wsl -d $Distribution -- bash $SetupScript $PipelineRoot
if ($LASTEXITCODE -ne 0) {
    throw "RetinaCAD WSL Python environment setup failed."
}

Write-Host "WSL engine ready for RetinaCAD."

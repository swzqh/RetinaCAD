param(
    [switch]$InstallDependencies,
    [string]$PythonPath = "python.exe"
)

$ErrorActionPreference = "Stop"
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $AppDir
$Python = (Get-Command $PythonPath -ErrorAction Stop).Source

if ($InstallDependencies) {
    & $Python -m pip install -r (Join-Path $AppDir "requirements-build.txt")
}

& $Python -c "import PIL, tkinter"
& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed. Install requirements-build.txt or provide an offline wheel."
}

$DistDir = Join-Path $AppDir "dist"
$WorkDir = Join-Path $AppDir "build"
$SpecDir = Join-Path $AppDir "build_spec"
New-Item -ItemType Directory -Path $DistDir, $WorkDir, $SpecDir -Force | Out-Null

Push-Location $AppDir
try {
    $PyInstallerArgs = @(
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name", "RetinaCAD",
        "--distpath", $DistDir,
        "--workpath", $WorkDir,
        "--specpath", $SpecDir,
        "--add-data", "${ProjectRoot}\model;model",
        "--add-data", "${AppDir}\wsl_engine;wsl_engine",
        "--add-data", "${ProjectRoot}\retina_pipeline;retina_pipeline",
        "--collect-all", "PIL"
    )

    $AssetsDir = Join-Path $AppDir "assets"
    $IconFile = Join-Path $AssetsDir "retinacad_icon.ico"
    if (Test-Path -LiteralPath $AssetsDir) {
        $PyInstallerArgs += @("--add-data", "${AssetsDir};assets")
    }
    if (Test-Path -LiteralPath $IconFile) {
        $PyInstallerArgs += @("--icon", $IconFile)
    }
    $PyInstallerArgs += "run_app.py"

    & $Python -m PyInstaller @PyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }

    $RuntimeDir = Join-Path $DistDir "RetinaCAD"
    Copy-Item -LiteralPath (Join-Path $AppDir "RUNTIME_README.md") -Destination $RuntimeDir
    Copy-Item -LiteralPath (Join-Path $AppDir "runtime_licenses") -Destination $RuntimeDir -Recurse
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "licenses") -Destination $RuntimeDir -Recurse
    Copy-Item -LiteralPath (Join-Path $AppDir "wsl_engine\setup_wsl_engine.ps1") -Destination $RuntimeDir
}
finally {
    Pop-Location
}

Write-Host "Built: $(Join-Path $DistDir 'RetinaCAD\RetinaCAD.exe')"

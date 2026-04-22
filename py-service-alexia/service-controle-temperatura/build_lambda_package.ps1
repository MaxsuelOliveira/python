param(
    [string]$PythonExe = "python",
    [string]$BuildRoot = ".build",
    [string]$OutputZip = "dist\\service-controle-temperatura.zip"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$buildRootPath = Join-Path $projectRoot $BuildRoot
$packagePath = Join-Path $buildRootPath "package"
$outputZipPath = Join-Path $projectRoot $OutputZip
$outputDir = Split-Path -Parent $outputZipPath

if (Test-Path -LiteralPath $buildRootPath) {
    Remove-Item -LiteralPath $buildRootPath -Recurse -Force
}

if (Test-Path -LiteralPath $outputZipPath) {
    Remove-Item -LiteralPath $outputZipPath -Force
}

New-Item -ItemType Directory -Path $packagePath -Force | Out-Null
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

& $PythonExe -m pip install -r requirements.txt -t $packagePath

Copy-Item lambda_function.py $packagePath
Copy-Item run_temperature_monitor.py $packagePath
Copy-Item turn_on_office_ac.py $packagePath
Copy-Item trigger_hot_action.py $packagePath
Copy-Item -Recurse config (Join-Path $packagePath "config")

$currentLocation = Get-Location
Set-Location $packagePath
try {
    Compress-Archive -Path * -DestinationPath $outputZipPath
}
finally {
    Set-Location $currentLocation
}

Write-Host "Pacote gerado em: $outputZipPath"

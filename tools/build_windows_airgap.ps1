param(
    [string]$PythonVersion = "3.11.9"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path "."
$Bundle = Join-Path $Root "dist/windows-airgap"
$PythonDir = Join-Path $Bundle "python"
$SitePackages = Join-Path $Bundle "app/Lib/site-packages"
$Wheelhouse = Join-Path $Bundle "wheelhouse"

Remove-Item -Recurse -Force $Bundle -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $PythonDir, $SitePackages, $Wheelhouse | Out-Null

python -m pip install --upgrade pip build
python -m build --wheel

$EmbeddedZip = "python-$PythonVersion-embed-amd64.zip"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/$EmbeddedZip"
$EmbeddedZipPath = Join-Path $Bundle $EmbeddedZip

Invoke-WebRequest -Uri $PythonUrl -OutFile $EmbeddedZipPath
Expand-Archive -Path $EmbeddedZipPath -DestinationPath $PythonDir

$Wheel = Get-ChildItem -Path "dist" -Filter "sftp_watcher-*.whl" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

python -m pip download `
    --dest $Wheelhouse `
    --only-binary=:all: `
    $Wheel.FullName

python -m pip install `
    --no-index `
    --find-links $Wheelhouse `
    --target $SitePackages `
    $Wheel.FullName

$PthFile = Get-ChildItem -Path $PythonDir -Filter "python*._pth" |
    Select-Object -First 1
$PythonVersionParts = $PythonVersion -split "\."
$PythonZipName = "python$($PythonVersionParts[0])$($PythonVersionParts[1]).zip"

@"
$PythonZipName
.
..\app\Lib\site-packages
import site
"@ | Set-Content -Path $PthFile.FullName -Encoding ASCII

if (Test-Path "alembic.ini") {
    Copy-Item "alembic.ini" $Bundle
}
if (Test-Path "alembic") {
    Copy-Item "alembic" $Bundle -Recurse
}

@"
@echo off
setlocal
cd /d "%~dp0"
"%~dp0python\python.exe" -m alembic -c "%~dp0alembic.ini" upgrade head
"@ | Set-Content -Path (Join-Path $Bundle "migrate-db.bat") -Encoding ASCII

@"
@echo off
setlocal
cd /d "%~dp0"
call "%~dp0migrate-db.bat"
if errorlevel 1 exit /b %errorlevel%
"%~dp0python\python.exe" -m sftp_watcher --env-file "%~dp0.env"
"@ | Set-Content -Path (Join-Path $Bundle "run-sftp-watcher.bat") -Encoding ASCII

@"
@echo off
setlocal
"%~dp0python\python.exe" -m sftp_watcher.db_admin %*
"@ | Set-Content -Path (Join-Path $Bundle "sftp-watcher-db.bat") -Encoding ASCII

$env:SFTP_STATE_STORE_DIR = Join-Path $Bundle "migration-smoke-test-state"

Push-Location $Bundle
try {
    & ".\python\python.exe" -m alembic -c ".\alembic.ini" upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic migration smoke test failed"
    }
}
finally {
    Pop-Location
    Remove-Item -Recurse -Force $env:SFTP_STATE_STORE_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:SFTP_STATE_STORE_DIR -ErrorAction SilentlyContinue
}

Compress-Archive `
    -Path (Join-Path $Bundle "*") `
    -DestinationPath "dist/sftp-watcher-windows-airgap.zip" `
    -Force

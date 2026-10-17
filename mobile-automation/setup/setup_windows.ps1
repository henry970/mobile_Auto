# ------------------------------------------------------------------
# One-command setup for Windows 10/11.
# Right-click PowerShell > Run as Administrator, cd to the project folder, then:
#   Set-ExecutionPolicy -Scope Process Bypass -Force; .\setup\setup_windows.ps1
# Safe to run more than once — it skips anything already installed.
# ------------------------------------------------------------------
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Has($cmd)  { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

if (-not (Has winget)) {
    Write-Host "winget is missing. Install 'App Installer' from the Microsoft Store, then re-run." -ForegroundColor Red
    exit 1
}

Step "Python"
if (-not (Has python)) { winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements; Refresh-Path }

Step "Node.js LTS"
if (-not (Has node)) { winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements; Refresh-Path }

Step "Java 17"
if (-not $env:JAVA_HOME) {
    winget install -e --id EclipseAdoptium.Temurin.17.JDK --accept-source-agreements --accept-package-agreements
    $jdk = Get-ChildItem "C:\Program Files\Eclipse Adoptium" -Directory -Filter "jdk-17*" | Select-Object -First 1
    if ($jdk) {
        [Environment]::SetEnvironmentVariable("JAVA_HOME", $jdk.FullName, "User")
        $env:JAVA_HOME = $jdk.FullName
    }
}

Step "Android SDK (platform-tools + build-tools)"
$Sdk = $env:ANDROID_HOME
if (-not $Sdk) {
    $studioSdk = "$env:LOCALAPPDATA\Android\Sdk"
    $Sdk = if (Test-Path $studioSdk) { $studioSdk } else { "$env:USERPROFILE\Android\Sdk" }
}
$SdkManager = "$Sdk\cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path $SdkManager)) {
    New-Item -ItemType Directory -Force -Path "$Sdk\cmdline-tools" | Out-Null
    $zip = "$env:TEMP\cmdline-tools.zip"
    Invoke-WebRequest "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath "$Sdk\cmdline-tools\tmp" -Force
    Move-Item "$Sdk\cmdline-tools\tmp\cmdline-tools" "$Sdk\cmdline-tools\latest" -Force
    Remove-Item "$Sdk\cmdline-tools\tmp" -Recurse -Force
}
"y`ny`ny`ny`ny`ny`ny`n" | & $SdkManager --licenses | Out-Null
& $SdkManager "platform-tools" "build-tools;34.0.0" | Out-Null
[Environment]::SetEnvironmentVariable("ANDROID_HOME", $Sdk, "User")
$env:ANDROID_HOME = $Sdk
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*platform-tools*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$Sdk\platform-tools", "User")
}
$env:Path += ";$Sdk\platform-tools"

Step "Appium + UiAutomator2 driver"
if (-not (Has appium)) { npm install -g appium; Refresh-Path; $env:Path += ";$Sdk\platform-tools" }
$drivers = appium driver list --installed 2>&1 | Out-String
if ($drivers -notmatch "uiautomator2") { appium driver install uiautomator2 }

Step "Allure report tool"
if (-not (Has allure)) { npm install -g allure-commandline; Refresh-Path }

Step "Python virtual environment + packages"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -q

Step "Demo app (ApiDemos) for the sample tests"
New-Item -ItemType Directory -Force -Path "apps" | Out-Null
if (-not (Test-Path "apps\ApiDemos-debug.apk")) {
    $rel = Invoke-RestMethod "https://api.github.com/repos/appium/android-apidemos/releases/latest"
    $asset = $rel.assets | Where-Object { $_.name -eq "ApiDemos-debug.apk" } | Select-Object -First 1
    Invoke-WebRequest $asset.browser_download_url -OutFile "apps\ApiDemos-debug.apk"
}

Step "Checking everything"
& .\.venv\Scripts\python.exe check_setup.py
Write-Host "`nSetup finished. Close and reopen your terminal once so the new PATH is picked up." -ForegroundColor Green

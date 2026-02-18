@echo off
set "LOG_FILE=build_log.txt"
if "%~1"=="_run" goto main

powershell -NoProfile -Command "cmd /c \"\"%~f0\" _run\" 2>&1 | Tee-Object -FilePath \"%LOG_FILE%\"; exit $LASTEXITCODE"
exit /b %errorlevel%

:main
REM Build script for Helldivers Numpad Macros
REM This script builds the EXE with PyInstaller and creates an installer with Inno Setup

echo ============================================
echo Helldivers Numpad Macros - Build Script
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause < con
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause < con
        exit /b 1
    )
)

echo.
echo [Step 1/3] Cleaning previous build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "HelldiversNumpadMacros.spec" del "HelldiversNumpadMacros.spec"

echo.
echo [Step 2/3] Building EXE with PyInstaller...
echo This may take a few minutes...

pyinstaller --noconfirm --onefile --windowed ^
    --name "HelldiversNumpadMacros" ^
    --add-data "assets;assets" ^
    --add-data "src/core/stratagem_data.py;." ^
    --add-data "src/config/version.py;." ^
    --add-data "src/managers/update_checker.py;." ^
    --add-data "src/ui/theme_dark_default.qss;." ^
    --add-data "src/ui/theme_dark_blue.qss;." ^
    --add-data "src/ui/theme_dark_red.qss;." ^
    --icon "assets/icon.ico" ^
    --manifest "app.manifest" ^
    main.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause < con
    exit /b 1
)

echo.
echo [Success] EXE created: dist\HelldiversNumpadMacros.exe

REM Read version from version.py as single source of truth
for /f "tokens=2 delims== " %%A in ('findstr /r /c:"^VERSION[ ]*=" src\config\version.py') do set "APP_VERSION=%%~A"
if "%APP_VERSION%"=="" set "APP_VERSION=unknown"
echo Detected app version: %APP_VERSION%

REM Sync installer version to match version.py
powershell -NoProfile -Command "& { $q = [char]34; $content = Get-Content installer\installer.iss; $content = $content -replace '^#define MyAppVersion .*$', ('#define MyAppVersion ' + $q + $env:APP_VERSION + $q); Set-Content installer\installer.iss $content }"

REM Check if Inno Setup is installed
echo.
echo [Step 3/3] Creating installer with Inno Setup...

set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist "%INNO_PATH%" (
    echo.
    echo WARNING: Inno Setup not found at default location
    echo Please install Inno Setup from: https://jrsoftware.org/isdl.php
    echo.
    echo You can manually compile installer.iss after installation
    echo.
    echo Build completed: dist\HelldiversNumpadMacros.exe
    goto zip_portable
)

set "INNO_RETRIES=3"
set "INNO_TRY=1"
:inno_retry
"%INNO_PATH%" "installer.iss"

set "INSTALLER_EXE=dist\HelldiversNumpadMacros-Setup-%APP_VERSION%.exe"
if exist "%INSTALLER_EXE%" goto inno_success

if %INNO_TRY% LSS %INNO_RETRIES% (
    echo WARNING: Inno Setup failed. Retrying in 2 seconds... (%INNO_TRY%/%INNO_RETRIES%)
    set /a INNO_TRY+=1
    timeout /t 2 /nobreak >nul
    goto inno_retry
)
echo ERROR: Inno Setup compilation failed
pause < con
exit /b 1

:inno_success

REM Now rename the portable EXE after Inno Setup has used it
set "PORTABLE_EXE_OLD=dist\HelldiversNumpadMacros.exe"
set "PORTABLE_EXE_NEW=dist\HelldiversNumpadMacros-Portable-%APP_VERSION%.exe"
if exist "%PORTABLE_EXE_OLD%" (
    ren "%PORTABLE_EXE_OLD%" "HelldiversNumpadMacros-Portable-%APP_VERSION%.exe"
    echo Renamed portable EXE: %PORTABLE_EXE_NEW%
)

echo.
echo ============================================
echo Build Complete!
echo ============================================
echo.
echo Portable EXE: dist\HelldiversNumpadMacros-Portable-%APP_VERSION%.exe
echo Installer EXE: dist\HelldiversNumpadMacros-Setup-%APP_VERSION%.exe
echo.
echo.
echo Build log saved to %LOG_FILE%
pause < con

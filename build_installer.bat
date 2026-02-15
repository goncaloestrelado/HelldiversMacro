@echo off
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
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
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
    --add-data "stratagem_data.py;." ^
    --add-data "version.py;." ^
    --add-data "update_checker.py;." ^
    --add-data "theme_dark_default.qss;." ^
    --add-data "theme_dark_blue.qss;." ^
    --add-data "theme_dark_red.qss;." ^
    --icon "assets/icon.ico" ^
    --manifest "app.manifest" ^
    main.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [Success] EXE created: dist\HelldiversNumpadMacros.exe

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
    pause
    exit /b 0
)

"%INNO_PATH%" "installer.iss"

if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo Build Complete!
echo ============================================
echo.
echo Standalone EXE: dist\HelldiversNumpadMacros.exe
echo Installer: dist\installer\HelldiversNumpadMacros-Setup-beta0.1.7.exe
echo.
pause

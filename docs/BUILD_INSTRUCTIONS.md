# Build & Release Instructions

## Prerequisites

1. **Python 3.8+** with PyQt6 installed
2. **PyInstaller**: `pip install pyinstaller`
3. **Inno Setup 6**: Download from [jrsoftware.org](https://jrsoftware.org/isdl.php)

## Building the Application

### Option 1: Automated Build (Recommended)

Simply run the build script:

```bash
build_installer.bat
```

This will:

1. Clean previous builds
2. Build the standalone EXE with PyInstaller
3. Create the installer with Inno Setup

### Option 2: Manual Build

**Step 1: Build EXE with PyInstaller**

```bash
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
```

**Step 2: Create Installer (optional)**

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer/installer.iss
```

## Output Files

- **Standalone EXE**: `dist\HelldiversNumpadMacros.exe`
- **Installer**: `dist\installer\HelldiversNumpadMacros-Setup-v1.0.0.exe`

## Creating a GitHub Release

### Manual Release

1. Update version in `src/config/version.py`
2. Build the application
3. Go to GitHub → Releases → "Create a new release"
4. Tag: `v1.0.0` (matching version.py)
5. Title: `Version 1.0.0`
6. Upload both files:
   - `HelldiversNumpadMacros-Setup-v1.0.0.exe` (installer)
   - `HelldiversNumpadMacros-Portable-v1.0.0.exe` (rename standalone)
7. Add release notes
8. Publish release

### Automated Release (GitHub Actions)

A GitHub Actions workflow is included (`.github/workflows/release.yml`) that automatically:

- Builds the application when you push a version tag
- Creates a GitHub release
- Uploads the installer and portable EXE

To use it:

1. Update `src/config/version.py` with new version
2. Commit changes
3. Create and push a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

## Update Checker

The app automatically checks for updates on startup (configurable in Settings).

When you create a new GitHub release:

1. Users will be notified of the update
2. They can view release notes in-app
3. Download button opens the GitHub release page

## Version Management

Always update the version in **one place**: `src/config/version.py`

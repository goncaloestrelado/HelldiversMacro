# Version Management Guide

## Single Source of Truth

All version information is now managed from **one location**: [`src/config/version.py`](src/config/version.py)

```python
VERSION = "beta0.3.0"
```

## How It Works

### 1. **Update Version Once**

- Edit `src/config/version.py` and change the `VERSION` variable
- This is the **only place** you need to update the version

### 2. **Automatic Synchronization**

When you run the build process, the `build_version_file.py` script automatically:

- ✅ Reads the version from `src/config/version.py`
- ✅ Generates `version_file.txt` (PyInstaller's version resource)
- ✅ Updates `app.manifest` with the matching Windows version
- ✅ Updates the installer version in `installer/installer.iss`

### 3. **Windows Properties Display**

The generated EXE will show correct version information in:

- File Properties → Details tab
- Windows version info APIs
- Add/Remove Programs (via installer)

## Build Process

### Using the Batch Script

```bash
build_installer.bat
```

**Steps performed:**

1. Generates version file from `src/config/version.py`
2. Cleans previous builds
3. Builds EXE with PyInstaller (includes version resources)
4. Creates installer with Inno Setup (if available)

### Manual Build with PyInstaller

```bash
python build_version_file.py  # Always run this first!
pyinstaller HelldiversNumpadMacros.spec
```

## Version Format

Use semantic versioning: `MAJOR.MINOR.PATCH`

- Examples: `1.0.0`, `0.2.1`, `2.1.0`

The script automatically:

- Converts `beta0.3.0` → `0.3.0.0` for Windows (uses numeric components)
- Handles pre-release versions (strips suffix after dash)

## Files Involved

| File                          | Purpose                      | Updated By                               |
| ----------------------------- | ---------------------------- | ---------------------------------------- |
| `src/config/version.py`       | **Single source of truth**   | You (manually)                           |
| `version_file.txt`            | PyInstaller version resource | `build_version_file.py` ✍️               |
| `app.manifest`                | Windows manifest             | `build_version_file.py` ✍️               |
| `installer/installer.iss`     | Inno Setup installer         | `build_installer.bat` ✍️                 |
| `HelldiversNumpadMacros.spec` | PyInstaller config           | Manual (but references version_file.txt) |

✍️ = Auto-generated, don't edit manually

## Checking Your Version in Code

To use the version in your Python code:

```python
from src.config.version import VERSION, APP_NAME

print(f"{APP_NAME} v{VERSION}")
```

## Troubleshooting

**Q: The version file wasn't updated**

```bash
# Re-run the script manually
python build_version_file.py
```

**Q: Windows properties still show old version**

- Ensure you built with the updated `version_file.txt`
- Files may be cached; try right-click → Properties in a fresh Explorer window

**Q: Version shows as X.0.0.0**

- Edit `src/config/version.py` and use `X.Y.Z` format
- Re-run `python build_version_file.py`

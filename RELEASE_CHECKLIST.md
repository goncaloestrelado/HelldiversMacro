# Release Checklist

Use this checklist when creating a new release.

## Pre-Release

- [ ] Update `VERSION` in `version.py` to new version (e.g., `"1.1.0"`)
- [ ] Test the application thoroughly
- [ ] Update README.md with any new features or changes
- [ ] Review and update CHANGELOG (if you have one)
- [ ] Commit all changes:
  ```bash
  git add version.py README.md
  git commit -m "Bump version to 1.1.0"
  git push origin main
  ```

## Build

### Manual Build

- [ ] Run `build_installer.bat`
- [ ] Verify both files are created:
  - `dist\HelldiversNumpadMacros.exe`
  - `dist\installer\HelldiversNumpadMacros-Setup-v1.1.0.exe`
- [ ] Test the installer on a clean machine if possible
- [ ] Test the portable EXE

### Automated Build (GitHub Actions)

- [ ] Create and push version tag:
  ```bash
  git tag v1.1.0
  git push origin v1.1.0
  ```
- [ ] Wait for GitHub Actions workflow to complete
- [ ] Check that the release was created automatically

## GitHub Release

If doing manual release:

- [ ] Go to https://github.com/goncaloestrelado/HelldiversMacro/releases
- [ ] Click "Create a new release"
- [ ] Tag version: `v1.1.0` (must start with 'v')
- [ ] Release title: `Version 1.1.0` or descriptive title
- [ ] Add release notes describing:
  - New features
  - Bug fixes
  - Breaking changes (if any)
  - Known issues (if any)
- [ ] Upload files:
  - Rename `dist\HelldiversNumpadMacros.exe` to `HelldiversNumpadMacros-Portable-v1.1.0.exe`
  - Upload `HelldiversNumpadMacros-Setup-v1.1.0.exe` (from dist\installer)
  - Upload the portable EXE
- [ ] Click "Publish release"

## Post-Release

- [ ] Test the update checker:
  - Run the previous version
  - Check that update notification appears
  - Verify release notes display correctly
  - Test "Download" button
- [ ] Announce the release (Discord, Reddit, etc.)
- [ ] Monitor for bug reports
- [ ] Update any external documentation

## Release Notes Template

```markdown
## What's New

### Features

- Added feature X
- Improved feature Y

### Bug Fixes

- Fixed issue where Z happened

### Changes

- Changed behavior of W

## Installation

**Installer (Recommended):**
Download `HelldiversNumpadMacros-Setup-v1.1.0.exe` and run the installer.

**Portable:**
Download `HelldiversNumpadMacros-Portable-v1.1.0.exe` and run it directly (no installation needed).

## Notes

- Update checker will notify users of this release
- Requires Windows 10 or later
- Administrator privileges may be required if Helldivers 2 runs with admin rights
```

## Version Numbering

Use Semantic Versioning (semver.org):

- `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)
- Increment MAJOR for breaking changes
- Increment MINOR for new features (backwards compatible)
- Increment PATCH for bug fixes

Examples:

- `1.0.0` → `1.0.1` (bug fix)
- `1.0.1` → `1.1.0` (new feature)
- `1.1.0` → `2.0.0` (breaking change)

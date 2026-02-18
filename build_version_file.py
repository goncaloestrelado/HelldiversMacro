"""
Generate version file for PyInstaller from src/config/version.py
This ensures Windows properties always use the same version as your app
"""

import os
import re
from pathlib import Path

# Read version from the single source of truth
VERSION_PY = Path("src/config/version.py")
namespace = {}
exec(VERSION_PY.read_text(), namespace)
version_string = namespace['VERSION']  # This gets VERSION from imported module

# Convert "0.2.0" to tuple format (0, 2, 0, 0)
version_parts = version_string.split('.')
while len(version_parts) < 4:
    version_parts.append('0')
version_tuple = ','.join(v.split('-')[0] for v in version_parts[:4])  # Handle pre-release versions

# Create version file content
version_file_content = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # Contains as sequence of up to four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    mask=0x3f,
    mask_eq=0x3f,
    # Contains a bitmask that specifies the valid bits 'flags'r
    reserved=0x0,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    strFileInfo=(
      # Contains a list of StringFileInfo blocks, each describing a language/codepage
      # combination.
      ('040904B0',
        [('CompanyName', 'HelldiversMacro'),
        ('FileDescription', 'Helldivers 2 Stratagem Macro Tool'),
        ('FileVersion', '{version_string}'),
        ('InternalName', 'HelldiversNumpadMacros'),
        ('LegalCopyright', ''),
        ('OriginalFilename', 'HelldiversNumpadMacros.exe'),
        ('ProductName', 'Helldivers Numpad Macros'),
        ('ProductVersion', '{version_string}')])
    ),
    VarFileInfo=[('Translation', [1033, 1200])]
  ),
  ffi=FixedFileInfo(
        # Contains as sequence of up to four items: (1, 2, 3, 4)
        # Set not needed items to zero 0.
        mask=0x3f,
        mask_eq=0x3f,
        # Contains a bitmask that specifies the valid bits 'flags'r
        reserved=0x0,
        # Contains a bitmask that specifies the Boolean attributes of the file.
        flag=0x0,
        # Contains a version number as a sequence of four items: major, minor, patch, build
        file_version=({version_tuple}),
        # Contains a version number as a sequence of four items: major, minor, patch, build
        prod_version=({version_tuple}),
        # Contains a bitmask that specifies the valid bits 'flags'r
        mask=0x3f,
        # Contains a bitmask that specifies the Boolean attributes of the file.
        mask_eq=0x3f,
  ),
)
'''

# Write to version_file.txt
with open('version_file.txt', 'w') as f:
    f.write(version_file_content)

print(f"✓ Generated version_file.txt for version {version_string}")

# Also update app.manifest with the correct version
manifest_path = Path("app.manifest")
manifest_content = manifest_path.read_text()
# Convert version to Windows format (0.2.0 -> 0.2.0.0)
windows_version = version_string + '.0' if version_string.count('.') == 2 else version_string
manifest_content = re.sub(
    r'version="[\d.]+"',
    f'version="{windows_version}"',
    manifest_content
)
manifest_path.write_text(manifest_content)
print(f"✓ Updated app.manifest version to {windows_version}")

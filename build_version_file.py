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
    mask=0x3f,
    mask_eq=0x3f,
    reserved=0x0,
    flag=0x0,
    file_version=({version_tuple}),
    prod_version=({version_tuple}),
  ),
  kids=[
    StringFileInfo(
      [StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'HelldiversMacro'),
        StringStruct(u'FileDescription', u'Helldivers 2 Stratagem Macro Tool'),
        StringStruct(u'FileVersion', u'{version_string}'),
        StringStruct(u'InternalName', u'HelldiversNumpadMacros'),
        StringStruct(u'LegalCopyright', u''),
        StringStruct(u'OriginalFilename', u'HelldiversNumpadMacros.exe'),
        StringStruct(u'ProductName', u'Helldivers Numpad Macros'),
        StringStruct(u'ProductVersion', u'{version_string}')])
      ]),
    VarFileInfo([VarFileEntry(u'Translation', [1033, 1200])])
  ]
)
'''

# Write to version_file.txt
with open('version_file.txt', 'w', encoding='utf-8') as f:
    f.write(version_file_content)

print(f"[OK] Generated version_file.txt for version {version_string}")

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
print(f"[OK] Updated app.manifest version to {windows_version}")

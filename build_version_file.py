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

# Convert any version string to numeric tuple format (e.g. "beta0.3.0" -> 0,3,0,0)
numeric_parts = re.findall(r'\d+', version_string)
while len(numeric_parts) < 4:
  numeric_parts.append('0')
version_tuple = ','.join(numeric_parts[:4])

# Create version file content
version_file_content = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple}),
    prodvers=({version_tuple}),
    mask=0x3f,
    flags=0x0,
  ),
  kids=[
    StringFileInfo(
      [StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'HelldiversMacro'),
        StringStruct(u'FileDescription', u'Helldivers 2 Stratagem Macro Tool'),
        StringStruct(u'FileVersion', u'{version_string}'),
        StringStruct(u'InternalName', u'Helldivers2StratCommander'),
        StringStruct(u'LegalCopyright', u''),
        StringStruct(u'OriginalFilename', u'Helldivers2StratCommander.exe'),
        StringStruct(u'ProductName', u'Helldivers 2 - Strat Commander'),
        StringStruct(u'ProductVersion', u'{version_string}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
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
# Convert version to Windows format using numeric components only (beta0.3.0 -> 0.3.0.0)
windows_version = '.'.join(numeric_parts[:4])
manifest_content = re.sub(
  r'version="[\w.-]+"',
    f'version="{windows_version}"',
    manifest_content
)
manifest_path.write_text(manifest_content)
print(f"[OK] Updated app.manifest version to {windows_version}")

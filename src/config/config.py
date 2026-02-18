"""
Configuration module for Helldivers Numpad Macros
Handles paths, settings, theme management, and utility functions
"""

import os
import sys
import shutil
import json
import ctypes
import re

from .constants import THEME_FILES, DEFAULT_SETTINGS


def get_app_data_dir():
    r"""Get the application data directory (Windows: %APPDATA%\HelldiversNumpadMacros)"""
    appdata = os.environ.get('APPDATA')
    if appdata:
        app_dir = os.path.join(appdata, "HelldiversNumpadMacros")
        os.makedirs(app_dir, exist_ok=True)
        return app_dir
    # Fallback for systems without APPDATA (shouldn't happen on Windows)
    return "profiles"


def migrate_old_files():
    """Migrate old profile and settings files from app directory to AppData"""
    new_app_data_dir = get_app_data_dir()
    old_profiles_dir = "profiles"
    old_settings_file = "general.json"
    

    if os.path.exists(old_profiles_dir) and old_profiles_dir != os.path.join(new_app_data_dir, "profiles"):
        try:
            new_profiles_dir = os.path.join(new_app_data_dir, "profiles")
            if not os.path.exists(new_profiles_dir):
                shutil.copytree(old_profiles_dir, new_profiles_dir)
                print(f"[Migration] Profiles migrated from {old_profiles_dir} to {new_profiles_dir}")
        except Exception as e:
            print(f"[Migration] Warning: Could not migrate profiles directory: {e}")
    
    if os.path.exists(old_settings_file):
        try:
            new_settings_file = os.path.join(new_app_data_dir, "general.json")
            if not os.path.exists(new_settings_file):
                shutil.copy2(old_settings_file, new_settings_file)
                print(f"[Migration] Settings migrated from {old_settings_file} to {new_settings_file}")
        except Exception as e:
            print(f"[Migration] Warning: Could not migrate settings file: {e}")


PROFILES_DIR = os.path.join(get_app_data_dir(), "profiles")
SETTINGS_FILE = os.path.join(get_app_data_dir(), "general.json")
ASSETS_DIR = "assets"

os.makedirs(PROFILES_DIR, exist_ok=True)
migrate_old_files()


def normalize(name):
    """Normalize name for comparison (remove spaces, special characters, lowercase)"""
    return name.lower().replace(" ", "").replace("_", "").replace("-", "").replace("/", "").replace('"', "")


def is_installed():
    """Check if app is installed or running portable"""
    exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
    exe_dir = os.path.dirname(os.path.abspath(exe_path))
    
    # Check if running from Program Files or similar installation directories
    program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
    
    return exe_dir.startswith(program_files) or exe_dir.startswith(program_files_x86)


def get_install_type():
    """Get the current installation type: 'installed' or 'portable'"""
    return "installed" if is_installed() else "portable"


def get_installer_filename(tag_name):
    """Generate expected installer filename from tag"""
    return f"HelldiversNumpadMacros-Setup-{tag_name}.exe"


def is_admin():
    """Check if the current process has administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Relaunch the current script with administrator privileges"""
    try:
        if getattr(sys, 'frozen', False):
            script = sys.executable
        else:
            script = os.path.abspath(sys.argv[0])
        
        params = ' '.join(sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        return True
    except:
        return False


def find_svg_path(name):
    """Find SVG file for stratagem, with simplified lookup since files now match official names"""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    assets_lookup = os.path.join(base_path, ASSETS_DIR)
    target = normalize(name)
    
    for root, dirs, files in os.walk(assets_lookup):
        for f in files:
            if f.endswith(".svg"):
                if normalize(os.path.splitext(f)[0]) == target:
                    return os.path.join(root, f)
    return None


def load_settings():
    """Load global settings from file"""
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            # Merge with defaults in case new settings were added
            result = DEFAULT_SETTINGS.copy()
            result.update(settings)
            return result
    except Exception as e:
        print(f"[Config] Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Save global settings to file"""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[Config] Error saving settings: {e}")


def apply_theme_to_stylesheet(qss_content, base_path):
    """Apply theme stylesheet with proper asset path resolution"""
    assets_root = os.path.join(base_path, ASSETS_DIR)
    return re.sub(
        r"url\((['\"]?)assets/([^'\")]+)\1\)",
        lambda m: f"url(\"{os.path.join(assets_root, m.group(2)).replace('\\', '/')}\")",
        qss_content,
    )


def get_theme_stylesheet(theme_name="Dark (Default)"):
    """Get the stylesheet content for a given theme"""
    try:
        theme_file = THEME_FILES.get(theme_name, THEME_FILES["Dark (Default)"])
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        qss_path = os.path.join(base_path, theme_file)
        
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                qss = f.read()
            return apply_theme_to_stylesheet(qss, base_path)
    except Exception as e:
        print(f"[Config] Theme Error: {e}")
    return ""


# Legacy name mapping for automatic migration of old save files
LEGACY_NAME_MAP = {
    "Machine Gun": "MG-43 Machine Gun",
    "Anti-Materiel Rifle": "APW-1 Anti-Materiel Rifle",
    "Stalwart": "M-105 Stalwart",
    "Expendable Anti-Tank": "EAT-17 Expendable Anti-Tank",
    "Recoilless Rifle": "GR-8 Recoilless Rifle",
    "Flamethrower": "FLAM-40 Flamethrower",
    "Autocannon": "AC-8 Autocannon",
    "Heavy Machine Gun": "MG-206 Heavy Machine Gun",
    "Airburst Rocket Launcher": "RL-77 Airburst Rocket Launcher",
    "Commando": "MLS-4X Commando",
    "Railgun": "RS-422 Railgun",
    "Spear": "FAF-14 Spear",
    "Jump Pack": "LIFT-850 Jump Pack",
    "Eagle 500KG Bomb": "Eagle 500kg Bomb",
    "Fast Recon Vehicle": "M-102 Fast Recon Vehicle",
    "Bastion": "TD-220 Bastion",
    "Bastion MK XVI": "TD-220 Bastion",
    "HMG Emplacement": "E/MG-101 HMG Emplacement",
    "Shield Generator Relay": "FX-12 Shield Generator Relay",
    "Tesla Tower": "A/ARC-3 Tesla Tower",
    "Grenadier Battlement": "E/GL-21 Grenadier Battlement",
    "Anti-Personnel Minefield": "MD-6 Anti-Personnel Minefield",
    "Supply Pack": "B-1 Supply Pack",
    "Grenade Launcher": "GL-21 Grenade Launcher",
    "Laser Cannon": "LAS-98 Laser Cannon",
    "Incendiary Mines": "MD-I4 Incendiary Mines",
    "Guard Dog Rover": "AX/LAS-5 \"Guard Dog\" Rover",
    "Ballistic Shield Backpack": "SH-20 Ballistic Shield Backpack",
    "Arc Thrower": "ARC-3 Arc Thrower",
    "Anti-Tank Mines": "MD-17 Anti-Tank Mines",
    "Quasar Cannon": "LAS-99 Quasar Cannon",
    "Shield Generator Pack": "SH-32 Shield Generator Pack",
    "Gas Mine": "MD-8 Gas Mines",
    "Gas Mines": "MD-8 Gas Mines",
    "Machine Gun Sentry": "A/MG-43 Machine Gun Sentry",
    "Gatling Sentry": "A/G-16 Gatling Sentry",
    "Mortar Sentry": "A/M-12 Mortar Sentry",
    "Guard Dog": "AX/AR-23 \"Guard Dog\"",
    "Autocannon Sentry": "A/AC-8 Autocannon Sentry",
    "Rocket Sentry": "A/MLS-4X Rocket Sentry",
    "EMS Mortar Sentry": "A/M-23 EMS Mortar Sentry",
    "Patriot Exosuit": "EXO-45 Patriot Exosuit",
    "Emancipator Exosuit": "EXO-49 Emancipator Exosuit",
    "Sterilizer": "TX-41 Sterilizer",
    "Guard Dog Breath": "AX/TX-13 \"Guard Dog\" Dog Breath",
    "Guard Dog Dog Breath": "AX/TX-13 \"Guard Dog\" Dog Breath",
    "Directional Shield": "SH-51 Directional Shield",
    "Anti-Tank Emplacement": "E/AT-12 Anti-Tank Emplacement",
    "Flame Sentry": "A/FLAM-40 Flame Sentry",
    "Portable Hellbomb": "B-100 Portable Hellbomb",
    "Hellbomb Portable": "B-100 Portable Hellbomb",
    "Hover Pack": "LIFT-860 Hover Pack",
    "One True Flag": "CQC-1 One True Flag",
    "De-Escalator": "GL-52 De-Escalator",
    "Guard Dog K-9": "AX/ARC-3 \"Guard Dog\" K-9",
    "Epoch": "PLAS-45 Epoch",
    "Laser Sentry": "A/LAS-98 Laser Sentry",
    "Warp Pack": "LIFT-182 Warp Pack",
    "Speargun": "S-11 Speargun",
    "Expendable Napalm": "EAT-700 Expendable Napalm",
    "Solo Silo": "MS-11 Solo Silo",
    "Maxigun": "M-1000 Maxigun",
    "Defoliation Tool": "CQC-9 Defoliation Tool",
    "Guard Dog Hot Dog": "AX/FLAM-75 \"Guard Dog\" Hot Dog",
    "C4 Pack": "B/MD C4 Pack",
    "Breaching Hammer": "CQC-20 Breaching Hammer",
    "CQC-20": "CQC-20 Breaching Hammer",
    "EAT-411": "EAT-411 Leveller",
    "GL-28": "GL-28 Belt-Fed Grenade Launcher",
    "Illumination Flare": "Orbital Illumination Flare",
}

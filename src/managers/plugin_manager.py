"""
Plugin manager for Helldivers Numpad Macros.
Loads data-only plugins that can provide stratagems, icon overrides and themes.
"""

import copy
import json
import os
import re
import shutil
import sys

from ..config import PLUGINS_DIR


class PluginManager:
    """Load and merge plugin content into runtime application data."""

    VALID_DIRECTIONS = {"up", "down", "left", "right"}
    COLOR_VALUE_PATTERN = re.compile(r"^(#[0-9A-Fa-f]{3,8}|rgba?\([^\)]+\)|hsla?\([^\)]+\)|[A-Za-z]+)$")
    DEFAULT_THEME_COLORS = {
        "background_color": "#111111",
        "border_color": "#666666",
        "accent_color": "#4a90e2",
    }

    @staticmethod
    def _get_local_plugins_dir():
        """Get plugin directory near executable/script."""
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.abspath(".")
        return os.path.join(base_dir, "plugins")

    @staticmethod
    def get_plugin_roots():
        """Get plugin roots in order of precedence (local first, then AppData)."""
        roots = [PluginManager._get_local_plugins_dir(), PLUGINS_DIR]
        deduped = []
        for root in roots:
            if root not in deduped:
                deduped.append(root)
        return deduped

    @staticmethod
    def _is_under_plugin_roots(path_value):
        """Check whether a path is inside configured plugin roots."""
        try:
            normalized_path = os.path.normcase(os.path.abspath(path_value))
            for root in PluginManager.get_plugin_roots():
                normalized_root = os.path.normcase(os.path.abspath(root))
                if normalized_path == normalized_root or normalized_path.startswith(normalized_root + os.sep):
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _validate_sequence(sequence):
        """Validate a stratagem input sequence."""
        if not isinstance(sequence, list) or not sequence:
            return False
        for step in sequence:
            if not isinstance(step, str) or step.lower() not in PluginManager.VALID_DIRECTIONS:
                return False
        return True

    @staticmethod
    def _resolve_plugin_path(plugin_dir, relative_or_absolute):
        """Resolve plugin resource path relative to plugin folder."""
        if not isinstance(relative_or_absolute, str) or not relative_or_absolute.strip():
            return None

        path_value = relative_or_absolute.strip()
        if os.path.isabs(path_value):
            return path_value
        return os.path.normpath(os.path.join(plugin_dir, path_value))

    @staticmethod
    def _load_manifest(manifest_path):
        """Read plugin manifest JSON file."""
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"[PluginManager] Failed loading manifest {manifest_path}: {e}")
        return None

    @staticmethod
    def _save_manifest(manifest_path, manifest_data):
        """Save plugin manifest JSON file."""
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
            return True
        except Exception as e:
            print(f"[PluginManager] Failed saving manifest {manifest_path}: {e}")
            return False

    @staticmethod
    def _is_valid_color_value(value):
        """Validate color format used by plugin theme colors."""
        if not isinstance(value, str):
            return False
        cleaned = value.strip()
        return bool(cleaned and PluginManager.COLOR_VALUE_PATTERN.match(cleaned))

    @staticmethod
    def _normalize_theme_colors(colors):
        """Normalize plugin theme colors from manifest entry."""
        if not isinstance(colors, dict):
            return None

        background = colors.get("background_color") or colors.get("background")
        border = colors.get("border_color") or colors.get("border")
        accent = colors.get("accent_color") or colors.get("accent")

        normalized = {}
        if PluginManager._is_valid_color_value(background):
            normalized["background_color"] = background.strip()
        if PluginManager._is_valid_color_value(border):
            normalized["border_color"] = border.strip()
        if PluginManager._is_valid_color_value(accent):
            normalized["accent_color"] = accent.strip()

        if not normalized:
            return None

        if "border_color" not in normalized and "accent_color" in normalized:
            normalized["border_color"] = normalized["accent_color"]
        if "accent_color" not in normalized and "border_color" in normalized:
            normalized["accent_color"] = normalized["border_color"]

        return {
            "background_color": normalized.get("background_color", "#111111"),
            "border_color": normalized.get("border_color", "#666666"),
            "accent_color": normalized.get("accent_color", "#4a90e2"),
        }

    @staticmethod
    def _backfill_theme_colors(manifest):
        """Ensure each theme entry has colors constants and persistable structure."""
        if not isinstance(manifest, dict):
            return False

        themes = manifest.get("themes")
        if not isinstance(themes, list):
            return False

        changed = False
        for theme_entry in themes:
            if not isinstance(theme_entry, dict):
                continue

            colors = theme_entry.get("colors")
            normalized = PluginManager._normalize_theme_colors(colors)
            if normalized:
                if colors != normalized:
                    theme_entry["colors"] = normalized
                    changed = True
                continue

            theme_entry["colors"] = dict(PluginManager.DEFAULT_THEME_COLORS)
            changed = True

        return changed

    @staticmethod
    def _discover_plugins(include_disabled=False):
        """Discover plugins from plugin root directories."""
        plugins = []
        seen_manifest_paths = set()

        for root in PluginManager.get_plugin_roots():
            if not os.path.isdir(root):
                continue

            try:
                entries = sorted(os.listdir(root))
            except Exception as e:
                print(f"[PluginManager] Cannot list plugin root {root}: {e}")
                continue

            for entry in entries:
                plugin_dir = os.path.join(root, entry)
                manifest_path = os.path.join(plugin_dir, "plugin.json")
                if os.path.isdir(plugin_dir) and os.path.exists(manifest_path):
                    if manifest_path in seen_manifest_paths:
                        continue
                    seen_manifest_paths.add(manifest_path)

                    manifest = PluginManager._load_manifest(manifest_path)
                    if not manifest:
                        continue

                    if PluginManager._backfill_theme_colors(manifest):
                        PluginManager._save_manifest(manifest_path, manifest)

                    if not include_disabled and manifest.get("enabled", True) is False:
                        continue

                    plugins.append({
                        "id": manifest.get("id", entry),
                        "name": manifest.get("name", entry),
                        "directory": plugin_dir,
                        "manifest": manifest,
                        "manifest_path": manifest_path,
                    })
                    continue

                if not os.path.isfile(plugin_dir):
                    continue

                if not entry.lower().endswith(".json"):
                    continue

                manifest_path = plugin_dir
                if manifest_path in seen_manifest_paths:
                    continue
                seen_manifest_paths.add(manifest_path)

                manifest = PluginManager._load_manifest(manifest_path)
                if not manifest:
                    continue

                if PluginManager._backfill_theme_colors(manifest):
                    PluginManager._save_manifest(manifest_path, manifest)

                if not include_disabled and manifest.get("enabled", True) is False:
                    continue

                file_stem = os.path.splitext(entry)[0]
                plugins.append({
                    "id": manifest.get("id", file_stem),
                    "name": manifest.get("name", file_stem),
                    "directory": root,
                    "manifest": manifest,
                    "manifest_path": manifest_path,
                })

        return plugins

    @staticmethod
    def list_plugins():
        """List all valid plugin manifests found across plugin roots."""
        plugin_list = []
        for plugin in PluginManager._discover_plugins(include_disabled=True):
            manifest = plugin.get("manifest", {})
            plugin_list.append({
                "id": str(plugin.get("id", "unknown")),
                "name": str(plugin.get("name", "unknown")),
                "enabled": bool(manifest.get("enabled", True)),
                "manifest_path": plugin.get("manifest_path", ""),
            })
        return plugin_list

    @staticmethod
    def set_only_enabled(selected_manifest_path):
        """Enable only the selected plugin manifest and disable all others."""
        if not selected_manifest_path:
            return False

        selected_normalized = os.path.normcase(os.path.normpath(selected_manifest_path))
        found_selected = False

        plugins = PluginManager._discover_plugins(include_disabled=True)
        for plugin in plugins:
            manifest_path = plugin.get("manifest_path", "")
            manifest = plugin.get("manifest", {})
            if not manifest_path or not isinstance(manifest, dict):
                continue

            current_path_normalized = os.path.normcase(os.path.normpath(manifest_path))
            should_enable = current_path_normalized == selected_normalized
            if should_enable:
                found_selected = True

            current_enabled = bool(manifest.get("enabled", True))
            if current_enabled == should_enable:
                continue

            manifest["enabled"] = should_enable
            PluginManager._save_manifest(manifest_path, manifest)

        return found_selected

    @staticmethod
    def set_enabled_manifests(selected_manifest_paths):
        """Enable plugins in selected manifest path list and disable all others."""
        if not isinstance(selected_manifest_paths, (list, tuple, set)):
            return False

        selected_normalized = {
            os.path.normcase(os.path.normpath(path))
            for path in selected_manifest_paths
            if isinstance(path, str) and path.strip()
        }

        found_selected = False
        plugins = PluginManager._discover_plugins(include_disabled=True)
        for plugin in plugins:
            manifest_path = plugin.get("manifest_path", "")
            manifest = plugin.get("manifest", {})
            if not manifest_path or not isinstance(manifest, dict):
                continue

            current_path_normalized = os.path.normcase(os.path.normpath(manifest_path))
            should_enable = current_path_normalized in selected_normalized
            if should_enable:
                found_selected = True

            current_enabled = bool(manifest.get("enabled", True))
            if current_enabled == should_enable:
                continue

            manifest["enabled"] = should_enable
            PluginManager._save_manifest(manifest_path, manifest)

        return found_selected or not selected_normalized

    @staticmethod
    def uninstall_plugin_by_manifest(manifest_path):
        """Uninstall plugin by manifest path. Removes plugin folder or standalone manifest file."""
        if not isinstance(manifest_path, str) or not manifest_path.strip():
            return False, "Invalid plugin manifest path."

        manifest_abs = os.path.abspath(manifest_path)
        if not os.path.exists(manifest_abs):
            return False, "Plugin manifest path not found."

        if not PluginManager._is_under_plugin_roots(manifest_abs):
            return False, "Refusing to remove path outside plugin folders."

        try:
            if os.path.basename(manifest_abs).lower() == "plugin.json":
                plugin_dir = os.path.dirname(manifest_abs)
                if PluginManager._is_under_plugin_roots(plugin_dir) and os.path.isdir(plugin_dir):
                    shutil.rmtree(plugin_dir)
                    return True, "Plugin folder removed."

            if os.path.isfile(manifest_abs):
                os.remove(manifest_abs)
                return True, "Plugin file removed."
        except Exception as e:
            return False, f"Failed uninstalling plugin: {e}"

        return False, "Nothing was removed."

    @staticmethod
    def build_runtime_data(base_stratagems_by_department, base_theme_files):
        """Build merged runtime data from base app data and plugins."""
        merged_departments = copy.deepcopy(base_stratagems_by_department)
        merged_theme_files = dict(base_theme_files)
        theme_sources = {theme_name: None for theme_name in merged_theme_files.keys()}
        icon_overrides = {}

        loaded_plugins = []
        warnings = []

        for plugin in PluginManager._discover_plugins():
            plugin_id = str(plugin.get("id", "unknown"))
            plugin_name = str(plugin.get("name", plugin_id))
            plugin_dir = plugin["directory"]
            manifest = plugin["manifest"]

            loaded_plugins.append(plugin_name)

            plugin_departments = manifest.get("stratagems_by_department", {})
            if isinstance(plugin_departments, dict):
                for department, stratagems in plugin_departments.items():
                    if not isinstance(department, str) or not isinstance(stratagems, dict):
                        warnings.append(f"[{plugin_id}] Invalid stratagems in department '{department}'")
                        continue

                    department_bucket = merged_departments.setdefault(department, {})
                    for stratagem_name, sequence in stratagems.items():
                        if not isinstance(stratagem_name, str) or not PluginManager._validate_sequence(sequence):
                            warnings.append(f"[{plugin_id}] Invalid sequence for stratagem '{stratagem_name}'")
                            continue

                        department_bucket[stratagem_name] = [step.lower() for step in sequence]

            plugin_icon_overrides = manifest.get("icon_overrides", {})
            if isinstance(plugin_icon_overrides, dict):
                for stratagem_name, icon_path in plugin_icon_overrides.items():
                    if not isinstance(stratagem_name, str):
                        continue

                    resolved_icon_path = PluginManager._resolve_plugin_path(plugin_dir, icon_path)
                    if resolved_icon_path and os.path.exists(resolved_icon_path):
                        icon_overrides[stratagem_name] = resolved_icon_path
                    else:
                        warnings.append(f"[{plugin_id}] Missing icon override file: {icon_path}")

            plugin_themes = manifest.get("themes", [])
            if isinstance(plugin_themes, list):
                for theme_entry in plugin_themes:
                    if not isinstance(theme_entry, dict):
                        continue

                    theme_name = theme_entry.get("name")
                    if not isinstance(theme_name, str):
                        continue

                    theme_colors = PluginManager._normalize_theme_colors(theme_entry.get("colors"))
                    if theme_colors:
                        merged_theme_files[theme_name] = theme_colors
                        theme_sources[theme_name] = plugin_name
                    else:
                        warnings.append(
                            f"[{plugin_id}] Theme '{theme_name}' must define colors in JSON: "
                            "colors.background_color, colors.border_color, colors.accent_color"
                        )

        merged_stratagems = {}
        for _, stratagems in merged_departments.items():
            merged_stratagems.update(stratagems)

        if loaded_plugins:
            print(f"[PluginManager] Loaded plugins: {', '.join(loaded_plugins)}")
        for warning in warnings:
            print(f"[PluginManager] Warning: {warning}")

        return {
            "stratagems_by_department": merged_departments,
            "stratagems": merged_stratagems,
            "theme_files": merged_theme_files,
            "theme_sources": theme_sources,
            "icon_overrides": icon_overrides,
            "loaded_plugins": loaded_plugins,
            "warnings": warnings,
        }

# Plugins (MVP v1)

This first version supports **data-only plugins** (no Python code execution).

## Where plugins are loaded from

The app scans both:

- `./plugins` (next to the executable or project root)
- `%APPDATA%/HelldiversNumpadMacros/plugins`

Current example packs (`orbital_napalm_plugin`, `hangar_example_pack`) were moved to `%APPDATA%/HelldiversNumpadMacros/plugins`.

Each plugin must be a folder containing a `plugin.json` file.

## Supported features

- Add or override stratagems
- Override SVG icons for stratagem names
- Add new plugin color themes to the Appearance dropdown

## `plugin.json` format

```json
{
  "id": "my-plugin-id",
  "name": "My Plugin",
  "enabled": true,
  "stratagems_by_department": {
    "My Department": {
      "My Stratagem": ["down", "left", "up", "right"]
    }
  },
  "icon_overrides": {
    "My Stratagem": "icons/my_stratagem.svg"
  },
  "themes": [
    {
      "name": "Dark with Green Accent",
      "colors": {
        "background_color": "#151a18",
        "border_color": "#2f7a5d",
        "accent_color": "#4bbf8a"
      }
    }
  ]
}
```

## Another example: add stratagems to `Hangar`

```json
{
  "id": "hangar-example-pack",
  "name": "Hangar Reinforcement Pack",
  "enabled": true,
  "stratagems_by_department": {
    "Hangar": {
      "Eagle Napalm Airstrike": ["up", "right", "down", "up"],
      "Eagle Smoke Strike": ["up", "right", "up", "down"],
      "Eagle Strafing Run": ["up", "right", "right"]
    }
  }
}
```

### Notes

- Directions must be one of: `up`, `down`, `left`, `right`.
- Relative file paths are resolved from the plugin folder.
- If a stratagem name already exists, plugin value overrides it.
- If a theme name already exists, plugin theme overrides it.
- Plugin themes are constrained: only `background-color`, `border-color`, and accent color values are applied.
- Theme colors are defined in `plugin.json` under `themes[].colors` (no plugin QSS file needed).
- Accepted keys are `background_color`, `border_color`, and `accent_color`.

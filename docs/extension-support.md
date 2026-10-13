# Additional KDE extension coverage

Reviewed 2026-10-13. This is configuration-transfer coverage, not a claim that
every plugin is installable or compatible on every Plasma release.

## Implemented in 1.8.2

- **Window Buttons** (`org.kde.windowbuttons`): bounded button-order list,
  Breeze selection and the Plasma color-scheme sentinel. Numeric/bool geometry
  uses the existing schema handling. Other decoration selections still need
  asset/dependency resolution; native QML dependencies are not bundled blindly.
  Source: https://github.com/moodyhunter/applet-window-buttons6/blob/master/package/contents/config/main.xml
- **PlasMusic Toolbar**: reviewed text visibility/alignment/position/scrolling
  controls, standard music icons. Copy both explicit values and safe installed
  schema defaults. Arbitrary text, custom image paths and player-specific data
  are not newly authorized by these adapters.
  Source: https://github.com/ccatterina/plasmusic-toolbar/blob/main/src/contents/config/main.xml
- **Karousel**: bounded percentage-based presetWidths, in addition to existing
  numeric gaps and boolean options. Caption rules and screen/desktop-specific
  mappings need separate privacy-safe adapters. Absolute-width presets are not
  newly supported.
  Source: https://github.com/peterfajdiga/karousel/blob/master/src/lib/config/definition.ts
- **Polonium**: regression coverage for explicit numeric layout settings already
  handled by the generic exporter. No claim of saved-layout/DBus-saver migration
  or automatic discovery of defaults embedded in TypeScript. Upstream documents
  Wayland support; do not promise equivalent X11 behavior.
  Source: https://github.com/zeroxoneafour/polonium/blob/master/src/controller/config.ts

## Useful next candidates

- **Mudeer**: screen splitting and layout shortcuts; shortcut collisions and
  monitor-relative layouts require an explicit migration policy.
  https://github.com/darkstego/Mudeer
- **Geometry Change**: movement/resizing animation for tiled windows; verify
  effect version compatibility and numeric animation settings.
  https://github.com/peterfajdiga/kwin4_effect_geometry_change
- **Panel Colorizer**: deepen existing support for non-empty per-widget
  overrides; association IDs must be remapped with imported applet IDs.
  https://github.com/luisbocanegra/plasma-panel-colorizer

Tests use small hand-written fixtures based on the above configuration formats.
No third-party executable code is fetched or run by these tests. A KDE graphical
end-to-end test remains necessary before claiming visual equivalence.

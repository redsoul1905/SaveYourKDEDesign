# SaveYourKDEDesign 1.8.4

- Fix the missing installation-source mapping for `kwin4_effect_shapecorners`.
  Fedora offers the maintainer's `matinlotfali/KDE-Rounded-Corners` COPR and
  `kwin-effect-roundcorners`; Arch/CachyOS offers the verified
  `kwin-effect-rounded-corners-git` AUR package. X11 uses the respective X11
  variant. Third-party installation requires user consent and authentication.
- Reuse the existing installation/recheck workflow; do not hide a missing effect
  or report success without checking it. Other distributions get the maintainer's
  instructions. Unknown effects are never mapped to arbitrary archive commands.
- Existing codes remain compatible: update the receiver and retry the import.

Upstream installation recipes: https://github.com/matinlotfali/KDE-Rounded-Corners#installation

QC: 142 offline tests. The reported s7xw22 archive's checksum was verified and
its manifest explicitly requires ShapeCorners. No packages were installed and
no desktop configuration was changed on the development computer. Real Fedora
rendering and availability of a compatible COPR build still require target-side
verification; these are not implied by the offline tests.

## Previous release: 1.8.3

- Stop exporting source taskbar launchers. On public import, preserve the
  receiver's primary-screen pins (deduplicated), or start empty using the new
  checkbox. The import rule also protects against launcher lists in old codes.
- Bundle selected hicolor widget icons, including the CachyOS start icon;
  previously hicolor was only declared as a system dependency. For old codes,
  use start-here-kde if the original start-menu icon is neither bundled nor
  available on the receiver.
- Explicitly disable requested-off effects before loading requested-on effects,
  reconfigure each enabled effect, and check that it is loaded. A load failure
  or missing required effect must not produce a successful-import message.
- Handle redundant kwin4_effect_glass keys alongside the current glass ID.
  Do not enable a separate ShapeCorners effect if the source explicitly disables
  it. Glass corner-radius settings remain preserved.

QC: 135 offline tests pass. The supplied zzuq40 archive was checksum-verified:
Glass blur/radius settings were present, the start icon was not bundled, source
pins were included, and ShapeCorners was disabled. A new source-only export
verifies icon bundling, exclusion of source pins and retained Glass radii.
No real desktop was imported during development. Actual blur rendering on the
Fedora target still needs graphical verification; plugin/driver incompatibility
cannot be repaired merely by copying configuration.

## Previous release: 1.8.2

- Preserve Window Buttons' validated button order and standard Breeze/Plasma
  appearance selections.
- Preserve reviewed PlasMusic text visibility, positions, alignment and scrolling
  options without accepting arbitrary private text.
- Preserve Karousel's percentage-based column-width presets.
- Apply reviewed widget adapters to safe schema defaults as well as explicit
  user settings. Add regression coverage for Polonium numeric layout settings.
- Document exact coverage, exclusions and upstream configuration sources in
  docs/extension-support.md. No extensions are installed on the development PC.

QC: 126 offline tests; no graphical cross-distribution certification implied.
Update both computers and generate a fresh code to include the additional values.

## Previous release: 1.8.1

- Eliminate false-positive reviews for supported visual settings: pager text
  mode, clock style/calendar selection, launcher actions/shortcut, round-corner
  class filters, empty Panel Colorizer overrides and supported monitor settings.
- Do not publish personal weather locations, private title filters or local
  notification/history state. Anonymous export excludes these automatically.
- Do not transfer Panel Colorizer's regenerable panelWidgets cache or local
  lastPreset path; preserve its active appearance configuration.
- Export root-disk sensor references by role and resolve the receiving system's
  root UUID before writing configuration. Do not guess for unrelated disks.
- Retain unresolved-visual-setting review rather than silently dropping unknown
  structures. Hardware temperature sensor availability remains target-dependent.

QC: 122 offline tests pass. The current real-source design exports with zero
setting-review prompts without uploading or modifying the desktop. This does
not establish graphical equivalence on Fedora; personal content is intentionally
not identical in anonymous exports. Update BOTH computers and create a new code.

## Previous release: 1.8.0

Update BOTH computers and generate a new code. Previously omitted settings
cannot be recovered from an old public design archive.

- Preserve portable numeric/boolean settings for KWin scripts and effects,
  including Krohnkite gaps/layout order and Glass/Blur brightness, saturation,
  decoration and corner settings. Support window-class filters.
- Discover data-only KConfigXT schemas for installed widgets/scripts/effects;
  include safe declared defaults. Schemas never authorize credentials, commands,
  private text or arbitrary file references.
- Identify settings requiring review before upload, with component, key and a
  concrete remediation proposal. Do not include raw private values in reports.
  The user must explicitly accept omissions/local-filter resets or cancel.
- Transfer virtual desktop count and rows, not source desktop IDs/names. A pager
  on an imported panel can otherwise remain invisible with one target desktop.
- Merge KWin values without deleting unrelated target preferences. Reload
  affected enabled scripts, create missing virtual desktops and verify count
  and script loading. Do not silently remove target workspaces containing windows.

QC: 117 offline tests pass. Real-source export checked without uploading or
changing the source desktop. Fedora graphical end-to-end validation is still
required. Arbitrary third-party app settings, free text and structured private
formats require reviewed adapters; universal pixel-identical rendering is not
guaranteed. Existing installation, panel and wallpaper checks remain in place.

## Previous release: 1.7.9

Update the application on BOTH the exporting and importing computer, then create
a fresh code. Old packages cannot recover previously omitted launcher entries.

- Stop the Plasma shell gracefully while capturing a public export so pending
  configuration is saved. Restart before upload, including on export failure.
- Stop the receiving shell before reading/merging/writing its layout and restart
  afterwards. Prefer the active systemd user service; support KDE's quit tool and
  direct startup for other sessions. Applications and KWin are not terminated.
- Bind incoming desktop wallpaper to the target's current KDE activity. Source
  activity IDs remain excluded from public packages.
- Normalize system/Flatpak launcher paths into desktop IDs. Preserve names with
  spaces and preferred application URLs; omit unsafe entries individually.
- Read AppletOrder from the actual General group and verify source versus export.
- Fix incorrect overlap warnings for panels set to fit their content.
- After startup, query the loaded Plasma shell for primary panel IDs, widget
  order, alignment, length mode, floating state and configured wallpaper. Do not
  show success if this check fails. Detailed failures are visible in the dialog.

- If the source already contains matching additional panels, offer to exclude
  those panels from the export with explicit consent; leave the source desktop
  untouched. Revalidate the choice after Plasma has saved its configuration.

Validation: 107 offline tests, including shell lifecycle/failure handling and
rejection of wrong wallpapers, extra panels and changed widget order. KDE's live
read-only interface was checked on the source; no desktop was restored during
development. Fedora and other target desktops still require graphical validation.
Native dependencies require distribution-specific package sources; pinned apps
and games are not installed automatically. This is not a universal guarantee of
pixel-identical rendering on every Plasma version, plugin and graphics driver.

## Previous release: 1.7.8

- Rename the primary application file to `saveyourkdedesign.py`. Keep an
  identical legacy source at `savedesktopdesign.py` so existing in-app updaters
  continue to work and migrate to the canonical launcher on their next start.
- Store a privacy-safe panel-fidelity contract in public designs: panel edge,
  geometry and ordered widget plugin IDs. Verify it after Plasma remaps local
  containment IDs during import.
- Report objectively overlapping panels in the export/import log without
  changing an author's layout. This prevents silent visual surprises while
  preserving intentional custom panel setups.
- Embed available wallpaper files in new shared designs and use portable paths
  on the receiving computer.

Validation: 95 automated offline tests, including panel geometry, widget order,
legacy updater compatibility and wallpaper portability.

## Previous release: 1.7.7

- Fix the false extraction-limit failure for large private backups. Public
  packages keep their stricter limits; private backups allow 1 million entries
  and 4 GB unpacked. Unsafe legacy external links are skipped and counted, never
  followed. The reported 429,395-entry backup is covered by a local restore test.
- Embed selected external file wallpapers in new private backups, including
  file symlinks, and rebase their paths on the receiving computer. Report missing
  wallpaper files with an instruction to reconnect the drive and retry.
- Keep validated Panel Colorizer appearance JSON up to 256 KB instead of dropping
  the reported 55-KB settings at the old 8-KB limit. Private text and commands are
  still excluded from public designs.
- Remap plasmashell panel-view IDs with layout IDs so panel size, length, opacity
  and positioning settings follow their panels. Preserve linked system trays
  even when their containment has no assigned screen.
- Use Plasma's primary-output numbering, not Qt's independent screen list or
  a guess based on how many panels a screen contains.
- Fix legacy category selection and safely restore through in-home dotfile links.
  Rollback no longer follows nested external links or directory cycles.

Validation: 92 offline tests, plus extraction/restoration of the reported archive
into a temporary home without modifying the running desktop. Graphical fidelity
on Arch, Fedora and Kubuntu has not been verified end-to-end. Old codes/backups
cannot supply omitted assets: create a fresh export from the intended design.

## Previous release: 1.7.6

- Fix public imports for systems where a visual configuration directory such as
  `~/.config/gtk-3.0` is managed by a symlink into a dotfiles directory inside
  the same user home. The safe link is preserved and its previous file content
  is included in the rollback archive.
- Resolve every destination before the first write. Links outside the user home,
  broken escapes and symlink loops are still rejected.
- Write restored files through an atomic same-directory replacement, avoiding a
  truncated configuration file if a copy is interrupted.
- Find portable KWin scripts and effects by their declared plugin ID as well as
  their directory name. This supports packages whose downloaded folder was
  renamed and other enabled KWin scripts without a hard-coded allowlist.
- Support both current `metadata.json` and legacy `metadata.desktop` KWin
  packages. Missing, malformed or duplicate package identities stop the import
  before any design setting is changed.
- Replace the misleading “not installed” label for bundled extensions with
  “will be installed / wird installiert”. Bundled KWin scripts, effects and
  Plasma widgets are copied from the design and are not repository errors.

Validation includes safe relative and absolute in-home destinations, external
destinations, link loops, rollback data behind links, legacy KWin metadata,
metadata-ID/folder-name differences, malformed bundles and the full test suite.
The suite is also verified in an isolated Python 3.10 environment.

## Previous release: 1.7.4

- Remove monitor count, resolution, scale, position and enumeration from public
  import compatibility checks. Display differences no longer block anything.
- Export only Plasma containments belonging to the source primary screen.
- Apply those containments to the target primary screen, remapping containment
  and applet identifiers safely.
- Preserve target secondary-screen containments and the target ScreenMapping.
- Keep Plasma-version/session and extension checks; display configuration itself
  is never changed.
- Old SDD1 designs remain accepted. For old multi-monitor exports without an
  explicit primary marker, Plasma screen 0 is treated as the source primary.

Validation covers different monitor counts, geometry and scaling, primary-only
filtering, identifier remapping and preservation of secondary target layouts.

## Previous release: 1.7.3

- Replace the unhelpful “no verified repository provider” result for Klassy and
  Glass with a concrete, distribution-specific installation proposal.
- Arch/CachyOS/Manjaro: verify and offer AUR packages `klassy` and
  `kwin-effects-glass-git` through an installed `yay` or `paru`.
- Fedora: use `dnf` with the confirmed `errornointernet/klassy` and
  `ama1470/kwin-effects-glass` COPR repositories. Fedora never receives AUR
  commands. Both package sources were resolved in an isolated Fedora 44 test.
- Run community installation in a visible terminal so the user can inspect the
  packages, confirm the source and enter the administrator password.
- Automatically recheck the retained design after the terminal closes.
- If automatic installation is unavailable, show exact commands or upstream
  installation pages in the main message instead of only internal identifiers.
- Ubuntu/Debian keep their own route: official Klassy OBS packages and the
  Plasma-version-specific upstream Glass build instructions.

Community repositories and AUR build recipes are not part of the base
distribution and require explicit consent. A failed or cancelled command does
not apply design settings; the next check provides a manual instruction.

## Previous release: 1.7.2

- Search for and offer required KDE extension packages even while the target
  monitor layout differs from the exported layout.
- Detect installed native KWin effects by their Qt plugin files when the live
  KWin DBus interface is unavailable. This fixes false Glass/legacy-Glass errors.
- Replace the final technical-only blocker popup with action-oriented dialogs.
  Package actions explain what will happen and keep technical output in Details.
- When screen geometry is the only remaining difference, offer **Open display
  settings**. After the KDE display module closes, the retained import is
  automatically checked again; the code does not need to be entered again.
- Keep the final compatibility check before applying any design settings.

SaveYourKDEDesign does not silently change monitor geometry: applying a layout
that does not match connected hardware can make a display or windows unreachable.
Unavailable or ambiguous repository packages are shown as such and are never
replaced with unverified install scripts.

## Previous release: 1.7.1

- Detect compiled Plasma applets, including the panel, clock, launcher and tray.
- Compare monitor geometry independently of enumeration order. Actual resolution,
  position and scaling differences still block faithful import.
- Look up missing compiled applet packages in configured Ubuntu/Fedora/Arch
  repositories, alongside KWin effects and decorations.
- Automatically recheck the retained design after file-index/native installation
  and offer the next available installation. No repeated code entry is required.
- When a new Plasma login is required, reopen the app to resume automatically.
  Administrator consent and final design review remain required.
- Ignore redundant old effect requirements only when the design also explicitly
  requires the available successor.
- Export all installed styles of exact selected font families, including widget
  and GTK font settings, using anonymized filenames.

Unavailable/ambiguous providers still cannot be installed automatically. No
unverified installers, new repositories, AUR builds or distribution upgrades.
Font redistribution requires appropriate licenses. Full graphical cross-distro
installation/login/restore tests remain pending; identical appearance across
arbitrary Plasma versions or hardware is not guaranteed.

## Previous release: 1.7.0

Previously SaveDesktopDesign. Old codes, settings, rollback files and the old
launcher remain compatible. In-app updates migrate the installed menu label.
The GitHub repository is now redsoul1905/SaveYourKDEDesign; compatibility with
the old update address is retained.

## Tela-dark export fix

The former 50,000-file limit rejected legitimate themes. The consistent
export/import limit is now 200,000 files and a separately limited 16 MB manifest.
Design data remains capped at 1 GB unpacked and 200 MB uploaded. Overrides count
once; errors distinguish file counts from size. The hicolor application-icon
fallback is supplied by the target instead of publishing source application
icons and external links. A local Tela-dark export with inherited themes passed:
108,973 files, a 7.4 MB manifest and a 35.8 MB package. Nothing was uploaded.
Recipients need 1.7.0 for large packages; old export codes remain supported.

## System preparation (experimental)

- Preview and confirm KDE installation on Ubuntu, Fedora and Arch.
- Check available Plasma versions and suggest system updates.
- Display bundled widget/KWin versions and declared Plasma minimums.
- Find native KWin effect/decoration packages by Qt plugin filenames in target
  repositories. Install unique providers after preview and confirmation.
- Prepare apt-file/file indexes separately with consent. Version 1.7.1 adds
  automatic rechecking after preparation and native installation.
- No automatic distribution upgrades, new repositories, AUR builds, arbitrary
  build scripts or copying of native binaries.

Not every native extension is automatically installable. Unavailable or ambiguous
providers, nonstandard filenames, undeclared dependencies and mismatched
Plasma/session/screens still block faithful import. System packages are not
undone by design rollback and can partially install if a transaction fails.

Validation: automated archive, transfer, GUI, rename/update, package-plan and
large-theme regression tests; actual KDE package resolution in isolated Ubuntu
24.04/26.04 and Fedora 44 containers. Full graphical installation/login/restore
and pixel-identical appearance have not been verified across these systems.
Only import trusted designs: themes and widgets may execute code.

# SaveYourKDEDesign

Formerly **SaveDesktopDesign**. Existing SDD1 codes, settings and rollback files
remain compatible. The primary source file is now `saveyourkdedesign.py`;
the old filename remains as a compatibility copy so existing installations can
update without a manual migration.
The preferred launcher is now `saveyourkdedesign`.
In-app updates also migrate the standard installed menu label on next startup;
custom launchers and development checkouts are left alone. The old settings
namespace remains in use, preserving language preferences and saved codes.
GitHub: `redsoul1905/SaveYourKDEDesign`. Update compatibility with the previous
repository address is retained for existing installations.

**Current version: 1.7.8** · [Changelog](#changelog)

**New in 1.7.8:** public designs carry a panel-fidelity contract for panel
geometry and widget order. Imports verify that contract after Plasma has remapped
its local IDs. Wallpaper files are embedded in fresh exports, and possible panel
overlaps are reported without changing an author's intended layout.
Cross-distribution pixel-identical rendering still needs an actual target-session
check; offline tests do not verify graphics drivers or third-party plugin behavior.

**New in 1.7.6:** public imports now work with safe dotfile-manager links such as
`~/.config/gtk-3.0` pointing into the same user home, while links outside the
home and link loops remain blocked. KWin scripts/effects are discovered by their
declared plugin ID, including legacy packages, and bundled components are clearly
shown as being installed from the design. Restored files are replaced atomically.
Version 1.7.4 made public designs use only the exporting primary screen as the
Plasma-layout source. Monitor count, resolution, scale, position and enumeration
are no longer compared and never block import. On the target, only primary-screen
containments are replaced; layouts and screen mapping for additional monitors are
preserved. Version 1.7.3 added actionable, distribution-specific installation
paths for known community-only components:
distribution-specific installation path. Arch derivatives can install Klassy and
Glass through an existing `yay`/`paru`. Fedora uses the confirmed Klassy and
Glass COPR repositories through `dnf` and never offers AUR. The user confirms
third-party sources and enters the password in a visible terminal; the import is
automatically checked afterwards. If this is unavailable, an exact command or
upstream installation page is displayed. Version 1.7.2 added action-oriented
dependency and display dialogs.
System preparation is experimental:
full graphical guest-system installation tests are still pending.

### KDE setup during import (experimental)

The import preflight can offer to install a missing KDE desktop on Ubuntu,
regular Fedora, and Arch/Arch-derived systems, after explicit confirmation and
administrator authentication. The repository candidate for Plasma must match
the exported upstream Plasma version. Ubuntu uses `kde-plasma-desktop` without
recommended packages, with the KDE administrator-authentication agent and the separate Wayland session when available and
needed; Fedora uses `@kde-desktop-environment`; Arch uses `plasma-meta`. Existing
desktop environments are not removed and the login manager is not explicitly
switched. Repository metadata may need refreshing through the system updater.
Before consent, a non-privileged package-solver preview is available under
**Details**, including the transaction summary when provided by the manager.
If the preview fails, installation is not offered. Arch with pending package
updates must be fully updated first; this flow does not perform partial updates.

When an existing Plasma installation needs an available matching update, the
app recommends the system updater; it does not perform distribution upgrades,
add repositories, or downgrade Plasma. Fedora Atomic/Silverblue/Kinoite is
detected and excluded from this package-install path. Unknown distributions
receive guidance rather than a guessed installation command.

After KDE installation, log out, select Plasma and reopen the app. The saved import
resumes automatically, downloading and verifying the code again. No design settings are applied from a GNOME
session, even if KDE packages are already installed. Package installations are
not covered by the design-file rollback. A failed transaction can have partially
installed packages; use the system package manager to inspect/recover it.

The import review lists bundled widgets, wallpaper plugins and KWin scripts/
effects with JSON metadata, comparing local and bundled versions. Declared
Plasma minimum versions block incompatible imports, including at the final
restore check. The bundled version replaces the local version, even if older;
this preserves the export rather than silently selecting a different latest
version. Legacy metadata, undeclared QML/native dependencies and runtime API
compatibility are not fully resolved. Missing native KWin effects/decorations
are looked up by scoped Qt/KWin plugin filenames in target repositories using
apt-file, dnf repoquery or pacman's file database. Unique providers can be
installed after preview and confirmation. Ambiguous/missing providers are not
guessed. File indexes can be prepared separately with consent. After index or native
package installation, the retained archive is automatically rechecked and the next
available installation is offered. Repeated installation attempts are stopped. If a
new Plasma login is needed, reopen the app afterwards to resume the saved import.
Compiled Plasma applets are detected in Qt plugin directories and missing providers
are looked up in the same distribution file indexes. Known community components
have explicit, separate routes: Arch derivatives may offer AUR packages `klassy`
and `kwin-effects-glass-git` through an existing `yay`/`paru`; Fedora may offer
`klassy` and `kwin-effects-glass` from their confirmed COPR repositories through
`dnf`. Fedora never receives AUR commands. Adding these community sources requires
explicit confirmation in a visible terminal. No arbitrary PPA or unknown build
script is selected. The Kvantum
mapping remains available. Nonstandard filenames, unindexed packages, native
binaries inside theme payloads and undeclared dependencies may still require
manual setup. This is not an arbitrary-plugin installer.
Plasma version and session checks still apply. Screen geometry is deliberately
ignored: the source primary-screen layout is mapped onto the target primary screen
without changing display settings. Secondary target-screen containments and KDE's
screen mapping are retained. This is not yet a universal one-click clone across
arbitrary KDE releases.

Validation: offline mocked Ubuntu/Fedora/Arch repositories and administrator
transactions, minimum-version checks, cancellation and active-session checks.
No real operating system packages are installed by the tests. Additional real
repository checks on 2026-10-10 resolved the installation on Ubuntu 24.04 and
26.04 (`apt-get --simulate`) and Fedora 44 (`dnf --assumeno`) in disposable
containers. The offered Plasma versions were 5.27.12, 6.6.6 and 6.7.5 respectively. These are not
full desktop tests: VM installation/relogin/restore verification is still
pending. Fedora's empty-container plan included about 3 GiB of
downloads; actual desktop transactions differ and must be reviewed.
Package choices follow the [Ubuntu package catalog](https://packages.ubuntu.com/kde-plasma-desktop)
and [Fedora KDE instructions](https://fedoraproject.org/wiki/KDE).

Backs up your **entire KDE Plasma design from A to Z into a single file** — and restores it on a new machine with one click.

Works on **Arch-based systems (CachyOS, EndeavourOS …), Ubuntu/Debian and Fedora** — anywhere KDE Plasma runs.

🌍 **Languages:** English · Deutsch · Français · Italiano · Español · Português · Türkçe — auto-detects your system language, switchable in the app.

![Previous-version screenshot (before the SaveYourKDEDesign rename)](screenshot.png)

## What gets backed up?

| Category | Contents |
|---|---|
| Plasma & KWin | Global themes (incl. `kdedefaults`), panel layouts, shortcuts, window rules, Krohnkite/script settings, session autostart |
| GTK & Kvantum | Glass/Kvantum themes, GTK 2/3/4 configuration |
| Themes & icons | Desktop themes, look-and-feel, window decorations (Aurorae), color schemes, icons, cursors |
| Fonts | Custom fonts incl. fontconfig |
| KWin scripts & effects | Krohnkite & co. from `~/.local/share/kwin` |
| Wallpapers & more | Wallpapers, Konsole profiles |
| Package lists | pacman (explicit) & AUR, enabled repositories, apt (manual), dnf (user-installed), Flatpak — e.g. for Rounded Corners, Force Blur, Kvantum |

> **Note:** Compiled KWin plugins (e.g. Rounded Corners) live in system directories and are reinstalled via the **package list**, not copied as files.
> Package restore works between machines of the **same distro family** (Arch→Arch, Ubuntu→Ubuntu, Fedora→Fedora); the design files themselves restore on any distro.

> **What is *not* included:** anything outside your home directory — `/etc` (including your enabled repositories), SDDM and GRUB themes, systemd services.
> On Arch, packages from extra repositories (`chaotic-aur`, `cachyos-*` …) appear as ordinary native packages in the list and are silently skipped if that repository is missing on the target machine. The backup therefore also stores `pacman-repos.txt`, and the generated install script compares both repository lists before it starts.

## Installation

**Arch / CachyOS / EndeavourOS:**
```bash
sudo pacman -S --needed git python python-pyqt6
```

**Ubuntu / Debian:**
```bash
sudo apt install git python3 python3-pyqt6
```

**Fedora:**
```bash
sudo dnf install git python3 python3-pyqt6
```

Then:
```bash
git clone https://github.com/redsoul1905/SaveYourKDEDesign.git
cd SaveYourKDEDesign
./install.sh
```

You'll then find **SaveYourKDEDesign** in your application menu.

Run directly without installing:

```bash
python3 saveyourkdedesign.py
```

## Usage

### Share a design with a code (new in 1.6)

**Large icon themes (fixed in 1.7):** up to 200,000 design files and a separately
bounded 16 MB manifest. Design data remains limited to 1 GB unpacked and 200 MB
uploaded. Overrides count once. `hicolor` is supplied by the target rather than
exporting application-owned icons/links. Tela-dark plus inherited themes was
tested locally: 108,973 files, a 7.4 MB manifest and a 35.8 MB package passed archive
validation, without an upload. Recipients must update before importing large
packages; older codes remain supported in 1.7.0.

1. Open **Share design → Create export code** (Deutsch: **Design teilen → Export-Code erstellen**).
2. Review the public-upload notice. After confirmation the app builds a separate
   visual design package and uploads it to **Catbox**, without an account.
3. Click **Copy code** and share the complete `SDD1:…` code on Reddit or with friends.
   The last successful code is remembered across app restarts.
4. On another PC, open **Share design → Import code** and paste the code. The app
   downloads the package automatically, verifies its SHA-256 checksum and archive
   paths, and checks the target desktop before offering to apply it.
5. If needed, the app can install the **Kvantum Qt 6 engine** from the target's
   configured repositories (`kvantum` on Arch/Fedora, `qt6-style-kvantum` on
   Debian/Ubuntu). Installation requires administrator authentication via `pkexec`.
   Other missing native extensions are reported and must be installed separately.
6. Confirm the trusted design, then log out and back in after import. Existing
   files are backed up using the application's rollback feature first.

**Public sharing is not a full private backup.** It exports an allowlist of visual
settings and the selected themes, icons, cursor themes, wallpapers, fonts, widgets
and available KWin scripts/effects. System-wide selected theme assets are copied
into user-level locations for portability. The export excludes the full package
list, hostname, username, archive ownership metadata, autostart configuration,
arbitrary widget commands, notes and unknown settings. The number of omitted
settings is shown. Selected theme/widget assets and wallpapers can themselves
contain personal material; review them before publishing. Only redistribute
assets whose licenses allow it. Use the existing **Back up** tab for private backups.

**Compatibility is conservative, not a promise of pixel-identical rendering.**
Public import currently requires the same full Plasma version and session type
(Wayland/X11). Screen geometry/scaling is ignored; only the exported primary-screen
layout is applied to the target primary screen. Native styles, decorations
and enabled effects must be available. Differences stop import before design
settings are written. Matching these checks does **not** prove identical rendering:
Qt/plugin versions, GPU drivers, color management, custom widget settings and
other unexported configuration can still differ. Installation commands are fixed
local mappings and never come from a downloaded manifest. Community repositories
or AUR builds are offered only for known components with explicit consent. A
universal one-click clone across arbitrary Plasma versions is not implemented.
Standard private-backup package lists still target the same distro family.

**Catbox limits:** maximum 200 MB per package; no splitting to bypass the limit.
Codes can be reused while the file is hosted; the exporting PC can be offline.
The provider currently says anonymous uploads expire after two years without
access. Availability is not guaranteed and some networks block Catbox. Catbox
itself is not open source. Keep a local backup. See the
[Catbox API](https://catbox.moe/tools.php), [FAQ](https://catbox.moe/faq.php) and
[terms](https://catbox.moe/legal.php); commercial use needs their prior approval.

**Trust:** the checksum detects changes to a downloaded file; it does not certify
its author or make it safe. KDE themes, widgets and scripts can execute code when
loaded. Only apply designs from trusted authors. Public archives cannot contain
symlinks, device files, arbitrary home paths or private package-install scripts.
Downloads and decompressed archives have size and file-count limits. Rollback
restores overwritten files, not newly added assets or installed packages.

The new sharing interface is available in German and English; other app languages
use English for the new sharing messages.

### Private backup and restore

**Back up (old machine):**
1. Launch the app → **Back up** tab
2. Select categories (default: everything) → **Create backup**
3. Copy the resulting `.tar.gz` to a USB drive / cloud storage

**Restore (new machine):**
1. Launch the app → **Restore** tab → choose the archive
2. Pick which categories should come back — you don't have to take the whole archive. Leave **Back up the current state first** ticked so you can undo the restore.
3. Click **Install packages** (opens a terminal; automatically uses `pacman`/`paru`/`yay`, `apt`, `dnf` or `flatpak` depending on your system)
4. **Log out and back in** so KWin effects and the design fully apply

Not happy with the result? **Roll back to the state before the last restore** puts your previous settings back. Note that it restores what was overwritten — files the restore *added* stay, so a newly installed icon theme remains on disk.

**The archive carries the app itself**, so a brand-new machine needs neither git nor an install first:

```bash
tar xzf plasma-design-2026-09-04.tar.gz app/saveyourkdedesign.py
python3 app/saveyourkdedesign.py
```

## Update

**From inside the app (v1.4.0 and newer):** click **Check for updates** in the top bar. It queries the latest GitHub release, shows you the release notes, and — if you confirm — replaces the installed file and offers to restart. No terminal, no git, no extra dependency.

The downloaded file is only installed if it is recognisably this application and compiles without errors; the previous version is kept next to it as `saveyourkdedesign.py.bak`. If you run the app from a git clone, the button points you to `./install.sh --update` instead of overwriting your working copy.

**From a git clone:** one command — pulls the latest version and reinstalls:

```bash
./install.sh --update
```

> Installed an older version (before v1.2.1)? Run this once inside your cloned folder, afterwards `--update` is available:
> ```bash
> git pull && ./install.sh
> ```

Or do a completely fresh install (deletes the old folder first):

```bash
cd ~/SaveYourKDEDesign && ./install.sh --update
```

## Uninstall

```bash
./install.sh --uninstall
```

## Requirements

- Linux with KDE Plasma — Arch-based (CachyOS, EndeavourOS …), Ubuntu/Debian or Fedora
- Python 3.10+ and PyQt6 (`python-pyqt6` on Arch, `python3-pyqt6` on Ubuntu/Fedora)
- Optional: `paru`/`yay` for AUR packages, `flatpak`

## Changelog

### v1.7.7

- Keep large, validated Panel Colorizer appearance settings while rejecting
  free-form private text, commands and paths.
- Remap panel-view IDs together with containment IDs; retain secondary panels
  and linked system-tray containments.
- Embed external file wallpapers in new private backups and rebase their paths
  on restore. An unavailable file wallpaper produces a reconnect-and-retry error.
- Separate local backup extraction limits (1 million entries / 4 GB unpacked)
  from public sharing limits. Skip unsafe external links in legacy private
  archives without following them; report the skipped count.
- Preserve legacy category selection and safe in-home dotfile-manager links.
- Add regression coverage for layout fidelity, wallpaper portability and rollback.

### v1.7.6

- Safe in-home dotfile symlinks are preserved during public import and their
  actual contents are covered by rollback; external and cyclic links are rejected.
- Portable KWin scripts/effects are matched by plugin metadata ID, not only by
  folder name, with support for modern and legacy metadata formats.
- Bundled extensions are validated before any settings change and are labelled
  as installed from the design instead of incorrectly appearing as missing.
- Individual restored files use atomic replacement.

### v1.6.0

- Catbox upload and import in a new **Share design** tab, without a Catbox account.
- Reusable, copyable `SDD1` codes containing the file ID and full SHA-256 digest.
- Separate public visual-export format with selected user/system theme assets,
  bundled wallpapers/fonts, reduced settings, and anonymous tar metadata.
- Strict archive validation, fixed Catbox endpoints, rejected redirects, bounded
  downloads/extraction, and checksum verification before importing.
- Plasma/session/screen compatibility checks and missing-native-component reporting;
  locally defined Kvantum package mapping for Arch, Debian/Ubuntu and Fedora.
- Private restore extraction also rejects unsafe links and paths. Restores stop
  on rollback/copy failures instead of reporting success after skipped writes.
  Legacy archives containing absolute or external symlinks now fail explicitly;
  they are no longer restored with the old permissive extraction behavior.
- Automated offline security, transfer, GUI and backup/rollback tests; an optional
  live Catbox probe uses only a tiny synthetic fixture.

### v1.5.0

- **A safety net under every restore.** Before anything is overwritten, the current state of exactly those paths is saved to `~/.savedesktopdesign-rollback.tar.gz`, and **Roll back to the state before the last restore** puts it back. Can be switched off per restore. It restores what was overwritten; files the restore added are not removed.
- **Selective restore.** The restore dialog now lists the categories the archive contains and lets you pick — take the icons from the old machine without its three-monitor panel layout. Archives without a manifest keep the old behaviour and restore everything.
- **The archive carries the app.** `saveyourkdedesign.py` is bundled as `app/saveyourkdedesign.py`, so a fresh machine needs no git clone and no install first: unpack that one file and run it.
- Restores are now path-exact instead of merging whole top-level directories, which is what makes the selection and the rollback precise.

### v1.4.0

- **One-click update from inside the app.** A **Check for updates** button in the top bar reads the latest GitHub release, shows its notes, and installs the new version on confirmation — then offers to restart. Uses only the Python standard library, no token and no extra dependency.
- **The installed version is shown next to the button** and tells you where you stand: `v1.4.0`, `v1.4.0 · up to date`, or `v1.4.0 · update to 1.4.1 available` in bold. A silent check at startup keeps it current — it only ever changes that label, never opens a dialog, and never blocks a backup or restore. Turn it off with **Check at startup**; the choice is remembered.
- The update is written atomically and only after the download has been verified: it must be recognisably this application and compile cleanly, otherwise nothing is touched. The previous version stays as `saveyourkdedesign.py.bak`.
- Running from a git clone is detected — the button points to `./install.sh --update` rather than overwriting your working copy.

### v1.3.3
Bug-fix release — every issue below was reproduced before it was fixed.

- **Fixed a crash:** backup and restore shared a single worker reference, so starting a restore while a backup was still running dropped the running `QThread` and aborted the app (`QThread: Destroyed while thread is still running`). Both now have their own reference; buttons and the language selector are locked for the duration of a job, and the window refuses to close while a thread is alive.
- **Fixed a false failure report:** if `fc-cache` was missing, restore raised `FileNotFoundError` *after* all files had already been copied back and reported "restore failed". Post-processing (font cache, KWin reconfigure, `kbuildsycoca`) now runs step by step and no longer invalidates a successful restore.
- **Fixed package-only backups:** an archive created with no category selected contains no `home/` folder and could not be restored at all — the package lists inside were ignored.
- **Fixed the language selector** resetting the log and progress bar of a running job.
- **More settings backed up:** `kdedefaults` (the global theme defaults — without it a restored global theme only applied halfway), `plasma-localerc`, `kactivitymanagerdrc`, `systemsettingsrc`, `plasma-workspace`.
- **Repository awareness:** backups now include `pacman-repos.txt`; the generated install script shows which repositories the old machine had before packages get skipped.
- Completed the French, Italian, Spanish, Portuguese and Turkish translations (7 keys were falling back to English).
- `install.sh --update` now reports local changes instead of exiting silently through `set -e`.
- Terminal commands and paths are quoted (`shlex`), so a home directory containing spaces no longer breaks package installation.
- Removed a hardcoded local path from `savedesktopdesign.desktop`.

### v1.3
- Automatically installs `paru` if no AUR helper is present.
- Backs up window decoration configs (Klassy, Lightly, SierraBreezeEnhanced).

### v1.2.2
- Reloads the KWin configuration after a restore so Krohnkite gaps and effects apply immediately.
- Added `./install.sh --update`.

### v1.2
- Ubuntu/Debian (apt) and Fedora (dnf) support.
- Restore replaces existing files and symlinks instead of failing with `Errno 17`.

### v1.1
- Seven languages (DE/EN/FR/IT/ES/PT/TR) with auto-detection and a language selector.

### v1.0
- Initial release.

## License

MIT — see [LICENSE](LICENSE).

## Development checks

With Python 3.10+ and PyQt6 installed:

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
python3 -m py_compile saveyourkdedesign.py
```

An opt-in integration check publishes a tiny **synthetic** package to Catbox and
downloads it by its generated code. It never reads or changes your desktop. The
anonymous test upload may remain on Catbox, so this is not run by CI:

```bash
python3 tests/live_catbox_probe.py --upload-synthetic-fixture
```

GitHub Actions runs the offline suite on Python 3.10, 3.12 and 3.13. Pushing a
version tag such as `v1.6.0` publishes a GitHub release only after all three test
jobs pass and the tag matches `VERSION`. Release text comes from
`RELEASE_NOTES.md`; `saveyourkdedesign.py` is attached as a downloadable asset.

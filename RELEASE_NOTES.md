# SaveYourKDEDesign 1.7.3

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

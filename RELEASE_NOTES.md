# SaveYourKDEDesign 1.7.1

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

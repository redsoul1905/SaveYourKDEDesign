# SaveYourKDEDesign 1.7.0

Previously SaveDesktopDesign. Old codes, settings, rollback files and the old
launcher remain compatible. In-app updates migrate the installed menu label.
The GitHub address remains unchanged until its owner completes the repository
rename; updates include a fallback during the transition.

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
- Prepare apt-file/file indexes separately with consent. Re-import after index
  preparation; log into Plasma again after plugin installation and re-import.
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

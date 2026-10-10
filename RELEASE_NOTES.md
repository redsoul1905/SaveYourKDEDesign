# SaveDesktopDesign 1.6.0 — Catbox sharing

Share a KDE design using a reusable code: create the public package, upload it
directly to Catbox, copy the code, and import it on another PC. Neither a Catbox
account nor an online source PC is needed to download an existing package.

The new Share design tab includes automatic upload/download, SHA-256 verification,
strict archive validation and a compatibility review before applying settings.
Public exports contain selected visual settings and assets, separately from full
private backups. The latest successful code is remembered.

Kvantum's Qt 6 engine can be installed through the target system's package manager
on Arch, Debian/Ubuntu and Fedora, with administrator authentication. Other missing
native components stop import and are reported. The importer requires matching
Plasma version, session type and screen geometry/scaling. It does not guarantee
pixel-identical appearance across machines or automatically resolve every native
extension. Unknown/private settings are omitted from public packages.

Catbox permits packages up to 200 MB. Anonymous files currently expire after two
years without access; hosting availability is not guaranteed. Keep local backups.
Only publish assets you may redistribute and only import from trusted authors:
KDE theme/widget code may run when loaded, even after archive validation.

Private restore extraction has also been hardened. Unsafe external/absolute links
are rejected, and rollback or file-copy errors stop restoration.

Validation: offline transfer/security/GUI and backup/rollback tests, plus a real
Catbox upload/download/checksum round trip using a tiny synthetic fixture. Full
visual equivalence across real Arch, Kubuntu and Fedora desktops has not been tested.

"""Regression tests for compiled Plasma applets and automatic import continuation."""
import unittest
import tarfile
from pathlib import Path
from unittest.mock import patch, Mock
import test_sharing as fixtures
from test_sharing import app, PROFILE, manifest, archive_file


class ImportContinuationTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown

    def test_safe_internal_dotfile_symlink_is_preserved_and_rolled_back(self):
        real = self.home / ".dotfiles/gtk-3.0"
        real.mkdir(parents=True)
        (real / "settings.ini").write_text("old")
        config = self.home / ".config"
        config.mkdir()
        (config / "gtk-3.0").symlink_to("../.dotfiles/gtk-3.0")
        rel = ".config/gtk-3.0/settings.ini"
        path = self.root / "design.sdd"
        archive_file(path, [("home/" + rel, b"new")], manifest([rel]))
        worker = app.RestoreWorker(str(path), public=True, screens=PROFILE["screens"])
        failures = []
        worker.failed.connect(failures.append)
        with patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app.RestoreWorker, "_post_restore"):
            worker.run()
        self.assertEqual(failures, [])
        self.assertTrue((config / "gtk-3.0").is_symlink())
        self.assertEqual((real / "settings.ini").read_text(), "new")
        with tarfile.open(app.rollback_path(), "r:gz") as archive:
            self.assertEqual(archive.extractfile("home/" + rel).read(), b"old")

    def test_public_restore_rejects_symlink_outside_home_before_writing(self):
        outside = self.root / "outside"
        outside.mkdir()
        config = self.home / ".config"
        config.mkdir()
        (config / "gtk-3.0").symlink_to(outside)
        rel = ".config/gtk-3.0/settings.ini"
        path = self.root / "design.sdd"
        archive_file(path, [("home/" + rel, b"new")], manifest([rel]))
        worker = app.RestoreWorker(str(path), public=True, screens=PROFILE["screens"])
        failures = []
        worker.failed.connect(failures.append)
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            worker.run()
        self.assertTrue(failures)
        self.assertFalse((outside / "settings.ini").exists())

    def test_public_restore_rejects_cyclic_target_symlink(self):
        config = self.home / ".config"
        config.mkdir()
        (config / "gtk-3.0").symlink_to("gtk-4.0")
        (config / "gtk-4.0").symlink_to("gtk-3.0")
        with self.assertRaises(ValueError):
            app.safe_public_restore_target(".config/gtk-3.0/settings.ini")

    def test_absolute_symlink_inside_home_is_allowed(self):
        real = self.home / ".dotfiles/gtk-4.0"
        real.mkdir(parents=True)
        config = self.home / ".config"
        config.mkdir()
        (config / "gtk-4.0").symlink_to(real)
        self.assertEqual(app.safe_public_restore_target(".config/gtk-4.0/settings.ini"),
                         real / "settings.ini")

    def test_screens_never_block_primary_design_import(self):
        first = PROFILE["screens"][0]
        second = {**first, "x": 1920}
        source = {**PROFILE, "screens": [first, second]}
        target = {**PROFILE, "screens": [second, first]}
        doc = {**manifest(), "profile": source}
        self.assertTrue(app.matching_profile(source, target))
        self.assertEqual(app.compatibility_issues(doc, target, []), [])
        target["screens"] = [first, {**second, "scale": 2}]
        self.assertTrue(app.matching_profile(source, target))
        self.assertEqual(app.compatibility_issues(doc, target, []), [])

    def test_export_keeps_only_primary_screen_containments(self):
        values = [
            ("[Containments][10]", "lastScreen", "0"),
            ("[Containments][10]", "plugin", "primary.desktop"),
            ("[Containments][10][Applets][11]", "plugin", "primary.applet"),
            ("[Containments][20]", "lastScreen", "1"),
            ("[Containments][20]", "plugin", "secondary.desktop"),
            ("[ScreenMapping]", "itemsOnDisabledScreens", "secret-machine-map"),
        ]
        result = app.primary_layout_values(values, 0)
        self.assertIn(("[Containments][10]", "plugin", "primary.desktop"), result)
        self.assertIn(("[Containments][10][Applets][11]", "plugin", "primary.applet"), result)
        self.assertFalse(any("secondary" in value for _, _, value in result))
        self.assertFalse(any(group == "[ScreenMapping]" for group, _, _ in result))

    def test_restore_replaces_primary_layout_and_preserves_secondary(self):
        source = """[Containments][1]
lastScreen=0
plugin=source.secondary
[Containments][2]
lastScreen=1
plugin=source.primary
AppletOrder=3
[Containments][2][Applets][3]
plugin=source.clock
"""
        target = """[Containments][10]
lastScreen=0
plugin=old.primary
[Containments][2]
lastScreen=1
plugin=target.secondary
[ScreenMapping]
foo=bar
"""
        merged = app.merge_primary_applet_config(source, target, 1, 0)
        self.assertNotIn("old.primary", merged)
        self.assertNotIn("source.secondary", merged)
        self.assertIn("target.secondary", merged)
        self.assertIn("source.primary", merged)
        self.assertIn("source.clock", merged)
        self.assertIn("lastScreen=0", merged)
        self.assertIn("[ScreenMapping]\nfoo=bar", merged)
        self.assertNotIn("[Containments][2]\nlastScreen=0\nplugin=source.primary", merged)

    def test_missing_source_primary_never_erases_target(self):
        target = "[Containments][1]\nlastScreen=0\nplugin=keep.me\n"
        source = "[Containments][2]\nlastScreen=1\nplugin=other.screen\n"
        self.assertEqual(app.merge_primary_applet_config(source, target, 0, 0), target)

    def test_compiled_applets_are_detected_without_allowlisting_unknown_ids(self):
        root = self.root / "plugins"
        plugin = root / "plasma/applets/org.kde.plasma.digitalclock.so"
        plugin.parent.mkdir(parents=True)
        plugin.touch()
        doc = manifest()
        doc["requirements"] = [{"kind": "asset", "name": "plasma/plasmoids/" + name}
                               for name in ("org.kde.plasma.digitalclock", "unknown.widget")]
        with patch.object(app, "plugin_roots", return_value=[root]), patch.object(Path, "exists", return_value=False):
            self.assertEqual(app.compatibility_issues(doc, PROFILE, []),
                             ["asset: plasma/plasmoids/unknown.widget"])

    def test_stale_effect_key_requires_explicit_available_successor(self):
        doc = manifest()
        old = {"kind": "effect", "name": "kwin4_effect_glass"}
        doc["requirements"] = [old, {"kind": "effect", "name": "glass"}]
        with patch.object(app.shutil, "which", return_value="qdbus6"), patch.object(app, "_run_cmd", return_value="glass\n"), \
                patch.object(app, "native_effect_available", return_value=False):
            self.assertEqual(app.compatibility_issues(doc, PROFILE, []), [])
            doc["requirements"] = [old]
            self.assertEqual(app.compatibility_issues(doc, PROFILE, []), ["effect: kwin4_effect_glass"])

    def test_recheck_uses_validated_local_archive_without_upload_or_download(self):
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
        worker = app.ShareWorker(PROFILE["screens"], dest=path, recheck=True)
        results, errors = [], []
        worker.ready.connect(lambda value, details: results.append(details))
        worker.failed.connect(errors.append)
        with patch.object(app, "download_design") as download, patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app, "native_extension_plan", return_value={"command": None}):
            worker.run()
        download.assert_not_called()
        self.assertEqual(errors, [])
        self.assertEqual(results[0]["issues"], [])

    def test_exact_font_family_exports_all_styles_not_fallback(self):
        regular, bold = self.root / "regular.ttf", self.root / "bold.ttf"
        regular.write_bytes(b"regular")
        bold.write_bytes(b"bold")
        output = f"Example,Localized Example\t{regular}\nExample\t{bold}\n"
        with patch.object(app, "_run_cmd", return_value=output):
            self.assertEqual(set(app.selected_font_files("Example")), {regular, bold})
            self.assertEqual(app.selected_font_files("Missing Font"), [])

    def test_native_success_starts_recheck_instead_of_deleting_download(self):
        window = Mock()
        window._share_outcome = ("/tmp/design.sdd", {"manifest": manifest(), "native_installed": True})
        with patch.object(app, "screen_profile", return_value=PROFILE["screens"]), \
                patch.object(app.QStyleFactory, "keys", return_value=[]):
            app.MainWindow._share_finished(window)
        window._clean_share_temp.assert_not_called()
        worker = window._start_share.call_args.args[0]
        self.assertTrue(worker.recheck)
        self.assertEqual(worker.dest, Path("/tmp/design.sdd"))

    def test_widget_and_gtk_fonts_are_bundled_anonymously(self):
        font = self.root / "personal-font.ttf"
        font.write_bytes(b"test font")
        def config(path):
            if "kdedefaults" in str(path):
                return []
            if path.name == "plasma-org.kde.plasma.desktop-appletsrc":
                return [("[Containments][1][Applets][2][Configuration]", "fontFamily", "Example")]
            if path.name == "settings.ini":
                return [("[Settings]", "gtk-font-name", "Example 11")]
            return []
        stage = self.root / "stage"
        stage.mkdir()
        with patch.object(app, "read_kconfig", side_effect=config), \
                patch.object(app, "selected_font_files", return_value=[font]) as fonts, \
                patch.object(app, "desktop_profile", return_value=PROFILE):
            doc = app.public_design(stage, PROFILE["screens"])
        bundled = [p for p in doc["paths"] if p.startswith(".local/share/fonts/")]
        self.assertEqual(len(bundled), 1)
        self.assertNotIn("personal", bundled[0])
        self.assertEqual((stage / "home" / bundled[0]).read_bytes(), b"test font")
        self.assertEqual(fonts.call_args.args, ("Example",))

    def test_kwin_script_is_found_by_plugin_id_not_folder_name(self):
        script = self.home / ".local/share/kwin/scripts/download-folder"
        (script / "contents/code").mkdir(parents=True)
        (script / "metadata.json").write_text(
            '{"KPlugin":{"Id":"real.script.id","Version":"1.2"}}')
        (script / "contents/code/main.js").write_text("// portable script")
        config = self.home / ".config/kwinrc"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text("[Plugins]\nreal.script.idEnabled=true\n")
        stage = self.root / "stage"
        stage.mkdir()
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            doc = app.public_design(stage, PROFILE["screens"])
        target = ".local/share/kwin/scripts/real.script.id/metadata.json"
        self.assertIn(target, doc["paths"])
        self.assertEqual(app.extension_package_info(stage / "home/.local/share/kwin/scripts/real.script.id")["id"],
                         "real.script.id")

    def test_resume_consumes_flag_and_downloads_saved_code(self):
        window = Mock()
        code = "SDD1:abcdef.sdd:" + "a" * 64
        window.settings.value.return_value = code
        window._worker_running.return_value = False
        app.MainWindow._resume_import(window)
        window.settings.setValue.assert_called_once_with("resume_import_after_login", False)
        window._download_import.assert_called_once_with(code)

    def test_compiled_widget_provider_is_resolved_on_fedora(self):
        doc = manifest()
        name = "plasma/plasmoids/org.kde.plasma.digitalclock"
        doc["requirements"] = [{"kind": "asset", "name": name}]
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "fedora"}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(Path, "exists", return_value=False), \
                patch.object(app, "_run_cmd", return_value="plasma-workspace\n") as query:
            result = app.native_extension_plan(doc, PROFILE, [], ["asset: " + name])
        self.assertEqual(result["command"], ["dnf", "install", "-y", "plasma-workspace"])
        self.assertIn("*/qt6/plugins/plasma/applets/org.kde.plasma.digitalclock.so", query.call_args.args[0])

    def test_same_native_transaction_is_not_offered_in_a_loop(self):
        window = Mock()
        command = ["dnf", "install", "-y", "example"]
        window._attempted_installs = {tuple(command)}
        details = {"manifest": manifest(), "issues": ["effect: example"],
                   "native": {"command": command, "notes": [], "providers": []}}
        window._share_outcome = ("/tmp/design.sdd", details)
        dialog = Mock()
        with patch.object(app, "QMessageBox", return_value=dialog):
            app.MainWindow._share_finished(window)
        window._start_share.assert_not_called()
        window.settings.setValue.assert_called_once_with("resume_import_after_login", True)
        self.assertIsNone(details["native"]["command"])

    def test_screen_mismatch_does_not_block_extension_package_lookup(self):
        doc = manifest()
        doc["requirements"] = [{"kind": "effect", "name": "example"}]
        target = {**PROFILE, "screens": [{**PROFILE["screens"][0], "x": 200}]}
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "fedora"}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(Path, "exists", return_value=False), \
                patch.object(app, "_run_cmd", return_value="kwin-effect-example\n"):
            result = app.native_extension_plan(doc, target, [], ["screens: mismatch", "effect: example"])
        self.assertEqual(result["command"], ["dnf", "install", "-y", "kwin-effect-example"])

    def test_effect_file_detection_survives_unavailable_dbus(self):
        root = self.root / "plugins"
        effect = root / "kwin/effects/plugins/glass.so"
        effect.parent.mkdir(parents=True)
        effect.touch()
        with patch.object(app, "plugin_roots", return_value=[root]):
            self.assertTrue(app.native_effect_available("glass", PROFILE))
            self.assertTrue(app.native_effect_available("kwin4_effect_glass", PROFILE))
            self.assertFalse(app.native_effect_available("missing", PROFILE))

    def test_known_arch_community_extensions_offer_interactive_install(self):
        doc = manifest()
        doc["requirements"] = [
            {"kind": "decoration", "name": "org.kde.klassy"},
            {"kind": "effect", "name": "glass"},
            {"kind": "effect", "name": "kwin4_effect_glass"},
        ]
        issues = [r["kind"] + ": " + r["name"] for r in doc["requirements"]]
        target = {**PROFILE, "screens": [{**PROFILE["screens"][0], "x": 500}]}
        def executable(name):
            return "/usr/bin/" + name if name in ("yay", "konsole") else None
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "cachyos", "ID_LIKE": "arch"}), \
                patch.object(app.shutil, "which", side_effect=executable), \
                patch.object(app, "_run_cmd", return_value="Repository: aur\nName: verified\n") as query:
            plan = app.community_extension_plan(doc, target, issues)
        self.assertEqual(plan["command"], ["/usr/bin/yay", "-S", "--needed",
                                           "klassy", "kwin-effects-glass-git"])
        self.assertEqual(plan["terminal"], "/usr/bin/konsole")
        self.assertEqual(query.call_count, 2)

    def test_community_plan_gives_exact_fallback_without_aur_helper(self):
        doc = manifest()
        doc["requirements"] = [{"kind": "decoration", "name": "org.kde.klassy"}]
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "arch"}), \
                patch.object(app.shutil, "which", return_value=None):
            plan = app.community_extension_plan(doc, PROFILE, ["decoration: org.kde.klassy"])
        self.assertIsNone(plan["command"])
        self.assertIn("yay -S --needed klassy", plan["notes"][0])

    def test_fedora_uses_copr_not_aur(self):
        doc = manifest()
        doc["requirements"] = [{"kind": "decoration", "name": "org.kde.klassy"},
                               {"kind": "effect", "name": "glass"}]
        issues = ["decoration: org.kde.klassy", "effect: glass"]
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "fedora"}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n):
            plan = app.community_extension_plan(doc, PROFILE, issues)
        self.assertEqual(plan["kind"], "fedora_copr")
        self.assertNotIn("yay", plan["manual_command"])
        self.assertNotIn("paru", plan["manual_command"])
        self.assertIn("errornointernet/klassy", plan["manual_command"])
        self.assertIn("ama1470/kwin-effects-glass", plan["manual_command"])
        self.assertEqual(plan["command"][:2], ["/usr/bin/bash", "-lc"])

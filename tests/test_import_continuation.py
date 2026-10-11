"""Regression tests for compiled Plasma applets and automatic import continuation."""
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import test_sharing as fixtures
from test_sharing import app, PROFILE, manifest, archive_file


class ImportContinuationTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown

    def test_screen_order_is_not_a_layout_difference(self):
        first = PROFILE["screens"][0]
        second = {**first, "x": 1920}
        source = {**PROFILE, "screens": [first, second]}
        target = {**PROFILE, "screens": [second, first]}
        doc = {**manifest(), "profile": source}
        self.assertTrue(app.matching_profile(source, target))
        self.assertEqual(app.compatibility_issues(doc, target, []), [])
        target["screens"] = [first, {**second, "scale": 2}]
        self.assertFalse(app.matching_profile(source, target))
        self.assertTrue(app.compatibility_issues(doc, target, []))

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

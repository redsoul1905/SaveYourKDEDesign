"""Rename/update/launcher regression tests; installs only into a temporary home."""
import ast
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import savedesktopdesign as app


class RenameTests(unittest.TestCase):
    def test_stable_release_updates_development_build(self):
        self.assertGreater(app._version_tuple("v1.7.0"), app._version_tuple("1.7.0-dev"))
        self.assertGreater(app._version_tuple("1.8.0-dev"), app._version_tuple("1.7.0"))
        self.assertEqual(app._version_tuple("v1.7"), app._version_tuple("1.7.0"))

    def test_old_update_client_recognizes_renamed_source(self):
        source = Path(app.__file__).read_text()
        self.assertGreater(len(source), 20000)
        self.assertIn("SaveDesktopDesign", source)
        self.assertIn("class MainWindow", source)
        compile(source, "download.py", "exec")
        self.assertEqual(app.APP_NAME, "SaveYourKDEDesign")
        self.assertEqual(app.LEGACY_APP_NAME, "SaveDesktopDesign")

    def test_missing_new_repository_falls_back_to_old_endpoint(self):
        error = urllib.error.HTTPError(app.RELEASE_API, 404, "Not found", {}, io.BytesIO())
        with patch.object(app.urllib.request, "urlopen", side_effect=[error, io.BytesIO(b'{}')]) as request:
            self.assertEqual(app.UpdateWorker()._get(app.RELEASE_API, "application/json"), b'{}')
        self.assertIn(app.LEGACY_GITHUB_REPO, request.call_args.args[0].full_url)
        error.close()

    def test_update_forbidden_and_oversize_do_not_fall_back(self):
        error = urllib.error.HTTPError(app.RELEASE_API, 403, "Forbidden", {}, io.BytesIO())
        with patch.object(app.urllib.request, "urlopen", side_effect=error) as request:
            with self.assertRaises(urllib.error.HTTPError):
                app.UpdateWorker()._get(app.RELEASE_API, "application/json")
            self.assertEqual(request.call_count, 1)
        error.close()
        with patch.object(app.urllib.request, "urlopen", return_value=io.BytesIO(b'x' * (app.MAX_DOWNLOAD + 1))):
            with self.assertRaises(ValueError):
                app.UpdateWorker()._get(app.RELEASE_API, "application/json")

    def test_installer_retains_old_alias_and_settings_with_spaces_in_home(self):
        repo = Path(app.__file__).parent
        with tempfile.TemporaryDirectory(prefix="sdd-qc-") as tmp:
            home = Path(tmp) / "home with spaces"
            home.mkdir()
            settings = home / ".config/SaveDesktopDesign/SaveDesktopDesign.conf"
            settings.parent.mkdir(parents=True)
            settings.write_text("[General]\nlanguage=de\nlast_import_code=keep-this\n")
            subprocess.run(["bash", str(repo / "install.sh")], env={**os.environ, "HOME": str(home)},
                           check=True, capture_output=True, text=True)
            for name in ("saveyourkdedesign", "savedesktopdesign"):
                launcher = home / ".local/bin" / name
                self.assertTrue(os.access(launcher, os.X_OK))
                subprocess.run(["bash", "-n", str(launcher)], check=True)
                self.assertIn(str(home / ".local/share/savedesktopdesign/savedesktopdesign.py"), launcher.read_text())
            entry = (home / ".local/share/applications/savedesktopdesign.desktop").read_text()
            self.assertIn("Name=SaveYourKDEDesign", entry)
            self.assertIn('Exec="' + str(home / ".local/bin/saveyourkdedesign") + '"', entry)
            self.assertIn("last_import_code=keep-this", settings.read_text())

    def test_settings_stay_in_legacy_namespace(self):
        tree = ast.parse(Path(app.__file__).read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "QSettings"]
        self.assertEqual(len(calls), 1)
        self.assertEqual([arg.id for arg in calls[0].args], ["LEGACY_APP_NAME", "LEGACY_APP_NAME"])

    def test_in_app_update_migrates_menu_but_preserves_custom_launcher(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, "HOME", Path(tmp)):
            installed = Path(tmp) / ".local/share/savedesktopdesign/savedesktopdesign.py"
            installed.parent.mkdir(parents=True)
            installed.touch()
            entry = Path(tmp) / ".local/share/applications/savedesktopdesign.desktop"
            entry.parent.mkdir(parents=True)
            entry.write_text("[Desktop Entry]\nName=SaveDesktopDesign\nExec=savedesktopdesign\n")
            app.migrate_installed_branding(installed)
            self.assertIn("Name=SaveYourKDEDesign", entry.read_text())
            launcher = Path(tmp) / ".local/bin/saveyourkdedesign"
            self.assertIn(str(installed), launcher.read_text())
            launcher.write_text("custom launcher")
            app.migrate_installed_branding(installed)
            self.assertEqual(launcher.read_text(), "custom launcher")

    def test_preview_uses_read_only_package_flags(self):
        from types import SimpleNamespace
        for command, flag, output, status in (
            (["apt-get", "install", "-y", "kde-plasma-desktop"], "--simulate", "1 newly installed", 0),
            (["dnf", "install", "-y", "@kde-desktop-environment"], "--assumeno", "Transaction Summary:\nOperation aborted by the user.", 1),
            (["pacman", "-S", "--noconfirm", "plasma-meta"], "--print", "plasma-meta 6.5.0", 0),
        ):
            with patch.object(app.subprocess, "run", return_value=SimpleNamespace(returncode=status, stdout=output, stderr="")) as run:
                self.assertIn(output, app.desktop_transaction_preview(command))
            args = run.call_args.args[0]
            self.assertIn(flag, args)
            self.assertNotIn("-y", args)
            self.assertNotIn("pkexec", args)

    def test_broken_package_plan_cannot_offer_install(self):
        from types import SimpleNamespace
        with patch.object(app.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="No match")):
            with self.assertRaises(ValueError):
                app.desktop_transaction_preview(["dnf", "install", "-y", "@kde-desktop-environment"])

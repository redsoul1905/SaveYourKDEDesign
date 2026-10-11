"""Offline tests: never upload personal data or touch the real desktop."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import savedesktopdesign as app


PROFILE = {"plasma": "6.5.0", "session": "wayland",
           "screens": [{"width": 1920, "height": 1080, "x": 0, "y": 0, "scale": 1.0}]}


def archive_file(path, entries, manifest=None):
    with tarfile.open(path, "w:gz") as archive:
        if manifest is not None:
            entries = [("manifest.json", json.dumps(manifest).encode()), *entries]
        for name, data in entries:
            if isinstance(data, tarfile.TarInfo):
                archive.addfile(data)
            else:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))


def manifest(paths=None):
    return {"public_design": 1, "paths": paths or [".config/kdeglobals"],
            "profile": PROFILE, "requirements": [], "categories": []}


class Response(io.BytesIO):
    def __init__(self, data, length=None):
        super().__init__(data)
        self.headers = {} if length is None else {"Content-Length": str(length)}


class SharingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "user"
        self.home.mkdir()
        self.home_patch = patch.object(app, "HOME", self.home)
        self.home_patch.start()

    def tearDown(self):
        self.home_patch.stop()
        self.temp.cleanup()

    def config(self, name, data):
        dest = self.home / ".config" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data)
        return dest

    def test_public_export_excludes_identity_commands_and_private_files(self):
        self.config("kdeglobals", "[General]\nColorScheme=NonexistentTestTheme\nPassword=secret\nRecentFiles=/home/me/private\n[Icons]\nTheme=TestIcons\n")
        self.config("plasma-org.kde.plasma.desktop-appletsrc", "[Containments][1]\nlocation=4\nactivityId=private-id\n[Containments][1][Applets][2][Configuration]\ntext=private note\ncommand=touch /tmp/unsafe\n")
        self.config("autostart/evil.desktop", "Exec=evil")
        icons = self.home / ".local/share/icons/TestIcons"
        icons.mkdir(parents=True)
        (icons / "index.theme").write_text("[Icon Theme]\nName=Test\n")
        (icons / "image.svg").write_text("<svg/>")
        (icons / "alias.svg").symlink_to("image.svg")
        stage = self.root / "stage"
        stage.mkdir()
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            result = app.public_design(stage, PROFILE["screens"])
        self.assertNotIn("hostname", result)
        self.assertNotIn("user", result)
        self.assertFalse(result["with_packages"])
        self.assertGreater(result["omitted_settings"], 0)
        all_text = "".join(p.read_text() for p in (stage / "home").rglob("*") if p.is_file())
        for secret in ("secret", "private note", "private-id", "touch /tmp", "Exec=evil"):
            self.assertNotIn(secret, all_text)
        alias = stage / "home/.local/share/icons/TestIcons/alias.svg"
        self.assertTrue(alias.is_file())
        self.assertFalse(alias.is_symlink())

    def test_wallpaper_is_bundled_and_source_home_is_not_exposed(self):
        wallpaper = self.home / "private-name.png"
        wallpaper.write_bytes(b"fake image")
        self.config("plasma-org.kde.plasma.desktop-appletsrc",
                    "[Containments][1]\nlastScreen=0\n"
                    "[Containments][1][Wallpaper][org.kde.image][General]\nImage=" + wallpaper.as_uri() + "\n")
        stage = self.root / "stage"
        stage.mkdir()
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            result = app.public_design(stage, [])
        config = (stage / "home/.config/plasma-org.kde.plasma.desktop-appletsrc").read_text()
        self.assertIn(app.HOME_TOKEN, config)
        self.assertNotIn(str(self.home), config)
        self.assertNotIn("private-name", config)
        self.assertTrue(any("wallpapers/sdd/" in p for p in result["paths"]))

    def test_global_theme_defaults_and_modified_kvantum_assets_are_preserved(self):
        self.config("kdedefaults/kdeglobals", "[General]\nColorScheme=MissingTestColors\n[KDE]\nAnimationDurationFactor=2\n")
        self.config("kdeglobals", "[KDE]\nAnimationDurationFactor=0.5\n")
        self.config("Kvantum/kvantum.kvconfig", "[General]\ntheme=TestTheme#\n")
        self.config("Kvantum/TestTheme/TestTheme.svg", "<svg/>")
        self.config("Kvantum/TestTheme#/TestTheme#.kvconfig", "[General]\nblur=true\n")
        (self.home / ".config/Kvantum/TestTheme#/TestTheme#.svg").symlink_to("../TestTheme/TestTheme.svg")
        stage = self.root / "stage"
        stage.mkdir()
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            result = app.public_design(stage, [])
        config = (stage / "home/.config/kdeglobals").read_text()
        self.assertIn("ColorScheme=MissingTestColors", config)
        self.assertIn("AnimationDurationFactor=0.5", config)
        self.assertNotIn("AnimationDurationFactor=2", config)
        self.assertIn(".config/Kvantum/TestTheme#/TestTheme#.svg", result["paths"])
        self.assertIn(".config/Kvantum/TestTheme/TestTheme.svg", result["paths"])
        self.assertIn("theme=TestTheme#", (stage / "home/.config/Kvantum/kvantum.kvconfig").read_text())

    def test_asset_link_cannot_publish_private_file(self):
        self.config("kdeglobals", "[Icons]\nTheme=TestIcons\n")
        icons = self.home / ".local/share/icons/TestIcons"
        icons.mkdir(parents=True)
        secret = self.home / "secret"
        secret.write_text("private")
        (icons / "leak").symlink_to(secret)
        stage = self.root / "stage"
        stage.mkdir()
        with self.assertRaises(ValueError):
            app.public_design(stage, [])

    def test_upload_streams_multipart_and_returns_reusable_integrity_code(self):
        path = self.root / "design.sdd"
        path.write_bytes(b"public demo")
        captured = {}

        def open_request(req):
            captured["body"] = b"".join(req.data)
            captured["length"] = int(req.get_header("Content-length"))
            self.assertEqual(req.full_url, app.CATBOX_API)
            return Response(b"https://files.catbox.moe/abcdef.sdd\n")

        with patch.object(app, "catbox_open", side_effect=open_request):
            code = app.upload_design(path)
        self.assertEqual(code, "SDD1:abcdef.sdd:" + hashlib.sha256(b"public demo").hexdigest())
        self.assertEqual(captured["length"], len(captured["body"]))
        self.assertIn(b'name="reqtype"\r\n\r\nfileupload', captured["body"])
        self.assertIn(b"public demo", captured["body"])

    def test_upload_rejects_oversize_before_network(self):
        path = self.root / "design.sdd"
        path.write_bytes(b"1234")
        with patch.object(app, "SHARE_LIMIT", 3), patch.object(app, "catbox_open") as network:
            with self.assertRaises(ValueError):
                app.upload_design(path)
            network.assert_not_called()

    def test_upload_rejects_non_catbox_response(self):
        path = self.root / "design.sdd"
        path.write_bytes(b"1234")
        with patch.object(app, "catbox_open", return_value=Response(b"https://evil.test/abcdef.sdd")):
            with self.assertRaises(ValueError):
                app.upload_design(path)

    def test_download_checks_digest_and_removes_failed_download(self):
        data = b"downloaded design"
        code = "SDD1:abcdef.sdd:" + hashlib.sha256(data).hexdigest()
        target = self.root / "received.sdd"
        with patch.object(app, "catbox_open", return_value=Response(data, len(data))):
            app.download_design(code, target)
        self.assertEqual(target.read_bytes(), data)
        target.unlink()
        with patch.object(app, "catbox_open", return_value=Response(b"tampered")):
            with self.assertRaises(ValueError):
                app.download_design(code, target)
        self.assertFalse(target.exists())

    def test_download_rejects_unbounded_stream_and_arbitrary_urls(self):
        target = self.root / "received.sdd"
        code = "SDD1:abcdef.sdd:" + "0" * 64
        with patch.object(app, "SHARE_LIMIT", 3), patch.object(app, "catbox_open", return_value=Response(b"1234")):
            with self.assertRaises(ValueError):
                app.download_design(code, target)
        self.assertFalse(target.exists())
        with patch.object(app, "catbox_open") as network:
            with self.assertRaises(ValueError):
                app.download_design("https://evil.test/file", target)
            network.assert_not_called()

    def test_download_never_deletes_an_existing_destination(self):
        target = self.root / "existing.sdd"
        target.write_bytes(b"keep me")
        with patch.object(app, "catbox_open", return_value=Response(b"new")):
            with self.assertRaises(FileExistsError):
                app.download_design("SDD1:abcdef.sdd:" + "0" * 64, target)
        self.assertEqual(target.read_bytes(), b"keep me")

    def test_public_tar_metadata_removes_owner_identity(self):
        member = tarfile.TarInfo("home/.config/kdeglobals")
        member.uid, member.gid = 1000, 1000
        member.uname, member.gname = "private-user", "private-group"
        member.mtime = 1234567
        member.pax_headers = {"comment": "private"}
        member = app.public_tar_metadata(member)
        self.assertEqual((member.uid, member.gid, member.uname, member.gname), (0, 0, "", ""))
        self.assertEqual(member.pax_headers, {})
        self.assertEqual(member.mtime, 0)

    def test_dependency_plan_is_local_and_distribution_specific(self):
        doc = manifest()
        doc["requirements"] = [{"kind": "style", "name": "kvantum"}]
        for manager, package in (("pacman", "kvantum"), ("apt-get", "qt6-style-kvantum"), ("dnf", "kvantum")):
            present = {manager, "pkexec", "apt-cache"}
            with patch.object(app.shutil, "which", side_effect=lambda name: "/usr/bin/" + name if name in present else None):
                plan = app.design_install_plan(doc, PROFILE, [])
                self.assertEqual(plan[1], package)
                self.assertEqual(plan[3][-1], package)
                self.assertIsNone(app.design_install_plan(doc, PROFILE, ["kvantum"]))
                self.assertIsNone(app.design_install_plan(doc, {**PROFILE, "plasma": "5.27.0"}, []))
        doc["requirements"] = [{"kind": "style", "name": "$(touch /tmp/pwned)"}]
        with patch.object(app.shutil, "which", return_value="/usr/bin/pkexec"):
            self.assertIsNone(app.design_install_plan(doc, PROFILE, []))

    def test_public_archive_requires_exact_allowlisted_manifest(self):
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
        self.assertEqual(app.inspect_public_archive(path)["profile"], PROFILE)
        for bad in ("home/../../outside", "home/.ssh/authorized_keys", "app/savedesktopdesign.py", "packages/apt-manual.txt"):
            archive_file(path, [(bad, b"bad")], manifest())
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                app.inspect_public_archive(path)
        archive_file(path, [("home/.config/kdeglobals", b"x")], manifest([".config/kwinrc"]))
        with self.assertRaises(ValueError):
            app.inspect_public_archive(path)

    def test_archive_rejects_links_devices_duplicates_and_bombs(self):
        path = self.root / "design.sdd"
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE):
            link = tarfile.TarInfo("home/.config/kdeglobals")
            link.type = kind
            link.linkname = "/tmp/escape"
            archive_file(path, [(link.name, link)], manifest())
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                app.inspect_public_archive(path)
        archive_file(path, [("home/.config/kdeglobals", b"x"), ("home/.config/kdeglobals", b"x")], manifest())
        with self.assertRaises(ValueError):
            app.inspect_public_archive(path)
        archive_file(path, [("home/.config/kdeglobals", b"1234")], manifest())
        with patch.object(app, "EXPANDED_LIMIT", 3), self.assertRaises(ValueError):
            app.inspect_public_archive(path)

    def test_safe_extract_rejects_link_escape_for_private_archives_too(self):
        path = self.root / "archive.tar.gz"
        link = tarfile.TarInfo("home/link")
        link.type = tarfile.SYMTYPE
        link.linkname = str(self.home)
        archive_file(path, [(link.name, link), ("home/link/escaped", b"bad")])
        dest = self.root / "extract"
        dest.mkdir()
        with tarfile.open(path) as archive, self.assertRaises(ValueError):
            app.safe_extract(archive, dest)
        self.assertFalse((self.home / "escaped").exists())

    def test_compatibility_blocks_unknown_or_different_environment(self):
        self.assertEqual(app.compatibility_issues(manifest(), PROFILE, []), [])
        for key, value in (("plasma", "5.27.0"), ("session", "x11")):
            current = {**PROFILE, key: value}
            self.assertTrue(app.compatibility_issues(manifest(), current, []))
        self.assertEqual(app.compatibility_issues(manifest(), {**PROFILE, "screens": []}, []), [])
        doc = manifest()
        doc["requirements"] = [{"kind": "style", "name": "Kvantum"}]
        self.assertEqual(app.compatibility_issues(doc, PROFILE, ["kvantum"]), [])
        self.assertTrue(app.compatibility_issues(doc, PROFILE, ["Breeze"]))

    def test_public_restore_rebases_paths_and_creates_working_rollback(self):
        original = self.config("kdeglobals", "[General]\nColorScheme=Old\n")
        path = self.root / "design.sdd"
        text = "[General]\nImage=file://@SDD_HOME@/.local/share/wallpapers/test.png\n"
        archive_file(path, [("home/.config/kdeglobals", text.encode())], manifest())
        worker = app.RestoreWorker(str(path), public=True)
        errors, done = [], []
        worker.failed.connect(errors.append)
        worker.finished_ok.connect(done.append)
        with patch.object(app, "desktop_profile", return_value=PROFILE), patch.object(worker, "_post_restore"):
            worker.run()
        self.assertEqual(errors, [])
        self.assertEqual(done, [False])
        self.assertIn(str(self.home), original.read_text())
        self.assertTrue(app.rollback_path().exists())
        rollback = app.RestoreWorker(str(app.rollback_path()), rollback=False)
        rollback.failed.connect(errors.append)
        with patch.object(rollback, "_post_restore"):
            rollback.run()
        self.assertEqual(errors, [])
        self.assertIn("ColorScheme=Old", original.read_text())

    def test_failed_rollback_blocks_writes(self):
        original = self.config("kdeglobals", "original")
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"changed")], manifest())
        worker = app.RestoreWorker(str(path), public=True)
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(app, "desktop_profile", return_value=PROFILE), patch.object(app, "make_rollback", side_effect=OSError("full disk")):
            worker.run()
        self.assertTrue(errors)
        self.assertEqual(original.read_text(), "original")

    def test_mismatched_import_and_symlinked_target_do_not_modify_home(self):
        original = self.config("kdeglobals", "original")
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"changed")], manifest())
        worker = app.RestoreWorker(str(path), public=True)
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(app, "desktop_profile", return_value={**PROFILE, "plasma": "5.0.0"}):
            worker.run()
        self.assertTrue(errors)
        self.assertEqual(original.read_text(), "original")
        original.unlink()
        original.parent.rmdir()
        outside = self.root / "outside"
        outside.mkdir()
        (self.home / ".config").symlink_to(outside)
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            worker.run()
        self.assertFalse((outside / "kdeglobals").exists())

    def test_private_backup_still_round_trips(self):
        original = self.config("kdeglobals", "original")
        path = self.root / "private.tar.gz"
        backup = app.BackupWorker(str(path), ["cat_plasma"], False)
        errors = []
        backup.failed.connect(errors.append)
        backup.run()
        original.write_text("changed")
        restore = app.RestoreWorker(str(path), rollback=False)
        restore.failed.connect(errors.append)
        with patch.object(restore, "_post_restore"):
            restore.run()
        self.assertEqual(errors, [])
        self.assertEqual(original.read_text(), "original")


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = app.QApplication.instance() or app.QApplication([])

    def test_share_tab_copy_and_async_download_review(self):
        from PyQt6.QtTest import QTest
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = app.QSettings(str(root / "settings.ini"), app.QSettings.Format.IniFormat)
            settings.setValue("language", "de")
            settings.setValue("check_updates_on_start", False)
            path = root / "fixture.sdd"
            archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
            code = "SDD1:abcdef.sdd:" + app.sha256_file(path)
            with patch.object(app, "QSettings", return_value=settings):
                window = app.MainWindow()
            self.assertTrue(window.windowTitle().startswith("SaveYourKDEDesign"))
            self.assertEqual(window.findChild(app.QTabWidget).tabText(2), "Design teilen")
            window._last_share_code = code
            window.share_code.setText(code)
            copy_button = next(b for b in window.findChildren(app.QPushButton) if b.text() == "Code kopieren")
            copy_button.click()
            self.assertEqual(self.qt.clipboard().text(), code)
            with patch.object(app.QInputDialog, "getText", return_value=(code, True)), \
                    patch.object(app, "catbox_open", return_value=Response(path.read_bytes())), \
                    patch.object(app, "desktop_profile", return_value=PROFILE), \
                    patch.object(app.QMessageBox, "question", return_value=app.QMessageBox.StandardButton.No) as review:
                window.import_code()
                self.assertFalse(window.share_export_btn.isEnabled())
                for _ in range(200):
                    QTest.qWait(10)
                    if window.share_export_btn.isEnabled():
                        break
                self.assertFalse(window.share_worker.isRunning())
                self.assertTrue(window.share_export_btn.isEnabled())
                review.assert_called_once()
                self.assertIsNone(window.share_temp)
                self.assertIsNone(window.restore_worker)
            window.close()
            window.deleteLater()
            self.qt.processEvents()


if __name__ == "__main__":
    unittest.main()

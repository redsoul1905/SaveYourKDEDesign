import io
import json
import tarfile
import unittest
from unittest.mock import patch
import test_sharing as fixtures
from test_sharing import app, PROFILE, manifest, archive_file


class LargeIconTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown
    config = fixtures.SharingTests.config

    def test_more_than_50k_icons_and_large_manifest_are_supported(self):
        paths = [".local/share/icons/Test/" + "x" * 70 + f"/f{i}" for i in range(50001)]
        data = json.dumps(manifest(paths)).encode()
        self.assertGreater(len(data), 4_000_000)
        path = self.root / "large.sdd"
        with tarfile.open(path, "w:gz") as archive:
            info = tarfile.TarInfo("manifest.json")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
            for rel in paths:
                info = tarfile.TarInfo("home/" + rel)
                info.size = 1
                archive.addfile(info, io.BytesIO(b"x"))
        self.assertEqual(len(app.inspect_public_archive(path)["paths"]), 50001)

    def test_real_file_and_manifest_safety_limits_still_enforced(self):
        path = self.root / "limit.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"1234")], manifest())
        with patch.object(app, "EXPANDED_LIMIT", 3), self.assertRaises(ValueError):
            app.inspect_public_archive(path)
        with patch.object(app, "SHARE_FILE_LIMIT", 0), self.assertRaises(ValueError):
            app.inspect_public_archive(path)
        with patch.object(app, "MANIFEST_LIMIT", 1), self.assertRaises(ValueError):
            app.inspect_public_archive(path)

    def test_theme_overrides_are_counted_once(self):
        self.config("kdeglobals", "[Icons]\nTheme=UniqueTestOverride\n")
        for base in (".icons", ".local/share/icons"):
            path = self.home / base / "UniqueTestOverride/icon.svg"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"<svg/>")
        stage = self.root / "stage"
        stage.mkdir()
        with patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app, "EXPANDED_LIMIT", 6), patch.object(app, "SHARE_FILE_LIMIT", 1):
            result = app.public_design(stage, [])
        self.assertIn(".local/share/icons/UniqueTestOverride/icon.svg", result["paths"])

    def test_hicolor_application_links_are_target_dependencies_not_exported(self):
        self.config("kdeglobals", "[Icons]\nTheme=hicolor\n")
        icon = self.home / ".local/share/icons/hicolor/private.svg"
        icon.parent.mkdir(parents=True)
        secret = self.home / "private.txt"
        secret.write_text("do not export")
        icon.symlink_to(secret)
        stage = self.root / "stage"
        stage.mkdir()
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            result = app.public_design(stage, [])
        self.assertIn({"kind": "asset", "name": "icons/hicolor"}, result["requirements"])
        self.assertFalse(any("hicolor/" in p for p in result["paths"]))

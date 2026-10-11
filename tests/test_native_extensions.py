import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import test_sharing as fixtures
from test_sharing import app, PROFILE, manifest, archive_file


class NativeTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown

    def plan(self, distro, output, name="org.kde.example", kind="decoration"):
        doc = manifest()
        doc["requirements"] = [{"kind": kind, "name": name}]
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": distro}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(Path, "exists", return_value=False), \
                patch.object(Path, "glob", return_value=iter([Path("Contents-amd64")])), \
                patch.object(app, "_run_cmd", side_effect=lambda cmd, timeout: "" if cmd[1] == "-Qu" else output) as query:
            result = app.native_extension_plan(doc, PROFILE, [], [kind + ": " + name])
        return result, query

    def test_distro_specific_providers_not_source_package_names(self):
        for distro, output, package in (("ubuntu", "kwin-style-example\n", "kwin-style-example"),
                                        ("fedora", "example-decoration\n", "example-decoration"),
                                        ("arch", "extra/example\n", "example")):
            result, _ = self.plan(distro, output)
            self.assertEqual(result["command"][-1], package)
            self.assertIn("org.kde.example", result["providers"][0])

    def test_effect_lookup_is_qt_and_plugin_directory_scoped(self):
        result, query = self.plan("fedora", "round-corners\n", "roundcorners", "effect")
        self.assertEqual(result["command"][-1], "round-corners")
        self.assertIn("*/qt6/plugins/kwin/effects/plugins/kwin_effect_roundcorners.so", query.call_args.args[0])

    def test_unknown_or_ambiguous_providers_not_installed(self):
        for output in ("", "one\ntwo\n"):
            result, _ = self.plan("fedora", output)
            self.assertIsNone(result["command"])
            self.assertTrue(result["notes"])

    def test_untrusted_plugin_and_package_names_cannot_be_commands(self):
        result, query = self.plan("fedora", "safe", "../../evil;command")
        self.assertIsNone(result["command"])
        query.assert_not_called()
        for output in ("--allowerasing", "https://evil/package.rpm", "$(touch /tmp/evil)"):
            self.assertIsNone(self.plan("fedora", output)[0]["command"])

    def test_ubuntu_missing_file_index_offers_separate_preparation(self):
        doc = manifest()
        doc["requirements"] = [{"kind": "effect", "name": "test"}]
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "ubuntu"}), \
                patch.object(app.shutil, "which", side_effect=lambda n: None if n == "apt-file" else "/usr/bin/" + n), \
                patch.object(Path, "exists", return_value=False):
            result = app.native_extension_plan(doc, PROFILE, [], ["effect: test"])
        self.assertEqual(result["command"][-1], "apt-file")
        self.assertTrue(result["prepare_index"])

    def test_incompatible_plasma_never_installs_plugins(self):
        with patch.object(app, "_run_cmd") as query:
            result = app.native_extension_plan(manifest(), {**PROFILE, "plasma": "5.27.0"}, [], [])
        self.assertIsNone(result["command"])
        query.assert_not_called()

    def test_worker_revalidates_provider_before_admin_auth(self):
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
        worker = app.NativeInstallWorker([], path, [], {"command": ["dnf", "install", "safe"], "providers": ["old"]})
        failures = []
        worker.failed.connect(failures.append)
        with patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app, "native_extension_plan", return_value={"command": ["dnf", "install", "other"], "providers": ["new"]}), \
                patch.object(app.subprocess, "run") as run:
            worker.run()
        run.assert_not_called()
        self.assertTrue(failures)

    def test_success_still_requires_relogin_and_does_not_apply_design(self):
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
        plan = {"command": ["dnf", "install", "-y", "native-plugin"], "providers": ["effect: test → native-plugin"]}
        worker = app.NativeInstallWorker([], path, [], plan)
        results = []
        worker.ready.connect(lambda *args: results.append(args))
        with patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app, "native_extension_plan", return_value=plan), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(app.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
            worker.run()
        self.assertTrue(results[0][1]["native_installed"])
        self.assertFalse((self.home / ".config/kdeglobals").exists())

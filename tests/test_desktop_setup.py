"""Repository/installer simulations only: never install or change a desktop."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_sharing as fixtures
from test_sharing import PROFILE, archive_file, manifest, app


class DesktopSetupTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown

    def setup_plan(self, distro, candidate, current=None):
        def query(cmd, timeout):
            if cmd[:2] == ["apt-cache", "policy"]:
                return "  Candidate: " + candidate
            if cmd[0] == "dnf":
                return candidate + "\n"
            if cmd[0] == "pacman":
                if cmd[1] == "-Qu":
                    return ""
                return "Version : " + candidate
            return "available"
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": distro}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(app, "_run_cmd", side_effect=query), \
                patch.object(Path, "exists", return_value=False):
            return app.desktop_setup(manifest(), current or {**PROFILE, "plasma": "", "desktop": ""})

    def test_missing_kde_ubuntu_fedora_arch(self):
        for distro, candidate, target in (("ubuntu", "4:6.5.0-0ubuntu1", "kde-plasma-desktop"),
                                           ("fedora", "6.5.0", "@kde-desktop-environment"),
                                           ("arch", "6.5.0-1", "plasma-meta")):
            plan = self.setup_plan(distro, candidate)
            self.assertIn(target, plan["command"])
            self.assertTrue(plan["notes"])
            self.assertNotIn("remove", plan["command"])

    def test_versions_unavailable_newer_older_and_unknown_never_install(self):
        for version in ("(none)", "", "5.27.12", "6.6.0", "bad metadata"):
            self.assertIsNone(self.setup_plan("ubuntu", version)["command"])
        self.assertIsNone(self.setup_plan("unknown", "6.5.0")["command"])

    def test_existing_desktop_only_suggests_update(self):
        plan = self.setup_plan("fedora", "6.5.0", {**PROFILE, "plasma": "6.4.0"})
        self.assertIsNone(plan["command"])
        self.assertTrue(any("Update" in n or "update" in n for n in plan["notes"]))

    def test_atomic_not_sent_to_dnf(self):
        with patch.object(Path, "exists", return_value=True), \
                patch.object(app, "_run_cmd") as query:
            plan = app.desktop_setup(manifest(), {**PROFILE, "plasma": ""})
        self.assertIsNone(plan["command"])
        self.assertIn("Atomic", plan["notes"][0])
        query.assert_not_called()

    def test_gnome_cannot_apply_even_if_plasma_installed(self):
        self.assertTrue(app.compatibility_issues(manifest(), {**PROFILE, "desktop": ""}, []))
        self.assertFalse(app.compatibility_issues(manifest(), {**PROFILE, "desktop": "KDE"}, []))

    def test_missing_authorization_never_offers_install(self):
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "fedora"}), \
                patch.object(app.shutil, "which", side_effect=lambda n: None if n == "pkexec" else "/usr/bin/" + n), \
                patch.object(app, "_run_cmd", return_value="6.5.0\n"), \
                patch.object(Path, "exists", return_value=False):
            plan = app.desktop_setup(manifest(), {**PROFILE, "plasma": ""})
        self.assertIsNone(plan["command"])

    def test_arch_derivative_uses_arch_plan(self):
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "cachyos", "ID_LIKE": "arch"}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(app, "_run_cmd", side_effect=lambda cmd, timeout: "" if cmd[1] == "-Qu" else "Version : 6.5.0-1\n"), \
                patch.object(Path, "exists", return_value=False):
            plan = app.desktop_setup(manifest(), {**PROFILE, "plasma": ""})
        self.assertEqual(plan["command"][0], "pacman")

    def test_extension_versions_and_minimum_from_actual_bundle(self):
        path = self.root / "design.sdd"
        rel = ".local/share/plasma/plasmoids/test.widget/metadata.json"
        local = self.home / rel
        local.parent.mkdir(parents=True)
        local.write_text(json.dumps({"KPlugin": {"Version": "2.0"}}))
        data = json.dumps({"KPlugin": {"Version": "1.0"}, "X-Plasma-API-Minimum-Version": "6.6"}).encode()
        archive_file(path, [("home/" + rel, data)], manifest([rel]))
        rows, issues = app.extension_preflight(path, PROFILE)
        self.assertIn("2.0 → 1.0", rows[0])
        self.assertTrue(issues)
        self.assertFalse(app.extension_preflight(path, {**PROFILE, "plasma": "6.6.1"})[1])

    def test_final_restore_blocks_extension_minimum_before_changes(self):
        path = self.root / "design.sdd"
        rel = ".local/share/kwin/scripts/test.script/metadata.json"
        data = json.dumps({"KPlugin": {"Version": "1.0"}, "X-Plasma-API-Minimum-Version": "7.0"}).encode()
        archive_file(path, [("home/" + rel, data)], manifest([rel]))
        worker = app.RestoreWorker(str(path), public=True, screens=PROFILE["screens"])
        failures = []
        worker.failed.connect(failures.append)
        with patch.object(app, "desktop_profile", return_value=PROFILE):
            worker.run()
        self.assertTrue(failures)
        self.assertFalse((self.home / rel).exists())

    def test_malformed_extension_metadata_is_rejected(self):
        path = self.root / "design.sdd"
        rel = ".local/share/kwin/effects/test.effect/metadata.json"
        archive_file(path, [("home/" + rel, b'[]')], manifest([rel]))
        with self.assertRaises(ValueError):
            app.extension_preflight(path, PROFILE)

    def test_desktop_worker_revalidates_consent(self):
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
        approved = {"command": ["dnf", "install", "-y", "@kde-desktop-environment"]}
        worker = app.DesktopSetupWorker([], path, approved)
        failures = []
        worker.failed.connect(failures.append)
        with patch.object(app, "desktop_setup", return_value={"command": None}), \
                patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app.subprocess, "run") as run:
            worker.run()
        run.assert_not_called()
        self.assertTrue(failures)

    def test_desktop_worker_success_does_not_apply_design(self):
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
        approved = {"command": ["apt-get", "install", "--no-remove", "--no-install-recommends", "-y", "kde-plasma-desktop"]}
        worker = app.DesktopSetupWorker([], path, approved)
        ready = []
        worker.ready.connect(lambda *args: ready.append(args))
        with patch.object(app, "desktop_setup", return_value=approved), \
                patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(app.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            worker.run()
        self.assertTrue(ready[0][1]["desktop_installed"])
        self.assertEqual(run.call_args.args[0][:3], ["/usr/bin/pkexec", "/usr/bin/env", "DEBIAN_FRONTEND=noninteractive"])
        self.assertFalse((self.home / ".config/kdeglobals").exists())

    def test_desktop_worker_cancelled_never_reports_success(self):
        path = self.root / "design.sdd"
        archive_file(path, [("home/.config/kdeglobals", b"[General]\n")], manifest())
        approved = {"command": ["dnf", "install", "-y", "@kde-desktop-environment"]}
        worker = app.DesktopSetupWorker([], path, approved)
        ready, failures = [], []
        worker.ready.connect(lambda *args: ready.append(args))
        worker.failed.connect(failures.append)
        with patch.object(app, "desktop_setup", return_value=approved), \
                patch.object(app, "desktop_profile", return_value=PROFILE), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(app.subprocess, "run", return_value=SimpleNamespace(returncode=126, stderr="cancelled")):
            worker.run()
        self.assertFalse(ready)
        self.assertTrue(failures)
        self.assertFalse((self.home / ".config/kdeglobals").exists())

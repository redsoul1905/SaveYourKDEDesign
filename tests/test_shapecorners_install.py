"""Native ShapeCorners installation is target-specific and requires consent."""
import unittest
from unittest.mock import patch
from test_sharing import app, PROFILE, manifest


class ShapeCornersInstallTests(unittest.TestCase):
    def plan(self, distro="fedora", session="wayland", tools=True, name="kwin4_effect_shapecorners",
             missing=True, plasma=None):
        doc = manifest()
        doc["requirements"] = [{"kind": "effect", "name": name}]
        target = {**PROFILE, "session": session}
        if plasma:
            target["plasma"] = plasma
        with patch.object(app.platform, "freedesktop_os_release",
                          return_value={"ID": distro, "ID_LIKE": "arch" if distro == "cachyos" else ""}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n if tools else None), \
                patch.object(app, "_run_cmd", return_value="verified") as query:
            result = app.community_extension_plan(doc, target, ["effect: " + name] if missing else [])
        return result, query

    def test_fedora_wayland_uses_maintainer_copr(self):
        plan, query = self.plan()
        self.assertEqual(plan["kind"], "fedora_copr")
        self.assertEqual(plan["packages"], ["kwin-effect-roundcorners"])
        self.assertIn("sudo dnf copr enable -y matinlotfali/KDE-Rounded-Corners", plan["command"][-1])
        self.assertIn("sudo dnf install -y kwin-effect-roundcorners", plan["command"][-1])
        self.assertNotIn("yay", plan["manual_command"])
        self.assertNotIn("paru", plan["manual_command"])
        query.assert_not_called()

    def test_x11_uses_target_session_not_source(self):
        plan, _ = self.plan(session="x11")
        self.assertEqual(plan["packages"], ["kwin-effect-roundcorners-x11"])
        plan, _ = self.plan(distro="arch", session="x11")
        self.assertEqual(plan["packages"], ["kwin-effect-rounded-corners-x11-git"])

    def test_cachyos_verifies_aur_before_offer(self):
        plan, query = self.plan(distro="cachyos")
        self.assertEqual(plan["kind"], "aur")
        self.assertEqual(plan["command"], ["/usr/bin/yay", "-S", "--needed", "kwin-effect-rounded-corners-git"])
        query.assert_called_once_with(["/usr/bin/yay", "-Si", "--aur", "kwin-effect-rounded-corners-git"], 90)

    def test_no_terminal_has_copyable_fedora_instructions(self):
        plan, _ = self.plan(tools=False)
        self.assertIsNone(plan["command"])
        self.assertIn("sudo dnf install -y kwin-effect-roundcorners", plan["notes"][0])

    def test_other_distros_receive_upstream_instructions_not_wrong_packages(self):
        for distro in ("debian", "ubuntu", "opensuse-tumbleweed"):
            with self.subTest(distro=distro):
                plan, _ = self.plan(distro=distro)
                self.assertIsNone(plan["command"])
                self.assertIn("KDE-Rounded-Corners#installation", " ".join(plan["notes"]))
                self.assertEqual(plan["manual_command"], "")

    def test_no_offer_for_unknown_installed_or_incompatible(self):
        for kwargs in ({"name": "untrusted; command"}, {"missing": False}, {"plasma": "5.27.0"}):
            with self.subTest(kwargs=kwargs):
                plan, _ = self.plan(**kwargs)
                self.assertIsNone(plan["command"])
                self.assertEqual(plan["packages"], [])

    def test_unverified_aur_does_not_run(self):
        doc = manifest()
        doc["requirements"] = [{"kind": "effect", "name": "kwin4_effect_shapecorners"}]
        with patch.object(app.platform, "freedesktop_os_release", return_value={"ID": "arch"}), \
                patch.object(app.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                patch.object(app, "_run_cmd", return_value=""):
            plan = app.community_extension_plan(doc, PROFILE, ["effect: kwin4_effect_shapecorners"])
        self.assertIsNone(plan["command"])
        self.assertIn("nicht verifiziert", plan["notes"][0])

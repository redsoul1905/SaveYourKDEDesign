import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from test_sharing import app, PROFILE


class EffectsAndPinsTests(unittest.TestCase):
    def layout(self, pin, with_general=True):
        return ('[Containments][1]\nplugin=org.kde.panel\nlastScreen=0\n'
                '[Containments][1][Applets][2]\nplugin=org.kde.plasma.icontasks\n' +
                ('[Containments][1][Applets][2][Configuration][General]\nlaunchers=' + pin + '\n'
                 if with_general else ''))

    def test_old_codes_keep_target_pins_not_source(self):
        result = app.merge_primary_applet_config(self.layout('applications:source-game.desktop'),
                                                 self.layout('applications:target-browser.desktop'), 0, 0)
        self.assertNotIn('source-game', result)
        self.assertIn('launchers=applications:target-browser.desktop', result)

    def test_empty_target_does_not_receive_source_or_default_pins(self):
        result = app.merge_primary_applet_config(self.layout('applications:source.desktop'), '', 0, 0)
        self.assertIn('launchers=\n', result)
        self.assertNotIn('source.desktop', result)

    def test_explicit_empty_taskbar_choice(self):
        result = app.merge_primary_applet_config(self.layout('applications:source.desktop'),
                                                 self.layout('applications:old.desktop'), 0, 0, preserve_pins=False)
        self.assertIn('launchers=\n', result)
        self.assertNotIn('.desktop', result)

    def test_new_codes_without_general_group_get_target_pins(self):
        result = app.merge_primary_applet_config(self.layout('', False), self.layout('applications:local.desktop'), 0, 0)
        self.assertIn('launchers=applications:local.desktop', result)

    def test_missing_distro_start_icon_has_portable_fallback(self):
        text = '[Containments][1][Applets][2]\nplugin=org.kde.plasma.kickoff\n[Containments][1][Applets][2][Configuration][General]\nicon=org.cachyos.hello\n'
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertIn('icon=start-here-kde', app.repair_launcher_icons(text, root, lambda name: False))
            self.assertIn('icon=org.cachyos.hello', app.repair_launcher_icons(text, root, lambda name: True))
            icon = root / '.local/share/icons/hicolor/scalable/apps/org.cachyos.hello.svg'
            icon.parent.mkdir(parents=True)
            icon.write_text('<svg/>')
            self.assertIn('icon=org.cachyos.hello', app.repair_launcher_icons(text, root, lambda name: False))

    def test_effects_are_loaded_reconfigured_and_verified_without_enabling_disabled_corners(self):
        calls, loaded = [], set()
        def call(path, method, *args):
            calls.append((method, args))
            if method.endswith('listOfEffects'):
                return 'glass\nblur\nkwin4_effect_shapecorners'
            if method.endswith('isEffectLoaded'):
                return 'true' if args[0] in loaded else 'false'
            if method.endswith('loadEffect') and not method.endswith('unloadEffect'):
                loaded.add(args[0]); return 'true'
            return ''
        app.activate_kwin_effects({'glassEnabled':'true', 'kwin4_effect_glassEnabled':'true',
                                   'blurEnabled':'false', 'kwin4_effect_shapecornersEnabled':'false'}, call)
        self.assertEqual(loaded, {'glass'})
        self.assertTrue(any(method.endswith('reconfigureEffect') and args == ('glass',) for method,args in calls))

    def test_effect_load_failure_is_not_success(self):
        def call(path, method, *args):
            return 'glass' if method.endswith('listOfEffects') else 'false'
        with self.assertRaisesRegex(ValueError, 'nicht ladbar: glass'):
            app.activate_kwin_effects({'glassEnabled':'true'}, call)

    def test_missing_required_effect_is_not_success(self):
        with self.assertRaisesRegex(ValueError, 'erkennt den benötigten Effekt nicht'):
            app.activate_kwin_effects({'customEnabled':'true'}, lambda *args: '', {'custom'})

    def test_selected_hicolor_start_icon_is_bundled(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / 'home'
            (home / '.config').mkdir(parents=True)
            icon = home / '.local/share/icons/hicolor/scalable/apps/test-start.svg'
            icon.parent.mkdir(parents=True)
            icon.write_text('<svg/>')
            (home / '.config/plasma-org.kde.plasma.desktop-appletsrc').write_text(
                '[Containments][1]\nlastScreen=0\nplugin=org.kde.panel\n'
                '[Containments][1][Applets][2]\nplugin=org.kde.plasma.kickoff\n'
                '[Containments][1][Applets][2][Configuration][General]\nicon=test-start\n')
            stage = root / 'stage'; stage.mkdir()
            with patch.object(app, 'HOME', home), patch.object(app, 'desktop_profile', return_value=PROFILE):
                manifest = app.public_design(stage, [])
            rel = '.local/share/icons/hicolor/scalable/apps/test-start.svg'
            self.assertIn(rel, manifest['paths'])
            self.assertEqual((stage / 'home' / rel).read_text(), '<svg/>')

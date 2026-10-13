"""Privacy and fidelity regressions; no real desktop or upload is used."""
import unittest
from unittest.mock import patch

import test_sharing as fixtures
from test_sharing import app, PROFILE


class ExtensionSettingsTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown
    config = fixtures.SharingTests.config

    def export(self):
        stage = self.root / 'stage'
        stage.mkdir()
        actions = []
        with patch.object(app, 'desktop_profile', return_value=PROFILE):
            manifest = app.public_design(stage, [], settings_review=actions)
        return stage, actions, manifest

    def test_krohnkite_glass_and_desktops_survive_export(self):
        self.config('kwinrc', '[Script-krohnkite]\nscreenGapTop=20\ncolumnsBalanced=true\n'
                    'floatingClass=[steam_app_]\nfloatingTitle=personal document\nignoreActivity=12345\n'
                    '[Effect-blurplus]\nBrightness=0.4\nBlurDecorations=true\nSaturation=1.1\n'
                    '[Desktops]\nNumber=3\nRows=1\nName_1=private\nId_1=source-id\n')
        stage, actions, manifest = self.export()
        text = (stage / 'home/.config/kwinrc').read_text()
        for setting in ['screenGapTop=20', 'columnsBalanced=true', 'floatingClass=[steam_app_]',
                        'Brightness=0.4', 'BlurDecorations=true', 'Saturation=1.1', 'Number=3', 'Rows=1']:
            self.assertIn(setting, text)
        for private in ['personal document', 'private', 'source-id', '12345']:
            self.assertNotIn(private, text)
        self.assertEqual({row['action'] for row in actions}, {'reset', 'review'})
        self.assertEqual(manifest['settings_review_count'], 1)
        self.assertTrue(all(row['solution'] for row in actions))

    def test_schema_defaults_for_unknown_script(self):
        package = self.home / '.local/share/kwin/scripts/example'
        (package / 'contents/config').mkdir(parents=True)
        (package / 'metadata.json').write_text('{"KPlugin":{"Id":"example","Version":"1"}}')
        (package / 'contents/config/main.xml').write_text(
            '<kcfg xmlns="http://www.kde.org/standards/kcfg/1.0"><group name="General">'
            '<entry name="GapSize" type="UInt"><default>17</default></entry>'
            '<entry name="Password" type="String"><default>private</default></entry>'
            '</group></kcfg>')
        self.config('kwinrc', '[Plugins]\nexampleEnabled=true\n')
        stage, _, _ = self.export()
        text = (stage / 'home/.config/kwinrc').read_text()
        self.assertIn('[Script-example]\nGapSize=17', text)
        self.assertNotIn('Password', text)

    def test_unknown_widget_reports_owner_and_solution_without_value(self):
        self.config('plasma-org.kde.plasma.desktop-appletsrc',
                    '[Containments][1]\nplugin=org.kde.panel\nlastScreen=0\n'
                    '[Containments][1][Applets][2]\nplugin=org.example.widget\n'
                    '[Containments][1][Applets][2][Configuration][General]\nCustomValue=private example\n')
        _, actions, _ = self.export()
        self.assertTrue(any('org.example.widget' in row['component'] and row['key'] == 'CustomValue'
                            and row['solution'] for row in actions))
        self.assertNotIn('private example', str(actions))

    def test_merge_preserves_target_and_never_source_desktop_identities(self):
        merged = app.merge_design_kconfig('[Desktops]\nNumber=3\nId_1=foreign\nName_1=foreign\n'
                                         '[Script-krohnkite]\nscreenGapTop=20\n',
                                         '[Desktops]\nNumber=1\nId_1=local\nName_1=Local\n'
                                         '[Unrelated]\nPreference=keep\n')
        self.assertIn('Preference=keep', merged)
        self.assertIn('Id_1=local', merged)
        self.assertIn('Name_1=Local', merged)
        self.assertIn('Id_3=', merged)
        self.assertNotIn('foreign', merged)

    def test_schema_does_not_authorize_private_values_or_invalid_types(self):
        for key, value, kind in [('ApiToken', '12345', 'UInt'), ('WindowTitle', '12345', 'Int'),
                                 ('File', '12', 'Path'), ('Gap', 'true', 'Int'),
                                 ('Gap', '-2', 'UInt'), ('Flag', '3', 'Bool')]:
            with self.subTest(key=key, value=value):
                self.assertEqual(app.portable_setting(key, value, {'type': kind})[0], 'review')

    def test_schema_entities_are_rejected(self):
        path = self.root / 'schema.xml'
        path.write_text('<!DOCTYPE kcfg [<!ENTITY leak SYSTEM "file:///etc/passwd">]><kcfg/>')
        with self.assertRaises(ValueError):
            app.read_setting_schema(path)

    def test_activation_creates_missing_desktops_and_reloads_script(self):
        calls = []
        def run(command, timeout):
            calls.append(command)
            if command[3].endswith('.count'):
                return '1' if sum(c[3].endswith('.count') for c in calls) == 1 else '3'
            if command[3].endswith('.rows'):
                return '1'
            if command[3].endswith('.isScriptLoaded'):
                return ['true', 'false', 'true'][sum(c[3].endswith('.isScriptLoaded') for c in calls) - 1]
            return ''
        with patch.object(app, '_run_cmd', side_effect=run), patch.object(app.time, 'sleep'):
            app.activate_kwin_design({'[Desktops]': {'Number': '3', 'Rows': '1'},
                                      '[Plugins]': {'krohnkiteEnabled': 'true'},
                                      '[Script-krohnkite]': {'screenGapTop': '20'}}, 'qdbus6')
        self.assertEqual(sum(c[3].endswith('.createDesktop') for c in calls), 2)
        self.assertTrue(any(c[3].endswith('.unloadScript') for c in calls))

    def test_activation_failure_not_reported_as_success(self):
        with patch.object(app, '_run_cmd', return_value=None):
            with self.assertRaisesRegex(ValueError, 'Ab- und wieder anmelden'):
                app.activate_kwin_design({}, 'qdbus6')

    def test_review_stops_before_network_upload(self):
        self.config('kwinrc', '[Script-example]\nGapSize=12\nCustomText=personal\n')
        worker = app.ShareWorker([])
        outcomes, errors = [], []
        worker.ready.connect(lambda code, details: outcomes.append((code, details)))
        worker.failed.connect(errors.append)
        with patch.object(app, 'desktop_profile', return_value=PROFILE), patch.object(app, 'upload_design') as upload:
            worker.run()
        upload.assert_not_called()
        self.assertEqual(errors, [])
        self.assertEqual(outcomes[0][0], '')
        self.assertTrue(outcomes[0][1]['settings_review'])

    def test_restore_merges_imported_kwin_preferences(self):
        self.config('kwinrc', '[Unrelated]\nPreference=keep\n[Effect-blurplus]\nBrightness=1.0\n')
        archive = self.root / 'design.sdd'
        fixtures.archive_file(archive, [('home/.config/kwinrc', b'[Effect-blurplus]\nBrightness=0.4\n')],
                              fixtures.manifest(['.config/kwinrc']))
        worker = app.RestoreWorker(str(archive), public=True, rollback=False)
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(app, 'desktop_profile', return_value=PROFILE), patch.object(worker, '_post_restore'):
            worker.run()
        self.assertEqual(errors, [])
        text = (self.home / '.config/kwinrc').read_text()
        self.assertIn('Preference=keep', text)
        self.assertIn('Brightness=0.4', text)


if __name__ == '__main__':
    unittest.main()

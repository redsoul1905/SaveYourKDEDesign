"""Round-trip regressions for layout, visual settings and legacy restore."""
import json
import tarfile
import unittest
from unittest.mock import patch

import test_sharing as fixtures
from test_sharing import app, PROFILE, archive_file


class LayoutFidelityTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown
    config = fixtures.SharingTests.config

    def test_missing_wallpaper_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, 'Connect the drive'):
            app.portable_wallpaper_config('Image=file://' + str(self.root / 'missing.png'))

    def test_external_wallpaper_symlink_embeds_real_file(self):
        image = self.root / 'wallpaper.png'
        image.write_bytes(b'image content')
        link = self.home / 'wallpaper-link.png'
        link.symlink_to(image)
        text, assets = app.portable_wallpaper_config('Image=file://' + str(link))
        self.assertEqual(assets[0][0], image)
        self.assertFalse(assets[0][0].is_symlink())
        self.assertIn(app.HOME_TOKEN, text)

    def test_rollback_does_not_follow_nested_external_links(self):
        icons = self.home / '.local/share/icons'
        icons.mkdir(parents=True)
        (icons / 'external').symlink_to(self.root)
        path = app.make_rollback(['.local/share/icons'], [], dereference=True)
        with tarfile.open(path) as archive:
            self.assertTrue(archive.getmember('home/.local/share/icons/external').issym())
            self.assertEqual(len(archive.getmembers()), 3)

    def test_colorizer_large_visual_json_survives_export(self):
        settings = json.dumps({'panel': {'normal': {'backgroundColor': {
            'custom': '#123456', 'alpha': 0.5, 'list': ['#abcdef'] * 1500}}}})
        self.assertGreater(len(settings), 8192)
        self.config('plasma-org.kde.plasma.desktop-appletsrc',
                    '[Containments][1]\nlastScreen=0\nplugin=org.kde.panel\n'
                    '[Containments][1][Applets][2][Configuration][General]\n'
                    'globalSettings=' + settings + '\nprivateField=private-person\n')
        stage = self.root / 'stage'
        stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE):
            app.public_design(stage, [])
        text = (stage / 'home/.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
        self.assertIn('globalSettings=' + settings, text)
        self.assertNotIn('private-person', text)
        self.assertFalse(app.share_layout_setting_allowed('globalSettings',
                         '{"panel":{"source":"/home/someone/private.png"}}'))

    def test_panel_view_ids_follow_imported_layout_and_keep_secondary(self):
        source = '[Containments][10]\nlastScreen=0\nplugin=org.kde.panel\n'
        target = ('[Containments][10]\nlastScreen=1\nplugin=org.kde.panel\n'
                  '[Containments][20]\nlastScreen=0\nplugin=org.kde.panel\n')
        mapping = {}
        merged = app.merge_primary_applet_config(source, target, 0, 0, mapping)
        views = app.merge_panel_views(
            '[PlasmaViews][Panel 10]\npanelLengthMode=1\npanelOpacity=2\n',
            '[PlasmaViews][Panel 10]\nsecondary=keep\n[PlasmaViews][Panel 20]\nold=remove\n',
            mapping, {'20'})
        self.assertIn('[Containments][' + mapping['10'] + ']', merged)
        self.assertIn('[Panel ' + mapping['10'] + ']\npanelLengthMode=1', views)
        self.assertIn('[Panel 10]\nsecondary=keep', views)
        self.assertNotIn('old=remove', views)

    def test_systray_containment_is_kept_without_screen_assignment(self):
        source = ('[Containments][1]\nlastScreen=0\n'
                  '[Containments][1][Applets][2][Configuration]\nSystrayContainmentId=3\n'
                  '[Containments][3]\nlastScreen=-1\nplugin=org.kde.plasma.private.systemtray\n')
        path = self.config('plasma-org.kde.plasma.desktop-appletsrc', source)
        selected = app.primary_layout_values(app.read_kconfig(path), 0)
        self.assertIn(('[Containments][3]', 'lastScreen', '-1'), selected)
        mapping = {}
        text = app.merge_primary_applet_config(source, '', 0, 0, mapping)
        self.assertIn('SystrayContainmentId=' + mapping['3'], text)
        self.assertIn('[Containments][' + mapping['3'] + ']', text)

    def test_old_backup_category_selection_does_not_silently_skip_everything(self):
        original = self.config('kdeglobals', 'old')
        archive = self.root / 'old-backup.tar.gz'
        archive_file(archive, [('home/.config/kdeglobals', b'restored')],
                     {'paths': ['.config/kdeglobals'], 'categories': ['cat_plasma']})
        worker = app.RestoreWorker(str(archive), ['cat_plasma'], rollback=False)
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(worker, '_post_restore'):
            worker.run()
        self.assertEqual(errors, [])
        self.assertEqual(original.read_text(), 'restored')

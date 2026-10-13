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

    def test_duplicate_panels_are_only_removed_when_explicitly_selected(self):
        layout = ('[Containments][1]\nlastScreen=0\nplugin=org.kde.panel\nlocation=3\n'
                  '[Containments][2]\nlastScreen=0\nplugin=org.kde.panel\nlocation=3\n')
        self.assertEqual(app.duplicate_panel_ids(layout, '', 0), ['2'])
        self.assertEqual(len(app.panel_layout_snapshot(layout, '', 0)), 2)
        self.assertEqual(len(app.panel_layout_snapshot(app.without_panels(layout, {'2'}), '', 0)), 1)

    def test_export_duplicate_choice_is_validated_and_preserves_source(self):
        text = ('[Containments][1]\nlastScreen=0\nplugin=org.kde.panel\nlocation=3\n'
                '[Containments][2]\nlastScreen=0\nplugin=org.kde.panel\nlocation=3\n')
        source = self.config('plasma-org.kde.plasma.desktop-appletsrc', text)
        self.config('plasmashellrc', '')
        stage = self.root / 'stage'
        stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE):
            manifest = app.public_design(stage, [], excluded_panels=['2'])
        self.assertEqual(len(manifest['layout']), 1)
        self.assertEqual(source.read_text(), text)
        other = self.root / 'invalid'
        other.mkdir()
        with self.assertRaisesRegex(ValueError, 'Auswahl'):
            app.public_design(other, [], excluded_panels=['1'])

    def test_export_failure_restarts_shell_and_never_uploads(self):
        worker = app.ShareWorker([], manage_session=True)
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(app, 'PlasmaSession') as factory, \
             patch.object(app, 'public_design', side_effect=ValueError('bad design')), \
             patch.object(app, 'upload_design') as upload:
            worker.run()
            factory.return_value.stop.assert_called_once()
            factory.return_value.start.assert_called_once()
            upload.assert_not_called()
        self.assertTrue(errors)

    def test_loaded_session_verification_rejects_extra_panel_and_wrong_wallpaper(self):
        session = app.PlasmaSession()
        session.dbus = 'qdbus6'
        session.activity = 'active'
        layout = ('[Containments][1]\nlastScreen=0\nplugin=org.kde.panel\n'
                  '[Containments][1][General]\nAppletOrder=3;2\n'
                  '[Containments][4]\nlastScreen=0\nplugin=org.kde.plasma.folder\nactivityId=active\n'
                  '[Containments][4][Wallpaper][org.kde.image][General]\nImage=file:///wallpaper.png\n')
        state = {'panels': [{'id': 1, 'screen': 0, 'order': '3;2', 'widgets': [2, 3]}],
                 'desktops': [{'screen': 0, 'image': 'file:///wallpaper.png'}]}
        with patch.object(app, '_run_cmd', return_value=json.dumps(state)):
            session.verify(layout, 0)
        for kind in ('wallpaper', 'panel', 'order'):
            changed = json.loads(json.dumps(state))
            if kind == 'wallpaper':
                changed['desktops'][0]['image'] = 'default.png'
            elif kind == 'panel':
                changed['panels'].append({'id': 99, 'screen': 0, 'order': '', 'widgets': []})
            else:
                changed['panels'][0]['order'] = '2;3'
            with patch.object(app, '_run_cmd', return_value=json.dumps(changed)), patch.object(app.QThread, 'msleep'):
                with self.assertRaisesRegex(RuntimeError, 'stimmt nicht'):
                    session.verify(layout, 0)

    def test_shell_stop_uses_systemd_when_active_and_kquitapp_otherwise(self):
        from types import SimpleNamespace
        for systemd in (True, False):
            session = app.PlasmaSession()
            def command(args, **kwargs):
                if 'is-active' in args:
                    return SimpleNamespace(returncode=0 if systemd else 3)
                return SimpleNamespace(returncode=0)
            with patch.object(app.shutil, 'which', side_effect=lambda name: name), \
                 patch.object(app, '_run_cmd', return_value='12345678-1234-1234-1234-123456789abc'), \
                 patch.object(app.subprocess, 'run', side_effect=command) as run, \
                 patch.object(session, 'running', return_value=False):
                session.stop()
                self.assertEqual(session.mode, 'systemd' if systemd else 'direct')
                commands = [call.args[0] for call in run.call_args_list]
                self.assertIn(['systemctl', '--user', 'stop', 'plasma-plasmashell.service'] if systemd
                              else ['kquitapp6', 'plasmashell'], commands)

    def test_real_general_group_widget_order_is_verified(self):
        source = ('[Containments][1]\nlastScreen=0\nplugin=org.kde.panel\n'
                  '[Containments][1][General]\nAppletOrder=3;2\n'
                  '[Containments][1][Applets][2]\nplugin=clock\n'
                  '[Containments][1][Applets][3]\nplugin=weather\n')
        before = app.panel_layout_snapshot(source, '', 0)
        after = app.panel_layout_snapshot(source.replace('3;2', '2;3'), '', 0)
        self.assertEqual(before[0]['widgets'], ['weather', 'clock'])
        self.assertNotEqual(before, after)

    def test_fit_content_is_not_reported_as_full_width_overlap(self):
        panel = {'edge': '3', 'widgets': [], 'geometry': {
            'panelLengthMode': '1', 'minLength': '2560', 'maxLength': '2560'}}
        self.assertEqual(app.panel_layout_warnings([panel, panel, panel], 2560), [])

    def test_launchers_normalize_flatpak_keep_spaces_and_drop_only_private_entries(self):
        value = ('applications:Against the Storm.desktop,preferred://filemanager,'
                 'file:///var/lib/flatpak/exports/share/applications/com.spotify.Client.desktop,'
                 'file:///home/private/secret.desktop,applications:org.kde.konsole.desktop')
        result = app.portable_launchers(value)
        self.assertEqual(result, 'applications:Against the Storm.desktop,preferred://filemanager,'
                         'applications:com.spotify.Client.desktop,applications:org.kde.konsole.desktop')
        self.assertTrue(app.share_layout_setting_allowed('launchers', result))
        self.assertNotIn('/home/', result)

    def test_export_keeps_portable_launcher_list(self):
        self.config('plasma-org.kde.plasma.desktop-appletsrc',
                    '[Containments][1]\nlastScreen=0\nplugin=org.kde.panel\n'
                    '[Containments][1][Applets][2][Configuration][General]\n'
                    'launchers=applications:Some Game.desktop,preferred://filemanager\n')
        stage = self.root / 'stage'
        stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE):
            app.public_design(stage, [])
        self.assertIn('launchers=applications:Some Game.desktop,preferred://filemanager',
                      (stage / 'home/.config/plasma-org.kde.plasma.desktop-appletsrc').read_text())

    def test_wallpaper_desktop_binds_to_target_activity(self):
        source = '[Containments][1]\nlastScreen=0\nplugin=org.kde.plasma.folder\n'
        target = '[Containments][2]\nlastScreen=0\nplugin=org.kde.plasma.folder\nactivityId=target\n'
        self.assertIn('activityId=target', app.merge_primary_applet_config(source, target, 0, 0))
        self.assertIn('activityId=active', app.merge_primary_applet_config(
            source, target, 0, 0, target_activity='active'))

    def test_failed_shell_stop_preserves_config_and_attempts_restart(self):
        original = self.config('plasma-org.kde.plasma.desktop-appletsrc', 'unchanged')
        archive = self.root / 'backup.tar.gz'
        archive_file(archive, [('home/.config/plasma-org.kde.plasma.desktop-appletsrc', b'new')],
                     {'paths': ['.config/plasma-org.kde.plasma.desktop-appletsrc']})
        worker = app.RestoreWorker(str(archive), rollback=False, manage_session=True)
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(app, 'PlasmaSession') as factory:
            session = factory.return_value
            session.mode = 'systemd'
            session.stop.side_effect = RuntimeError('still running')
            worker.run()
            session.start.assert_called_once()
        self.assertTrue(errors)
        self.assertEqual(original.read_text(), 'unchanged')

    def test_shell_stops_before_write_and_restarts_after_write(self):
        original = self.config('plasma-org.kde.plasma.desktop-appletsrc', 'old')
        archive = self.root / 'backup.tar.gz'
        archive_file(archive, [('home/.config/plasma-org.kde.plasma.desktop-appletsrc', b'new')],
                     {'paths': ['.config/plasma-org.kde.plasma.desktop-appletsrc']})
        worker = app.RestoreWorker(str(archive), rollback=False, manage_session=True)
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(app, 'PlasmaSession') as factory, patch.object(worker, '_post_restore'):
            session = factory.return_value
            session.mode = None
            session.stop.side_effect = lambda: self.assertEqual(original.read_text(), 'old')
            session.start.side_effect = lambda: self.assertEqual(original.read_text(), 'new')
            worker.run()
            session.stop.assert_called_once()
            session.start.assert_called_once()
        self.assertEqual(errors, [])

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

    def test_layout_snapshot_preserves_panel_geometry_and_widget_order(self):
        source = '''[Containments][1]
lastScreen=0
location=3
plugin=org.kde.panel
AppletOrder=11;12
[Containments][1][Applets][11]
plugin=org.kde.plasma.digitalclock
[Containments][1][Applets][12]
plugin=org.kde.netspeedWidget
[Containments][2]
lastScreen=0
location=3
plugin=org.kde.panel
AppletOrder=21
[Containments][2][Applets][21]
plugin=org.kde.plasma.systemmonitor.memory
'''
        views = '''[PlasmaViews][Panel 1]
alignment=1
panelLengthMode=1
[PlasmaViews][Panel 1][Defaults]
minLength=960
maxLength=960
offset=0
[PlasmaViews][Panel 2]
alignment=2
panelLengthMode=1
[PlasmaViews][Panel 2][Defaults]
minLength=960
maxLength=960
offset=0
'''
        expected = app.panel_layout_snapshot(source, views, 0)
        self.assertEqual(expected[0]['widgets'], [
            'org.kde.plasma.digitalclock', 'org.kde.netspeedWidget'])
        mapping = {}
        restored = app.merge_primary_applet_config(source, '', 0, 0, mapping)
        restored_views = app.merge_panel_views(views, '', mapping, set())
        self.assertEqual(app.panel_layout_snapshot(restored, restored_views, 0), expected)

    def test_layout_qc_reports_overlapping_top_panels_without_rewriting_them(self):
        layout = [{'edge': '3', 'widgets': [],
                   'geometry': {'alignment': '132', 'minLength': '1920',
                                'maxLength': '1920', 'offset': '0'}},
                  {'edge': '3', 'widgets': [],
                   'geometry': {'alignment': '2', 'minLength': '1920',
                                'maxLength': '1920', 'offset': '0'}}]
        self.assertEqual(app.panel_layout_warnings(layout, 1920),
                         ['Panels 1 and 2 overlap at edge 3'])
        self.assertTrue(app.valid_layout_snapshot(layout))

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

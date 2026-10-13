"""Small source-informed fixtures; no extension code is executed."""
import unittest
from unittest.mock import patch
import test_sharing as fixtures
from test_sharing import app, PROFILE


class PopularExtensionTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown
    config = fixtures.SharingTests.config

    def test_window_buttons_validates_order(self):
        self.assertEqual(app.widget_setting_adapter('org.kde.windowbuttons', 'buttons', '5|4|3|10|2|9')[0], 'copy')
        for value in ('5|99', '5|run command', '/home/private', '5||4'):
            self.assertIsNone(app.widget_setting_adapter('org.kde.windowbuttons', 'buttons', value))
        self.assertIsNone(app.widget_setting_adapter('unknown.widget', 'buttons', '5|4|3'))

    def test_music_visual_text_is_not_arbitrary_text(self):
        for key, value in [('songTextInPanel', 'false'), ('titlePosition', '2'),
                           ('fullViewSongTextVisible', 'true'), ('textScrollingSpeed', '5')]:
            self.assertEqual(app.widget_setting_adapter('plasmusic-toolbar', key, value)[0], 'copy')
        for key, value in [('titlePosition', 'private title'), ('noMediaText', 'private'),
                           ('songTextInPanel', 'secret'), ('albumPlaceholder', '/home/me/picture')]:
            self.assertIsNone(app.widget_setting_adapter('plasmusic-toolbar', key, value))

    def test_karousel_relative_widths_are_bounded(self):
        self.assertEqual(app.kwin_setting_adapter('[Script-karousel]', 'presetWidths', '50%,100%')[1], '50%, 100%')
        for value in ('0%', '101%', '-10%', '50%;command', 'private'):
            self.assertIsNone(app.kwin_setting_adapter('[Script-karousel]', 'presetWidths', value))

    def test_adapters_also_preserve_implicit_schema_defaults(self):
        package = self.home / '.local/share/plasma/plasmoids/plasmusic-toolbar'
        (package / 'contents/config').mkdir(parents=True)
        (package / 'metadata.json').write_text('{"KPlugin":{"Id":"plasmusic-toolbar","Version":"4.3.1"}}')
        (package / 'contents/config/main.xml').write_text(
            '<kcfg><group name="General">'
            '<entry name="songTextInPanel" type="Bool"><default>true</default></entry>'
            '<entry name="titlePosition" type="Int"><default>1</default></entry>'
            '</group></kcfg>')
        self.config('plasma-org.kde.plasma.desktop-appletsrc',
                    '[Containments][1]\nplugin=org.kde.panel\nlastScreen=0\n'
                    '[Containments][1][Applets][2]\nplugin=plasmusic-toolbar\n')
        self.config('kwinrc', '[Script-karousel]\npresetWidths=50%,100%\ngapsOuterTop=16\n'
                    '[Script-polonium]\nHalfMiddleSplit=0.5\nTileResizeAmount=10\n')
        stage = self.root / 'stage'
        stage.mkdir()
        review = []
        with patch.object(app, 'desktop_profile', return_value=PROFILE):
            app.public_design(stage, [], settings_review=review)
        text = (stage / 'home/.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
        self.assertIn('songTextInPanel=true', text)
        self.assertIn('titlePosition=1', text)
        text = (stage / 'home/.config/kwinrc').read_text()
        self.assertIn('presetWidths=50%, 100%', text)
        self.assertIn('HalfMiddleSplit=0.5', text)
        self.assertEqual(review, [])

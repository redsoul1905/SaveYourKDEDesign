import json
import shutil
import subprocess
import unittest
from unittest.mock import patch
import test_sharing as fixtures
from test_sharing import app, PROFILE


LEGACY_CURSOR = '''workspace.clientActivated.connect(function() {
    callDBus("org.kde.krunner", "/App", "", "run",
             "/home/" + (process.env.USER || "privatefixture") + "/.local/bin/move-cursor-to-focus.sh");
});'''


def layout_source(image='file:///home/privatefixture/picture.png'):
    data = {'desktops': [{'wallpaperPlugin': 'org.kde.image', 'config': {
        '/Wallpaper/org.kde.image/General': {'Image': image, 'SlidePaths': '/home/privatefixture/'},
        '/Wallpaper/video/General': {'VideoUrls': 'private history'},
    }}], 'panels': [{'applets': [{'config': {'General': {
        'lastPreset': '/home/privatefixture/preset', 'panelWidgets': 'private cache',
        'launchers': 'applications:private.desktop',
        'globalSettings': json.dumps({'radius': 17, 'lastPreset': '/home/privatefixture/preset'})}}}]}]}
    return (app.LAYOUT_PREFIX + json.dumps(data) + app.LAYOUT_SUFFIX).encode()


class PortableLayoutAssetTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown
    config = fixtures.SharingTests.config

    def test_only_reviewed_cursor_implementation_is_migrated(self):
        result = app.portable_cursor_script(LEGACY_CURSOR.encode())
        self.assertEqual(result, app.PORTABLE_CURSOR_SCRIPT.encode())
        self.assertNotIn(b'privatefixture', result)
        self.assertNotIn(b'xdotool', result)
        self.assertNotIn(b'/home/', result)
        self.assertIsNone(app.portable_cursor_script((LEGACY_CURSOR+'\nrunUnknownCommand();').encode()))
        self.assertEqual(app.portable_cursor_script(result), result)

    def test_saved_layout_keeps_values_not_history_or_local_bookmarks(self):
        calls=[]
        def bundle(value):
            calls.append(value)
            return 'file://@SDD_HOME@/.local/share/wallpapers/sdd/neutral.png'
        result=app.portable_saved_layout(layout_source(), bundle)
        self.assertEqual(len(calls),1)
        self.assertNotIn(b'privatefixture', result)
        self.assertNotIn(b'VideoUrls', result)
        self.assertNotIn(b'launchers', result)
        self.assertIn(b'radius', result)
        self.assertIn(b'17', result)
        self.assertIsNotNone(app.read_serialized_layout(result))

    def test_unknown_executable_layout_is_not_evaluated_or_rewritten(self):
        source=layout_source()+b'\nexecuteOtherCode();'
        self.assertEqual(app.portable_saved_layout(source, lambda value: self.fail('called')), source)

    def test_complete_asset_export_bundles_neutral_wallpaper_and_cursor(self):
        self.config('kdeglobals', '[General]\nLookAndFeelPackage=PortableFixture\n')
        self.config('kwinrc', '[Plugins]\ncursor-follows-focusEnabled=true\n')
        wallpaper=self.home/'privatefixture.png'; wallpaper.write_bytes(b'fixture image')
        saved=self.home/'.local/share/plasma/look-and-feel/PortableFixture/contents/layouts/org.kde.plasma.desktop-layout.js'
        saved.parent.mkdir(parents=True); original=layout_source(wallpaper.as_uri()); saved.write_bytes(original)
        script=self.home/'.local/share/kwin/scripts/cursor-follows-focus'
        script.mkdir(parents=True); (script/'main.js').write_text(LEGACY_CURSOR)
        (script/'metadata.json').write_text(json.dumps({'KPlugin':{'Id':'cursorfollowsfocus','Version':'1.0'},
                                                     'X-Plasma-MainScript':'main.js','X-Plasma-API':'javascript'}))
        stage=self.root/'stage'; stage.mkdir()
        with patch.object(app,'desktop_profile',return_value=PROFILE):
            manifest=app.public_design(stage,[])
        self.assertEqual(saved.read_bytes(), original)
        self.assertEqual((script/'main.js').read_text(),LEGACY_CURSOR)
        self.assertIn({'kind':'kwin_action','name':'MoveMouseToFocus'}, manifest['requirements'])
        dest=stage/'home/.local/share/kwin/scripts/cursor-follows-focus'
        self.assertTrue((dest/'contents/code/main.js').is_file())
        self.assertFalse((dest/'main.js').exists())
        meta=json.loads((dest/'metadata.json').read_text())
        self.assertEqual(meta['KPlugin']['Id'],'cursor-follows-focus')
        self.assertNotIn('X-Plasma-MainScript',meta)
        self.assertEqual(len([p for p in manifest['paths'] if '/wallpapers/sdd/' in p]),1)
        for rel in manifest['paths']:
            self.assertNotIn(b'privatefixture',(stage/'home'/rel).read_bytes())

    def test_target_action_is_checked_without_invoking_it(self):
        manifest={'profile':PROFILE,'requirements':[{'kind':'kwin_action','name':'MoveMouseToFocus'}]}
        with patch.object(app.shutil,'which',return_value='/usr/bin/qdbus6'), \
                patch.object(app,'_run_cmd',return_value='MoveMouseToFocus\n') as query:
            self.assertEqual(app.compatibility_issues(manifest,PROFILE,[]),[])
        self.assertTrue(query.call_args.args[0][-1].endswith('.shortcutNames'))
        self.assertNotIn('invokeShortcut',' '.join(query.call_args.args[0]))
        with patch.object(app.shutil,'which',return_value=None):
            self.assertIn('KWin-Aktion fehlt',app.compatibility_issues(manifest,PROFILE,[])[0])

    @unittest.skipUnless(shutil.which('node'), 'Node is optional for JavaScript harness tests')
    def test_javascript_uses_receiver_home_and_native_action(self):
        layout=app.portable_saved_layout(layout_source(),lambda value:'file://@SDD_HOME@/.local/share/wallpapers/sdd/neutral.png').decode()
        program='''const assert = require('assert');
var received;
function getApiVersion() { return { loadSerializedLayout: value => { received=value; } }; }
function userDataPath() { return "/home/receiver with #"; }
'''+layout+'''
assert.equal(received.desktops[0].config['/Wallpaper/org.kde.image/General'].Image,
 'file:///home/receiver%20with%20%23/.local/share/wallpapers/sdd/neutral.png');
var callback; var calls=[];
var workspace={windowActivated:{connect: function(fn) { callback=fn; }}};
function callDBus() { calls.push(Array.from(arguments)); }
'''+app.PORTABLE_CURSOR_SCRIPT+'''
callback(null); assert.equal(calls.length,0);
callback({}); assert.deepEqual(calls[0], ['org.kde.kglobalaccel','/component/kwin',
 'org.kde.kglobalaccel.Component','invokeShortcut','MoveMouseToFocus']);
'''
        subprocess.run(['node','-e',program],check=True,capture_output=True,text=True)

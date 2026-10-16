"""Privacy regressions use synthetic data, never upload or touch a desktop."""
import struct
import zlib
import unittest
from unittest.mock import patch
import test_sharing as fixtures
from test_sharing import app, PROFILE, manifest, archive_file


def chunk(kind, body):
    return struct.pack('!I', len(body)) + kind + body + struct.pack('!I', zlib.crc32(kind + body) & 0xffffffff)


def png(extra=b''):
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
            + extra + chunk(b'IDAT', zlib.compress(b'\0\0\0\0')) + chunk(b'IEND', b''))


class PublicPrivacyTests(unittest.TestCase):
    setUp = fixtures.SharingTests.setUp
    tearDown = fixtures.SharingTests.tearDown
    config = fixtures.SharingTests.config

    def test_empty_packaging_markers_are_omitted(self):
        self.config('kdeglobals', '[Icons]\nTheme=PrivacyFixture\n')
        icons = self.home / '.local/share/icons/PrivacyFixture'
        icons.mkdir(parents=True)
        (icons/'test.svg').write_text('<svg/>')
        for name in ('.placeholder', '.gitkeep', '.keep'):
            (icons/name).touch()
        stage = self.root/'stage'; stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE):
            result = app.public_design(stage, [])
        self.assertTrue(any(p.endswith('test.svg') for p in result['paths']))
        self.assertFalse(any(p.endswith(('.placeholder', '.gitkeep', '.keep')) for p in result['paths']))

    def test_nonempty_packaging_markers_still_block(self):
        self.config('kdeglobals', '[Icons]\nTheme=PrivacyFixture\n')
        icons = self.home / '.local/share/icons/PrivacyFixture'
        icons.mkdir(parents=True)
        (icons/'.placeholder').write_text('private content')
        stage = self.root/'stage'; stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE), self.assertRaisesRegex(ValueError, 'Datenschutz'):
            app.public_design(stage, [])

    def test_upload_gate_still_rejects_hidden_markers(self):
        rel = '.local/share/icons/Test/.placeholder'
        path = self.root/'unsafe.sdd'
        archive_file(path, [('home/'+rel, b'')], manifest([rel]))
        with patch.object(app, 'catbox_open') as network, self.assertRaises(ValueError):
            app.upload_design(path)
        network.assert_not_called()

    def test_secret_files_block_export_instead_of_copying(self):
        self.config('kdeglobals', '[Icons]\nTheme=PrivacyFixture\n')
        icons = self.home / '.local/share/icons/PrivacyFixture'
        icons.mkdir(parents=True)
        (icons / '.env').write_text('API_TOKEN=synthetic-secret')
        stage = self.root / 'stage'; stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE), self.assertRaisesRegex(ValueError, 'Datenschutz'):
            app.public_design(stage, [])

    def test_generic_name_is_not_exported(self):
        self.config('kdeglobals', '[General]\nname=PersonalNameFixture\nColorScheme=Breeze\n')
        stage = self.root / 'stage'; stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE):
            app.public_design(stage, [])
        self.assertNotIn('PersonalNameFixture', (stage/'home/.config/kdeglobals').read_text())

    def test_personal_script_paths_and_identity_block(self):
        for value in (b'file:///home/alice/Pictures/photo.png', b'file:\\/\\/\\/home/alice/private',
                      b'/mnt/backup/Documents', b'/home%2Falice%2Fprivate', b'API_TOKEN=fixture-secret',
                      b'{"apiToken":"fixture-secret"}', b'-----BEGIN PRIVATE KEY-----'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                app.check_public_content(value, 'theme/script.js')
        with patch.dict(app.os.environ, {'USER': 'IdentityFixture'}), self.assertRaises(ValueError):
            app.check_public_content(b'process.env.USER || "IdentityFixture"', 'script.js')

    def test_utf16_sensitive_text_blocked(self):
        with self.assertRaises(ValueError):
            app.check_public_content('API_TOKEN=fixture-secret'.encode('utf-16'), 'data.txt')

    def test_error_does_not_echo_secret(self):
        with self.assertRaises(ValueError) as error:
            app.check_public_content(b'API_TOKEN=DoNotEchoThis', 'theme/config')
        self.assertNotIn('DoNotEchoThis', str(error.exception))

    def test_png_metadata_removed_pixels_unchanged(self):
        for kind in (b'tEXt', b'iTXt', b'zTXt', b'eXIf', b'tIME'):
            with self.subTest(kind=kind):
                cleaned = app.clean_public_media(png(chunk(kind, b'Author\0PrivateFixture')), 'wall.png')
                self.assertEqual(cleaned, png())
                self.assertEqual(app.clean_public_media(cleaned, 'wall.png'), cleaned)

    def test_png_malformed_unknown_and_trailing_content_blocked(self):
        for data in (png()[:-1], png()+b'private', png(chunk(b'zzZz', b'private'))):
            with self.assertRaises(ValueError):
                app.clean_public_media(data, 'wall.png')

    def test_jpeg_comments_removed_without_recompression(self):
        body = b'Author PrivateFixture'
        jpeg = b'\xff\xd8\xff\xfe' + struct.pack('!H', len(body)+2) + body + b'\xff\xd9'
        self.assertEqual(app.clean_public_media(jpeg, 'wall.jpg'), b'\xff\xd8\xff\xd9')
        with self.assertRaises(ValueError):
            app.clean_public_media(jpeg+b'private', 'wall.jpg')

    def test_webp_metadata_removed(self):
        metadata = b'XMP '+struct.pack('<I', 4)+b'name'
        pixels = b'VP8 '+struct.pack('<I', 2)+b'xx'
        data = b'RIFF'+struct.pack('<I', 4+len(metadata)+len(pixels))+b'WEBP'+metadata+pixels
        clean = app.clean_public_media(data, 'wall.webp')
        self.assertEqual(clean, b'RIFF'+struct.pack('<I', 4+len(pixels))+b'WEBP'+pixels)

    def test_svg_editor_metadata_removed_visible_elements_retained(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><metadata>/home/alice/private</metadata><rect width="1" height="1"/></svg>'
        cleaned = app.clean_public_media(svg, 'icon.svg')
        self.assertNotIn(b'/home/', cleaned)
        self.assertIn(b'rect', cleaned)
        self.assertEqual(app.clean_public_media(cleaned, 'icon.svg'), cleaned)

    def test_unknown_media_and_disguised_containers_blocked(self):
        for name, data in [('movie.mp4', b'video'), ('image.avif', b'image'), ('data.bin', b'PK\x03\x04hidden')]:
            with self.assertRaises(ValueError):
                app.clean_public_media(data, name)

    def test_final_gate_cannot_be_bypassed_by_direct_upload(self):
        for content in (b'API_TOKEN=fixture-secret', b'/home/alice/secret'):
            path = self.root/'unsafe.sdd'
            archive_file(path, [('home/.config/kdeglobals', content)], manifest())
            with patch.object(app, 'catbox_open') as network, self.assertRaises(ValueError):
                app.upload_design(path)
            network.assert_not_called()

    def test_final_gate_rejects_uncleaned_media(self):
        rel = '.local/share/wallpapers/sdd/image.png'
        path = self.root/'unsafe.sdd'
        archive_file(path, [('home/'+rel, png(chunk(b'tEXt', b'Author\0PrivateFixture')))], manifest([rel]))
        with patch.object(app, 'catbox_open') as network, self.assertRaises(ValueError):
            app.upload_design(path)
        network.assert_not_called()

    def test_final_gate_accepts_cleaned_media(self):
        rel = '.local/share/wallpapers/sdd/image.png'
        path = self.root/'safe.sdd'
        archive_file(path, [('home/'+rel, png())], manifest([rel]))
        app.audit_public_upload(path)

    def test_selected_theme_cannot_follow_link_into_sibling(self):
        self.config('kdeglobals', '[Icons]\nTheme=PrivacyFixture\n')
        icons = self.home / '.local/share/icons/PrivacyFixture'
        icons.mkdir(parents=True)
        secret = icons.parent / 'personal.txt'; secret.write_text('private fixture')
        (icons / 'leak.txt').symlink_to(secret)
        stage = self.root / 'stage'; stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE), self.assertRaisesRegex(ValueError, 'link leaves'):
            app.public_design(stage, [])

    def test_tela_variants_can_share_public_base_icons(self):
        for variant, base in [('Tela-dark', 'Tela'), ('Tela-light', 'Tela'),
                              ('Tela-circle-dark', 'Tela-circle'), ('Tela-circle-light', 'Tela-circle')]:
            with self.subTest(variant=variant):
                self.config('kdeglobals', '[Icons]\nTheme='+variant+'\n')
                root = self.home / '.local/share/icons'
                (root/base/'16/apps').mkdir(parents=True, exist_ok=True)
                (root/base/'index.theme').write_text('[Icon Theme]\nName='+base+'\n')
                (root/base/'16/apps/test.svg').write_text('<svg/>')
                (root/variant/'16').mkdir(parents=True, exist_ok=True)
                (root/variant/'16/apps').symlink_to('../../'+base+'/16/apps')
                stage = self.root/variant; stage.mkdir()
                with patch.object(app, 'desktop_profile', return_value=PROFILE):
                    app.public_design(stage, [])
                self.assertEqual((stage/'home/.local/share/icons'/variant/'16/apps/test.svg').read_text(), '<svg/>')

    def test_tela_base_cannot_redirect_to_private_directory(self):
        self.config('kdeglobals', '[Icons]\nTheme=Tela-dark\n')
        root = self.home / '.local/share/icons'
        (root/'Tela-dark').mkdir(parents=True)
        private = self.home/'personal'; private.mkdir()
        (private/'index.theme').write_text('[Icon Theme]\n')
        (private/'secret.svg').write_text('<svg/>')
        (root/'Tela').symlink_to(private)
        (root/'Tela-dark/apps').symlink_to('../Tela')
        stage=self.root/'stage'; stage.mkdir()
        with patch.object(app, 'desktop_profile', return_value=PROFILE), self.assertRaisesRegex(ValueError, 'link leaves'):
            app.public_design(stage, [])

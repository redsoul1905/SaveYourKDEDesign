"""Private restore regressions; all writes stay in a temporary HOME."""
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import saveyourkdedesign as app


class RestoreSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.home_patch = patch.object(app, 'HOME', self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.archive = self.root / 'backup.tar.gz'
        self.target = self.home / '.config/kdeglobals'
        self.target.parent.mkdir()
        self.target.write_text('old')

    def write_archive(self, paths=None, files=None, **extra):
        manifest = {'paths': paths if paths is not None else ['.config/kdeglobals'],
                    'categories': ['cat_plasma', 'cat_fonts'], **extra}
        contents = {'manifest.json': json.dumps(manifest),
                    **(files if files is not None else {'home/.config/kdeglobals': 'new'})}
        with tarfile.open(self.archive, 'w:gz') as tar:
            for name, value in contents.items():
                data = value.encode()
                member = tarfile.TarInfo(name)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))

    def restore(self, categories=None, rollback=False):
        worker = app.RestoreWorker(str(self.archive), categories, rollback)
        errors, successes = [], []
        worker.failed.connect(errors.append)
        worker.finished_ok.connect(successes.append)
        with patch.object(worker, '_post_restore'):
            worker.run()
        return errors, successes

    def test_empty_category_match_does_not_restore_other_categories(self):
        self.write_archive()
        self.assertEqual(self.restore(['cat_fonts']), ([], [False]))
        self.assertEqual(self.target.read_text(), 'old')

    def test_empty_manifest_paths_do_not_restore_unlisted_files(self):
        self.write_archive(paths=[])
        self.assertEqual(self.restore(), ([], [False]))
        self.assertEqual(self.target.read_text(), 'old')

    def test_manifest_traversal_is_rejected_before_writes(self):
        outside = self.root / 'outside'
        outside.write_text('keep')
        self.write_archive(paths=['../outside'], files={'home/dummy': 'x', 'outside': 'bad'})
        errors, successes = self.restore()
        self.assertTrue(errors)
        self.assertFalse(successes)
        self.assertEqual(outside.read_text(), 'keep')

    def test_rollback_failure_blocks_restore(self):
        self.write_archive()
        with patch.object(app, 'make_rollback', side_effect=OSError('disk full')):
            errors, successes = self.restore(rollback=True)
        self.assertTrue(errors)
        self.assertFalse(successes)
        self.assertEqual(self.target.read_text(), 'old')

    def test_incomplete_rollback_is_removed_and_previous_backup_preserved(self):
        app.rollback_path().write_bytes(b'previous')
        with patch.object(tarfile.TarFile, 'add', side_effect=OSError('unreadable')):
            with self.assertRaises(OSError):
                app.make_rollback(['.config/kdeglobals'], ['cat_plasma'])
        self.assertEqual(app.rollback_path().read_bytes(), b'previous')
        self.assertFalse(app.rollback_path().with_name(app.rollback_path().name + '.new').exists())

    def test_copy_failure_preserves_file_and_reports_failure(self):
        self.write_archive()
        def partial_copy(source, dest, **kwargs):
            Path(dest).write_text('partial')
            raise OSError('disk full')
        with patch.object(app.shutil, 'copy2', side_effect=partial_copy):
            errors, successes = self.restore()
        self.assertTrue(errors)
        self.assertFalse(successes)
        self.assertEqual(self.target.read_text(), 'old')
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_symlink_creation_failure_preserves_destination(self):
        source = self.root / 'link'
        source.symlink_to('some-target')
        with patch.object(app.os, 'symlink', side_effect=OSError('failed')):
            with self.assertRaises(OSError):
                app.RestoreWorker('')._merge(source, self.target)
        self.assertEqual(self.target.read_text(), 'old')

    def test_directory_staging_failure_preserves_destination_file(self):
        source = self.root / 'directory'
        source.mkdir()
        with patch.object(app.shutil, 'copytree', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                app.RestoreWorker('')._merge(source, self.target)
        self.assertEqual(self.target.read_text(), 'old')

    def test_type_changes_work_in_both_directions(self):
        source = self.root / 'directory'
        source.mkdir()
        (source / 'item').write_text('content')
        worker = app.RestoreWorker('')
        worker._merge(source, self.target)
        self.assertEqual((self.target / 'item').read_text(), 'content')
        worker._merge(source / 'item', self.target)
        self.assertEqual(self.target.read_text(), 'content')

    def test_failed_type_change_restores_original_directory(self):
        destination = self.home / 'dir'
        destination.mkdir()
        (destination / 'keep').write_text('keep')
        real_replace = app.os.replace
        def fail_commit(src, dst):
            if Path(src).name == 'new':
                raise OSError('rename failed')
            return real_replace(src, dst)
        with patch.object(app.os, 'replace', side_effect=fail_commit):
            with self.assertRaises(OSError):
                app.RestoreWorker('')._merge(self.target, destination)
        self.assertEqual((destination / 'keep').read_text(), 'keep')

    def test_package_lists_are_replaced_not_merged(self):
        self.write_archive(paths=[], files={'packages/pacman-explicit.txt': 'old-package'})
        self.assertEqual(self.restore(), ([], [True]))
        self.write_archive(paths=[], files={'packages/flatpak.txt': 'org.new.App'})
        self.assertEqual(self.restore(), ([], [True]))
        package_dir = self.home / '.savedesktopdesign-packages'
        self.assertEqual([p.name for p in package_dir.iterdir()], ['flatpak.txt'])

    def test_backup_without_packages_clears_stale_lists(self):
        packages = self.home / '.savedesktopdesign-packages'
        packages.mkdir()
        (packages / 'apt-manual.txt').write_text('old')
        self.write_archive()
        self.assertEqual(self.restore(), ([], [False]))
        self.assertEqual(list(packages.iterdir()), [])

    def test_package_copy_failure_keeps_previous_lists(self):
        packages = self.home / '.savedesktopdesign-packages'
        packages.mkdir()
        (packages / 'apt-manual.txt').write_text('old')
        self.write_archive(paths=[], files={'packages/flatpak.txt': 'org.new.App'})
        with patch.object(app.shutil, 'copy2', side_effect=OSError('disk full')):
            errors, successes = self.restore()
        self.assertTrue(errors)
        self.assertFalse(successes)
        self.assertEqual((packages / 'apt-manual.txt').read_text(), 'old')
        self.assertEqual(len(list(packages.iterdir())), 1)

    def test_rollback_does_not_clear_package_lists(self):
        packages = self.home / '.savedesktopdesign-packages'
        packages.mkdir()
        (packages / 'apt-manual.txt').write_text('keep')
        self.write_archive(rollback=True)
        self.assertEqual(self.restore(), ([], [False]))
        self.assertEqual((packages / 'apt-manual.txt').read_text(), 'keep')

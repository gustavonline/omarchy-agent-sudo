"""Registration contracts in disposable homes; no native broker/auth calls."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('registration', ROOT / 'registration.py')
reg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reg)


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / 'home'
        self.home.mkdir()
        self.omarchy = self.base / 'omarchy'
        self.stock = self.omarchy / 'default/agents/skills/omarchy'
        self.stock.mkdir(parents=True)
        self.stock_file = self.stock / 'SKILL.md'
        self.stock_file.write_text('---\nname: omarchy\ndescription: original triggers\n---\nOriginal guide\n')
        self.env = patch.dict(os.environ, {'HOME': str(self.home), 'OMARCHY_PATH': str(self.omarchy)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_normal_entry_routes_without_package_edits_and_refreshes_after_update(self):
        original = self.stock_file.read_bytes()
        (self.stock / 'plugins.md').write_text('Live topic guide')
        reg.install(self.home)
        reg.install(self.home)
        entry = self.home / '.agents/skills/omarchy/SKILL.md'
        self.assertIn(str(self.stock_file), entry.read_text())
        self.assertIn(str(ROOT / 'SKILL.md'), entry.read_text())
        self.assertNotIn('Original guide', entry.read_text())
        self.assertEqual(original, self.stock_file.read_bytes())
        self.assertEqual(reg.problems(self.home), [])
        self.stock_file.write_text('---\nname: omarchy\ndescription: updated triggers\n---\nNew guide\n')
        hook = self.home / '.config/omarchy/hooks/post-update.d/99-agent-access'
        subprocess.run([str(hook)], check=True, capture_output=True)
        self.assertIn('updated triggers', entry.read_text())
        self.assertIn('New guide', self.stock_file.read_text())
        self.assertEqual((self.stock / 'plugins.md').read_text(), 'Live topic guide')

    def test_late_custom_root_conflict_changes_no_other_registration(self):
        custom = self.home / '.codex/skills/omarchy'
        custom.mkdir(parents=True)
        (custom / 'SKILL.md').write_text('Owner method')
        with self.assertRaises(ValueError):
            reg.install(self.home)
        self.assertFalse((self.home / '.agents/skills/omarchy-agent-access').exists())
        self.assertFalse((self.home / '.local/bin/omarchy-agent-access').exists())
        self.assertEqual((custom / 'SKILL.md').read_text(), 'Owner method')

    def test_remove_restores_stock_and_preserves_unrelated_replacement(self):
        reg.install(self.home)
        unrelated = self.home / '.claude/skills/omarchy-agent-access'
        unrelated.unlink()
        unrelated.mkdir()
        (unrelated / 'SKILL.md').write_text('Replacement owner method')
        reg.remove(self.home)
        self.assertEqual((self.home / '.agents/skills/omarchy').resolve(), self.stock)
        self.assertEqual((unrelated / 'SKILL.md').read_text(), 'Replacement owner method')
        self.assertFalse((self.home / '.local/bin/omarchy-agent-access').exists())
        self.assertFalse((self.home / '.config/omarchy/hooks/post-update.d/99-agent-access').exists())

    def test_diagnostics_identify_broken_registration_and_missing_entry(self):
        reg.install(self.home)
        command = self.home / '.local/bin/omarchy-agent-access'
        command.unlink()
        command.symlink_to(self.base / 'gone')
        entry = self.home / '.local/share/omarchy-agent-access/omarchy/SKILL.md'
        entry.unlink()
        paths = {x['path'] for x in reg.problems(self.home)}
        self.assertIn(str(command), paths)
        self.assertIn(str(entry), paths)

    def test_dangling_custom_entry_is_not_replaced(self):
        managed = self.home / '.local/share/omarchy-agent-access/omarchy'
        managed.mkdir(parents=True)
        entry = managed / 'SKILL.md'
        entry.symlink_to(self.base / 'missing-owner-file')
        with self.assertRaises(ValueError):
            reg.install(self.home)
        self.assertTrue(entry.is_symlink())
        self.assertFalse((self.home / '.local/bin/omarchy-agent-access').exists())

    @unittest.skipUnless(shutil.which('omarchy'), 'Actual Omarchy CLI unavailable')
    def test_headless_install_native_update_reinstall_and_remove(self):
        source = self.base / 'source'
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        def git(*args, cwd=source):
            return subprocess.run(['git', '-c', 'user.name=Fixture', '-c',
                                   'user.email=fixture@example.invalid', *args],
                                  cwd=cwd, check=True, capture_output=True, text=True)
        git('init')
        git('add', '.')
        git('commit', '-m', 'Disposable fixture')
        result = subprocess.run([str(source / 'install-user.sh')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = self.home / '.config/omarchy/plugins/io.github.gustavonline.passwordless-sudo'
        self.assertEqual((self.home / '.agents/skills/omarchy-agent-access').resolve(), installed)
        self.assertEqual(self.stock_file.read_text().splitlines()[-1], 'Original guide')
        subprocess.run([str(installed / 'install-user.sh')], check=True, capture_output=True)
        git('remote', 'set-url', 'origin', str(source), cwd=installed)
        (source / 'SKILL.md').write_text((source / 'SKILL.md').read_text() + '\nUpdated fixture method.\n')
        git('add', 'SKILL.md')
        git('commit', '-m', 'Fixture update')
        # Only desktop rescan is substituted. Git/native Omarchy updater are real.
        fakebin = self.base / 'bin'
        fakebin.mkdir()
        shell = fakebin / 'omarchy-shell'
        shell.write_text('#!/bin/sh\nexit 0\n')
        shell.chmod(0o755)
        env = dict(os.environ, PATH=str(fakebin) + ':' + os.environ['PATH'])
        result = subprocess.run([str(installed / 'agent-access'), 'update'],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Updated fixture method.', (self.home / '.agents/skills/omarchy-agent-access/SKILL.md').read_text())
        subprocess.run([str(installed / 'agent-access'), 'remove-registration'],
                       check=True, capture_output=True)
        self.assertEqual((self.home / '.agents/skills/omarchy').resolve(), self.stock)
        self.assertTrue((installed / 'approval/z13-admin').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install
from runner import Programs


class WorkspaceTests(unittest.TestCase):
    def account(self, slot):
        return dict(slot=slot, hash='$6$testhash', db_password='a' * 48)

    def test_name_validation(self):
        for value in ('../alice', 'a;rm', 'A', '', 'a' * 21, '7bob'):
            with self.assertRaises(ValueError):
                install.validate_name(value)
        self.assertEqual(install.validate_name('student_1'), 'student_1')

    def test_two_accounts_and_update_preserve_work(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            alice, ap, asp = install.provision('alice', self.account(0), ROOT, data)
            bob, bp, bsp = install.provision('bob', self.account(1), ROOT, data)
            self.assertEqual((ap, bp, asp, bsp), (8100, 8101, 9200, 9202))
            for home, name, port in ((alice, 'alice', 9201), (bob, 'bob', 9203)):
                config = (home / 'web/code/config.php').read_text()
                self.assertIn((home / 'active_script.py').as_posix(), config)
                self.assertNotIn('/home/client', config)
                blocks = (home / 'web/blocks/index.php').read_text()
                self.assertIn((home / 'control.sock').as_posix(), blocks)
                self.assertNotIn('/run/codynick-script-control.sock', blocks)
                stage = (home / 'web/blocks/stage.php').read_text()
                self.assertIn(f'127.0.0.1:{port}', stage)
                bridge = (home / 'lib/SpriteStage.py').read_text()
                self.assertIn(f'127.0.0.1:{port}', bridge)
                self.assertIn(f'cnmu_{name}', (home / 'lib/Dashboard.py').read_text())
                self.assertIn(f'cnmu_{name}', (home / 'web/dashboard/config.php').read_text())
                self.assertIn('exclusive=True', (home / 'lib/CodyNick.py').read_text())
                self.assertIn("fetch('/simulation/state'", (home / 'simulator/app.js').read_text())
                self.assertTrue((home / 'web/favicon.ico').exists())
                self.assertTrue((home / 'web/blocks/vendor/blockly/blockly.min.js').exists())
            saved = alice / 'web/blocks/data/designs/own.json'
            saved.write_text('{"my": "design"}')
            main = alice / 'web/blocks/data/main.json'
            main.write_text('{"my": "workspace"}')
            active = alice / 'active_script.py'
            active.write_text('print("my code")')
            project = alice / 'userfiles/mine.py'
            project.write_text('print(123)')
            token = (alice / 'token').read_text()
            install.provision('alice', self.account(0), ROOT, data)
            self.assertEqual(saved.read_text(), '{"my": "design"}')
            self.assertEqual(main.read_text(), '{"my": "workspace"}')
            self.assertEqual(active.read_text(), 'print("my code")')
            self.assertEqual(project.read_text(), 'print(123)')
            self.assertEqual((alice / 'token').read_text(), token)
            self.assertFalse((bob / 'userfiles/mine.py').exists())

    def test_setup_does_not_install_ai_or_alter_networking(self):
        source = (ROOT / 'install.py').read_text()
        for operation in ('netplan apply', 'hostapd', 'torch==', 'llama_cpp', 'ufw allow'):
            self.assertNotIn(operation, source)

    def test_manifest(self):
        if (ROOT / 'release.json').exists():
            install.verify(ROOT)


@unittest.skipUnless(os.name == 'posix', 'POSIX process groups required')
class RunnerTests(unittest.TestCase):
    def test_stop_only_own_user_and_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            a = Path(temp) / 'alice'
            b = Path(temp) / 'bob'
            for home in (a, b):
                home.mkdir()
                (home / 'active_script.py').write_text('import time\nprint("started",flush=True)\ntime.sleep(60)\n')
            alice, bob = Programs(a, sys.executable), Programs(b, sys.executable)
            try:
                alice.control('start')
                bob.control('start')
                time.sleep(.2)
                first = alice.process
                alice.control('stop')
                self.assertIsNotNone(first.poll())
                self.assertIsNone(bob.process.poll())
                alice.control('start')
                self.assertNotEqual(first.pid, alice.process.pid)
                with self.assertRaises(ValueError):
                    bob.control('restart;bad')
                self.assertIsNone(bob.process.poll())
            finally:
                alice.control('stop')
                bob.control('stop')


if __name__ == '__main__':
    unittest.main()

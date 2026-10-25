import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gateway


class LoginTests(unittest.TestCase):
    def test_sessions_select_only_logged_in_account(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'accounts.json'
            path.write_text(json.dumps({'alice': {'slot': 0, 'hash': 'alicehash'},
                                        'bob': {'slot': 1, 'hash': 'bobhash'}}))
            sessions = gateway.Sessions(path)
            with patch('gateway.verify_password', return_value=False):
                self.assertIsNone(sessions.login('alice', 'wrong'))
                self.assertIsNone(sessions.login('../alice', 'wrong'))
            with patch('gateway.verify_password', return_value=True):
                alice = sessions.login('alice', 'password')
                bob = sessions.login('bob', 'password')
            self.assertNotEqual(alice, bob)
            self.assertEqual(sessions.account(alice)[0], 'alice')
            self.assertEqual(sessions.account(bob)[1]['slot'], 1)
            sessions.logout(alice)
            self.assertIsNone(sessions.account(alice))
            self.assertEqual(sessions.account(bob)[0], 'bob')
            # A password change invalidates that account's existing sessions.
            path.write_text(json.dumps({'bob': {'slot': 1, 'hash': 'newhash'}}))
            self.assertIsNone(sessions.account(bob))

    def test_session_expiry(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'accounts.json'
            path.write_text('{"alice":{"slot":0,"hash":"test"}}')
            sessions = gateway.Sessions(path)
            with patch('gateway.verify_password', return_value=True), patch('gateway.time.monotonic', return_value=1):
                token = sessions.login('alice', 'password')
            with patch('gateway.time.monotonic', return_value=gateway.SESSION_SECONDS + 2):
                self.assertIsNone(sessions.account(token))

    @unittest.skipUnless(shutil.which('openssl'), 'OpenSSL required')
    def test_existing_sha512_passwords(self):
        encoded = subprocess.run(['openssl', 'passwd', '-6', '-stdin'], input='the password\n',
                                 capture_output=True, text=True, check=True).stdout.strip()
        self.assertTrue(gateway.verify_password('the password', encoded))
        self.assertFalse(gateway.verify_password('wrong', encoded))
        self.assertFalse(gateway.verify_password('the password\nanything', encoded))
        self.assertFalse(gateway.verify_password('the password', '$6$bad;command$bad'))

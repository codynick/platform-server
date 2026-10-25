"""Create disposable test accounts in an ephemeral CI VM only."""
import json
from pathlib import Path
import subprocess

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install

config = Path('/etc/codynick-multi')
config.mkdir(mode=0o700, exist_ok=True)
encoded = subprocess.run(['openssl', 'passwd', '-6', '-stdin'],
    input='OnlyForEphemeralCI123\n', text=True, capture_output=True, check=True).stdout.strip()
install.save_accounts({name: {'slot': index, 'hash': encoded, 'db_password': 'a' * 48}
    for index, name in enumerate(('alice', 'bob'))})

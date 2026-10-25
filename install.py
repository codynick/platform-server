"""Small multi-user adapter around CodyNick 0.11.0's existing interfaces."""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error

VERSION = '0.1.0'
SOURCE = Path(__file__).resolve().parent
CONFIG = Path('/etc/codynick-multi')
DATA = Path('/var/lib/codynick-multi')
APP = Path('/opt/codynick-multi')
ACCOUNTS = CONFIG / 'accounts.json'


def run(*args, **kwargs):
    print('+', args[0], ' '.join(str(a) for a in args[1:3]), flush=True)
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def write(path, content, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.new')
    temp.write_text(content, encoding='utf-8')
    temp.chmod(mode)
    temp.replace(path)


def save_accounts(accounts):
    write(ACCOUNTS, json.dumps(accounts, indent=2), 0o600)


def accounts():
    return json.loads(ACCOUNTS.read_text()) if ACCOUNTS.exists() else {}


def validate_name(name):
    if not re.fullmatch('[a-z][a-z0-9_]{0,19}', name):
        raise ValueError('Use 1-20 lowercase letters, digits, underscore; start with a letter.')
    return name


def password_hash():
    first = getpass.getpass('Password (at least 8 characters): ')
    second = getpass.getpass('Repeat password: ')
    if len(first) < 8 or first != second:
        raise ValueError('Passwords must match and contain at least 8 characters.')
    return subprocess.run(['openssl', 'passwd', '-6', '-stdin'], input=first + '\n',
                          text=True, capture_output=True, check=True).stdout.strip()


def new_account(name, saved):
    validate_name(name)
    if name in saved:
        raise ValueError('Account exists. Use passwd to change its password.')
    used = {a['slot'] for a in saved.values()}
    slot = next((n for n in range(100) if n not in used), None)
    if slot is None:
        raise ValueError('Account limit reached (100).')
    return {'slot': slot, 'hash': password_hash(), 'db_password': secrets.token_hex(24),
            'created': datetime.now(timezone.utc).isoformat()}


def prepare():
    if platform.machine() not in ('x86_64', 'aarch64'):
        raise RuntimeError('Ubuntu x86-64 or ARM64 is required.')
    os_release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if os_release.get('ID', '').strip('"') != 'ubuntu':
        raise RuntimeError('This edition requires Ubuntu.')
    CONFIG.mkdir(parents=True, exist_ok=True)
    CONFIG.chmod(0o700)
    saved = accounts()
    if not saved:
        print('Create the first web account. This is not a Linux/SSH account.')
        name = validate_name(input('Username [teacher]: ').strip() or 'teacher')
        saved[name] = new_account(name, saved)
        save_accounts(saved)


def copy_tree(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.keep'))


def transform(text, home, sim_port, sprite_port):
    return (text.replace('/home/client', home.as_posix())
            .replace('/run/codynick-script-control.sock', (home / 'control.sock').as_posix())
            .replace('127.0.0.1:8092', f'127.0.0.1:{sprite_port}')
            .replace("('127.0.0.1', 8092)", f"('127.0.0.1', {sprite_port})"))


def page(name):
    label = html.escape(name)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CodyNick | {label}</title>
<link rel="icon" href="/favicon.ico"><link rel="stylesheet" href="/assets/multi.css"></head>
<body><header><strong>CodyNick</strong><span>{label}</span><small>Multi-user {VERSION}</small></header>
<main><h1>Your Tools</h1><nav>
<a href="/code/">Python IDE</a><a href="/blocks/">Block Coding</a>
<a href="/simulator/">Gadget Simulator</a><a href="/dashboard/">Dashboard</a>
<a href="/guide.html">Guide</a></nav></main></body></html>'''


def provision(name, account, source=SOURCE, data=DATA):
    validate_name(name)
    home = data / 'users' / name
    web = home / 'web'
    web_port = 8100 + account['slot']
    sim_port = 9200 + account['slot'] * 2
    sprite_port = sim_port + 1
    upstream = source / 'upstream/components'
    for directory in ('userfiles', 'images', 'audio', 'lib', 'web', 'simulator', 'sprite'):
        (home / directory).mkdir(parents=True, exist_ok=True)
    for directory in ('code', 'blocks', 'dashboard', 'assets'):
        origin = upstream / 'ide' / directory
        # Blockly data is persistent, not a release payload.
        shutil.copytree(origin, web / directory, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('data', '__pycache__', '*.pyc'))
    for asset in ('favicon.ico', 'tool-navigation.css'):
        origin = upstream / 'ide/assets' / asset
        if origin.exists():
            shutil.copy2(origin, web / asset)
    copy_tree(upstream / 'simulator', home / 'simulator')
    copy_tree(upstream / 'sprite-stage', home / 'sprite')
    for lib in ('CodyNick.py', 'CodyNickSimulator.py', 'Dashboard.py', 'SpriteStage.py'):
        shutil.copy2(upstream / 'client' / lib, home / 'lib' / lib)
    for root in (web, home / 'lib', home / 'sprite'):
        for path in root.rglob('*'):
            if path.suffix in ('.py', '.php') and path.is_file():
                text = transform(path.read_text(encoding='utf-8'), home, sim_port, sprite_port)
                if path.name == 'Dashboard.py':
                    text = text.replace('"database": "codynick"', f'"database": "cnmu_{name}"')
                    text = text.replace('"user": "codynick"', f'"user": "cnmu_{name}"')
                    text = text.replace('"password": "codynick"', f'"password": "{account["db_password"]}"')
                if path == web / 'dashboard/config.php':
                    text = text.replace('$db_name = "codynick";', f'$db_name = "cnmu_{name}";')
                    text = text.replace('$db_user = "codynick";', f'$db_user = "cnmu_{name}";')
                    text = text.replace('$db_pass = "codynick";', f'$db_pass = "{account["db_password"]}";')
                if path.name == 'CodyNick.py':
                    text = text.replace('write_timeout=1,', 'write_timeout=1,\n            exclusive=True,')
                write(path, text)
    for filename in ('active_script.py', 'log.log'):
        if not (home / filename).exists():
            write(home / filename, '# Your personal CodyNick script\n' if filename.endswith('.py') else '')
    if not (home / 'token').exists():
        write(home / 'token', secrets.token_hex(32), 0o640)
    write(home / 'runtime.json', json.dumps({'sim_port': sim_port, 'sprite_port': sprite_port}))
    (web / 'blocks/data/designs').mkdir(parents=True, exist_ok=True)
    if not (web / 'blocks/data/main.json').exists():
        write(web / 'blocks/data/main.json', '{}')
    # Keep the simulator behind the same authenticated web origin.
    write(web / 'simulator/index.php', "<?php header('Location: /simulation/'); exit;\n")
    sim_index = home / 'simulator/index.html'
    text = sim_index.read_text().replace('href="/', 'href="/simulation/').replace('src="/', 'src="/simulation/')
    write(sim_index, text)
    sim_js = home / 'simulator/app.js'
    text = sim_js.read_text().replace("history.replaceState(null, '', '/');", "history.replaceState(null, '', '/simulation/');")
    text = text.replace("mainPanelUrl.port = '';", '')
    text = text.replace("fetch('/", "fetch('/simulation/").replace('src="/', 'src="/simulation/')
    write(sim_js, text)
    # Copies of non-AI demo scripts only; never replace user-created files.
    examples = home / 'userfiles/CodyNick examples'
    examples.mkdir(exist_ok=True)
    for relative in ('temperature_color_display.py', 'temperature_on_ledmat.py',
                     'codyjoy_pro_led_sound_test.py', 'dashboard', 'simulator', 'blockly'):
        src = upstream / 'examples' / relative
        dst = examples / relative
        if src.is_dir():
            copy_tree(src, dst)
        elif src.exists():
            shutil.copy2(src, dst)
    write(web / 'index.html', page(name))
    write(web / 'assets/multi.css', (source / 'multi.css').read_text())
    write(web / 'guide.html', (source / 'guide.html').read_text())
    # HTTP Basic auth's per-account password file is outside the document root.
    write(home / 'passwords', name + ':' + account['hash'] + '\n', 0o640)
    return home, web_port, sim_port


def configure_account(name, account):
    home, port, sim_port = provision(name, account)
    database = 'cnmu_' + name
    password = account['db_password']
    sql = (f"CREATE DATABASE IF NOT EXISTS `{database}`;"
           f"CREATE USER IF NOT EXISTS '{database}'@'localhost' IDENTIFIED BY '{password}';"
           f"ALTER USER '{database}'@'localhost' IDENTIFIED BY '{password}';"
           f"GRANT ALL ON `{database}`.* TO '{database}'@'localhost';")
    run('mariadb', input=sql, text=True)
    run('chown', '-R', 'codymulti:www-data', home)
    run('chmod', '-R', 'u+rwX,g+rwX,o-rwx', home)
    # All Python scripts intentionally share one unprivileged OS account.
    unit = f'''[Unit]
Description=CodyNick workspace {name}
After=network.target mariadb.service
[Service]
User=codymulti
Group=www-data
SupplementaryGroups=dialout
UMask=0007
ExecStart=/usr/bin/python3 -u {APP}/current/runner.py {home}
Restart=on-failure
RestartSec=3
KillMode=control-group
TimeoutStopSec=12
[Install]
WantedBy=multi-user.target
'''
    write(Path('/etc/systemd/system') / f'codynick-multi-{name}.service', unit)
    conf = f'''Listen {port}
<VirtualHost *:{port}>
DocumentRoot "{home}/web"
DirectoryIndex index.php index.html
<Directory "{home}/web">
Options -Indexes +FollowSymLinks
AllowOverride None
AuthType Basic
AuthName "CodyNick {name}"
AuthUserFile "{home}/passwords"
Require user {name}
</Directory>
<Location />
AuthType Basic
AuthName "CodyNick {name}"
AuthUserFile "{home}/passwords"
Require user {name}
</Location>
<Directory "{home}/web/blocks/data">
Require all denied
</Directory>
ProxyPass /simulation/ http://127.0.0.1:{sim_port}/
ProxyPassReverse /simulation/ http://127.0.0.1:{sim_port}/
<Location /simulation/>
RequestHeader set Authorization "Bearer { (home / 'token').read_text().strip() }"
</Location>
ErrorLog ${{APACHE_LOG_DIR}}/codynick-multi-{name}.log
</VirtualHost>
'''
    write(Path('/etc/apache2/sites-available') / f'codynick-multi-{name}.conf', conf, 0o640)
    run('a2ensite', f'codynick-multi-{name}')
    run('systemctl', 'daemon-reload')
    run('systemctl', 'enable', f'codynick-multi-{name}')
    run('systemctl', 'restart', f'codynick-multi-{name}')
    return port


def state(stage, error=None):
    write(DATA / 'state.json', json.dumps({'version': VERSION, 'stage': stage,
          'updated_at': datetime.now(timezone.utc).isoformat(), 'error': error}, indent=2))


def install():
    state('installing')
    try:
        prepare()
        run('apt-get', '-o', 'DPkg::Lock::Timeout=600', '-o', 'Acquire::Retries=5', 'update')
        env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
        run('apt-get', '-o', 'DPkg::Lock::Timeout=600', '-o', 'Acquire::Retries=5', 'install', '-y',
            'apache2', 'libapache2-mod-php', 'php-mysql', 'php-mbstring', 'mariadb-server',
            'python3-venv', 'python3-pip', 'curl', 'openssl', env=env)
        run('id', '-u', 'www-data', stdout=subprocess.DEVNULL)
        if subprocess.run(['id', '-u', 'codymulti'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            run('useradd', '--system', '--home-dir', str(DATA), '--shell', '/usr/sbin/nologin', 'codymulti')
        run('usermod', '-aG', 'dialout,www-data', 'codymulti')
        APP.mkdir(parents=True, exist_ok=True)
        if not (APP / 'env/bin/python').exists():
            run('python3', '-m', 'venv', APP / 'env')
        run(APP / 'env/bin/pip', 'install', '--retries', '5', 'pyserial==3.5',
            'requests==2.32.5', 'keyboard==0.13.5', 'mysql-connector-python==9.4.0')
        # Atomic release selector; old source remains available for rollback.
        link = APP / 'current.new'
        link.unlink(missing_ok=True)
        link.symlink_to(SOURCE, target_is_directory=True)
        link.replace(APP / 'current')
        write('/usr/local/sbin/codynick-multi-user', '#!/bin/sh\nexec /usr/bin/python3 /opt/codynick-multi/current/install.py "$@"\n', 0o755)
        run('a2enmod', 'proxy', 'proxy_http', 'headers')
        run('systemctl', 'enable', '--now', 'mariadb', 'apache2')
        ports = {}
        for name, account in accounts().items():
            ports[name] = configure_account(name, account)
        run('apache2ctl', 'configtest')
        run('systemctl', 'restart', 'apache2')
        for name, port in ports.items():
            health(name, port)
        state('ready')
        print(f'CodyNick Multi-user {VERSION}: READY', flush=True)
        for name, port in ports.items():
            print(f'{name}: http://<device-IP>:{port}/', flush=True)
        print('Networking was not changed. AI was not installed.', flush=True)
    except Exception as error:
        state('failed', str(error))
        raise


def health(name, port):
    run('systemctl', 'is-active', '--quiet', f'codynick-multi-{name}')
    # Authentication must protect every user's root page.
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=5)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise
    else:
        raise RuntimeError(f'Authentication missing on account {name}')
    home = DATA / 'users' / name
    for _ in range(30):
        if (home / 'control.sock').exists():
            break
        time.sleep(.5)
    else:
        raise RuntimeError(f'Run/Stop socket not ready for {name}')
    for endpoint in ('sim_port', 'sprite_port'):
        port = json.loads((home / 'runtime.json').read_text())[endpoint]
        request = urllib.request.Request(f'http://127.0.0.1:{port}/state')
        if endpoint == 'sim_port':
            request.add_header('Authorization', 'Bearer ' + (home / 'token').read_text().strip())
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
            if (endpoint == 'sprite_port' and not result.get('ok')) or (endpoint == 'sim_port' and 'scene' not in result):
                raise RuntimeError('Simulator state check failed')


def verify(root):
    manifest = json.loads((root / 'release.json').read_text())
    for relative, digest in manifest['files'].items():
        path = root / relative
        if path.resolve().is_relative_to(root.resolve()) is False:
            raise RuntimeError('Invalid release path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Release checksum failed: ' + relative)
    print(f'Verified {len(manifest["files"])} files.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['verify', 'prepare', 'install', 'add-user', 'passwd', 'list', 'status'])
    parser.add_argument('value', nargs='?')
    args = parser.parse_args()
    if args.action == 'verify':
        verify(Path(args.value))
        return
    if os.geteuid() != 0:
        raise SystemExit('Use sudo for account management and installation.')
    if args.action in ('prepare', 'install'):
        globals()[args.action]()
    elif args.action == 'status':
        print((DATA / 'state.json').read_text())
    elif args.action == 'list':
        for name, account in accounts().items():
            print(f'{name}: http://<device-IP>:{8100 + account["slot"]}/')
    else:
        name = validate_name(args.value or input('Username: ').strip())
        saved = accounts()
        if args.action == 'add-user':
            saved[name] = new_account(name, saved)
        else:
            if name not in saved:
                raise ValueError('Unknown account')
            saved[name]['hash'] = password_hash()
        save_accounts(saved)
        port = configure_account(name, saved[name])
        run('apache2ctl', 'configtest')
        run('systemctl', 'reload', 'apache2')
        health(name, port)
        print(f'Account ready: http://<device-IP>:{port}/')


if __name__ == '__main__':
    main()

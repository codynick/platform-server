"""Destructive-to-test-VM only: run after install in an ephemeral Linux CI VM."""
import http.cookiejar
import json
from pathlib import Path
import time
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request

PASSWORD = 'OnlyForEphemeralCI123'
DATA = Path('/var/lib/codynick-multi/users')
CLIENTS = {}


def login(name, password=PASSWORD):
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    client.addheaders = [('Host', '127.0.0.1:8080'), ('Origin', 'http://127.0.0.1:8080')]
    data = urllib.parse.urlencode({'username': name, 'password': password}).encode()
    req = urllib.request.Request('http://127.0.0.1/login', data, {'Host': '127.0.0.1:8080'})
    with client.open(req, timeout=15) as response:
        page = response.read()
        assert name.encode() in page, page
    return client


def request(port, path, name='alice', data=None, json_body=False):
    headers = {'Host': '127.0.0.1:8080'}
    if data is not None:
        if json_body:
            data = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        else:
            data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data, headers)
    if name not in CLIENTS:
        CLIENTS[name] = login(name)
    with CLIENTS[name].open(req, timeout=15) as response:
        return response.read()


with urllib.request.urlopen('http://127.0.0.1/code/') as response:
    assert urllib.parse.urlsplit(response.url).path == '/login'
    assert b'Username' in response.read()

with urllib.request.urlopen('http://127.0.0.1/') as response:
    public = response.read()
    assert b'Start Creating' in public and b'hero-photo' in public
    assert b'/admin/users' not in public

# A tool chosen before login remains the destination after authentication.
destination_client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
with destination_client.open('http://127.0.0.1/blocks/') as response:
    assert 'next=%2Fblocks%2F' in response.url
    assert b'name="next" value="/blocks/"' in response.read()
form = urllib.parse.urlencode({'username': 'alice', 'password': PASSWORD, 'next': '/blocks/'}).encode()
with destination_client.open('http://127.0.0.1/login', form) as response:
    assert urllib.parse.urlsplit(response.url).path == '/blocks/'
with destination_client.open('http://127.0.0.1/') as response:
    private = response.read()
    assert b'practical-workspace' in private and b'account-menu' in private
    assert b'<section class="hero"' not in private
with destination_client.open('http://127.0.0.1/logout', b'') as response:
    assert urllib.parse.urlsplit(response.url).path == '/login'
with destination_client.open('http://127.0.0.1/blocks/') as response:
    assert urllib.parse.urlsplit(response.url).path == '/login'

for port, name in ((80, 'alice'), (80, 'bob')):
    for path in ('/', '/code/', '/blocks/', '/dashboard/', '/simulation/', '/simulation/app.js'):
        assert request(port, path, name), (name, path)
    assert 'scene' in json.loads(request(port, '/simulation/state', name))
    assert json.loads(request(port, '/blocks/stage.php', name))['ok']
    try:
        request(port, '/', 'wrong')
    except urllib.error.HTTPError as error:
        assert error.code == 401
    else:
        raise AssertionError('Wrong account accepted')
    # Real PHP -> Unix socket -> independent Python process.
    code = f'import time\nimport Dashboard\nDashboard.clear()\nc=Dashboard.Card("info","{name}",value="{name}")\nfor i in range(90):\n    print("{name}",i,flush=True)\n    time.sleep(1)\n'
    assert json.loads(request(port, '/code/?action=run', name, {'content': code}))['ok']
    assert json.loads(request(port, '/blocks/designs.php?action=save', name,
           {'name': 'same-name', 'overwrite': True, 'workspace': {'blocks': {'languageVersion': 0}, 'test_owner': name}}, True))['ok']
    x = 15 if name == 'alice' else -15
    request(port, '/blocks/stage.php', name, {'action': 'go', 'x': x, 'y': 0}, True)
    scene = json.loads(request(port, '/simulation/state', name))['scene']
    scene['temperature'] = 19 if name == 'alice' else 27
    request(port, '/simulation/command', name, {'action': 'scene', 'scene': scene}, True)

time.sleep(3)
for port, name in ((80, 'alice'), (80, 'bob')):
    log = (DATA / name / 'log.log').read_text()
    assert name in log and 'Traceback' not in log, log
    cards = json.loads(request(port, '/dashboard/cards.php?action=state', name))
    assert name in json.dumps(cards), cards
    other = 'bob' if name == 'alice' else 'alice'
    assert other not in json.dumps(cards), cards
    assert json.loads(request(port, '/blocks/stage.php', name))['state']['x'] == (15 if name == 'alice' else -15)
    assert json.loads(request(port, '/simulation/state', name))['scene']['temperature'] == (19 if name == 'alice' else 27)

assert json.loads(request(80, '/code/?action=stop', 'alice', {}))['ok']
before = (DATA / 'bob/log.log').read_text()
time.sleep(1.5)
assert len((DATA / 'bob/log.log').read_text()) > len(before), 'Stopping Alice interrupted Bob'
state = json.loads(request(80, '/blocks/designs.php?action=load&name=same-name', 'bob'))
assert 'bob' in json.dumps(state) and 'alice' not in json.dumps(state)
assert b'alice' in request(80, '/?user=bob', 'alice')
# The first account is the administrator; students cannot open or POST Users.
try:
    request(80, '/admin/users', 'bob')
except urllib.error.HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError('Student opened account management')
try:
    request(80, '/admin/users', 'bob', {'username': 'forbidden', 'password': PASSWORD, 'confirm': PASSWORD})
except urllib.error.HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError('Student created an account')
page = request(80, '/admin/users', 'alice').decode()
csrf = re.search(r'name="csrf" value="([a-f0-9]+)"', page).group(1)
try:
    request(80, '/admin/users', 'alice', {'username': 'badcsrf', 'password': PASSWORD, 'confirm': PASSWORD, 'csrf': 'invalid'})
except urllib.error.HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError('Missing CSRF protection')
student = 'web_' + secrets.token_hex(4)
out = request(80, '/admin/users', 'alice', {'username': student, 'password': PASSWORD, 'confirm': PASSWORD, 'csrf': csrf})
assert (student + ' added.').encode() in out, out
assert student.encode() in request(80, '/', student)
assert b'/admin/users' not in request(80, '/', student)
assert b'alice' in request(80, '/', 'alice'), 'Adding a student signed out the teacher'
# Self-service password change checks the old password and ignores forged targets.
page = request(80, '/account/password', student).decode()
own_csrf = re.search(r'name="csrf" value="([a-f0-9]+)"', page).group(1)
try:
    request(80, '/admin/password?user=alice', student)
except urllib.error.HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError('Student opened administrator reset')
try:
    request(80, '/account/password', student, {'csrf':own_csrf, 'current_password':'wrong', 'password':'ChangedPassword123', 'confirm':'ChangedPassword123'})
except urllib.error.HTTPError as error:
    assert error.code == 400
else:
    raise AssertionError('Incorrect current password accepted')
out = request(80, '/account/password?user=alice', student, {'csrf':own_csrf, 'current_password':PASSWORD, 'password':'ChangedPassword123', 'confirm':'ChangedPassword123'})
assert b'Password changed. Sign in again.' in out
try:
    login(student)
except urllib.error.HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError('Old password still accepted')
CLIENTS[student] = login(student, 'ChangedPassword123')
# Administrator reset invalidates just that user's sessions and leaves programs running.
page = request(80, '/admin/password?user=' + student, 'alice').decode()
admin_csrf = re.search(r'name="csrf" value="([a-f0-9]+)"', page).group(1)
before = (DATA / 'bob/log.log').read_text()
out = request(80, '/admin/password?user=' + student, 'alice', {'csrf':admin_csrf,'password':PASSWORD,'confirm':PASSWORD})
assert ('Password updated for ' + student).encode() in out
assert b'Username' in request(80, '/', student)
CLIENTS[student] = login(student)
time.sleep(1.2)
assert len((DATA / 'bob/log.log').read_text()) > len(before)
assert b'alice' in request(80, '/', 'alice')
assert b'Username' in request(80, '/logout', 'alice', {})
assert b'Username' in request(80, '/code/', 'alice')
assert b'bob' in request(80, '/', 'bob')
for name in ('alice', 'bob'):
    text = Path(f'/etc/apache2/sites-enabled/codynick-multi-{name}.conf').read_text()
    assert 'Listen 127.0.0.1:' in text and 'Listen 810' not in text
print('Shared login, logout, forwarded Host:8080, independent tools and private backend listeners passed.')

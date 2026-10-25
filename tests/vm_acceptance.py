"""Destructive-to-test-VM only: run after install in an ephemeral Linux CI VM."""
import base64
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

PASSWORD = 'OnlyForEphemeralCI123'
DATA = Path('/var/lib/codynick-multi/users')


def request(port, path, name='alice', data=None, json_body=False):
    headers = {'Authorization': 'Basic ' + base64.b64encode(f'{name}:{PASSWORD}'.encode()).decode()}
    if data is not None:
        if json_body:
            data = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        else:
            data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data, headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read()


for port, name in ((8100, 'alice'), (8101, 'bob')):
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

time.sleep(3)
for port, name in ((8100, 'alice'), (8101, 'bob')):
    log = (DATA / name / 'log.log').read_text()
    assert name in log and 'Traceback' not in log, log
    cards = json.loads(request(port, '/dashboard/cards.php?action=state', name))
    assert name in json.dumps(cards), cards
    other = 'bob' if name == 'alice' else 'alice'
    assert other not in json.dumps(cards), cards

assert json.loads(request(8100, '/code/?action=stop', 'alice', {}))['ok']
before = (DATA / 'bob/log.log').read_text()
time.sleep(1.5)
assert len((DATA / 'bob/log.log').read_text()) > len(before), 'Stopping Alice interrupted Bob'
state = json.loads(request(8101, '/blocks/designs.php?action=load&name=same-name', 'bob'))
assert 'bob' in json.dumps(state) and 'alice' not in json.dumps(state)
print('Real Apache authentication, IDE Run/Stop, named designs, simulator, sprites and dashboards passed.')

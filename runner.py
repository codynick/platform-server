"""One user's Run/Stop socket and private simulation backends."""
import json
import os
from pathlib import Path
import signal
import socketserver
import subprocess
import sys
import threading


class Programs:
    def __init__(self, home, python, env=None):
        self.home = Path(home)
        self.python = python
        self.env = dict(os.environ if env is None else env)
        self.process = None
        self.lock = threading.Lock()

    def stop(self):
        if self.process is not None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=3)
        self.process = None

    def control(self, action):
        if action not in ('start', 'stop'):
            raise ValueError('Only start and stop are allowed')
        with self.lock:
            self.stop()
            if action == 'start':
                with (self.home / 'log.log').open('wb') as log:
                    self.process = subprocess.Popen(
                        [self.python, '-u', str(self.home / 'active_script.py')],
                        cwd=self.home, env=self.env, stdout=log,
                        stderr=subprocess.STDOUT, start_new_session=True)
        return {'ok': True, 'state': 'running' if action == 'start' else 'stopped'}


def main():
    home = Path(sys.argv[1])
    account = json.loads((home / 'runtime.json').read_text())
    env = dict(os.environ, HOME=str(home), PYTHONPATH=str(home / 'lib'),
               CODYNICK_LOG_FILE=str(home / 'log.log'),
               CODYNICK_SIM_URL='http://127.0.0.1:' + str(account['sim_port']),
               CODYNICK_SIM_TOKEN_FILE=str(home / 'token'))
    programs = Programs(home, '/opt/codynick-multi/env/bin/python', env)
    children = [
        subprocess.Popen(['/usr/bin/python3', '-u', str(home / 'simulator/server.py'),
                          '--port', str(account['sim_port']), '--token-file', str(home / 'token'),
                          '--scene-file', str(home / 'scene.json')]),
        subprocess.Popen(['/usr/bin/python3', '-u', str(home / 'sprite/server.py')]),
    ]

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(5)
            try:
                action = self.rfile.readline(32).decode().strip()
                result = programs.control(action)
            except Exception as error:
                result = {'ok': False, 'error': str(error)}
            self.wfile.write((json.dumps(result) + '\n').encode())

    path = home / 'control.sock'
    path.unlink(missing_ok=True)
    server = socketserver.ThreadingUnixStreamServer(str(path), Handler)
    server.daemon_threads = True
    os.chmod(path, 0o660)

    def finish(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, finish)
    try:
        server.timeout = 0.5
        while True:
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A private simulator backend exited; restarting account service')
            server.handle_request()
    finally:
        programs.stop()
        server.server_close()
        path.unlink(missing_ok=True)
        for child in children:
            child.terminate()
        for child in children:
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    main()

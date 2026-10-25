"""Root-only fixed-action broker; HTTP/Python student processes stay unprivileged."""
import json
import os
import socket
import struct
import traceback
import install


def dispatch(request):
    if not isinstance(request, dict) or request.get('action') not in ('add-student', 'reset-password', 'change-password'):
        raise ValueError('Unsupported account action.')
    actor = request.get('actor', '')
    name = request.get('username', '')
    password = request.get('password', '')
    if not all(isinstance(x, str) for x in (actor, name, password)):
        raise ValueError('Invalid account fields.')
    if request['action'] == 'add-student':
        install.add_student(actor, name, password)
    else:
        current = request.get('current_password', '')
        if not isinstance(current, str):
            raise ValueError('Invalid password field.')
        install.change_password(actor, name, password, current,
                                reset=request['action'] == 'reset-password')
    return {'ok': True, 'username': name}


def main():
    import pwd
    if os.geteuid() != 0 or os.environ.get('LISTEN_PID') != str(os.getpid()) or os.environ.get('LISTEN_FDS') != '1':
        raise SystemExit('Root systemd socket activation is required.')
    allowed = pwd.getpwnam('codymulti').pw_uid
    with socket.socket(fileno=3) as listener:
        while True:
            client, _ = listener.accept()
            with client:
                try:
                    client.settimeout(5)
                    _, uid, _ = struct.unpack('3i', client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid != allowed:
                        raise PermissionError('Client not permitted.')
                    data = b''
                    while b'\n' not in data and len(data) <= 8192:
                        chunk = client.recv(8193 - len(data))
                        if not chunk:
                            break
                        data += chunk
                    if len(data) > 8192 or not data.endswith(b'\n'):
                        raise ValueError('Invalid account request.')
                    result = dispatch(json.loads(data))
                except (ValueError, PermissionError) as error:
                    result = {'ok': False, 'error': str(error)}
                except Exception:
                    traceback.print_exc()
                    result = {'ok': False, 'error': 'Account setup did not finish. Check the account service log before retrying.'}
                try:
                    client.sendall((json.dumps(result) + '\n').encode())
                except OSError:
                    pass


if __name__ == '__main__':
    main()

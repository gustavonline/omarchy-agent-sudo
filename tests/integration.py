"""Root integration in a disposable container only. No host mounts or real secrets."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import pty
import pwd
import select
import struct
import subprocess
import time
from urllib.parse import parse_qs, urlsplit

PLUGIN = Path('/opt/plugin')
OWNER = 'access-test'
BROKER = '/usr/local/sbin/z13-admin'


def root(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def owner(*args, check=True):
    account = pwd.getpwnam(OWNER)
    def drop():
        os.setgroups([])
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
    return subprocess.run(['/usr/bin/sudo', '-n', BROKER, *args], preexec_fn=drop,
                          env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir},
                          capture_output=True, text=True, check=check)


def otp(secret, counter):
    digest = hmac.digest(base64.b32decode(secret), struct.pack('>Q', counter), 'sha1')
    offset = digest[-1] & 15
    return str((struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000).zfill(6)


def prompt(args, code):
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(args[0], args, {'PATH': '/usr/bin:/bin', 'SUDO_USER': OWNER, 'HOME': '/root'})
    buffer = b''
    sent = False
    deadline = time.monotonic() + 12
    try:
        while time.monotonic() < deadline:
            readable, _, _ = select.select([fd], [], [], 0.2)
            if readable:
                try:
                    data = os.read(fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                buffer += data
                if not sent and b'code: ' in buffer:
                    # Read-only status must not wait for the live OTP prompt.
                    before = time.monotonic()
                    owner('status')
                    assert time.monotonic() - before < 2
                    os.write(fd, (code() + '\n').encode())
                    sent = True
        else:
            os.kill(pid, 9)
            raise AssertionError('OTP prompt timed out')
    finally:
        os.close(fd)
    _, status = os.waitpid(pid, 0)
    assert sent, 'OTP prompt was not reached'
    return os.waitstatus_to_exitcode(status)


assert os.geteuid() == 0 and Path('/.dockerenv').exists(), 'Container-only test'
new_broker = (PLUGIN / 'approval/z13-admin').read_bytes()
legacy = Path('/opt/legacy-broker')
assert legacy.exists(), 'Provide the unchanged reviewed 2.0.1 broker in the build fixture'
assert hashlib.sha256(legacy.read_bytes()).hexdigest() == 'f9de02eb172c5ca0c2d591bf3b0381368a4dfed0cd8a9fb8837db06f4a2740dd'
(PLUGIN / 'approval/z13-admin').write_bytes(legacy.read_bytes())
root('/bin/bash', str(PLUGIN / 'install-approval.sh'), OWNER)
(PLUGIN / 'approval/z13-admin').write_bytes(new_broker)
assert json.loads(owner('status').stdout)['version'] == '2.0.1'

# Capture the generated enrollment URI inside this disposable container only.
# The fixture never prints it and never touches a host credential.
root('/bin/mv', '/usr/bin/qrencode', '/usr/bin/qrencode.real')
Path('/usr/bin/qrencode').write_text('#!/bin/sh\numask 077\ncat > /root/enrollment-uri\n')
Path('/usr/bin/qrencode').chmod(0o755)
def enrollment_code():
    secret = parse_qs(urlsplit(Path('/root/enrollment-uri').read_text()).query)['secret'][0]
    return otp(secret, int(time.time() // 30))
assert prompt([BROKER + '-enroll', 'enroll'], enrollment_code) == 0
auth = Path('/var/lib/z13-admin/auth.json')
assert auth.stat().st_mode & 0o777 == 0o600
original_auth = auth.read_bytes()
secret = json.loads(original_auth)['secret']

# Upgrade old 2.0.1 with an existing pending request; preserve enrollment,
# consumed counter and request bytes rather than granting fresh access.
old_request = json.loads(owner('request', '--minutes', '15', '--reason', 'Upgrade fixture').stdout)
request_path = Path('/run/z13-admin/request.json')
old_request_bytes = request_path.read_bytes()
# An upgrade must preserve enrollment and replay protection byte for byte.
root('/bin/bash', str(PLUGIN / 'install-approval.sh'), OWNER)
assert auth.read_bytes() == original_auth
assert request_path.read_bytes() == old_request_bytes
assert json.loads(owner('status').stdout)['version'] == '2.1.0'
owner('revoke')
# A real user cannot bypass the broker duration parser.
for invalid in ('0', '-1', '241', '1.5', 'NaN', 'inf', '+2', ' 2', '５'):
    assert owner('request', '--minutes', invalid, '--reason', 'Invalid fixture', check=False).returncode != 0
assert json.loads(owner('status').stdout)['max_minutes'] == 240
request = json.loads(owner('request', '--hours', '4', '--reason', 'Container fixture').stdout)
assert request['minutes'] == 240
assert owner('approve', request['id'], '--hours', '5', check=False).returncode != 0
code = otp(secret, int(time.time() // 30) + 1)
assert prompt([BROKER, 'approve', request['id'], '--hours', '2'], lambda: code) == 0
first = json.loads(owner('status').stdout)['request']
assert first['minutes'] == 120 and 7195 <= first['seconds_left'] <= 7200
assert 'uid=0' in owner('run', request['id'], '--', '/usr/bin/id').stdout
owner('run', request['id'], '--', '/usr/bin/true')
second = json.loads(owner('status').stdout)['request']
assert second['runs'] == 2 and second['expires'] == first['expires']
owner('shorten', request['id'], '--minutes', '1')
assert owner('shorten', request['id'], '--minutes', '2', check=False).returncode != 0
owner('revoke')
assert owner('run', request['id'], '--', '/usr/bin/id', check=False).returncode != 0
request = json.loads(owner('request', '--minutes', '1', '--reason', 'Replay fixture').stdout)
assert prompt([BROKER, 'approve', request['id']], lambda: code) != 0
owner('revoke')

# Fail the final policy check, then verify transactional rollback of every file.
paths = [Path('/etc/omarchy-sudo-approval-owner'), Path(BROKER), Path(BROKER + '-enroll'), Path('/etc/sudoers.d/90-z13-admin')]
before = {str(path): hashlib.sha256(path.read_bytes()).digest() for path in paths}
root('/bin/mv', '/usr/sbin/visudo', '/usr/sbin/visudo.real')
Path('/usr/sbin/visudo').write_text('#!/bin/sh\nn=$(cat /tmp/visudo-count 2>/dev/null || echo 0)\nn=$((n+1))\necho "$n" >/tmp/visudo-count\n[ "$n" = 3 ] && exit 1\nexec /usr/sbin/visudo.real "$@"\n')
Path('/usr/sbin/visudo').chmod(0o755)
assert root('/bin/bash', str(PLUGIN / 'install-approval.sh'), OWNER, check=False).returncode != 0
assert all(hashlib.sha256(Path(path).read_bytes()).digest() == digest for path, digest in before.items())
assert json.loads(owner('status').stdout)['enrolled'] is True
# Reviewed rollback restores the old ceiling; it must first close any grant.
owner('revoke')
root('/bin/cp', str(legacy), BROKER)
root('/bin/cp', str(legacy), BROKER + '-enroll')
root('/bin/chmod', '0755', BROKER)
assert json.loads(owner('status').stdout)['version'] == '2.0.1'
assert owner('request', '--minutes', '240', '--reason', 'Old ceiling fixture', check=False).returncode != 0
assert auth.read_bytes() != original_auth  # replay counter was advanced, not reset
assert json.loads(owner('status').stdout)['enrolled'] is True
print('Fresh install, enrollment, upgrade preservation, multiple commands, shortening, revoke, replay denial, non-blocking status and rollback passed.')

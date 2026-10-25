# CodyNick Multi-user 0.1.0

Separate classroom edition based on CodyNick 0.11.0 (upstream commit 50539ea).
Ubuntu Server x86-64 VM and ARM64; Python IDE, Blockly, sprites, gadget simulation,
dashboard. No AI packages/models. No changes to the original Sohaware/rpi repository.

## Install or upgrade: one fixed command

```bash
wget -4 -O /tmp/codynick-multi-setup.sh "https://raw.githubusercontent.com/codynick/rpi-multi-user/main/setup.sh?$(date +%s)" && sudo bash /tmp/codynick-multi-setup.sh
```

First installation asks for a web username and password. These are independent
of Linux/SSH accounts. Installation then runs in the background across SSH
disconnects. Wait for `CodyNick Multi-user 0.1.0: READY`.

```bash
sudo tail -n 80 -f /var/log/codynick-multi/install.log
sudo codynick-multi-user status
sudo codynick-multi-user list
```

Open `http://VM-IP:8100/` for the first account and enter that account's credentials
in the browser prompt. VM networking must allow client access: bridged/host-only
networking, or an explicit NAT forwarding rule. Allow the relevant TCP ports if
a firewall is enabled; the installer does not alter firewall rules.

## Accounts

```bash
sudo codynick-multi-user add-user student1
sudo codynick-multi-user add-user student2
sudo codynick-multi-user passwd student1
sudo codynick-multi-user list
```

Each account receives its own numbered port: 8100, 8101, ... 8199. One account
per browser profile is recommended. Authentication is HTTP Basic, not a shared
session login page. No registration, roles, account deletion or recovery UI yet.
The teacher provisions accounts over SSH. Do not publish this HTTP service to the Internet.

## Minimum-change architecture

The tested single-user interfaces are reused rather than rewritten. Each account
gets its own document root, Run/Stop socket, Python process, dashboard database,
simulator and sprite state. The private services listen on loopback; Apache
proxies the simulator behind the same authenticated web address. Libraries and
interfaces come from one vendored source tree and are materialized per account.
This uses more disk/processes than a fully namespaced backend but changes much
less upstream code. There is no AI memory overhead.

- Personal files: `/var/lib/codynick-multi/users/NAME/userfiles/`
- Named designs: `.../web/blocks/data/designs/`
- Active script and log: `.../active_script.py`, `.../log.log`
- Account configuration: `/etc/codynick-multi/accounts.json` (root-only)
- Managed release: `/opt/codynick-multi/current`
- Account service: `codynick-multi-NAME.service`
- Private backend ports: 9200-9399 on loopback only

The updater preserves user files, active scripts, designs and simulation layouts.
The `CodyNick examples` folder is managed and replaced; students must work outside it.
Running scripts are stopped during an update. They do not auto-resume on reboot;
the user presses Run. The original single-user scripts/services are not stopped or
reconfigured; for the first test use a clean VM to avoid port/hardware conflicts.

## Networking and physical hardware

Networking is deliberately unchanged on both architectures in this first edition.
Use an existing LAN connection/hotspot. There is no new hotspot provisioning,
Raspberry Pi firmware operation or device cloning logic in this installer.
Physical CJP use in a VM requires USB passthrough. The only serial-driver change
is pyserial `exclusive=True` on Linux; serial detection/timing is unchanged.
Keyboard emulation requiring root is not supported by the unprivileged runner;
browser sprite keys and simulator joysticks work without root.

## Test with two users

1. Create student1 and student2. Open their addresses in separate browser profiles/devices.
2. Run different printing loops. Stop one; the other must continue.
3. Save files/designs with the same names; load them and verify different contents.
4. Run simulator examples and different sprite programs. Scenes must remain independent.
5. Create a dashboard counter in each account; clearing one must not clear the other.
6. Re-run the same installation command; verify saved files and named designs survive.

This is an initial release requiring VM acceptance testing. No hostile-code sandbox:
student programs intentionally share an unprivileged OS account. CPU/RAM quotas,
HTTPS, per-user Linux identities and multi-tenant AI are outside this version.

## Development and publication

`python -m unittest discover -s tests` checks generation, preserved data and process
separation. Linux CI also lints PHP and tests real independent process groups.
`python tools/seal.py` regenerates the release file hashes. Publish immutable tag
`v0.1.0-multi-user` with main. Never move a published tag; make a new release.
Keep the fixed command unchanged on later versions. Older source directories are
retained; automated downgrade selection is not implemented in this initial edition.

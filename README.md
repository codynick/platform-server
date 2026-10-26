# CodyNick Multi-user 0.1.5

Separate classroom edition based on CodyNick 0.11.0 (upstream commit 50539ea).
Ubuntu Server x86-64 VM and ARM64; Python IDE, Blockly, sprites, gadget simulation,
dashboard. No AI packages/models. No changes to the original Sohaware/rpi repository.

## Install or upgrade: one fixed command

```bash
wget -4 -O /tmp/codynick-multi-setup.sh "https://raw.githubusercontent.com/codynick/rpi-multi-user/main/setup.sh?$(date +%s)" && sudo bash /tmp/codynick-multi-setup.sh
```

First installation asks for a web username and password. These are independent
of Linux/SSH accounts. Installation then runs in the background across SSH
disconnects. Wait for `CodyNick Multi-user 0.1.5: READY`.

```bash
sudo tail -n 80 -F /var/log/codynick-multi/install.log
sudo codynick-multi-user status
sudo codynick-multi-user list
```

All users open `http://VM-IP/` and enter their own username and password in the
shared login page. For VirtualBox NAT on Windows, forward TCP **2222 to guest 22**
for SSH and **8080 to guest 80** for all web users. Open `http://127.0.0.1:8080/`.
No additional user-port forwarding rules are needed. The installer does not alter
firewall rules. Use a dedicated VM; its default Apache site becomes this portal.

## Accounts

Sign in with the first account (normally `teacher`), choose **Users** on the main
panel, and enter a username, password and password confirmation under **Add Student**.
The account appears in the list and can sign in at the same address immediately
after successful creation. The existing teacher session stays signed in.

On upgrade from 0.1.0/0.1.1, the first-created account becomes Administrator;
existing other accounts become Students. All passwords and files are retained.
Only administrators can open Users or create students through the web interface.
To reset a password, choose **Reset** in that user's row of the Users table.
Any user can choose **Change Password** on the main panel to update their own
password after entering the current password. Changed accounts must sign in again;
password changes do not restart their Python script. Use HTTPS, an SSH tunnel or
a trusted private connection for passwords. There is no web account deletion or role editing yet.
The original SSH commands still work:

```bash
sudo codynick-multi-user add-user student1
sudo codynick-multi-user add-user student2
sudo codynick-multi-user passwd student1
sudo codynick-multi-user list
```

Everyone uses the same address. A session cookie selects the signed-in account;
use separate browser profiles/devices to test multiple users simultaneously.
Sign Out is on the main panel. Sessions expire after 12 hours idle and are cleared
when the login service restarts; running scripts continue until Stop or an upgrade.
Adding an account does not sign out others. Password changes invalidate that account's
sessions. There is no self-registration. Do not publish this HTTP service to the Internet.

## Minimum-change architecture

The tested single-user interfaces are reused rather than rewritten. Each account
gets its own document root, Run/Stop socket, Python process, dashboard database,
simulator and sprite state. A small Python session router sits behind Apache's
single public port 80 and routes to private loopback-only account sites. Apache
proxies each simulator behind that account's same-origin paths. Libraries and
interfaces come from one vendored source tree and are materialized per account.
This uses more disk/processes than a fully namespaced backend but changes much
less upstream code. There is no AI memory overhead.

- Personal files: `/var/lib/codynick-multi/users/NAME/userfiles/`
- Named designs: `.../web/blocks/data/designs/`
- Active script and log: `.../active_script.py`, `.../log.log`
- Account configuration: `/etc/codynick-multi/accounts.json` (root-only)
- Managed release: `/opt/codynick-multi/current`
- Account service: `codynick-multi-NAME.service`
- Shared login service: `codynick-multi-gateway.service` (loopback 9000)
- Fixed-action root account broker: `codynick-multi-admin.socket` / `.service`
- Private account sites: loopback 8100-8199, not public user addresses
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

1. Create student1 and student2. Open the same address in separate browser profiles/devices; sign in separately.
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
`v0.1.5-block-simulator` with main. Never move a published tag; make a new release.
Keep the fixed command unchanged on later versions. Older source directories are
retained; automated downgrade selection is not implemented in this initial edition.

## Changes in 0.1.1

Shared form-based sign-in/sign-out and one public address replace per-user public
ports and browser Basic authentication. Existing 0.1.0 account passwords, files,
designs and dashboard databases are retained. Old private services remain the same;
only web listeners, login/routing, installer metadata, tests and guides changed.

## Changes in 0.1.2

Administrator-only Users page with Add Student and an account list; no general
root shell/sudo access is given to the web service. A fixed-action Unix socket
broker validates administrator role, username and password and provisions students
using the existing account setup. CSRF tokens protect account-creation forms.
This is browser-role separation, not a hostile-Python sandbox: the earlier shared
Linux-identity limitation remains. The main panel now uses the original RPi panel's
CodyNick logo, blue/white styling and tool-card layout, with correct account, role
and release information. New-listener health checks wait for Apache reload readiness
instead of reporting a transient Connection Refused traceback.

## Changes in 0.1.3

Web administrator password resets and current-password-verified self-service changes,
with confirmation, CSRF protection and affected-session invalidation. Authentication
refresh no longer restarts a user's program, including terminal password changes.
The installer creates its log file before launching the background worker and uses
retrying log follow, avoiding the first-install "No such file" display race.

## Changes in 0.1.4

Python IDE compact layout only at viewport widths of 760px and below. Files move
into a toggled drawer that closes after file selection; Run and Stop stay in the
visible toolbar. The compact Run label reads "Run"; desktop retains "Run this File".
Editor/terminal sizing adapts to portrait, landscape and browser viewport changes.
Desktop geometry above the breakpoint, script controls, account isolation and
other tools are unchanged. Browser tests compare desktop bounds with the old layout
and exercise real Run/Stop plus Files at phone and landscape sizes.

## Changes in 0.1.5: Blockly to gadget simulator

In Block Coding, select **Simulator** under **Run on**, next to the design name.
Choose **Open Simulator**, add the required gadgets to the simulation space, then
press **Run** in Blockly. Sprite blocks can run alongside the simulated gadgets.
The existing per-account process and simulator keep users independent; no USB
serial connection is opened in Simulator mode and there is no hardware fallback.

Mode is saved with autosave, named designs and downloaded `.codynick` files.
Older designs without a mode remain on **Hardware** for compatibility. Changing
the selector updates the next generated program, not a currently running script.

Before a simulated program starts, required gadgets are checked. If a gadget is
missing, the terminal and simulator report: **Add [gadget] to the simulation space,
then re-run the app.** No session is locked by that preflight error, so users can
add the gadget and rerun without an extra Stop. Stop now sends a graceful interrupt
before the existing forced-stop fallback, releasing simulation sessions for quick reruns.

Supported: CJP LEDs/joystick/buzzer, standalone joystick, LED matrix, standalone
seven-segment and ultrasonic devices, temperature, soil moisture, and Wi-Fi/IoT.
Motion/RFID/keypad, legacy sensor aliases, library updates and unsupported device
IDs are rejected clearly in Simulator mode rather than accessing physical hardware.

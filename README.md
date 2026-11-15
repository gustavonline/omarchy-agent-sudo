# Omarchy Agent Access

Phone-approved sudo for local and remote agents. One code opens a short access window; the agent can run multiple commands until it closes.

## Install

From a clean reviewed checkout, including a headless SSH session:

~~~sh
./install-user.sh
~~~

This installs the user plugin, command and bundled skill in three owner skill roots,
without enabling a widget, modifying package files or changing broker/enrollment.
Enable the optional widget later with omarchy plugin enable io.github.gustavonline.passwordless-sudo.

Native omarchy plugin add remains supported. After it, run the installed
./agent-access install-skill once if no widget loads. The native plugin API has
no install/update lifecycle hook; a manifest cannot supply one. Existing skill
links follow in-place updates. A user post-update hook refreshes the normal Omarchy
entry after package updates; it delegates to current packaged topic guides.

Click the lock in the centre of the bar to set up your phone. Enter your normal administrator password for the first installation, scan the QR in an authenticator app, then confirm a code in the terminal. Existing phone enrollment is preserved when upgrading.

Installing through an agent? Ask it to read [SKILL.md](SKILL.md) in the plugin folder. The widget registers that skill beside Omarchy's own skills for Codex, Claude and other compatible agents. A remote agent can register it without opening the panel:

```sh
~/.config/omarchy/plugins/io.github.gustavonline.passwordless-sudo/agent-access install-skill
```

Requires Omarchy with Quickshell, Python 3, sudo, jq, qrencode, Foot and flock. Setup reports missing dependencies; it does not install packages or restart the computer.

## Quick access

- **Left-click:** open the phone-code terminal with the default duration. If access is already open, show its status.
- **Right-click:** open the panel to choose a duration, shorten a window or close it.
- **Default:** five minutes. Change it in Omarchy's widget settings; the reviewed broker limit is four hours (240 minutes). Minutes and hours are selectable in the panel. The panel reads the installed broker limit: an older 2.0.1 broker still permits only 15 minutes until explicitly upgraded.

The widget starts in the centre section and can be moved like other Omarchy widgets. It uses the stock panel components, foreground colours, typography and progress style. The bar counts down while access is open.

After enrollment you do not need to be near the computer. Your agent requests access when you are ready. You may choose an existing trusted
chat to send a code, but it remains subject to that chat's retention. The agent
can use either the owner's own SSH/terminal (or a genuinely private-input
facility), or the owner's explicitly selected trusted-chat-to-agent-PTY flow.
For the latter, the agent submits the fresh, single-use code through its available
stdin tool to the broker's hidden prompt. The code can remain in both chat and
tool-input transcripts: hidden terminal echo does not make that a secret channel.
The owner can choose this exposure; a missing private-input API does not forbid it.
Do not repeat an already clear session choice. Never echo or report the code,
put it in CLI arguments/environment/files, add diagnostic logs, replay it or
promise transcript deletion. No browser approval server is introduced.

## Agent commands

```sh
omarchy-agent-access request 5 "Install the reviewed change"
omarchy-agent-access approve-terminal REQUEST_ID
omarchy-agent-access run REQUEST_ID -- /usr/bin/id
omarchy-agent-access run REQUEST_ID -- /usr/bin/true
omarchy-agent-access status
omarchy-agent-access shorten 1
omarchy-agent-access close
```

Approval needs a PTY. Enter the code at the hidden prompt, never in command arguments or environment variables. One code opens the window, not just one command. The human may reduce the requested duration at approval with `approve-terminal REQUEST_ID --minutes N` or `--hours N`. A longer window requires a new request and code.

The protected broker retains its older `z13-admin` name for compatibility with existing enrollment. It is not tied to Z13 hardware. This version supports one enrolled owner account; remote agents use that account's existing authorized connection.

## Updates

```sh
omarchy-agent-access update
omarchy-agent-access doctor
```

The plugin, skill links and root broker live outside Omarchy's packaged files. They survive normal package updates. Plugin updates refresh the skill through its links. A changed root component shows **Update access service** and needs an explicit authorized upgrade; it is never replaced silently.

Tested with Omarchy 4.0.6. CI runs the tests, a clean installation in a disposable container and manifest validation against current Omarchy source. A future shell API change may still require a plugin update. `doctor` reports missing dependencies, invalid manifests, stale root code and missing skill registration.

## Access boundaries

Only the broker is passwordless. Ordinary sudo/PAM and existing permissions are preserved. Expiry and early close prevent new commands through the broker; they do not stop running root processes, undo changes or sandbox approved root code. Do not leave a separate broad passwordless-sudo grant open if phone approval is to gate access.

QR secrets and replay protection stay in root-only state outside the checkout. The panel, status output and logs do not expose codes or enrollment secrets. Normal owner sudo remains the recovery route.

The original Omarchy passwordless flow is available through the optional **Show legacy Omarchy sudo** setting. Its timer is separate from phone-approved access.

## Remove

First run omarchy-agent-access remove-registration. It removes only our links/hook,
restores known stock routing, preserves custom skills and retains generated files
for recovery. It does not uninstall root enrollment.

Close any open window first. Removing the bar widget leaves the protected broker and enrollment intact. To disable root access through this plugin, use normal owner sudo to remove `/etc/sudoers.d/90-z13-admin`, then run `visudo -c`. Remove the broker and its private state only when you intend to retire enrollment too. Skill and command links point at the plugin folder; remove those links when removing the plugin permanently.

## Development

```sh
./test.sh
omarchy plugin validate .
./tests/ui-smoke.sh
docker build -f tests/Dockerfile -t agent-access-test .
docker run --rm --network=none --pids-limit=128 --memory=384m agent-access-test
```

The container tests use a synthetic owner and generated test credentials. No host directories or real enrollment data are mounted.

MIT. See [LICENSE](LICENSE).


### Custom access windows

Use explicit whole units: omarchy-agent-access request 90m "Maintenance" or request 2h "Maintenance". Bare numbers are minutes; quick without a duration uses five minutes. The protected broker also accepts mutually exclusive --minutes N / --hours N on request, approval and shorten. Fractions, signs, whitespace, non-finite numbers, zero and durations above four hours are rejected; there is no rounding or automatic renewal. The approval terminal displays normalized minutes before asking for the code. Status and the widget show the granted duration and remaining time; multiple commands never restart that clock. Shortening never moves the existing expiry later. Close or expiry requires a new request and fresh code before more commands.

Version 0.6.0 includes broker 2.1.0. Updating only user files does not update the root service or its ceiling. Review the exact commit and broker hash, retain a protected recovery copy of the old binaries/policy, then use the normal owner-authorized installer. It preserves phone enrollment and ordinary sudo policy. Do not treat an existing access window as authorization to upgrade the broker. A rollback of a newly granted long window must revoke that window first; restoring an older binary alone cannot shorten an already persisted expiry.

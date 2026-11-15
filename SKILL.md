---
name: omarchy-agent-access
description: Find and use installed Omarchy Agent Access for authorized temporary sudo, phone/TOTP approval and remote administration; repair user skill registration without changing root enrollment.
---

# Omarchy Agent Access

Plugin: ~/.config/omarchy/plugins/io.github.gustavonline.passwordless-sudo.
Command: omarchy-agent-access; if PATH is stale, use the plugin's ./agent-access.
For an SSH task, read this file on the target host. Host skill links do not appear
automatically in the calling computer's catalogue.

## Discover and maintain

The normal Omarchy entry in ~/.agents/skills/omarchy/SKILL.md (or the selected host
skill root) routes privilege work here and ordinary tasks to the current packaged
Omarchy skill/topic guides without editing /usr/share/omarchy. Run doctor for
actual links, command, discovery entry and broker readiness. Missing discovery is
not unenrolled phone state. Preserve conflicts with owner-authored skills.

From a clean reviewed checkout, ./install-user.sh installs user files and the
three skill roots headlessly, without widget loading or root changes.
After native plugin-add, explicitly run the installed ./agent-access install-skill
once if no widget has loaded. The current Omarchy API has no install/update hook.
Existing links follow native updates; omarchy-agent-access update also repairs
registration and reports native failures. The post-update user hook refreshes the
entry after Omarchy updates. Refresh a caller whose skill catalogue was cached.
remove-registration removes our links/hook, restores known stock routing and
preserves unrelated skills; it does not uninstall the plugin or root enrollment.

## Request, approve, run, close

1. Recover accepted command scope, then status. No skill grants permission for
   work or authorizes a new account, model or broad passwordless-sudo rule.
2. Check owner readiness before request MINUTES "purpose" (1–15 minutes).
   Read the actual ID/status. Slow answers are not approval or automatic retries.
3. In a PTY run approve-terminal REQUEST_ID. It rejects mismatched, expired or
   non-pending IDs. Over SSH use ssh -tt HOST 'omarchy-agent-access approve-terminal REQUEST_ID'.
   The broker reads the code at its hidden prompt; never put OTP in argv, env,
   a saved file, shell history or logging/debug output. Never reuse a code.
4. Verify actual status before run ID -- /absolute/command args, within the
   accepted scope. Multiple commands share a fixed window. Expiry prevents new
   starts, not existing root processes or their changes.
5. Close unused access and verify status. Report refusal/expiry; do not bypass
   it. Request anew only when the owner is ready; extension needs fresh approval.

### Chat and mobile input

The owner may explicitly choose an existing trusted chat to send a fresh code.
That exposes the code to the chat's retention; never promise transcript deletion.
Do not echo it, quote it in a report, store it, or include it in commands.
Transfer directly to the hidden PTY only through an actually available private
input mechanism. Hidden terminal echo does not protect an agent tool's logged
input: a write-stdin tool with recorded arguments is not a secret-input API.

If no private-input mechanism exists, explain that before requesting a code.
The supported fallback is the owner's own SSH/terminal, entering the code directly
at approve-terminal's hidden prompt; the agent resumes after approved status.
There is no browser approval URL/server. This plugin cannot make another app's
logged tool inputs private or clear its chat history.

## Enrollment and root upgrades

Existing enrollment survives user registration/updates. First enrollment or a real
root-component upgrade uses ./agent-access setup in the owner's terminal: the owner
enters their password and scans the QR there. Never reset enrollment for discovery.
Read README.md before root changes; stale root code is reported, not replaced silently.

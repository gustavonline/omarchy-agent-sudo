"""User-owned registration. No package files, root broker or enrollment writes."""
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
MARKER = '<!-- Managed by Omarchy Agent Access -->'
HOOK_MARKER = '# Managed by Omarchy Agent Access'


def skill_links(home):
    return [Path(home) / b / 'omarchy-agent-access' for b in
            ('.agents/skills', '.claude/skills', '.codex/skills')]


def layout(home=None):
    home = Path.home() if home is None else Path(home)
    stock = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'default/agents/skills/omarchy'
    managed = home / '.local/share/omarchy-agent-access/omarchy'
    links = {x: HERE for x in skill_links(home)}
    links[home / '.local/bin/omarchy-agent-access'] = HERE / 'agent-access'
    if (stock / 'SKILL.md').is_file():
        for b in ('.agents/skills', '.claude/skills', '.codex/skills'):
            links[home / b / 'omarchy'] = managed
    hook = home / '.config/omarchy/hooks/post-update.d/99-agent-access'
    return stock, managed, links, hook


def atomic_text(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.agent-access-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def entry_text(stock):
    parts = (stock / 'SKILL.md').read_text().split('---', 2)
    return ('---' + parts[1] + '---\n\n' + MARKER + '\n\n# Omarchy\n\n'
                'For authorized privileged work or temporary sudo, first read the installed '
                f'[Agent Access skill]({HERE / "SKILL.md"}) and run '
                'omarchy-agent-access status. Do not bypass that selected approval route '
                'with generic sudo/pkexec advice. No skill grants authority for the work.\n\n'
                f'Read the current [packaged Omarchy skill]({stock / "SKILL.md"}) '
                'for the requested Omarchy task and its topic guides at their original paths. '
                'The packaged files are unchanged; their current content is not copied here. '
                'Remote callers read these host paths over their existing SSH connection; '
                'the host catalogue is not automatically the caller machine catalogue.\n')


def install(home=None):
    stock, managed, links, hook = layout(home)
    # Reject all registration conflicts before changing anything.
    for link, target in links.items():
        if not (link.exists() or link.is_symlink()):
            continue
        allowed = {target.resolve()}
        if link.name == 'omarchy':
            allowed.add(stock.resolve())
        if not link.is_symlink() or link.resolve() not in allowed:
            raise ValueError(f'Unrelated registration at {link}; preserve it')
    entry = managed / 'SKILL.md'
    if managed.is_symlink() or entry.is_symlink() or (entry.exists() and MARKER not in entry.read_text()):
        raise ValueError(f'Unmanaged Omarchy entry at {entry}; preserve it')
    if hook.is_symlink() or (hook.exists() and HOOK_MARKER not in hook.read_text()):
        raise ValueError(f'Unrelated post-update hook at {hook}; preserve it')
    for link in links:
        temp = link.with_name(link.name + '.agent-access-new')
        if temp.exists() or temp.is_symlink():
            raise ValueError(f'Registration staging path occupied: {temp}')
    if (stock / 'SKILL.md').is_file():
        parts = (stock / 'SKILL.md').read_text().split('---', 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError('Packaged Omarchy skill has no supported frontmatter')
        text = entry_text(stock)
        atomic_text(entry, text)
    for link, target in links.items():
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() and link.resolve() == target.resolve():
            continue
        temp = link.with_name(link.name + '.agent-access-new')
        temp.symlink_to(target, target_is_directory=target.is_dir())
        try:
            os.replace(temp, link)
        finally:
            if temp.is_symlink():
                temp.unlink()
    import shlex
    atomic_text(hook, '#!/bin/sh\n' + HOOK_MARKER + '\nexec ' +
                shlex.quote(str(HERE / 'agent-access')) + ' install-skill\n', 0o700)


def problems(home=None):
    stock, managed, links, hook = layout(home)
    errors = []
    for link, target in links.items():
        if not link.is_symlink() or link.resolve() != target.resolve():
            errors.append({'path': str(link), 'repair': 'Run install-skill; resolve unrelated conflicts without replacing them'})
    if not (stock / 'SKILL.md').is_file():
        errors.append({'path': str(stock / 'SKILL.md'), 'repair': 'Select installed Omarchy with OMARCHY_PATH'})
    elif not (managed / 'SKILL.md').is_file() or (managed / 'SKILL.md').read_text() != entry_text(stock):
        errors.append({'path': str(managed / 'SKILL.md'), 'repair': 'Run install-skill to restore the Omarchy entry'})
    if not hook.is_file() or hook.is_symlink() or HOOK_MARKER not in hook.read_text():
        errors.append({'path': str(hook), 'repair': 'Run install-skill to restore the package-update registration hook'})
    return errors


def remove(home=None):
    stock, managed, links, hook = layout(home)
    for link, target in links.items():
        if not link.is_symlink() or link.resolve() != target.resolve():
            continue
        if link.name == 'omarchy' and (stock / 'SKILL.md').is_file():
            temp = link.with_name(link.name + '.agent-access-new')
            if temp.exists() or temp.is_symlink():
                raise ValueError(f'Registration staging path occupied: {temp}')
            temp.symlink_to(stock, target_is_directory=True)
            os.replace(temp, link)
        else:
            link.unlink()
    if hook.is_file() and not hook.is_symlink() and HOOK_MARKER in hook.read_text():
        hook.unlink()
    # Retain generated entry for recovery; never remove owner directories/root state.

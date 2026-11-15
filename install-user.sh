#!/bin/bash
# Install a reviewed checkout headlessly; no broker or enrollment writes.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$(readlink -f -- "$0")")" && pwd)
target="$HOME/.config/omarchy/plugins/io.github.gustavonline.passwordless-sudo"
omarchy plugin validate "$source_dir"
if [[ $source_dir == "$target" ]]; then
  exec "$target/agent-access" install-skill
fi
[[ ! -e $target && ! -L $target ]] || {
  echo 'Already installed: use omarchy-agent-access update or its install-skill to repair registration.' >&2
  exit 1
}
[[ -z $(git -C "$source_dir" status --porcelain) ]] || {
  echo 'Select a clean reviewed commit before installation.' >&2
  exit 1
}
mkdir -p -- "$(dirname -- "$target")"
mkdir -- "$target"
git clone --no-hardlinks -- "$source_dir" "$target"
git -C "$target" remote set-url origin https://github.com/gustavonline/omarchy-agent-sudo.git
omarchy plugin validate "$target"
"$target/agent-access" install-skill
echo 'User plugin and skills installed; broker/enrollment unchanged.'
echo 'Start a fresh agent context. Enable the optional bar widget when a desktop is available.'

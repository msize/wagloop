#!/usr/bin/env bash
# Install wagloop skills for Claude Code, Codex and Devin, plus WagFlow's implementer roles.
# Safe to re-run: roles are overwritten from their source checkouts; other settings are untouched.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
flow="${WAGFLOW:-$(cd "$here/.." && pwd)/wagflow}"
wagloop="$(cygpath -m "$here/bin/wagloop.py")"
bin="$here/bin"   # Git Bash form: the skills show it as the launchers to run
codex_review="${CODEX_REVIEW_SKILL:?set CODEX_REVIEW_SKILL to how Codex invokes its review skill, e.g. \$plugin:review}"
claude_review="${CLAUDE_REVIEW_SKILL:?set CLAUDE_REVIEW_SKILL to how Claude Code invokes its review skill, e.g. /plugin:review}"
devin_review="${DEVIN_REVIEW_SKILL:?set DEVIN_REVIEW_SKILL to how Devin invokes its review skill, e.g. review}"

[ -f "$flow/lib/wagmsg.py" ] || {
  echo "install: wagflow not found at $flow (git clone https://github.com/msize/wagflow there, or set WAGFLOW)" >&2
  exit 2
}

for source in "$flow/claude/commands/wagflow-implementer.md" \
              "$flow/codex/skills/wagflow-implementer/SKILL.md"; do
  [ -f "$source" ] || {
    echo "install: missing WagFlow implementer role at $source (update the WagFlow checkout)" >&2
    exit 2
  }
done

install_skill() {
  local src="$1" dst="$2" review="$3"
  mkdir -p "$dst"
  sed -e "s|@WAGLOOP@|$wagloop|g" -e "s|@BIN@|$bin|g" -e "s|@REVIEW_SKILL@|$review|g" "$src/SKILL.md" > "$dst/SKILL.md"
  echo "installed $dst/SKILL.md"
}

for role in author reviewer; do
  install_skill "$here/skills/claude/wagloop-$role" "$HOME/.claude/skills/wagloop-$role" "$claude_review"
  install_skill "$here/skills/codex/wagloop-$role" "$HOME/.codex/skills/wagloop-$role" "$codex_review"
  install_skill "$here/skills/devin/wagloop-$role" "$HOME/.config/devin/skills/wagloop-$role" "$devin_review"
done

mkdir -p "$HOME/.claude/commands" "$HOME/.codex/skills/wagflow-implementer"
cp "$flow/claude/commands/wagflow-implementer.md" "$HOME/.claude/commands/"
cp "$flow/codex/skills/wagflow-implementer/SKILL.md" "$HOME/.codex/skills/wagflow-implementer/"
echo "installed WagFlow implementer roles for Claude Code and Codex"

chmod +x "$here/bin/wagloop-claude" "$here/bin/wagloop-codex" "$here/bin/wagloop-devin" "$here/bin/wagloop.py"

case ":$PATH:" in
  *":$here/bin:"*) ;;
  *) echo "add to PATH to get wagloop-claude, wagloop-codex and wagloop-devin: export PATH=\"$here/bin:\$PATH\"" ;;
esac

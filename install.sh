#!/usr/bin/env bash
# Install the wagloop author and reviewer skills for both Claude Code and Codex, and put bin/ on
# the user PATH hint. Safe to re-run: the skills are overwritten from this checkout, nothing else
# is touched.
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
chmod +x "$here/bin/wagloop-claude" "$here/bin/wagloop-codex" "$here/bin/wagloop-devin" "$here/bin/wagloop.py"

case ":$PATH:" in
  *":$here/bin:"*) ;;
  *) echo "add to PATH to get wagloop-claude, wagloop-codex and wagloop-devin: export PATH=\"$here/bin:\$PATH\"" ;;
esac

# Project verification

- Run commands from Git Bash. Python 3.10+ and Git for Windows are required.
- Tests: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v`.
- Shell syntax: `for script in install.sh bin/wagloop-*; do bash -n "$script" || exit; done`.
- Whitespace: `git --no-optional-locks diff --check`.
- Shell tests use temporary homes and mock CLIs. Do not run the installer against the real user
  home for verification.
- Transport comes from sibling `wagflow/lib`, or `WAGFLOW`. Keep dependency changes
  outside this repository out of scope unless explicitly requested.
- Devin skills install under `~/.config/devin/skills`. The launcher references the exact file
  because Windows global discovery paths differ and Claude compatibility skills share names.
- Codex is sandboxed and needs a Claude or Devin peer. Devin uses explicit long-poll tool waits,
  not background shell completion notifications.

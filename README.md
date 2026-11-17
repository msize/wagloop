# wagloop

An Author writes an OpenSpec change, a Reviewer reviews every step, in one wagterm split. Either
role can be Claude Code, Codex or Devin CLI. Phase 1 is the proposal with spec deltas, phase 2 the tasks,
phase 3 the implementation task by task. Each step goes back and forth until the Reviewer
approves, at most three rounds. The human passes the gates and commits at the end.

Each harness gets the same pair of thin skills, `wagloop-author` and `wagloop-reviewer`. The
transport is wagflow's vendored, fail-closed tooling: `wagmsg` (a file mailbox), `peerchat`
(the doorbell that types one pointer line into a provably empty composer) and `wb.py wait-mail`
(Claude's background waiter and Devin's explicit long-poll waiter).

| piece | what |
|---|---|
| `skills/claude/wagloop-author` | Claude as Author: phases, rounds, gates, staging checkpoints |
| `skills/claude/wagloop-reviewer` | Claude as Reviewer: reviews with `CLAUDE_REVIEW_SKILL`, answers by mail |
| `skills/codex/wagloop-author` | Codex as Author, inside its sandbox |
| `skills/codex/wagloop-reviewer` | Codex as Reviewer: reviews with `CODEX_REVIEW_SKILL`, answers by mail |
| `skills/devin/wagloop-author` | Devin as Author: phases, rounds, gates, staging checkpoints |
| `skills/devin/wagloop-reviewer` | Devin as Reviewer: reviews with `DEVIN_REVIEW_SKILL`, answers by mail |
| `bin/wagloop.py` | one wrapper for all: mailbox at `<checkout>/.wagloop/`, one box per role |
| `bin/wagloop-claude` | registers the pane, starts Claude with the role's skill |
| `bin/wagloop-codex` | registers the pane, starts Codex sandboxed with the mailbox in its tool environment |
| `bin/wagloop-devin` | registers the pane, starts Devin with the exact installed role skill path |

## Requirements

- [msize/wagterm](https://github.com/msize/wagterm) with `wagtermctl` on PATH, Git Bash, Python 3.10+
- [msize/wagflow](https://github.com/msize/wagflow) cloned next to this repo, or `WAGFLOW` set
- OpenSpec CLI, the CLIs for the selected harnesses, and a review skill for each harness that plays Reviewer
  (see How to review in the reviewer skills)
- Devin CLI with `exec`, `get_output` and `kill_shell` tools when either role uses Devin

## Install

```bash
CODEX_REVIEW_SKILL='$<plugin>:<review-skill>' \
CLAUDE_REVIEW_SKILL='/<plugin>:<review-skill>' \
DEVIN_REVIEW_SKILL='<review-skill-name>' ./install.sh
export PATH="<path-to-wagloop>/bin:$PATH"
```

All three review-skill variables are required. They identify existing review skills, not model
names. For Devin, use the name passed to its skill tool. The installer renders both roles for
all three harnesses and can be run again after updating this checkout.

The same run installs WagFlow's implementer roles: `/wagflow-implementer` for Claude Code at
`~/.claude/commands/wagflow-implementer.md` and the Codex skill at
`~/.codex/skills/wagflow-implementer/SKILL.md`. These files are copied verbatim from the sibling
WagFlow checkout (or `WAGFLOW`) and refreshed on every run; their source stays in WagFlow.
An incomplete WagFlow checkout is rejected before any installed roles are changed.

Claude and Codex retain their existing skill directories. Devin skills go to
`~/.config/devin/skills/wagloop-{author,reviewer}/SKILL.md`. The Devin launcher explicitly
asks the agent to read that file: global skill discovery paths vary by platform, and a
compatibility-loaded Claude skill with the same name must not override the Devin instructions.
Installation does not change permissions, trust settings or CLI configuration.

### Rebranding

This is a clean switch to `wagloop`, with no legacy command or skill aliases. Reinstall the
skills and update PATH to this checkout's `bin/`. Set `WAGFLOW` if the transport checkout is
not a sibling named `wagflow`. It must provide `lib/wagmsg.py`, `lib/wag.py` and `lib/wb.py`.
Use `wagtermctl` and the `WAGTERM_*` terminal environment. `WAGLOOP_BASH` optionally selects
Git Bash's `bash.exe` when starting a Reviewer from a non-Bash pane.

Existing mailbox data is not migrated or deleted. New loops use `.wagloop/`. Previously
installed skills remain untouched, but the new launchers only reference `wagloop-*`.

## Use

In the project checkout, inside wagterm, start the Author and name its Reviewer with `with=`:

```bash
wagloop-claude author add-retry-policy gates=p1 with=codex   # with=codex is the default
wagloop-claude author add-retry-policy with=claude
wagloop-claude author add-retry-policy with=devin
wagloop-codex author add-retry-policy                      # with=claude is the default
wagloop-codex author add-retry-policy with=devin
wagloop-devin author add-retry-policy                      # with=codex is the default
wagloop-devin author add-retry-policy with=claude
wagloop-devin author add-retry-policy with=devin
```

Describe the change instead of naming it, or pass nothing and pick from the active changes.
`review [<name>]` instead of a change sends the uncommitted changes that already exist to review
as one step. Arguments after `--` go to the selected CLI unchanged, for example:

```bash
wagloop-devin author review with=claude -- --model codex
```

`devin` selects the harness, not its model. The launcher does not force a model or permission mode.

### From a running session

In a Claude Code session that runs in a wagterm pane, call the skills directly. They run
`init` themselves, so the result is the same as with the launcher:

```
/wagloop-author                                        # Codex reviews, pick from the active changes
/wagloop-author with=claude                            # Claude reviews
/wagloop-author with=devin                             # Devin reviews
/wagloop-author add-retry-policy gates=all with=claude   # name the change, stop after every phase
/wagloop-author review with=codex                      # review the existing uncommitted changes
/wagloop-reviewer                                      # this session reviews for an Author started next to it
```

Codex needs its launcher in either role. It registers the pane, which the sandbox cannot do
from inside, turns off the status line that would block every ring, and sets up the sandbox and
the mailbox environment. `$wagloop-author` typed into a plain `codex` session does not work.

In a running Devin session, ask it to read and follow the installed file
`~/.config/devin/skills/wagloop-author/SKILL.md` with your arguments, or the corresponding
reviewer file. Do not invoke a same-named Claude compatibility skill. Prefer the launcher,
which chooses the correct file automatically.

### What happens

The Author's `init` splits its session left/right when it is not split yet. The Reviewer starts in
the right pane, at the checkout root, through `wagloop-<with> reviewer`:

- Claude or Devin Author: with its first request, after the request is filed, so the Reviewer starts
  working on it at once;
- Codex Author: right away, by the launcher, since from inside its sandbox it could not later.

A Reviewer already running in the right pane is kept. A right pane that is neither a shell prompt
nor the Reviewer is never typed into: `init` stops and says what to start there. The Reviewer can
still be started by hand with `wagloop-codex reviewer`, `wagloop-claude reviewer` or
`wagloop-devin reviewer`.

| Author / Reviewer | Claude | Codex | Devin |
|---|---|---|---|
| Claude | yes | yes | yes |
| Codex | yes | no | yes |
| Devin | yes | yes | yes |

Codex cannot wake another Codex from its sandbox, so that pairing remains rejected.

Each launcher runs `wagloop.py --as <role> init --tool <tool>`, which creates `.wagloop/`, adds it
and `review-runs/` to `.git/info/exclude`, and registers its own pane under its role. From there
`wagloop.py send` picks the doorbell by the recipient: a Codex pane gets a `Chat from ...:` pointer
typed into its composer. Claude uses its background waiter. Devin keeps its turn open and
waits explicitly with `exec` and `get_output`, using one four-minute `wagloop.py wait` at a time.
This does not rely on background shell completion generating a new turn. Human gates and
failures stop the Devin waiter before the turn ends.

Devin registers through wagflow's `hub` API because older mailbox CLI versions do not accept
`--tool devin`. No wagflow changes or Devin composer automation are needed.

`.git/info/exclude` is the checkout's own ignore file: it works like `.gitignore` but is never
committed, so the project's `.gitignore` stays untouched and nobody else sees the entries.
`git check-ignore -v .wagloop/` shows the rule.

## How it is bounded

- Codex runs `--sandbox workspace-write --ask-for-approval never` without network, in either role.
  It cannot reach the wagterm pipe, so it never types into a pane: it writes mail, and the Claude
  or Devin peer's waiter picks it up. That is why at least one side must be Claude or Devin.
- Devin runs with the user's existing permission and trust settings. The launcher grants no
  extra permissions and does not enable a sandbox. Reviewer read-only behavior is a role rule,
  not an OS security boundary.
- The Reviewer writes only under `.wagloop/` and `review-runs/`.
- The Author never commits or pushes. After each approved task it stages with `git add -A`, so the
  next review is exactly `git diff`.
- A phase that is not approved after round 3 stops and waits for the human.

## Verify

From Git Bash:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
for script in install.sh bin/wagloop-*; do bash -n "$script" || exit; done
git --no-optional-locks diff --check
```

Tests cover message routing for all nine pairings, registration, reviewer startup, CLI argument
handling, unchanged Codex sandbox flags, and repeatable installation into a temporary home.
They mock agent CLIs and terminal control, not live two-agent conversations.

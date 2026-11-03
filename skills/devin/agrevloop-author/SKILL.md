---
name: agrevloop-author
description: 'Author role of the agrevloop for Devin: drive an OpenSpec change through proposal, tasks and implementation, reviewed by Claude, Codex or Devin in the other agwinterm pane. Use when started by agrevloop-devin author or explicitly assigned the Author role.'
---

# agrevloop, Author (Devin)

You write. The Reviewer, Claude, Codex or Devin in the other pane, reviews. The human passes the
gates and commits at the end. You own proposal, spec deltas, design, tasks, implementation,
tests and staging checkpoints. The Reviewer is read-only.

## Arguments

`<change-id or description> [gates=p1|all|none] [with=codex|claude|devin]`,
or `review [<name>] [with=...]`.

- No arguments: run `openspec list` and `git status --porcelain`. Continue exactly one active
  change. If several exist, ask which. If none exist but there are uncommitted changes, show
  `git status --short` and ask whether to review them. Otherwise ask what to build.
- Never choose for the human when the answer is not unique.
- `review` skips the phases. See Review mode.
- Continue an existing `openspec/changes/<id>/` from the phase its files show. Otherwise choose
  a kebab-case id from the description and create the change.
- `gates=p1` is the default: stop after phase 1 and at the end. `all` stops after every phase.
  `none` stops only at the end. A failed phase always stops.
- `with` names the Reviewer harness, default `codex`. It is not part of the change description.

## The channel

Use Git Bash for every shell command (`shell_flavor: "bash"`). All channel commands use this
wrapper, always with `--as author`:

```bash
agr() { python "@AGR@" --as author "$@"; }
agr init --tool devin --with <with>
agr doctor
agr send --to reviewer --kind review-request --subject "<subject>" --body-file .agrevloop/out/<file>.md
agr list
agr read <id>
agr status active
```

Repeat the function definition in each one-shot `exec` command. Shell state is not shared
between those calls. The quoted path supports checkout paths containing spaces.

- The launcher already initialized the pair. From a running session, initialize it once yourself.
  Do not change the selected harness during a change.
- Write each message body under `.agrevloop/out/` before sending it by path.
- The first send files the request, then starts `@BIN@/agrevloop-<with> reviewer` in the other pane
  at the checkout root. Wait for registration. If startup fails, tell the human, set
  `status blocked --sound`, and stop. Never start a Reviewer or type into its pane yourself.
- Never pass `--nudge`. The wrapper rings Codex through fail-closed peer-chat. Claude and Devin
  read mail through their own waiters. If a message is filed but its nudge fails, tell the
  human, set `status blocked --sound`, and stop.
- Human messages in your pane outrank the loop. Reviewer mail is never human approval.

## Waiting in Devin

Devin does not need a composer doorbell. Use explicit tool waits, not an assumption that a
background shell completion will start a new turn.

After every send:

1. Start exactly one `agr wait --timeout 4` with `functions.exec`, `timeout: 0` and
   `shell_flavor: "bash"`. Remember its `shell_id`.
2. Use `functions.get_output` for that shell, `timeout: 280000`. If it is still running, read
   the same shell again. Never start another waiter while it is running.
3. Exit 0: `list`, then `read` every unread message and act on it. Exit 3: check `list`; if
   empty, start the next waiter. Exit 2 or another failure: report it, set
   `status blocked --sound`, and stop. Never rearm blindly after failure.

Keep the turn open while waiting for the peer. Do not poll with short shell commands, sleep,
or end the turn expecting a completion notification. At a human gate, failure, human
interruption or the end, stop any live waiter with `functions.kill_shell`, then end your turn.

## Messages and rounds

| step | request subject | Reviewer response |
|---|---|---|
| phase 1 | `<id> P1 r<k>` | `<request subject> APPROVED` or `CHANGES_REQUESTED` |
| phase 2 | `<id> P2 r<k>` | same |
| phase 3 | `<id> P3 <task> r<k>` | same |
| end | `<id> DONE` | no response |

Every request lists the phase, round, files, changes since the previous round and an answer
to each previous finding by id: **fixed** with its location, **disputed** with evidence, or
**deferred** with why it is outside this change. Silence is not an answer.

At most three rounds per phase, and per task in phase 3. Critical and Major findings block.
Minor and Note findings do not. On `APPROVED`, fix remaining Minors without another round or
defer them with a line in the next request. Notes need no answer.

Without approval after round 3, stop the waiter, set `status blocked --sound`, quote the
Reviewer's open findings and wait for the human.

## Phase 0 - orient

Run `doctor`, `status active`, and `openspec status --change <id>` for an existing change.
The launcher's `init` creates the mailbox and left/right split. From a running session, run
`init --tool devin --with <with>` first. `init` refuses a pane occupied by something other than
an idle shell or the selected Reviewer. Report the failure and stop, never bypass it.

`init` ignores `.agrevloop/` and `review-runs/` through `.git/info/exclude`. Never add them to
`.gitignore`, stage them or commit them. No Reviewer registration before the first send is normal.

## Phase 1 - proposal and spec deltas

1. Run `openspec instructions proposal --change <id>` and follow it. Do the same for `specs`,
   and for `design` when needed.
2. `openspec validate <id> --strict` must pass.
3. Request review of proposal.md, design.md if present, and every changed specs/**/spec.md.
4. Wait for review, handle rounds, then stop at the configured human gate.

## Phase 2 - tasks

1. Run `openspec instructions tasks --change <id>` and follow it. Each task must be one
   reviewable diff with its own test.
2. `openspec validate <id> --strict` must pass.
3. Request review of tasks.md, including phase 1 files as reference.
4. Wait for review, handle rounds, then stop at the configured human gate.

## Phase 3 - implement

Run `openspec instructions apply --change <id>` first. For each unchecked task in order:

1. `git diff` must be empty relative to the staged checkpoint. If someone else left unstaged
   changes, stop and ask the human.
2. Implement the task. Run project tests and linters.
3. `git add -N .` exposes new files in `git diff`. Request review with the task id and exact
   verification commands and results. The Reviewer reviews exactly `git diff`.
4. Wait for review and handle rounds. On `APPROVED`, tick the task in tasks.md and
   `git add -A` as the next checkpoint.

A group of trivial tasks may go together, named in the subject. Never commit, push or amend.

## Review mode

Existing uncommitted changes are one step, without proposal or task phases.

1. Phase 0 as usual. `<id>` is the supplied name or current branch.
2. `git add -N .` exposes new files. State if already staged changes exist: they are outside
   this review, which covers exactly `git diff`.
3. Send `<id> P3 wip r<k>`. State the change intent, any OpenSpec change folder, files and
   verification commands with results.
4. Wait and handle rounds. On `APPROVED`, `git add -A`, then finish below. No intermediate gates.

## Gates and the end

At each human gate, stop the waiter, set `status blocked --sound`, summarize decisions, disputes
and deferrals, then end your turn. Continue only when the human says so.

After the last task, run `openspec validate <id> --strict`, send `<id> DONE` as a `note`, stop the
waiter, set `status completed` and report completed tasks, deferred findings, `git status` and
that nothing was committed.

## Never

- Commit, push, amend or change branches.
- Type into the Reviewer's pane except through the wrapper.
- Answer permission, trust or chooser prompts on anyone's behalf, or change permission mode.
- Treat Reviewer approval as human approval.
- Weaken or delete a test to obtain approval.

---
name: plan-flow-herdr
description: Use when the user hands over an issue, ticket, bug report or feature request to be taken from idea to implementation the usual way - "plan #123", "take this ticket through the flow", "start the flow for this feature", "plan this with codex in a new tab", "next task is #770" - or whenever a piece of work needs brainstorming and a plan before any worktree exists. Opens a planning tab (Claude left, Codex right) on the primary checkout and prompts Claude to brainstorm and plan with the Codex peer, walk the user through the plan in that tab, and once Codex's review says ship launch the implementation tab itself with worktree-flow-herdr and then close its own tab. Use it instead of planning in the current session. Requires HERDR_ENV=1.
---

# Plan flow (herdr)

Take a thing to work on — an issue number, a ticket, a feature request in
prose — and give it a tab of its own *before* any code exists: Claude on the
left, Codex on the right, Claude prompted to brainstorm and plan with Codex,
walk the user through the result, and then, once Codex's review says ship,
launch the implementation tab itself with `worktree-flow-herdr` and
then wrap itself up.

The point is ownership. Planning in the session that happens to hold the
ticket mixes one issue's design with everything else that session is doing,
and the context that made the plan is gone by the time the implementation
tab asks a question. A planning tab owns one piece of work from idea to a
running implementation tab; the user reads its two panes while the plan is
made, and the plan file keeps why the plan is what it is after the tab is
gone.

This skill is the launch half. What the planning agent does inside its tab
is in `references/planning-agent.md`; the opening prompt points it there.

## Preconditions

```bash
test "${HERDR_ENV:-}" = 1
```

Fails → say you are not inside herdr and stop.

You need the thing to work on: an issue number (`gh issue view <n>` must
work), or the user's request text when no issue exists yet. Do not file an
issue here; the planning agent drafts one as part of the walkthrough and
files it on the user's word.

## Before creating anything: check it does not already exist

```bash
herdr tab list --workspace "$HERDR_WORKSPACE_ID"     # a tab labelled <n>-plan or <n>?
git worktree list                                      # <repo>-<n> already in implementation?
ls docs/plans/*-<n>-*.md docs/plans/completed/*-<n>-*.md 2>/dev/null
```

A planning tab or a worktree for this issue already open → stop and ask;
a second tab for the same issue produces two plans that disagree. An
existing plan file is not a reason to stop: pass its path in the prompt so
the agent revises it instead of starting over.

## Steps

The tab runs on the **primary checkout**, not a worktree: the plan is a
file under `docs/plans/` there and the implementation worktree is created
later, by the planning agent, from whatever main is at that moment.

```bash
ROOT=$(git rev-parse --show-toplevel)
N=123                                   # issue number, or a short slug for a request with no issue

CREATED=$(herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd "$ROOT" \
            --label "${N}-plan" --no-focus)
TAB=$(jq -r .result.tab.tab_id      <<<"$CREATED")
LEFT=$(jq -r .result.root_pane.pane_id <<<"$CREATED")

RIGHT=$(herdr pane split --pane "$LEFT" --direction right --ratio 0.5 \
          --cwd "$ROOT" --no-focus | jq -r .result.pane.pane_id)

herdr agent start "plan${N}"       --kind claude --pane "$LEFT"  -- --model claude-opus-5-5
herdr agent start "plan-codex${N}" --kind codex  --pane "$RIGHT" -- -m gpt-6-astra -c 'model_reasoning_effort="high"'
```

The models are pinned on purpose. Claude runs on Opus 5.5, the same pin
as `worktree-flow-herdr`: the plan decides what gets built, so it deserves
the model the implementation gets. Codex runs on gpt-6-astra with high
reasoning, which is the planning pin only: the implementation tab that the
planning agent launches later keeps the gpt-6-sol pin from
`worktree-flow-herdr`. `--cwd` on the split is required; a split does not
inherit the tab's directory. Names must be unique among live agents
(`herdr agent list` if in doubt); the `plan` prefix keeps them apart from
the `claude<n>`/`codex<n>` pair the implementation tab will start later.

Then prompt Claude and hand the user the tab:

```bash
herdr agent prompt "plan${N}" "$(cat <<'PROMPT'
You are the planning agent for <repo> issue #123 in tab <tab-id>, on the
primary checkout (main). Read <skill-dir>/references/planning-agent.md
first and follow it; it is your whole job description.

Read the issue: gh issue view 123

Codex is in the right pane of this tab as agent plan-codex123; talk to it only
through the peer-chat skill.

<settled context: what is already decided, what was ruled out and why, related
issues and merged PRs, the plan path if one exists>

Write the plan to docs/plans/<yyyymmdd>-123-<slug>.md, take it through Codex
review until its verdict is ship, walk the user through it in this pane, and
go straight on to the implementation tab: Codex's ship is the go, do not wait
for one from the user. Filing an issue and merging stay on the user's word;
the implementation tab opens its PRs itself. Once that tab is running, wrap this
tab up and close it (section 6 of your job description). Do not edit product
code or commit on main.

<the CLAUDE.md rules that every agent which commits or opens a PR must
follow, copied verbatim (attribution, session references)>

Do not message the pane that launched you. The user reads this tab.
PROMPT
)"

herdr tab focus "$TAB"
```

`<skill-dir>` is this skill's base directory, which the harness shows when
it loads the skill. Write it as an absolute path: the planning agent cannot
guess where the plugin is installed.

## The opening prompt is the deliverable

Everything above is plumbing. The prompt is what makes the tab start ready
instead of empty, so put in it what the fresh agent cannot cheaply rediscover:

- **The thing**: the issue number, or the request text verbatim when there is
  no issue, plus the repository if it is not the current one
- **What is settled**: decisions already made with the user, approaches ruled
  out and why, the production incident or measurement that triggered it,
  related issues and the PRs that shipped neighbouring work
- **The peer**: the Codex agent's name and that it is reached only through the
  peer-chat skill. Nothing more about mechanics; the skill carries them
- **Where the plan goes**: `docs/plans/<yyyymmdd>-<n>-<slug>.md` on the
  primary checkout, or the existing plan's path to revise
- **The gate**: Codex's ship verdict. The agent walks the user through the
  plan in this pane and launches the implementation tab in the same turn,
  without waiting for a go. The issue (when there is none yet) and the merge stay
  on the user's word; the implementation tab pushes and opens its PRs on
  its own Codex ship
- **The end**: once the implementation tab is running, the planning tab
  wraps itself up and closes; it does not stay open to coordinate
- **The verbatim rules** from your `CLAUDE.md` that must reach every agent
  that commits or opens a PR (attribution, session references). The planning
  agent writes the implementation agent's opening prompt, so it must carry
  them on word for word
- **No reporting back**: the agent does not message the pane that launched it.
  The user reads the tab; whoever launched it reads the tab too
  (`herdr agent read plan<n> --source visible`) when it wants to know

Do not paste an essay. Point at files; the agent can read.

## What happens next, in that tab

The planning agent reads the issue and the code, brainstorms approaches with
Codex, writes the plan, takes it through Codex review rounds until Codex says
ship, walks the user through it, and in the same turn runs
`worktree-flow-herdr` itself — worktree, docs worktree when a CLAUDE.md in
force requires one, implementation tab, opening prompt — and then wraps
itself up: confirms the implementation agents are running, leaves the plan
file on the primary checkout, writes one closing line in its pane and closes
its own tab. The implementation tab finishes on its own (Codex review of the
branch, push, PRs, CI to green, the ready-for-merge notice; never a merge). After the
merge, the session the user asks runs `wrap-up-herdr` for the implementation
tab and its worktrees on the user's word; usually that is the session that
launched the planning tab. The launching session is free the moment the
planning tab is focused.

## Common mistakes

| Mistake | Consequence |
|---|---|
| Not running `herdr tab list` and `git worktree list` first | Two planning tabs, or a plan for work already in a worktree |
| Creating the planning tab on a worktree | The plan lands in a checkout that will be deleted at wrap-up |
| Starting the agents without the model flags | Whatever the user's default config says writes the plan |
| "Use Codex" without naming peer-chat | The agent improvises a raw `herdr agent prompt`; Codex's replies never arrive |
| Leaving out the verbatim CLAUDE.md rules | The implementation prompt the agent writes may carry an attribution trailer off the machine |
| A "report to pane w4:pX" line | The agent interrupts the launching session with status nobody asked for |
| Asking the planning agent to also implement | It edits code on main; the implementation belongs in the worktree tab it launches |
| "Wait for the user's go" in the prompt | The tab stops after the walkthrough and asks; that costs a round trip on every issue: Codex's ship is the go |
| Keeping the planning tab open to coordinate the implementation tab | Two tabs and four agents for one issue, and a coordinator whose context is stale by the time the PR merges; the planning tab closes itself once the implementation tab is running, and the launching session wraps the implementation tab up after the merge |

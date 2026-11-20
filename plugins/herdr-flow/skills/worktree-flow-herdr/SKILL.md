---
name: worktree-flow-herdr
description: Use when the user says "start working on that in a new worktree", "that issue in a new worktree", "spin up a worktree for this", or otherwise asks to begin work on an issue or plan in an isolated checkout - creates a git worktree in a sibling directory, opens a new herdr tab on it, starts Claude in the left pane and Codex in the right, and hands Claude the opening prompt. Requires HERDR_ENV=1.
---

# Worktree flow (herdr)

Take a thing to work on — an issue, a plan file, a PR — and stand up an isolated
workspace for it: its own git worktree, its own herdr tab, Claude on the left,
Codex on the right for peer review, and Claude already prompted.

The point is that the new tab starts *ready*, not empty. An agent that lands in
a worktree with no context re-derives what you already know.

## Preconditions

```bash
test "${HERDR_ENV:-}" = 1
```

Fails → say you are not inside herdr and stop.

## Before creating anything: check it doesn't already exist

**This is the step that actually bites.** Long-lived repos accumulate worktrees,
and a stale one for your issue may already be sitting there at an old commit.

```bash
git worktree list
```

If one already covers this issue, **stop and ask**. Do not create a second one
and do not silently reuse the stale one — its branch may predate work that has
since merged, which is exactly the trap. Offer: reuse as-is, rebase it, or
remove and recreate. The user decides.

## Steps

Match the repo's existing worktree naming — read it off `git worktree list`
rather than inventing one. A common shape is `<repo>-<issue-number>`.

```bash
REPO=$(basename "$(git rev-parse --show-toplevel)")
WT="$(dirname "$(git rev-parse --show-toplevel)")/${REPO}-123"   # sibling dir
BRANCH=fix/123-login-timeout

git worktree add -b "$BRANCH" "$WT" main

# When a CLAUDE.md in force requires a companion documentation change, the
# docs worktree is part of this workspace: same number, same tab, same plan,
# torn down together. <docs-repo> is the repository that CLAUDE.md names.
DOCS="$(dirname "$(git rev-parse --show-toplevel)")/<docs-repo>"
git -C "$DOCS" worktree list                       # a stale one bites here too
git -C "$DOCS" worktree add -b docs/123-login-timeout "${DOCS}-123" main
```

Branch off whatever the work is actually based on — usually `main`, but check.

```bash
# Tab on the worktree. Keep focus where the user is until the end.
# tab create returns BOTH ids - no second call needed
CREATED=$(herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd "$WT" \
            --label "123" --no-focus)
TAB=$(jq -r .result.tab.tab_id      <<<"$CREATED")
LEFT=$(jq -r .result.root_pane.pane_id <<<"$CREATED")

# Right pane. --cwd is required: a split does not inherit the tab's directory.
RIGHT=$(herdr pane split --pane "$LEFT" --direction right --ratio 0.5 \
          --cwd "$WT" --no-focus | jq -r .result.pane.pane_id)

herdr agent start claude123 --kind claude --pane "$LEFT"  -- --model claude-opus-5-5
herdr agent start codex123  --kind codex  --pane "$RIGHT" -- -m gpt-6-sol -c 'model_reasoning_effort="high"'
```

The models are pinned on purpose and are part of this flow: Claude on Opus 5.5,
Codex on gpt-6-sol with high reasoning. Everything after `--` goes to the agent
binary; the `codex` shell function from the peer-chat setup (`~/.zshrc`) keeps
its pane pin and appends these. Do not drop the flags because the user's default config happens to match
today: a changed default would silently change what reviews the code.

Agent names must match `[a-z][a-z0-9_-]{0,31}` and be unique among *live* agents
— `herdr agent list` first if you might collide. Suffix them with the issue
number and they stay unique and readable.

Then prompt Claude and hand the user the tab:

```bash
herdr agent prompt claude123 "$(cat <<'PROMPT'
You are working on issue #123 in a dedicated worktree on branch
fix/123-login-timeout.

Read the issue first: gh issue view 123

<the specific opening instruction — see below>
PROMPT
)"

herdr tab focus "$TAB"
```

## The opening prompt is the deliverable

Everything above is plumbing. The prompt is what makes the new tab useful, so
put the context in it that the fresh agent cannot cheaply rediscover:

- **What to read first** — the issue, and the plan file by path if one exists
- **Where the work is defined** — "follow `docs/plans/<file>.md`, tasks 1-3"
- **Constraints already settled** — decisions made, approaches ruled out and why
- **The peer** — "Codex is in the right pane of this tab as agent codex123; talk to
  it only through the peer-chat skill." Name the agent and name the skill, nothing
  more about mechanics: the skill carries them. A prompt that improvises a raw
  `herdr agent prompt` RPC or a `/tmp` file drop gets a reviewer that cannot reply.
- **The review handshake** — a review is a round trip, and the agent's half
  is to stop. After committing a task it sends Codex the diff range and the
  ask, and that send is the last action of its turn: it ends the turn and
  starts nothing until the reply arrives. Codex can deliver only to an idle
  pane; an agent that goes on to the next task, a test run or "reading ahead"
  makes every delivery attempt fail, and the review it will later report as
  done never happened. On the reply it fixes, commits, re-sends, ends again,
  until Codex says ship for that task. If no reply comes the panes sit idle
  and the user asks; that is cheaper than an unreviewed task. Write this as a
  rule in the prompt: "each review request ends your turn; do nothing until
  the reply"
- **How it finishes** — "commit per task; after the last task have Codex
  review the whole branch; on its ship, push, open the PR(s) (docs PR first,
  product PR linking it), watch CI until green and fix a red check on the
  branch without asking, then send the ready-for-merge notice if your team
  uses one (a chat post, for example); never merge". A finished branch should
  not sit waiting for a word to become a PR; the merge is the one gate left
- **The documentation worktree** — when one was created above: its path and
  branch, which pages this issue touches or the reason it touches none, and
  that the docs change is a task of the plan like any other: committed there,
  reviewed by the same peer, built strict, done before the stop point above.
  Once PRs are authorized, the docs PR opens first and the product PR links it
- **No reporting back** — the agent does not message the coordinator's pane on
  its own: no progress notes, no "task done", no questions fired at the tab
  that launched it. The user reads both panes, and the coordinator reads the
  tab (`herdr agent list`, `herdr agent read <agent> --source visible`) when it
  wants to know where things are. The only message the agent sends to the
  coordinator is the answer to a question the coordinator asked it directly,
  through peer-chat, and it answers the way that message says. Write this into
  the prompt as a rule; do not write a "report to pane w4:pX" line, which turns
  the coordinator into a second user and interrupts whatever it is doing

Do not paste an essay. Point at files; the agent can read.

## Common mistakes

| Mistake | Consequence |
|---|---|
| Not running `git worktree list` first | A stale worktree for that issue already exists at an old commit |
| Omitting `--cwd` on `pane split` | Right pane opens in the *calling* pane's directory, not the worktree |
| Focusing during construction | User is yanked between tabs mid-setup |
| Generic agent names (`claude`, `reviewer`) | Collides with a live agent; `agent start` fails |
| Starting the agents without the model flags | Whatever the user's default config says runs the issue; the flow pins Opus 5.5 and gpt-6-sol high |
| Prompting before `agent start` returns | It returns only once the agent is interactive-ready — let it |
| A prompt that just says "work on #123" | Agent re-derives context you already had |
| "Use Codex to review" without naming peer-chat | Agent improvises a raw `herdr agent prompt` RPC; the reply never reaches it, or arrives as two words |
| Leaving the docs worktree for the agent to create later | It becomes a separate job that never starts; create it beside the product worktree |
| A "report progress to pane w4:pX" line in the prompt | The agent interrupts the coordinator's turn with status it did not ask for; the coordinator reads the tab instead and asks directly when it needs something |
| No "each review request ends your turn" rule in the prompt | The agent asks for a review and keeps working; peer-chat refuses to deliver to a working pane, the reply is lost or lands mid-task, and the task is reported as reviewed when it was not |
| "Do not open a PR without asking" in the prompt | The finished branch waits for someone to notice; in this flow the agent opens the PR on Codex's ship, watches CI to green and sends the ready-for-merge notice |

## Cleanup

When the branch is merged, the worktree is not automatically removed. Use the
`wrap-up-herdr` skill: it captures unpushed commits, unread review files and
still-working agents *before* deleting, then closes the tab, removes the
worktree and branches, and writes the retrospective. The bare minimum, only
after those checks:

```bash
herdr tab close "$TAB"
git worktree remove "$WT"
git branch -d "$BRANCH"     # -D after a squash merge
```

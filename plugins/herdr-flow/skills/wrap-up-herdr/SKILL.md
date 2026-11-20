---
name: wrap-up-herdr
description: Use when the user says "wrap up", "clean up the worktree", "close that tab", "tear down" or "retro" after a PR from a worktree-flow-herdr tab has merged - captures anything still sitting in the worktree, review files and agent panes BEFORE deleting, then removes the tab, worktree, branches and temp files, and writes a few-sentence retrospective. Requires HERDR_ENV=1.
---

# Wrap up (herdr)

The mirror of worktree-flow-herdr. A merged PR leaves behind a tab with two
agents, a worktree, a local and maybe a remote branch, review drop files under
`/tmp`, scratchpad notes, sometimes E2E containers. Tear it all down, but
**capture first, delete second**: the last thing a peer reviewer said, and the
last commit an agent made, are routinely not on main yet.

## Preconditions

```bash
test "${HERDR_ENV:-}" = 1
```

Fails → say you are not inside herdr and stop.

Inputs: the branch or worktree name, the PR number, the tab ID. Recover what
the user did not give you from `git worktree list`, `gh pr list --state merged
--head <branch>` and `herdr tab list --workspace "$HERDR_WORKSPACE_ID"`. Never
guess a tab ID from sidebar order.

## Step 0: the PR is actually merged

```bash
gh pr view <n> --json state,mergedAt,headRefName --jq '"\(.state) \(.mergedAt) \(.headRefName)"'
```

Anything but `MERGED` → stop and ask. A wrap-up on an open PR deletes the
branch under it. When the body links a companion docs PR, the workflow
has two PRs; read the second the same way, in its own repository:

```bash
gh pr view <docs-pr-url> --json state,mergedAt,headRefName
```

Both must be `MERGED` before anything in Step 2 runs. A docs PR that is not
(open, closed unmerged, or the docs line your project requires is missing
or gives no accepted reason) means the workflow is not finished: still run the
Step 1 reads, then report what is owed with the pages affected, keep the tab,
both worktrees and both branches, and stop. The tab holds the agents that own
the docs task; closing it ends that work.

## Step 1: capture before you delete anything

**This is the step that bites.** Everything below reads; nothing writes.

Every check below runs once per worktree. With a docs PR there are two:
resolve the docs worktree from the docs repo's own list by the PR's head
branch, never by reconstructing a name.

```bash
WT=../<repo>-<name>
DOCS=<docs-repo>                                 # the repo the CLAUDE.md in force names
DOCS_BRANCH=$(gh pr view <docs-pr-url> --json headRefName --jq .headRefName)
DOCS_WT=$(git -C "$DOCS" worktree list --porcelain | awk -v b="refs/heads/$DOCS_BRANCH" '/^worktree /{w=$2} $0=="branch "b{print w}')

for T in "$WT" "$DOCS_WT"; do
  git -C "$T" status --short                                  # uncommitted work
  git -C "$T" log --format='%h %s' origin/main..HEAD          # commits not on main
  git -C "$T" log --format='%h %s' @{upstream}..HEAD 2>/dev/null   # unpushed commits
done
herdr agent list                                 # agents still working in the tab?
herdr agent read <left-agent> --source visible --lines 40
ls -d /tmp/peer-review-*<n>* 2>/dev/null         # peer review drop files
```

Then decide, in this order:

- **Uncommitted changes, unpushed commits or commits not on main, in either
  worktree** → do not delete. Preserve the commits on a local branch
  (`git branch keep/<name> <sha>`, in that repo), tell the user what is in
  them and ask: follow-up PR, or drop. A squash-merged PR shows the *merged*
  commits here too; compare against the PR's merge commit or the diff, not
  just the commit list. A merged docs PR proves nothing about a commit made
  after it.
- **An agent still `working` or `blocked`** → do not close its tab. Report
  what it is doing and wait for the user.
- **Review files with a verdict the user has not seen** → quote the verdict
  and any `change first` finding in the wrap-up, then delete the files.

## Step 2: tear down

Only after Step 0 said `MERGED` for every PR of the workflow and Step 1 is
clean for every worktree, or the user has decided. There is one teardown; the
two worktrees of one workflow go together or not at all.

```bash
herdr tab close <tab-id>
git worktree remove "$WT"                        # add --force only for a dirty tree the user told you to discard
git branch -d <branch> || git branch -D <branch> # -D is normal after a squash merge; only after Step 0 said MERGED
git ls-remote --heads origin <branch> | grep -q . && git push origin --delete <branch>
git worktree prune
docker ps -a --filter "name=<repo>-<name>" --format '{{.Names}}'   # E2E stacks are namespaced by checkout dir
rm -rf /tmp/peer-review-*<n>*                   # and any scratch files you wrote for it
```

The docs side, with the values Step 1 resolved; none of it when the docs PR
is not `MERGED` or its worktree was not clean:

```bash
git -C "$DOCS" worktree remove "$DOCS_WT"
git -C "$DOCS" branch -D "$DOCS_BRANCH"
git -C "$DOCS" ls-remote --heads origin "$DOCS_BRANCH" | grep -q . && git -C "$DOCS" push origin --delete "$DOCS_BRANCH"
git -C "$DOCS" worktree prune
```

Stop any Monitor you armed for this PR (TaskStop). Pull main in the primary
checkout so the next worktree branches off the merged commit.

Leave alone: other worktrees, other people's branches, stale `fix/*` branches
from earlier work, the agent's own memory. Mention them in one line if they
look abandoned; do not delete what you did not create.

## Step 3: the retrospective

A few sentences in the reply, nothing in the repo. Cover, in this order:

1. what was wrong and how it showed (the symptom, with the number if one
   changed a decision);
2. what shipped and where (PR number, no diff tour);
3. what the peer review changed, or that it did not happen and why;
4. one thing to do differently next time.

Plain sentences, past tense, no headers. Take items 1 and 2 from the merged
PR's body (`gh pr view <n> --json body`) and the plan file, not from the PR
title: a title compresses, and a retrospective that misstates what shipped is
worse than none. If Step 1 found work not on main, the retrospective says so
and the "differently" line is usually "review before merge, not after".

## Common mistakes

| Mistake | Consequence |
|---|---|
| Deleting the worktree before `git log origin/main..HEAD` | The agent's last commit, made after the merge on a reviewer's finding, is gone |
| `rm -rf /tmp/peer-review-*` before reading it | The one `change first` verdict the user paid Codex for is never seen |
| Closing a tab with an agent still `working` | Interrupts a push or a review round mid-flight |
| `git branch -d` on a squash-merged branch and giving up | Not an error; `-D` is expected once Step 0 confirmed the merge |
| Wrapping up on `state=OPEN` | Deletes the branch under a live PR |
| Deleting old `fix/*` branches "while here" | Not asked; some are unmerged work |
| Tearing down on the product PR's merge alone | The docs PR is open or its branch holds a later unpushed commit; closing the tab ends the agents that own it |
| `git worktree list` here for the docs worktree | Worktrees are per repository; it is in the docs repo's list |

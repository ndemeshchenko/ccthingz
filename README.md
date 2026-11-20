# ccthingz

Things for [Claude Code](https://code.claude.com) (and its Codex peers), published as a Claude Code
plugin marketplace.

## Install

```sh
claude plugin marketplace add ndemeshchenko/ccthingz
claude plugin install peer-chat@ccthingz
claude plugin install herdr-flow@ccthingz
```

Or, inside a session: `/plugin marketplace add ndemeshchenko/ccthingz`, then `/plugin install peer-chat@ccthingz`.
Update later with `claude plugin marketplace update ccthingz`.

## Plugins

### peer-chat

Lets Claude Code and [Codex](https://developers.openai.com/codex) talk to each other as peers when they
run in two panes of the same [herdr](https://herdr.dev) tab. Say "chat with codex" (or "talk to claude"
on the Codex side), and each agent sends its messages to the other's pane with the `peer-chat` script.
You read both panes. The conversation is the result, even when code comes out of it.

What the script takes care of:

- **Routing:** `--to` takes an exact pane ID (any tab), else a pane name in the caller's tab, else an
  agent kind (`codex` / `claude`) in the caller's tab; `--tab` changes which tab that is. It refuses
  when the target is ambiguous, and names and kinds never cross tabs. The output reports the
  `pane_id` and `tab_id` the message went to.
- **Labelling:** messages arrive as `Chat from Claude: …` / `Chat from Codex: …`, so the receiver reads
  them as conversation, not as a new instruction from you.
- **Turn safety:** it sends only when the peer is `idle` or `done`, so it never interrupts a turn in
  progress. It refuses outright when the peer is `blocked` on an approval, and it retries only what is
  safe to retry.

Requirements: herdr (with its socket API), `python3`, and both agents started by you in the same tab.

#### Setup

**Claude side:** installing the plugin is all it takes. The `peer-chat` skill loads automatically, and
the script ships in the plugin's `bin/`, which Claude Code puts on the Bash tool's `PATH`.

**Codex side** needs three things. Codex doesn't see Claude's plugin `bin/`.

1. Put the script on your shell `PATH`, for example:
   ```sh
   curl -fsSL https://raw.githubusercontent.com/ndemeshchenko/ccthingz/main/plugins/peer-chat/bin/peer-chat \
     -o ~/.local/bin/peer-chat && chmod +x ~/.local/bin/peer-chat
   ```
   Re-run it after updating the plugin. Claude's copy lives in a version-numbered cache folder, so don't
   symlink to it.
2. Install the Codex-side skill. Copy [`codex/peer-chat`](codex/peer-chat) to `~/.agents/skills/peer-chat`
   (older Codex versions read `~/.codex/skills/`).
3. Add the approval rule from [`codex/peer-chat/default.rules.snippet`](codex/peer-chat/default.rules.snippet)
   to `~/.codex/rules/default.rules`, and the `codex()` function from
   [`codex/peer-chat/zshrc.snippet`](codex/peer-chat/zshrc.snippet) to `~/.zshrc`. Codex runs commands
   through a shared app-server daemon that would otherwise report another pane's `HERDR_*` variables.
   The function pins Codex's own pane. Launch Codex through it from the pane it should live in.
   The skill runs `peer-chat` outside the sandbox (`sandbox_permissions: "require_escalated"`),
   because herdr is not reachable from inside it; the approval rule is what keeps that escalation
   from prompting on every send.

### herdr-flow

Three skills that take a piece of work from an issue to a merged PR, each stage in its own
[herdr](https://herdr.dev) tab with Claude on the left and Codex on the right as the reviewer.

- **`plan-flow-herdr`**: "plan #123". Opens a planning tab on the primary checkout. Claude
  brainstorms and writes `docs/plans/<date>-<n>-<slug>.md` with Codex, takes it through Codex
  review until the verdict is ship, walks you through it, then launches the implementation tab
  and closes its own tab.
- **`worktree-flow-herdr`**: "start #123 in a new worktree". Creates a git worktree in a sibling
  directory (plus a docs worktree when your `CLAUDE.md` requires a docs change), opens a tab on
  it, starts both agents with pinned models and gives Claude an opening prompt that already holds
  the context. Claude commits per task, has Codex review each one, opens the PR(s) on Codex's
  ship of the whole branch and watches CI to green. It never merges.
- **`wrap-up-herdr`**: "wrap up #123" after the merge. Captures unpushed commits, unread review
  verdicts and still-working agents first, then closes the tab and removes the worktrees and
  branches, and writes a short retrospective.

Requirements: herdr, `gh`, `jq`, and the **peer-chat** plugin above, set up on both sides: the
agents talk only through it. The planning agent uses `superpowers:brainstorming` and a
plan-writing skill when they are installed. The model pins in the skills (`claude-opus-5-5`,
`gpt-6-sol` / `gpt-6-astra` with high reasoning) are a choice; change them in the skill text if
you want other models.

## Credits

`peer-chat` is a port of the two-agent-chat recipe from umputun's
[agterm cookbook](https://github.com/umputun/agterm) onto herdr's agent API. agterm is MIT licensed,
Copyright (c) 2026 Umputun.

## License

MIT, see [LICENSE](LICENSE).

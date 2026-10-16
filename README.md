# ccthingz

Things for [Claude Code](https://code.claude.com) (and its Codex peers), published as a Claude Code
plugin marketplace.

## Install

```sh
claude plugin marketplace add ndemeshchenko/ccthingz
claude plugin install peer-chat@ccthingz
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

- **Routing:** `--to codex` / `--to claude` resolves to exactly one agent of that kind in the caller's
  tab, or to a pane named or ID'd exactly. It refuses when the target is ambiguous.
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

## Credits

`peer-chat` is a port of the two-agent-chat recipe from umputun's
[agterm cookbook](https://github.com/umputun/agterm) onto herdr's agent API. agterm is MIT licensed,
Copyright (c) 2026 Umputun.

## License

MIT, see [LICENSE](LICENSE).

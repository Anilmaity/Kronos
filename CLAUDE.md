# Kronos workspace — root CLAUDE.md

The full project instructions were moved to `shared/CLAUDE.md` in the 2026-07-29 root
cleanup. They are imported below so every session still auto-loads them — **edit
`shared/CLAUDE.md`, not this file**, when the architecture doc needs changes.

@shared/CLAUDE.md

## Project knowledge vault (Obsidian)

Deep project knowledge lives in a standalone Obsidian vault at **`E:\Projects\KronosVault`**
(deliberately outside the git repos): architecture maps, the live strategy roster, incident
postmortems, deploy gotchas, and research-campaign histories. Start at `Home.md` — it is the
map of contents and carries the current production status snapshot.

When production state changes (roster, deploys, incidents), update the high-churn notes
`20 Strategies/Live Roster.md`, `40 Incidents/Timeline.md`, `30 Operations/Deploy Gotchas.md`
and bump their `updated:` frontmatter.

## Workspace root contents beyond the three repos

- `shared/` — non-repo workspace files: the full CLAUDE.md imported above, chart PNGs,
  audit docs, and reports (created in the 2026-07-29 root cleanup).
- `ClaudeTradingRD/` — research-sandbox git checkout (origin = the Mac dev machine over
  Tailscale, `100.75.120.39`; sync is two-way — check the Mac for unpushed work).
- `.claude/` — workspace-level Claude Code settings and skills.

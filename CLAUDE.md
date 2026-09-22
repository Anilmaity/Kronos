# Kronos workspace — root CLAUDE.md

The full project instructions were moved to `shared/CLAUDE.md` in the 2026-07-29 root
cleanup. They are imported below so every session still auto-loads them — **edit
`shared/CLAUDE.md`, not this file**, when the architecture doc needs changes.

@shared/CLAUDE.md

## Project knowledge vault (Obsidian)

Deep project knowledge lives in a standalone Obsidian vault at **`/Users/anil/Projects/KronosVault`**
on the Mac (`E:\Projects\KronosVault` on the old Windows box; deliberately outside the git repo): architecture maps, the live strategy roster, incident
postmortems, deploy gotchas, and research-campaign histories. Start at `Home.md` — it is the
map of contents and carries the current production status snapshot.

When production state changes (roster, deploys, incidents), update the high-churn notes
`20 Strategies/Live Roster.md`, `40 Incidents/Timeline.md`, `30 Operations/Deploy Gotchas.md`
and bump their `updated:` frontmatter.

## Workspace root contents beyond the three product folders

The root is a git monorepo (GitHub `Anilmaity/Kronos`, since 2026-09-20 — see `shared/CLAUDE.md`).

- `shared/` — the full CLAUDE.md imported above, chart PNGs, audit docs, and reports
  (created in the 2026-07-29 root cleanup).
- `ClaudeTradingRD/` — research sandbox (corpus studies, lab harnesses). Formerly its own repo
  synced with the Mac over Tailscale; now just a folder in the monorepo.
- `kb/` — local Chroma semantic index over the lab reports + vault (`kb/ask.py`, `kb/index_kb.py`);
  the `chroma/` store and `.venv/` are rebuilt locally, not committed.
- `.claude/` — workspace-level Claude Code settings and skills.

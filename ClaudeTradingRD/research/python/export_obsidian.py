"""Export the TTrades research corpus into the KronosVault Obsidian vault.

Builds `<vault>/50 Research/TTrades Library/` from the research folder:
  Playlists/    one note per playlist (16) - its videos in order
  Videos/       one note per video (443) - playlists, study unit, every concept citing it
  Study Units/  one note per unit (32) - the full study note, IDs turned into wikilinks
  Concepts/     one note per concept (505), by category - every field of the YAML
  Reports/      the written reports (meta/*.md, concepts/INDEX.md, RESUME.md, ...)
  TTrades Library.md - map of contents

The output folder is owned by this script: it is deleted and rebuilt on every run, so
never hand-edit notes inside it. Transcripts are linked, not copied.

    python python/export_obsidian.py [--vault /Users/anil/Projects/KronosVault]
"""
import argparse
import collections
import glob
import json
import os
import re
import shutil

import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # research/
OUT_NAME = "TTrades Library"
MARKER = ".generated-by-export_obsidian"

REPORT_FILES = [
    "RESUME.md", "README.md", "concepts/INDEX.md", "concepts/_SCHEMA.md",
    *sorted(os.path.relpath(p, HERE) for p in glob.glob(os.path.join(HERE, "meta", "*.md"))),
]
SECTION_ORDER = [
    ("definition", "Definition"), ("timeframes", "Timeframes"),
    ("preconditions", "Preconditions"), ("detection_rules", "Detection rules"),
    ("invalidation", "Invalidation"), ("execution", "Execution"), ("variants", "Variants"),
    ("measurable", "Measurable"), ("ambiguities", "Ambiguities"),
]
FRONT_KEYS = {"id", "name", "category", "status", "voice", "aliases", "draft_count",
              "voice_playlist"}
HANDLED = FRONT_KEYS | {k for k, _ in SECTION_ORDER} | {
    "sources", "guest_sources", "related", "contributing_units"}


def safe_name(s, limit=90):
    s = re.sub(r"(?<=\d):(?=\d)", ".", s)  # 10:00 -> 10.00
    s = s.replace("/", "-").replace("\\", "-").replace(":", " -").replace("->", "to")
    s = re.sub(r'[*?"<>|#^\[\]]', "", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:limit].rstrip(" .") or "Untitled"


def fmt_dur(sec):
    if not sec:
        return "?"
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def frontmatter(d):
    return "---\n" + yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=1000) + "---\n"


def render(v, indent=0):
    """Render an arbitrary YAML value as markdown bullets."""
    pad = "  " * indent
    if isinstance(v, dict):
        out = []
        for k, x in v.items():
            if isinstance(x, (dict, list)):
                out.append(f"{pad}- **{k}:**")
                out.append(render(x, indent + 1))
            else:
                out.append(f"{pad}- **{k}:** {x}")
        return "\n".join(out)
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, dict):
                items = list(x.items())
                k0, x0 = items[0]
                head = f"**{k0}:** {x0}" if not isinstance(x0, (dict, list)) else f"**{k0}:**"
                out.append(f"{pad}- {head}")
                if isinstance(x0, (dict, list)):
                    out.append(render(x0, indent + 2))
                if len(items) > 1:
                    out.append(render(dict(items[1:]), indent + 1))
            elif isinstance(x, list):
                out.append(render(x, indent + 1))
            else:
                out.append(f"{pad}- {x}")
        return "\n".join(out)
    return f"{pad}{v}"


class Linker:
    """Turns backticked IDs and relative .md links into wikilinks, outside code fences."""

    def __init__(self, targets, files):
        self.targets = targets  # token -> note name
        self.files = files      # repo-relative .md path / basename -> note name

    def _code(self, m):
        tok = m.group(1)
        note = self.targets.get(tok)
        return f"[[{note}|{tok}]]" if note else m.group(0)

    def _mdlink(self, m):
        text, path, anchor = m.group(1), m.group(2), m.group(3) or ""
        key = os.path.normpath(path).lstrip("./")
        note = self.files.get(key) or self.files.get(os.path.basename(path))
        return f"[[{note}{anchor}|{text}]]" if note else m.group(0)

    def __call__(self, text):
        out, fenced = [], False
        for line in text.split("\n"):
            if line.lstrip().startswith("```"):
                fenced = not fenced
            elif not fenced:
                line = re.sub(r"(?<!\[\[)`([A-Za-z0-9_.-]+)`", self._code, line)
                line = re.sub(r"\[([^\]]+)\]\((?!https?:)([^)#\s]+\.md)(#[^)]*)?\)", self._mdlink, line)
            out.append(line)
        return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default="/Users/anil/Projects/KronosVault")
    args = ap.parse_args()

    out = os.path.join(args.vault, "50 Research", OUT_NAME)
    if os.path.exists(out):
        if not os.path.exists(os.path.join(out, MARKER)):
            raise SystemExit(f"{out} exists but was not created by this script - refusing to delete it")
        shutil.rmtree(out)

    load = lambda p: json.load(open(os.path.join(HERE, p)))
    playlists = load("meta/playlists.json")
    units = load("meta/study_units.json")
    tstatus = load("meta/transcripts_status.json")
    concepts = []
    for f in sorted(glob.glob(os.path.join(HERE, "concepts", "[!_]*", "*.yaml"))):
        d = yaml.safe_load(open(f))
        d["_file"] = os.path.relpath(f, HERE)
        concepts.append(d)

    # ---- note names --------------------------------------------------------------
    videos = {}  # id -> {title, duration, url, playlists: [..]}
    for p in playlists:
        for i, v in enumerate(p["videos"], 1):
            e = videos.setdefault(v["id"], {**v, "playlists": []})
            e["playlists"].append((p["title"], i))
    vname = {vid: f"{safe_name(v.get('title') or 'Untitled', 80)} ({vid})" for vid, v in videos.items()}
    pname = {p["title"]: f"Playlist - {safe_name(p['title'])}" for p in playlists}
    uname = {u["unit_id"]: u["unit_id"] for u in units}
    cname, seen = {}, set()
    for c in concepts:
        n = safe_name(c["name"])
        if n.lower() in seen:
            n = f"{n} ({c['id']})"
        seen.add(n.lower())
        cname[c["id"]] = n
    rname = {r: "Report - " + ("concepts " if r.startswith("concepts/") else "")
             + os.path.splitext(os.path.basename(r))[0].strip("_")
             for r in REPORT_FILES if os.path.exists(os.path.join(HERE, r))}

    targets = {**{k: v for k, v in vname.items()}, **cname, **uname}
    files = {}
    for r, n in rname.items():
        files[os.path.normpath(r)] = n
        files.setdefault(os.path.basename(r), n)
    for u in uname:
        files[f"notes/{u}.md"] = uname[u]
        files.setdefault(f"{u}.md", uname[u])
    link = Linker(targets, files)

    unit_of = collections.defaultdict(list)
    for u in units:
        for v in u["videos"]:
            unit_of[v["id"]].append(u["unit_id"])
    cites = collections.defaultdict(lambda: collections.defaultdict(list))  # vid -> cid -> quotes
    for c in concepts:
        for s in (c.get("sources") or []) + (c.get("guest_sources") or []):
            if isinstance(s, dict) and s.get("video_id"):
                cites[s["video_id"]][c["id"]].append(s.get("quote", ""))
    unit_concepts = collections.defaultdict(list)
    for c in concepts:
        for u in c.get("contributing_units") or []:
            unit_concepts[u].append(c["id"])

    def write(rel, text):
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.rstrip() + "\n")

    os.makedirs(out)
    open(os.path.join(out, MARKER), "w").write(
        "Generated by ClaudeTradingRD/research/python/export_obsidian.py - rebuilt on every run.\n")
    TAG = "ttrades"
    clink = lambda cid: f"[[{cname[cid]}]]" if cid in cname else f"`{cid}`"
    vlink = lambda vid: f"[[{vname[vid]}]]" if vid in vname else f"`{vid}`"

    # ---- videos ------------------------------------------------------------------
    for vid, v in videos.items():
        ts = tstatus.get(vid, {})
        fm = {"tags": [TAG, "ttrades/video"], "video_id": vid, "url": v.get("url"),
              "duration": fmt_dur(v.get("duration")),
              "playlists": [t for t, _ in v["playlists"]], "study_units": unit_of.get(vid, []),
              "transcript": ("ok" if ts.get("ok") else "missing"),
              "concepts_citing": len(cites.get(vid, {}))}
        b = [frontmatter(fm), f"# {v.get('title') or 'Untitled'}", "",
             f"[Watch on YouTube]({v.get('url')}) · {fmt_dur(v.get('duration'))} · `{vid}`", ""]
        b.append("**Playlists:** " + " · ".join(f"[[{pname[t]}]] (#{i})" for t, i in v["playlists"]))
        b.append("**Studied in:** " + (" · ".join(f"[[{u}]]" for u in unit_of.get(vid, [])) or "—"))
        if ts.get("ok"):
            b.append(f"**Transcript:** {ts.get('source', '?')}, {ts.get('words', '?')} words — "
                     f"`ClaudeTradingRD/research/raw/transcripts/{vid}.txt`")
        else:
            reason = ts.get("reason") or ts.get("error") or "not available"
            b.append(f"**Transcript:** none — {reason}")
        b += ["", f"## Concepts citing this video ({len(cites.get(vid, {}))})", ""]
        for cid, quotes in sorted(cites.get(vid, {}).items(), key=lambda kv: cname.get(kv[0], kv[0])):
            b.append(f"- {clink(cid)}")
            b += [f"  - “{q}”" for q in quotes if q]
        if not cites.get(vid):
            b.append("_No concept cites this video directly (see its study unit for context)._")
        write(f"Videos/{vname[vid]}.md", "\n".join(b))

    # ---- playlists ---------------------------------------------------------------
    for p in playlists:
        fm = {"tags": [TAG, "ttrades/playlist"], "playlist_id": p["playlist_id"],
              "url": p["url"], "video_count": p["video_count"]}
        b = [frontmatter(fm), f"# {p['title']}", "", f"[Open on YouTube]({p['url']}) · "
             f"{p['video_count']} videos · {fmt_dur(sum(v.get('duration') or 0 for v in p['videos']))}", "",
             "| # | Video | Length | Transcript | Study unit | Concepts |", "|---:|---|---:|:---:|---|---:|"]
        for i, v in enumerate(p["videos"], 1):
            ok = "✓" if tstatus.get(v["id"], {}).get("ok") else "✗"
            us = ", ".join(f"[[{u}]]" for u in unit_of.get(v["id"], [])) or "—"
            b.append(f"| {i} | [[{vname[v['id']]}\\|{safe_name(v.get('title') or 'Untitled', 70)}]] | "
                     f"{fmt_dur(v.get('duration'))} | {ok} | {us} | {len(cites.get(v['id'], {}))} |")
        write(f"Playlists/{pname[p['title']]}.md", "\n".join(b))

    # ---- study units -------------------------------------------------------------
    for u in units:
        uid = u["unit_id"]
        fm = {"tags": [TAG, "ttrades/unit"], "unit_id": uid, "playlist": u["playlist"],
              "batch": f"{u['batch']} of {u['of']}", "videos": u["n_videos"],
              "transcripts_present": sum(1 for v in u["videos"] if tstatus.get(v["id"], {}).get("ok")),
              "runtime": fmt_dur(u.get("runtime_sec")), "concepts_contributed": len(unit_concepts[uid])}
        note = open(os.path.join(HERE, "notes", f"{uid}.md"), encoding="utf-8").read()
        b = [frontmatter(fm), f"> [!info] Study unit `{uid}` — [[{pname[u['playlist']]}]], batch "
             f"{u['batch']} of {u['of']}", f"> {u['n_videos']} videos · {fmt_dur(u.get('runtime_sec'))} · "
             f"{len(unit_concepts[uid])} concepts contributed · source `research/notes/{uid}.md`", "",
             "> [!abstract]- Videos in this unit", *[f"> - {vlink(v['id'])}" for v in u["videos"]], "",
             "> [!abstract]- Concepts this unit contributed to",
             *[f"> - {clink(c)}" for c in sorted(unit_concepts[uid], key=lambda c: cname[c])], "",
             link(note)]
        write(f"Study Units/{uid}.md", "\n".join(b))

    # ---- concepts ----------------------------------------------------------------
    for c in concepts:
        fm = {"tags": [TAG, "ttrades/concept", f"ttrades/{c['category']}", f"ttrades/{c['status']}"],
              "concept_id": c["id"], "category": c["category"], "status": c["status"],
              "voice": c.get("voice"), "aliases": [c["id"], *(c.get("aliases") or [])],
              "draft_count": c.get("draft_count"), "source": f"research/{c['_file']}"}
        if c.get("voice_playlist"):
            fm["voice_playlist"] = c["voice_playlist"]
        b = [frontmatter(fm), f"# {c['name']}", "",
             f"`{c['id']}` · **{c['category']}** · status **{c['status']}** · voice **{c.get('voice')}**", ""]
        for key, title in SECTION_ORDER:
            val = c.get(key)
            if val in (None, [], {}, ""):
                continue
            b += [f"## {title}", ""]
            if key == "detection_rules" and isinstance(val, list):
                b += [f"{i}. {r}" if not isinstance(r, (dict, list)) else f"{i}.\n{render(r, 1)}"
                      for i, r in enumerate(val, 1)]
            elif isinstance(val, (dict, list)):
                b.append(render(val))
            else:
                b.append(str(val))
            b.append("")
        for key in [k for k in c if k not in HANDLED and not k.startswith("_")]:
            b += [f"## {key.replace('_', ' ').title()}", "", render(c[key]) if isinstance(c[key], (dict, list)) else str(c[key]), ""]
        for key, title in (("sources", "Sources"), ("guest_sources", "Guest sources")):
            srcs = c.get(key) or []
            if not srcs:
                continue
            b += [f"## {title} ({len(srcs)})", ""]
            for s in srcs:
                if isinstance(s, dict):
                    q = f" — “{s['quote']}”" if s.get("quote") else ""
                    extra = {k: x for k, x in s.items() if k not in ("video_id", "title", "quote")}
                    b.append(f"- {vlink(s.get('video_id'))}{q}" + (f" ({', '.join(f'{k}: {x}' for k, x in extra.items())})" if extra else ""))
                else:
                    b.append(f"- {s}")
            b.append("")
        if c.get("related"):
            b += ["## Related", "", " · ".join(clink(r) for r in c["related"]), ""]
        if c.get("contributing_units"):
            b += ["## Contributing study units", "", " · ".join(f"[[{u}]]" for u in c["contributing_units"]), ""]
        write(f"Concepts/{c['category'].title()}/{cname[c['id']]}.md", "\n".join(b))

    # ---- reports -----------------------------------------------------------------
    for r, n in rname.items():
        text = open(os.path.join(HERE, r), encoding="utf-8").read()
        fm = {"tags": [TAG, "ttrades/report"], "source": f"ClaudeTradingRD/research/{r}"}
        write(f"Reports/{n}.md", frontmatter(fm) + "\n" + link(text))

    # ---- map of contents ---------------------------------------------------------
    st = collections.Counter(c["status"] for c in concepts)
    vo = collections.Counter(c.get("voice") for c in concepts)
    ok = sum(1 for v in videos if tstatus.get(v, {}).get("ok"))
    b = [frontmatter({"tags": [TAG, "moc"]}), "# 📚 TTrades Library", "",
         "> [!warning] Generated — do not edit inside this folder",
         "> Rebuilt from `ClaudeTradingRD/research/` by `python/export_obsidian.py`; every run deletes and",
         "> recreates this folder. Put commentary in [[TTrades Corpus]] or other notes outside it.", "",
         "The complete TTrades_edu research corpus: every playlist, every video, every study note, every",
         "concept and every report. Overview and verdicts: [[TTrades Corpus]] · [[TTrades Method Spec]].", "",
         "| | |", "|---|---|",
         f"| playlists | {len(playlists)} |", f"| unique videos | {len(videos)} ({ok} with transcripts) |",
         f"| study units | {len(units)} |",
         f"| concepts | {len(concepts)} — " + " · ".join(f"{k} {v}" for k, v in st.most_common()) + " |",
         "| voice | " + " · ".join(f"{k} {v}" for k, v in vo.most_common()) + " |", "",
         "> [!important] Phase 2 changed the headline — read [[Report - RESUME]] before acting on any finding.", "",
         "## Start here", "", "- [[Report - RESUME]] — project state, the authority",
         "- [[Report - ttrades_method_spec]] — the method as buildable rules",
         "- [[Report - concepts INDEX]] — all 505 concepts in one table", "",
         "## Playlists", ""]
    for p in sorted(playlists, key=lambda p: -p["video_count"]):
        b.append(f"- [[{pname[p['title']]}]] — {p['video_count']} videos")
    b += ["", "## Study units", ""]
    for u in units:
        b.append(f"- [[{u['unit_id']}]] — {u['playlist']} ({u['batch']}/{u['of']}), {u['n_videos']} videos, "
                 f"{len(unit_concepts[u['unit_id']])} concepts")
    b += ["", "## Concepts by category", ""]
    bycat = collections.defaultdict(list)
    for c in concepts:
        bycat[c["category"]].append(c)
    for cat in sorted(bycat):
        b += [f"### {cat.title()} ({len(bycat[cat])})", ""]
        for s in ("specified", "underspecified", "contested"):
            xs = sorted((c for c in bycat[cat] if c["status"] == s), key=lambda c: cname[c["id"]])
            if xs:
                b.append(f"**{s}** ({len(xs)}): " + " · ".join(f"[[{cname[c['id']]}]]" for c in xs))
                b.append("")
    b += ["## Reports", ""] + [f"- [[{n}]]" for n in sorted(rname.values())]
    write(f"{OUT_NAME}.md", "\n".join(b))

    n = sum(len(fs) for _, _, fs in os.walk(out)) - 1
    print(f"wrote {n} notes to {out}")


if __name__ == "__main__":
    main()

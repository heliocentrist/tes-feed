# tes-feed — Reading List RSS Feed

A static RSS feed + HTML index of articles ingested into the user's foam-notes wiki at `C:\Dev\Notes\TechVault\foam-notes`. Published at https://reading.theelderscripts.com.

## Repository layout

- `feed.json` — canonical store of feed items. Hand-curated + auto-synced. **This is the source of truth.**
- `sync_foam_notes.py` — scans `foam-notes/sources/ingested/**/*.md`, parses YAML frontmatter, appends new items to `feed.json` (deduped by URL).
- `generate.py` — reads `feed.json`, writes `public/feed.xml` (RSS 2.0) and `public/index.html` (browser view), sorted newest-first, capped at 200 items.
- `public/` — what gets deployed (static hosting).

## Update workflow

When the user has ingested new sources into foam-notes and wants the feed updated:

```bash
cd C:\Dev\Projects\tes-feed
python sync_foam_notes.py     # appends new foam-notes items to feed.json
python generate.py            # regenerates public/feed.xml + public/index.html
git add -A
git commit -m "Sync: new posts"
git push
```

That's the whole loop. The deploy is whatever points at `public/` (Cloudflare Pages / GitHub Pages / similar — check git history if you need to know exactly).

## How `sync_foam_notes.py` finds foam-notes

The script resolves the foam-notes ingested directory in this order:

1. `FOAM_NOTES_SOURCES` env var (absolute path to `…/sources/ingested`)
2. `FOAM_NOTES_DIR` env var (path to repo root; appends `sources/ingested`)
3. Hard-coded candidates: `C:\Dev\Notes\TechVault\foam-notes\sources\ingested`, `/home/claude/foam-notes/sources/ingested`, then `~/Dev/Notes/TechVault/foam-notes/sources/ingested`.

Add new candidates to `_resolve_foam_sources()` if the user's setup changes; don't hardcode at the call site.

## Item shape in `feed.json`

```json
{
  "title": "...",
  "url": "https://...",       // canonical, used as dedup key
  "summary": "...",            // <=500 chars
  "date": "Fri, 01 May 2026 00:00:00 +0000",  // RFC 822
  "source": "Author Name",     // string; "" if unknown
  "auto": false                // false for foam-notes-derived; manually-added entries also use false
}
```

Dedup is by `url` exact match. If the same article gets reingested under a slightly different URL (utm tags, trailing slash), it will appear twice — fix by editing `feed.json` directly.

## Frontmatter parsing — what works, what doesn't

The sync reads YAML frontmatter from each `*.md` file under `sources/ingested/`. It handles:

- `title:` — used as feed item title; falls back to filename
- `source:` — must start with `http://` or `https://`. **No URL → item skipped.**
- `author:` — string or list. Wikilinks `[[Name]]` and `[Name](url)` are stripped. Common job-title suffixes (Dr., PhD, Senior, CEO, …) are trimmed via `ROLE_PATTERNS`. Twitter handles lose the leading `@`.
- `description:` — short summary; falls back to first non-heading line of the body.
- `created:` — `YYYY-MM-DD` or ISO datetime. Falls back to the file's mtime, which is usually wrong by days — **prefer setting `created` in the source frontmatter.**

Things that *don't* parse cleanly and need post-sync cleanup in `feed.json`:

- **Garbage author wikilinks** like `author: [[the end of this guide you will be able to:]]` (seen in the Anthropic cookbook source). The parser treats this as the author. Edit `feed.json` to set the right name.
- **Inconsistent author handles for the same person** (e.g., `[[ashwingop]]` in Part 2 vs `[[Ashwin Gopinath (@ashwingop)]]` in Part 3). Foam-notes precedent uses the bare handle, but the feed should show a real name. Normalize in `feed.json`.
- **Empty `published:`** and `created:` — the script uses file mtime, which can sort items oddly.

Rule of thumb: after `sync_foam_notes.py`, scan its stdout. If any "+ Added" line shows a weird author (lowercase only, contains `:`, looks like a sentence fragment), open `feed.json` and fix that item before regenerating.

## Manual additions (no foam-notes source)

If the user wants something in the feed that isn't ingested into foam-notes, just edit `feed.json` and append an item with the shape above (`auto: false`). Then run `python generate.py`. Don't invent dates — use the article's actual publish date in RFC 822 form, or the date the user sent it to you.

## What this feed is *not*

- It is not a subscription syncer. Earlier commits had RSS subscriptions (Pragmatic Engineer, ACOUP); those were removed in `0c78ded`. The feed is now driven by foam-notes ingests + occasional manual adds only. Don't reintroduce subscriptions unless the user asks.
- It is not auto-deployed from this repo by Claude — pushing to `main` is what deploys. Always commit *and* push when finishing a sync.

## Sanity-check commands

- Item count: `python -c "import json; print(len(json.load(open('feed.json',encoding='utf-8'))['items']))"`
- List most recent 10 by stored date: `python -c "import json; d=json.load(open('feed.json',encoding='utf-8')); [print(it['date'][:16], '|', it['source'][:25], '|', it['title'][:60]) for it in d['items'][-10:]]"`
- Find duplicates by URL: `python -c "import json,collections; d=json.load(open('feed.json',encoding='utf-8')); c=collections.Counter(i['url'] for i in d['items']); [print(u) for u,n in c.items() if n>1]"`

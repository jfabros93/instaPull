# Candid Image Review

Review Made Goods' approved Candid UGC by several tags at once, mark images Keep or Remove
for each site placement (for example `living_room + seating`), and record the photographer.

- **Tag filter:** Must have all (AND), at least one (OR), Exclude (NOT), plus presets for the
  wall-candid sections (Category, Palette, Material) and hints for variant spellings
  (`grey`/`gray`, `living_room`/`living-room`).
- **Shared marks:** Keep/Remove and notes are saved per placement and shared with the team.
  Export the removal list as CSV.
- **Tag QC:** in an image's detail view, flag wrong tags to remove and add missing ones. Changes
  are saved per image and shared with the team, and can be exported as CSV. The app doesn't
  write to Candid; each change clears once Candid's feed shows it.
- **Photographer credit:** read from the caption (📸, Photo by, Photography:, Shot by, …),
  or entered by the team.

## How it works

| Path | What it does |
| --- | --- |
| `index.html` | The whole interface. Images load from Candid's CDN (`?w=` picks the size). |
| `api/catalog.py` | Reads the Candid feed live and caches it at Vercel's edge for 15 minutes. |
| `api/state.py` | Reads and writes the team's marks. Needs the team password. |
| `lib/candid.py` | Fetches and shapes the feed. `python3 lib/candid.py` prints counts. |
| `lib/photographer.py` | Finds the photographer credit in a caption. |
| `lib/store.py` | Keeps marks in Upstash Redis (or `.local-state.json` when run locally). |
| `seed.json` | Marks carried over from the first version of the app, loaded once. |

## Vercel setup

1. Import this repo as a Vercel project (no framework, no build command).
2. **Storage → Upstash for Redis**: create a free database and connect it to the project.
   This adds `KV_REST_API_URL` and `KV_REST_API_TOKEN`.
3. **Settings → Environment Variables**: add `TEAM_PASSWORD` (the password the team types in).
4. Redeploy so the new variables take effect.

## Run locally

```bash
python3 dev_server.py
```

Then open http://localhost:3000 and sign in with the password `dev`. Python 3.9+ and no
packages needed.

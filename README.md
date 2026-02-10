# MD-Easy

A small Markdown doc server with a **refresh hook** for AI-updated documentation. Use it so users can browse plans, docs, and agent `.md` files while agents edit them. The UI stays in sync and **keeps the user’s place** unless the current document is removed.

## Features

- **Serves `.md` files** from a directory (e.g. project root or `docs/`)
- **Refresh hook**: `POST /refresh` — call when docs change (e.g. from an AI agent) so the UI refetches
- **State preservation**: Current file and scroll position are kept across refreshes; the user is only moved if the current file is removed
- **SSE**: The frontend listens to `/api/events` so it refreshes as soon as the hook is called (no polling)

## Quick start

```bash
# Install and run (serves .md from repo root; run from project root)
pip install -r src/requirements.txt
cd src && DOC_ROOT=.. python server.py
# Open http://localhost:8765
```

With Docker (serve `/path/to/your/docs`):

```bash
docker build -t md-easy .
docker run -p 8765:8765 -v /path/to/your/docs:/docs md-easy
# Open http://localhost:8765
```

Or pull from GitHub Container Registry (after pushing to `main`/`master` or a `v*` tag):

```bash
docker pull ghcr.io/YOUR_ORG/md-easy:latest
docker run -p 8765:8765 -v /path/to/your/docs:/docs ghcr.io/YOUR_ORG/md-easy:latest
```

## Refresh hook (for AI agents)

When your agent (or any process) updates Markdown files, call the refresh hook so the browser view updates without a full reload, and the user’s location is preserved (or they’re sent home only if the current doc was removed).

```bash
# Notify the server that docs changed
curl -X POST http://localhost:8765/refresh

# Optional body (JSON)
curl -X POST http://localhost:8765/refresh -H "Content-Type: application/json" -d '{"reason": "Updated CLAUDE.md"}'
```

**Behavior:**

- **Current file still exists**: Content is refetched, scroll position restored; user stays on the same doc.
- **Current file was removed**: User is taken back to the welcome/index; sidebar is updated.

## API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Single-page app (sidebar + doc viewer) |
| `GET /api/config` | Client config (e.g. `theme` from `THEME` env) |
| `GET /api/files` | List of all `.md` paths under `DOC_ROOT` |
| `GET /api/doc?path=...` | Rendered HTML for one `.md` file |
| `GET /api/version` | Current refresh version (for optional polling) |
| `POST /refresh` | **Refresh hook** — bumps version and notifies SSE clients |
| `GET /api/events` | Server-Sent Events stream for refresh notifications |

## GitHub builds

Pushes to `main`/`master` and version tags (`v*`) build the image and push to [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry). Image tags:

- `latest` — built from the default branch
- `sha-<short-sha>` — git commit (e.g. `sha-a1b2c3d`)
- `<branch>` — branch name for non-default branches
- `v1.0.0`, `1.0`, `1` — from semver tags

## Theming

Set the **`THEME`** env var (or pass `?theme=` in the URL) to pick a design:

| Theme | Description |
|-------|-------------|
| `default` | Dark UI with purple accent |
| `homebrew` | Homebrew CLI–style: green on black |
| `solarized-light` | Solarized light palette |
| `solarized-dark` | Solarized dark palette |

**Docker:**

```bash
docker run -p 8765:8765 -e THEME=homebrew -v /path/to/docs:/docs md-easy
docker run -p 8765:8765 -e THEME=solarized-dark -v /path/to/docs:/docs md-easy
```

**URL override:** Open `http://localhost:8765/?theme=solarized-light` to try a theme without changing env.

## Environment

- **`DOC_ROOT`** — Directory to scan and serve `.md` from (default: current directory).
- **`PORT`** — Server port (default: `8765`).
- **`THEME`** — `default` \| `homebrew` \| `solarized-light` \| `solarized-dark` (default: `default`).

## State preservation

- **URL**: Current document is encoded in the hash, e.g. `#/docs/plan.md`.
- **Scroll**: Scroll position per document is stored in `sessionStorage` and restored after refresh.
- **On refresh**: File list and current doc are refetched; if the current path is still in the list, the doc is reloaded and scroll restored; otherwise the user is sent to the index.

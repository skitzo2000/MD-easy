# MD-Easy

A small Markdown doc server with a **refresh hook** for AI-updated documentation. Use it so users can browse plans, docs, and agent `.md` files while agents edit them. The UI stays in sync and **keeps the user’s place** unless the current document is removed.

## Features

- **Serves `.md` files** from a directory (e.g. project root or `docs/`)
- **Refresh hook**: `POST /refresh` — call when docs change (e.g. from an AI agent) so the UI refetches
- **State preservation**: Current file and scroll position are kept across refreshes; the user is only moved if the current file is removed
- **SSE**: The frontend listens to `/api/events` so it refreshes as soon as the hook is called (no polling)
- **Working links**: Relative `.md` links in documents are rewritten to open in the doc viewer (default base URL: `http://localhost:PORT`)
- **Section links**: In-doc and cross-doc links with fragments (e.g. `[Section](other.md#section-id)`) open the doc and scroll to the heading; headings get slugified IDs from the TOC extension
- **Navigate + highlight**: The refresh hook can optionally tell the viewer to open a specific path and section and briefly highlight it (for AI “look here” flows)

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

**Security:** If you set the `REFRESH_API_KEY` environment variable, `POST /refresh` requires authentication. Provide the key via **`X-API-Key: <your-key>`** or **`Authorization: Bearer <your-key>`**. If `REFRESH_API_KEY` is not set, the refresh endpoint remains open (fine for local use; set the key for exposed instances).

```bash
# Notify the server that docs changed (no key required if REFRESH_API_KEY is unset)
curl -X POST http://localhost:8765/refresh

# With API key (when REFRESH_API_KEY is set)
curl -X POST http://localhost:8765/refresh -H "X-API-Key: your-secret-key"
curl -X POST http://localhost:8765/refresh -H "Authorization: Bearer your-secret-key"

# Optional body (JSON)
curl -X POST http://localhost:8765/refresh -H "Content-Type: application/json" -H "X-API-Key: your-secret-key" -d '{"reason": "Updated CLAUDE.md"}'

# Refresh and tell the viewer to open a doc/section and highlight it (for AI agents)
curl -X POST http://localhost:8765/refresh -H "Content-Type: application/json" -d '{"reason": "Updated plan", "navigate_path": "docs/plan.md", "navigate_fragment": "implementation", "highlight": true}'
```

**Body fields:**

- **`reason`** (optional): Human-readable reason for the refresh.
- **`navigate_path`** (optional): After refreshing, open this doc path (e.g. `docs/plan.md`). Requires a path under `DOC_ROOT`.
- **`navigate_fragment`** (optional): Scroll to this heading ID (slug) and briefly highlight it (e.g. `implementation` for `## Implementation`).
- **`highlight`** (optional, default `true`): When `navigate_path` is set, whether to briefly highlight the section (if `navigate_fragment` is also set).

**Behavior:**

- **Current file still exists**: Content is refetched, scroll position restored; user stays on the same doc (unless `navigate_path` is set).
- **If `navigate_path` is set**: Viewer opens that doc (and scrolls to `navigate_fragment` if provided), with a short highlight. Use this so the AI can point the user at a specific section after updating docs.
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
- **`HOST`** — Bind address. If unset, server binds to `127.0.0.1` (localhost only). If set (e.g. `0.0.0.0` for LAN), server binds to that address and **requires** `REFRESH_API_KEY` (startup fails otherwise).
- **`BASE_URL`** — Base URL for doc viewer links (default: `http://localhost:PORT`). Returned in `GET /api/config` as `baseUrl`; used when rewriting `.md` links in rendered docs.
- **`REFRESH_API_KEY`** — Optional when binding to localhost. If set (or when `HOST` is set), `POST /refresh` requires this value in the `X-API-Key` or `Authorization: Bearer` header.

## Section links (for AI and docs)

Headings get slugified `id` attributes (e.g. `## API Reference` → `id="api-reference"`). Use them for in-doc and cross-doc links:

- **In-doc**: `[Section name](#section-id)` — same file, scrolls to the heading and briefly highlights it. Use lowercase, hyphenated IDs (e.g. `#api-reference`).
- **Cross-doc**: `[Section](path/to/doc.md#section-id)` — opens the doc and scrolls to that section. Relative paths are rewritten to the viewer.

Shareable URLs: `{baseUrl}/#/path/to/doc.md#section-id` opens the doc and scrolls to the section.

## State preservation

- **URL**: Current document (and optional section) is encoded in the hash, e.g. `#/docs/plan.md` or `#/docs/plan.md#implementation`.
- **Scroll**: Scroll position per document is stored in `sessionStorage` and restored after refresh (section links override and scroll to the fragment).
- **On refresh**: File list and current doc are refetched; if the current path is still in the list, the doc is reloaded and scroll restored; otherwise the user is sent to the index.

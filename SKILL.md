---
name: md-easy-server
description: Run and use the MD-Easy Markdown doc server; call the refresh hook after editing .md files so the browser view updates. Use when serving project docs for browsing, when an AI edits markdown and the user has the doc viewer open, or when the user mentions MD-Easy, refresh hook, or doc server.
---

# MD-Easy server

MD-Easy serves `.md` files from a directory and exposes a **refresh hook** so when an agent (or any process) updates markdown, the browser view refetches without a full reload and keeps the user’s place. Links between `.md` files in written content are rewritten so they open in the doc viewer (working links).

## When to use this skill

- The user wants to browse project markdown (plans, CLAUDE.md, docs) while an AI edits them.
- You are editing or creating `.md` files and the user may have the MD-Easy UI open.
- The user asks how to run the doc server or how to trigger a refresh after changes.

## Running the server

**From repo (serve project root as doc root):**
```bash
pip install -r src/requirements.txt
cd src && DOC_ROOT=.. python server.py
# Open http://localhost:8765
```

**Custom doc root and port:**
```bash
DOC_ROOT=/path/to/docs PORT=8765 python src/server.py
```

**Docker:**
```bash
docker run -p 8765:8765 -v /path/to/docs:/docs md-easy
```

**Host and API key:** By default the server binds to **localhost** (`127.0.0.1`) and the refresh hook can be open. If the user sets **`HOST`** (e.g. `HOST=0.0.0.0` to accept LAN connections), the server binds to that address and **requires** `REFRESH_API_KEY` to be set; startup fails otherwise. So: localhost = no key required; non-local binding = API key required.

Key env: `DOC_ROOT`, `PORT` (default `8765`), `THEME`, `HOST` (optional; if set, bind there and require `REFRESH_API_KEY`), `BASE_URL` (optional; default `http://localhost:PORT` — used for link generation), `REFRESH_API_KEY` (see below).

## Calling the refresh hook (after editing markdown)

After you create or modify any `.md` file under the server’s `DOC_ROOT`, call the refresh hook so the UI refetches and stays in sync.

**If `REFRESH_API_KEY` is not set** (e.g. local only):
```bash
curl -X POST http://localhost:8765/refresh
```

**If `REFRESH_API_KEY` is set** (recommended for exposed instances), send the key in one of these headers:
- `X-API-Key: <key>`
- `Authorization: Bearer <key>`

```bash
# Prefer using env so the key is not in command history
curl -X POST http://localhost:8765/refresh -H "X-API-Key: $REFRESH_API_KEY"
# Optional JSON body
curl -X POST http://localhost:8765/refresh -H "X-API-Key: $REFRESH_API_KEY" \
  -H "Content-Type: application/json" -d '{"reason": "Updated CLAUDE.md"}'
```

Use the same host/port the user runs the server on (default `http://localhost:8765`). Without a valid key when `REFRESH_API_KEY` is set, the server returns 401.

## Working links to other .md files

When you write markdown that links to other docs, use **relative paths** so the server can turn them into working doc-viewer links:

- Same directory: `[Other doc](other.md)` or `[Other](./other.md)`.
- Subdirectory: `[Guide](subdir/guide.md)`.
- Parent / root: `[README](../README.md)` or `[Index](/README.md)`.

The server rewrites such links to `{baseUrl}/#/{path}` so they open in the same viewer. By default `baseUrl` is `http://localhost:{PORT}`; if the user runs with a different host (e.g. `HOST=0.0.0.0` and `BASE_URL=http://192.168.1.5:8765`), get the base from `GET /api/config` (`baseUrl`) and use it when you need to output a shareable doc URL. Do not hardcode localhost in shareable links when the server is not on localhost.

## Workflow for AI agents

1. User has MD-Easy running (or you help them start it with the commands above).
2. You edit or create `.md` files under the server’s `DOC_ROOT`. Use relative `.md` links so they work in the viewer.
3. After saving changes, call `POST /refresh` (with `X-API-Key` or `Authorization: Bearer` if the server uses `REFRESH_API_KEY`).
4. The browser view updates; the user’s current file and scroll position are preserved unless that file was removed.

For full API, env vars, and Docker details, see [README.md](README.md).

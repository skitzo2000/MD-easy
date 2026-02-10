"""
MD-Easy — Markdown doc server with refresh hook for AI-updated docs.
Serves .md files; agents call POST /refresh to signal updates; clients preserve place unless doc is removed.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import markdown
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Where to serve .md files from (override with DOC_ROOT env)
DOC_ROOT = Path(os.environ.get("DOC_ROOT", ".")).resolve()
# Theme: default | homebrew | solarized-light | solarized-dark (env THEME)
THEME = (os.environ.get("THEME") or "default").strip().lower()
VALID_THEMES = {"default", "homebrew", "solarized-light", "solarized-dark"}
if THEME not in VALID_THEMES:
    THEME = "default"
if not DOC_ROOT.exists():
    DOC_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MD-Easy", description="MD doc server with refresh hook for agents")

# SSE: when refresh is triggered, notify connected clients
_refresh_event = asyncio.Event()
_refresh_version = 0


def _collect_md_files(base: Path, prefix: str = "") -> list[str]:
    out = []
    try:
        for p in sorted(base.iterdir()):
            rel = f"{prefix}{p.name}" if prefix else p.name
            if p.name.startswith(".") or p.name == "node_modules":
                continue
            if p.is_file() and p.suffix.lower() == ".md":
                out.append(rel)
            elif p.is_dir():
                out.extend(_collect_md_files(p, f"{rel}/"))
    except PermissionError:
        pass
    return out


def _safe_path(subpath: str) -> Path:
    """Resolve path under DOC_ROOT; forbid traversal."""
    subpath = subpath.lstrip("/").replace("..", "")
    return (DOC_ROOT / subpath).resolve()


def _under_root(p: Path) -> bool:
    return p == DOC_ROOT or DOC_ROOT in p.parents


@app.get("/api/config")
def get_config():
    """Theme and client config; theme is from env THEME (or default)."""
    return {"theme": THEME}


@app.get("/api/files")
def list_files():
    """List all .md files under DOC_ROOT (recursive)."""
    return {"files": _collect_md_files(DOC_ROOT), "version": _refresh_version}


@app.get("/api/doc")
def get_doc(path: str = ""):
    """Get content of one .md file. Returns HTML-rendered body and raw path for client state."""
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="path required")
    full = _safe_path(path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    if not _under_root(full):
        raise HTTPException(status_code=403, detail="forbidden")
    raw = full.read_text(encoding="utf-8", errors="replace")
    html = markdown.markdown(raw, extensions=["extra", "codehilite", "toc"])
    return {"path": path, "html": html, "raw": raw}


@app.get("/api/version")
def get_version():
    """Current refresh version; clients poll or use SSE to detect when to refetch."""
    return {"version": _refresh_version}


class RefreshBody(BaseModel):
    reason: str | None = None


@app.post("/refresh")
def refresh_hook(body: RefreshBody | None = None):
    """
    Refresh hook: call this when docs are updated (e.g. from an AI agent).
    Bumps version and wakes SSE listeners so the UI refetches while preserving
    the user's current location unless that file was removed.
    """
    global _refresh_version
    _refresh_version += 1
    _refresh_event.set()
    _refresh_event.clear()
    return {"ok": True, "version": _refresh_version, "reason": getattr(body, "reason", None) or ""}


@app.get("/api/events")
async def sse_events():
    """Server-Sent Events: stream refresh notifications so the client can refetch without polling."""
    from fastapi.responses import StreamingResponse

    async def stream():
        last = _refresh_version
        while True:
            try:
                await asyncio.wait_for(_refresh_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                yield f"data: {{\"ping\": true}}\n\n"
                continue
            if _refresh_version != last:
                last = _refresh_version
                yield f"data: {{\"version\": {last}}}\n\n"
    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_static_dir = Path(__file__).parent / "static"
app.mount("/themes", StaticFiles(directory=_static_dir / "themes"), name="themes")


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the single-page app."""
    return (_static_dir / "index.html").read_text(encoding="utf-8")


# Optional: serve raw .md for debugging
@app.get("/raw/{path:path}", response_class=PlainTextResponse)
def raw_md(path: str):
    full = _safe_path(path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="not found")
    if not _under_root(full):
        raise HTTPException(status_code=403, detail="forbidden")
    return full.read_text(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8765")))

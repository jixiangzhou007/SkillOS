"""Download one official SkillsBench task via GitHub API (git-clone fallback for GFW)."""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "benchflow-ai/skillsbench"
DEFAULT_BRANCH = "main"


def _api_get(url: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "SkillOS-OfficialSkillsBench/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _download_tree(repo: str, tree_sha: str, dest: Path, prefix: str = "") -> int:
    url = f"https://api.github.com/repos/{repo}/git/trees/{tree_sha}?recursive=1"
    data = _api_get(url)
    count = 0
    for item in data.get("tree", []):
        path = item.get("path", "")
        if not path.startswith(prefix):
            continue
        if item.get("type") != "blob":
            continue
        rel = path[len(prefix) :].lstrip("/\\")
        if not rel:
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        blob = _api_get(item["url"])
        content = blob.get("content", "")
        if blob.get("encoding") == "base64":
            out.write_bytes(base64.b64decode(content))
        else:
            out.write_text(content, encoding="utf-8")
        count += 1
    return count


def download_task(
    task_id: str,
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    dest_root: Path | None = None,
) -> Path:
    dest_root = dest_root or ROOT / "vendor" / "skillsbench" / "tasks"
    dest = dest_root / task_id
    dest.mkdir(parents=True, exist_ok=True)

    meta_url = f"https://api.github.com/repos/{repo}/contents/tasks/{task_id}?ref={branch}"
    try:
        meta = _api_get(meta_url)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Task not found: {task_id} ({e})") from e

    if not isinstance(meta, list):
        raise SystemExit(f"Unexpected API response for tasks/{task_id}")

    sha = meta[0].get("sha") if meta else None
    # list dir response doesn't give tree sha directly; fetch parent tree entry
    tree_url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=0"
    # simpler: walk each top-level entry
    n = 0
    for entry in meta:
        name = entry["name"]
        if entry["type"] == "file":
            out = dest / name
            blob = _api_get(entry["url"])
            raw = blob.get("content", "")
            out.write_bytes(base64.b64decode(raw) if blob.get("encoding") == "base64" else raw.encode())
            n += 1
        elif entry["type"] == "dir":
            n += _download_tree(repo, entry["sha"], dest / name, prefix="")

    if not (dest / "task.md").exists():
        raise SystemExit(f"Download incomplete: {dest}/task.md missing ({n} files)")
    print(f"Downloaded {n} files -> {dest}")
    return dest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("task_id", nargs="?", default="citation-check")
    p.add_argument(
        "--dest-root",
        type=Path,
        default=ROOT / "vendor" / "skillsbench" / "tasks",
        help="Parent directory for tasks/<task_id>/",
    )
    args = p.parse_args()
    download_task(args.task_id, dest_root=args.dest_root)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent


def repo_root() -> Path:
    env = os.environ.get("REPO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return _PACKAGE_ROOT.parents[1]


def repo_path(raw: str | Path, root: Path | None = None) -> Path:
    path = Path(str(raw)).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (root or repo_root()) / path


def repo_relative(raw: str | Path, root: Path | None = None) -> str:
    """Return a repo-relative path for artifacts; leave outside-repo paths absolute."""
    base = (root or repo_root()).resolve()
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(base).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def config_for_disk(cfg: dict, root: Path | None = None) -> dict:
    """Copy config with repo-relative paths for committed/local audit files."""
    out = json.loads(json.dumps(cfg))
    exp = out.get("experiment", {})
    if exp.get("out_dir"):
        exp["out_dir"] = repo_relative(exp["out_dir"], root)
    tok = out.get("tokenization", {})
    for key in ("export_root", "mad_root"):
        if tok.get(key):
            tok[key] = repo_relative(tok[key], root)
    return out

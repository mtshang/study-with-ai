import json
import re
from pathlib import Path

DIRECTORIES = ("api", "courses", "skill_mcp")
FILES = (".env", "settings.json", "user.json")

def storage_name(username: str, user_id: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", username.lower())
    slug = re.sub(r"-+", "-", slug).strip("-_")[:32] or "user"
    # Prefix avoids Windows reserved basenames, full UUID provides stable uniqueness.
    return f"u_{slug}--{user_id}"

def user_path(root: Path, dirname: str) -> Path:
    if not re.fullmatch(r"u_[a-z0-9_-]+--[0-9a-f-]{36}", dirname):
        raise ValueError("Invalid storage directory")
    target = (root / dirname).resolve()
    if target.parent != root.resolve():
        raise ValueError("User directory escaped storage root")
    return target

def remove_new_directory(root: Path, dirname: str):
    """Rollback only this operation's known files, never recursively delete arbitrary data."""
    target = user_path(root, dirname)
    for name in FILES:
        (target / name).unlink(missing_ok=True)
    for name in DIRECTORIES:
        child = target / name
        if child.exists(): child.rmdir()
    target.rmdir()

def provision(root: Path, dirname: str, user_id: str):
    root.mkdir(parents=True, exist_ok=True)
    target = user_path(root, dirname)
    target.mkdir(exist_ok=False)
    try:
        for name in DIRECTORIES: (target / name).mkdir()
        (target / ".env").write_text("", encoding="utf-8")
        (target / "settings.json").write_text("{}\n", encoding="utf-8")
        (target / "user.json").write_text(json.dumps({"schema_version": 1, "user_id": user_id}, indent=2) + "\n", encoding="utf-8")
    except Exception:
        remove_new_directory(root, dirname)
        raise

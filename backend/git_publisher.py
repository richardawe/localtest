"""
Deploys the frontend + generated data to the gh-pages branch using
git worktree so the main branch checkout is never disturbed.
"""
import logging
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config import BASE_DIR, FRONTEND_DIR, GITHUB_TOKEN, GITHUB_REPO_URL

log = logging.getLogger(__name__)

DATA_DIR = BASE_DIR / "data"


def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    log.debug("git: %s (cwd=%s)", " ".join(cmd), cwd)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def _authenticated_url() -> str:
    """Inject GitHub token into the remote URL for push auth."""
    if GITHUB_TOKEN and "github.com" in GITHUB_REPO_URL:
        url = GITHUB_REPO_URL.replace("https://", f"https://x-token:{GITHUB_TOKEN}@")
        return url
    return GITHUB_REPO_URL


def _ensure_gh_pages_branch() -> None:
    """Create gh-pages as an orphan branch if it doesn't exist on the remote."""
    result = _run(
        ["git", "ls-remote", "--heads", _authenticated_url(), "gh-pages"],
        cwd=BASE_DIR,
        check=False,
    )
    if "gh-pages" not in result.stdout:
        log.info("Creating orphan gh-pages branch on remote")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _run(["git", "init"], cwd=tmp_path)
            _run(["git", "checkout", "--orphan", "gh-pages"], cwd=tmp_path)
            # Create a minimal index.html so the branch isn't empty
            (tmp_path / "index.html").write_text(
                "<html><body>Deploying...</body></html>", encoding="utf-8"
            )
            _run(["git", "add", "index.html"], cwd=tmp_path)
            _run(
                ["git", "-c", "user.email=deploy@hairtrends.local",
                 "-c", "user.name=HairTrends Deploy",
                 "commit", "-m", "chore: init gh-pages"],
                cwd=tmp_path,
            )
            _run(
                ["git", "remote", "add", "origin", _authenticated_url()],
                cwd=tmp_path,
            )
            _run(["git", "push", "origin", "gh-pages"], cwd=tmp_path)


def publish() -> bool:
    """
    Copies frontend/ + data/ into a gh-pages worktree, commits, and pushes.
    Returns True on success, False on failure.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    worktree_path = BASE_DIR / ".gh-pages-worktree"

    try:
        _ensure_gh_pages_branch()

        # Remove stale worktree if it exists (e.g. from a previous crashed run)
        if worktree_path.exists():
            _run(["git", "worktree", "remove", "--force", str(worktree_path)],
                 cwd=BASE_DIR, check=False)
            shutil.rmtree(worktree_path, ignore_errors=True)

        # Fetch latest gh-pages
        _run(
            ["git", "fetch", _authenticated_url(), "gh-pages:refs/remotes/origin/gh-pages"],
            cwd=BASE_DIR, check=False,
        )

        # Add worktree on gh-pages branch
        _run(
            ["git", "worktree", "add", str(worktree_path), "origin/gh-pages"],
            cwd=BASE_DIR,
        )

        # Copy frontend source files
        for item in FRONTEND_DIR.iterdir():
            dest = worktree_path / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Copy generated data
        dest_data = worktree_path / "data"
        if dest_data.exists():
            shutil.rmtree(dest_data)
        if DATA_DIR.exists():
            shutil.copytree(DATA_DIR, dest_data)

        # Copy robots.txt if present
        robots = FRONTEND_DIR / "robots.txt"
        if robots.exists():
            shutil.copy2(robots, worktree_path / "robots.txt")

        # Commit
        _run(["git", "add", "-A"], cwd=worktree_path)

        status = _run(["git", "status", "--porcelain"], cwd=worktree_path)
        if not status.stdout.strip():
            log.info("No changes to deploy — gh-pages is already up to date")
            return True

        _run(
            ["git",
             "-c", "user.email=deploy@hairtrends.local",
             "-c", "user.name=HairTrends Deploy",
             "commit", "-m", f"deploy: {timestamp}"],
            cwd=worktree_path,
        )

        # Push
        push_result = _run(
            ["git", "push", _authenticated_url(), "HEAD:gh-pages"],
            cwd=worktree_path,
            check=False,
        )
        if push_result.returncode != 0:
            log.error("Push failed: %s", push_result.stderr)
            return False

        log.info("Deployed to gh-pages at %s", timestamp)
        return True

    except Exception as e:
        log.error("git_publisher.publish() failed: %s", e, exc_info=True)
        return False
    finally:
        # Always clean up the worktree
        if worktree_path.exists():
            _run(["git", "worktree", "remove", "--force", str(worktree_path)],
                 cwd=BASE_DIR, check=False)
            shutil.rmtree(worktree_path, ignore_errors=True)

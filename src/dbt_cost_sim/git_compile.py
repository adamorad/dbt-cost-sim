"""Convenience orchestration: compile a dbt project at two git refs.

Uses `git worktree` so both refs can be compiled without disturbing the
caller's working tree or requiring a `git checkout`, then shells out to
`dbt compile` in each worktree to produce a manifest.json.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class CompileError(RuntimeError):
    """Raised when `git worktree` or `dbt compile` fails for a ref."""


@contextmanager
def _worktree(repo_dir: Path, ref: str) -> Iterator[Path]:
    if shutil.which("git") is None:
        raise CompileError("git is not installed or not on PATH")

    tmp_dir = Path(tempfile.mkdtemp(prefix="dbt-cost-sim-worktree-"))
    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(tmp_dir), ref],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise CompileError(f"git worktree add failed for ref '{ref}': {exc.stderr}") from exc

    try:
        yield tmp_dir
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(tmp_dir)],
            cwd=repo_dir,
            check=False,
            capture_output=True,
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)


def compile_manifest_at_ref(
    repo_dir: str | Path,
    project_subdir: str,
    ref: str,
    dbt_target: str | None = None,
) -> Path:
    """Check out `ref` into a scratch worktree, run `dbt compile`, return the manifest path.

    The returned manifest.json is copied out to its own temp file before the
    worktree is torn down, so it stays readable after this function returns.
    Callers are responsible for cleaning it up (or letting the OS temp
    directory reap it).
    """
    if shutil.which("dbt") is None:
        raise CompileError("dbt is not installed or not on PATH")

    repo_dir = Path(repo_dir)
    with _worktree(repo_dir, ref) as worktree_dir:
        project_dir = worktree_dir / project_subdir
        cmd = ["dbt", "compile", "--project-dir", str(project_dir)]
        if dbt_target:
            cmd += ["--target", dbt_target]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise CompileError(f"dbt compile failed for ref '{ref}': {exc.stderr}") from exc

        manifest_path = project_dir / "target" / "manifest.json"
        if not manifest_path.exists():
            raise CompileError(f"manifest.json not found after compiling ref '{ref}'")

        persisted_dir = Path(tempfile.mkdtemp(prefix="dbt-cost-sim-manifest-"))
        persisted = persisted_dir / f"manifest-{ref.replace('/', '_')}.json"
        persisted.write_bytes(manifest_path.read_bytes())
        return persisted

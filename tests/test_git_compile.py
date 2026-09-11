from __future__ import annotations

import json
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from dbt_cost_sim.git_compile import CompileError, compile_manifest_at_ref


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _run(["git", "init"], cwd=repo_dir)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir)
    _run(["git", "config", "user.name", "Test"], cwd=repo_dir)
    (repo_dir / "dbt_project.yml").write_text("name: fixture_project\n")
    _run(["git", "add", "."], cwd=repo_dir)
    _run(["git", "commit", "-m", "initial"], cwd=repo_dir)
    return repo_dir


def _install_fake_dbt(bin_dir: Path, script_body: str) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_dbt = bin_dir / "dbt"
    fake_dbt.write_text(script_body)
    fake_dbt.chmod(fake_dbt.stat().st_mode | stat.S_IEXEC)


_SUCCEEDING_DBT_SCRIPT = """#!/bin/sh
project_dir=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "--project-dir" ]; then
    project_dir="$arg"
  fi
  prev="$arg"
done
mkdir -p "$project_dir/target"
echo '{"nodes": {}}' > "$project_dir/target/manifest.json"
exit 0
"""

_FAILING_DBT_SCRIPT = """#!/bin/sh
echo "compilation error: model foo.sql has a syntax error" >&2
exit 1
"""


def test_compile_manifest_at_ref_happy_path(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fake_bin = tmp_path / "fakebin"
    _install_fake_dbt(fake_bin, _SUCCEEDING_DBT_SCRIPT)
    monkeypatch.setenv("PATH", f"{fake_bin}:{shutil.os.environ['PATH']}")

    manifest_path = compile_manifest_at_ref(git_repo, ".", "HEAD")

    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text()) == {"nodes": {}}


def test_worktree_is_cleaned_up_after_success(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fake_bin = tmp_path / "fakebin"
    _install_fake_dbt(fake_bin, _SUCCEEDING_DBT_SCRIPT)
    monkeypatch.setenv("PATH", f"{fake_bin}:{shutil.os.environ['PATH']}")

    compile_manifest_at_ref(git_repo, ".", "HEAD")

    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    # Only the main worktree (the repo itself) should remain.
    assert result.stdout.count("worktree ") == 1


def test_worktree_is_cleaned_up_after_dbt_compile_failure(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fake_bin = tmp_path / "fakebin"
    _install_fake_dbt(fake_bin, _FAILING_DBT_SCRIPT)
    monkeypatch.setenv("PATH", f"{fake_bin}:{shutil.os.environ['PATH']}")

    with pytest.raises(CompileError, match="dbt compile failed"):
        compile_manifest_at_ref(git_repo, ".", "HEAD")

    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.count("worktree ") == 1


def test_missing_manifest_after_compile_raises(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # A dbt that exits 0 but never writes a manifest — e.g. a misconfigured project.
    _install_fake_dbt(tmp_path / "fakebin", "#!/bin/sh\nexit 0\n")
    monkeypatch.setenv("PATH", f"{tmp_path / 'fakebin'}:{shutil.os.environ['PATH']}")

    with pytest.raises(CompileError, match="manifest.json not found"):
        compile_manifest_at_ref(git_repo, ".", "HEAD")


def test_bad_ref_raises_compile_error(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _install_fake_dbt(tmp_path / "fakebin", _SUCCEEDING_DBT_SCRIPT)
    monkeypatch.setenv("PATH", f"{tmp_path / 'fakebin'}:{shutil.os.environ['PATH']}")

    with pytest.raises(CompileError, match="git worktree add failed"):
        compile_manifest_at_ref(git_repo, ".", "not-a-real-ref")


def test_missing_dbt_binary_raises_before_touching_git(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "dbt" else "/usr/bin/true")

    with pytest.raises(CompileError, match="dbt is not installed"):
        compile_manifest_at_ref(git_repo, ".", "HEAD")


def test_missing_git_binary_raises(git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "git" else "/usr/bin/true")

    with pytest.raises(CompileError, match="git is not installed"):
        compile_manifest_at_ref(git_repo, ".", "HEAD")

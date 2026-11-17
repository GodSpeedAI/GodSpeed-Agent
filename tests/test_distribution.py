"""Distribution contract: wheel, sdist, container, and default test selection.

Asserts the public agentic_capability_loop adapter ships in built artifacts and
the container copies it before project install. Built-artifact proof lives here;
operator validation reports configuration evidence only.
"""
from __future__ import annotations

import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _uv() -> str:
    uv = shutil.which("uv")
    assert uv is not None, "uv is required to build distribution artifacts"
    return uv


def _build_artifacts(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_uv(), "build", "--wheel", "--sdist", "--out-dir", str(dist)],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return dist


def _top_level_names_in_wheel(wheel: Path) -> set[str]:
    with zipfile.ZipFile(wheel) as archive:
        return {
            name.split("/")[0]
            for name in archive.namelist()
            if "/" in name and not name.startswith(".")
        }


def _top_level_names_in_sdist(sdist: Path) -> set[str]:
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
    top: set[str] = set()
    for name in names:
        parts = name.split("/")
        if len(parts) >= 2:
            top.add(parts[1])
    return top


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_artifacts(tmp_path_factory.mktemp("dist-build"))


def test_wheel_contains_both_packages(dist: Path) -> None:
    wheels = list(dist.glob("*.whl"))
    assert wheels, "no wheel was built"
    top = _top_level_names_in_wheel(wheels[0])
    assert "godspeed_nav" in top
    assert "agentic_capability_loop" in top


def test_sdist_contains_both_packages(dist: Path) -> None:
    sdists = list(dist.glob("*.tar.gz"))
    assert sdists, "no sdist was built"
    top = _top_level_names_in_sdist(sdists[0])
    assert "godspeed_nav" in top
    assert "agentic_capability_loop" in top


@pytest.mark.parametrize("suffix", ["*.whl", "*.tar.gz"])
def test_clean_install_imports_both_packages(dist: Path, suffix: str) -> None:
    artifacts = sorted(dist.glob(suffix))
    assert artifacts, f"no artifact matching {suffix}"
    result = subprocess.run(
        [
            _uv(), "run", "--isolated",
            "--with", str(artifacts[0]),
            "python", "-c", "import agentic_capability_loop, godspeed_nav",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_default_collection_includes_adapter_tests() -> None:
    result = subprocess.run(
        [_uv(), "run", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "agentic_capability_loop/tests/test_v1_contract.py" in result.stdout


def test_dockerfile_copies_adapter_before_project_install() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    copy_line = next(
        (i for i, line in enumerate(dockerfile) if "agentic_capability_loop/" in line and line.strip().startswith("COPY")),
        None,
    )
    install_lines = [
        i for i, line in enumerate(dockerfile)
        if "uv sync --no-dev" in line and "no-install-project" not in line and line.strip().startswith("RUN")
    ]
    assert copy_line is not None, "Dockerfile does not COPY agentic_capability_loop"
    assert install_lines, "Dockerfile has no project install step"
    assert copy_line < install_lines[-1], "adapter must be copied before project install"

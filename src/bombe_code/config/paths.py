from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "bombe-code"

_CONFIG_NAMES = ("bombe.json", "bombe.jsonc")


@dataclass(frozen=True)
class BombePaths:
    data: Path
    config: Path
    state: Path
    cache: Path
    log: Path
    tmp: Path


def get_paths() -> BombePaths:
    dirs = PlatformDirs(appname=APP_NAME, appauthor=False)
    data = Path(dirs.user_data_dir)
    return BombePaths(
        data=data,
        config=Path(dirs.user_config_dir),
        state=Path(dirs.user_state_dir),
        cache=Path(dirs.user_cache_dir),
        log=data / "log",
        tmp=Path(os.environ.get("TMPDIR", "/tmp")) / APP_NAME,
    )


def _find_named(directory: Path) -> Path | None:
    for name in _CONFIG_NAMES:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def _find_in_dir(directory: Path) -> Path | None:
    found = _find_named(directory)
    if found is not None:
        return found
    dot_dir = directory / ".bombe"
    if dot_dir.is_dir():
        return _find_named(dot_dir)
    return None


def _find_home_config() -> Path | None:
    home_bombe = Path.home() / ".bombe"
    if not home_bombe.is_dir():
        return None
    return _find_named(home_bombe)


def discover_config(start: Path) -> Path | None:
    env_dir = os.environ.get("BOMBE_CONFIG_DIR")
    if env_dir:
        found = _find_named(Path(env_dir))
        if found is not None:
            return found

    current = Path(start).resolve()
    for directory in (current, *current.parents):
        found = _find_in_dir(directory)
        if found is not None:
            return found
    return _find_home_config()

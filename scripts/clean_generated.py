"""Remove only reproducible application builds; preserve sessions and tool caches."""

from pathlib import Path
import shutil
from scripts.common import ROOT


def clean(root: Path = ROOT) -> None:
    for relative in ["build", "frontend/dist"]:
        target = root / relative
        if target.is_symlink():
            raise ValueError(f"Refusing generated-directory symlink: {target}")
        if target.exists():
            shutil.rmtree(target)
        print(f"Cleaned {relative}")


if __name__ == "__main__":
    clean()

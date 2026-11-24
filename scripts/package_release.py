from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = ROOT / "release-assets"


def version_string() -> str:
    if os.getenv("GITHUB_REF_TYPE") == "tag":
        return os.getenv("GITHUB_REF_NAME", "v1.1.0")
    sha = os.getenv("GITHUB_SHA", "local")
    return f"dev-{sha[:7]}"


def add_docs_to_zip(archive: zipfile.ZipFile, base: str) -> None:
    for filename in ("README.md", "LICENSE", "docs/MACOS_FIRST_RUN.md", "docs/WINDOWS_FIRST_RUN.md"):
        path = ROOT / filename
        if path.is_file():
            archive.write(path, f"{base}/{Path(filename).name}")


def main() -> None:
    platform_name = os.environ["TURTLE_PLATFORM"].lower()
    arch = os.environ["TURTLE_ARCH"].lower()
    version = version_string()
    OUT.mkdir(parents=True, exist_ok=True)

    if platform_name == "macos":
        app_bundle = DIST / "Turtle.app"
        if not app_bundle.is_dir():
            raise SystemExit(f"PyInstaller macOS app bundle not found: {app_bundle}")
        asset = OUT / f"Turtle-GUI-{version}-macos-{arch}.app.zip"
        if asset.exists():
            asset.unlink()
        subprocess.run(
            ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app_bundle), str(asset)],
            check=True,
        )
    elif platform_name == "windows":
        executable = DIST / "Turtle.exe"
        if not executable.is_file():
            raise SystemExit(f"PyInstaller Windows executable not found: {executable}")
        asset = OUT / f"Turtle-GUI-{version}-windows-{arch}.zip"
        package_dir = f"Turtle-GUI-{version}-windows-{arch}"
        with zipfile.ZipFile(asset, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.write(executable, f"{package_dir}/Turtle.exe")
            add_docs_to_zip(archive, package_dir)
    elif platform_name == "linux":
        executable = DIST / "Turtle"
        if not executable.is_file():
            raise SystemExit(f"PyInstaller Linux executable not found: {executable}")
        asset = OUT / f"Turtle-GUI-{version}-linux-{arch}.tar.gz"
        package_dir = f"Turtle-GUI-{version}-linux-{arch}"
        with tarfile.open(asset, "w:gz") as archive:
            archive.add(executable, arcname=f"{package_dir}/Turtle")
            for filename in ("README.md", "LICENSE", "docs/MACOS_FIRST_RUN.md", "docs/WINDOWS_FIRST_RUN.md"):
                path = ROOT / filename
                if path.is_file():
                    archive.add(path, arcname=f"{package_dir}/{Path(filename).name}")
    else:
        raise SystemExit(f"Unsupported platform: {platform_name}")

    print(f"Created release asset: {asset}")


if __name__ == "__main__":
    main()

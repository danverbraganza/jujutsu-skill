"""Download and cache official jj release binaries from GitHub."""

import os
import platform
import subprocess
import tarfile
import tempfile
from pathlib import Path

RELEASE_URL = "https://github.com/jj-vcs/jj/releases/download/v{version}/jj-v{version}-{target}.tar.gz"


def cache_dir() -> Path:
    return Path(os.environ.get("JJ_EVAL_CACHE", Path.home() / ".cache" / "jj-skill-eval"))


def release_target() -> str:
    system = platform.system()
    if system == "Darwin":
        # platform.machine() says x86_64 under Rosetta, so ask the hardware instead.
        arm = subprocess.run(["sysctl", "-n", "hw.optional.arm64"], capture_output=True, text=True)
        return ("aarch64" if arm.stdout.strip() == "1" else "x86_64") + "-apple-darwin"
    if system == "Linux":
        arch = "aarch64" if platform.machine() in ("aarch64", "arm64") else "x86_64"
        return f"{arch}-unknown-linux-musl"
    raise RuntimeError(f"jj publishes no release binary for {system}")


def ensure_jj(version: str) -> Path:
    """Return the path to a cached jj binary for `version`, downloading it on first use."""
    binary = cache_dir() / f"jj-{version}" / "jj"
    if binary.exists():
        return binary
    binary.parent.mkdir(parents=True, exist_ok=True)
    url = RELEASE_URL.format(version=version, target=release_target())
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / "jj.tar.gz"
        subprocess.run(["curl", "-fsSL", "-o", str(archive_path), url], check=True)
        with tarfile.open(archive_path) as archive:
            member = next(m for m in archive.getmembers() if m.isfile() and Path(m.name).name == "jj")
            staged = binary.with_suffix(".download")
            staged.write_bytes(archive.extractfile(member).read())
    staged.chmod(0o755)
    staged.rename(binary)
    if jj_version(binary) != version:
        raise RuntimeError(f"{url} unpacked to jj {jj_version(binary)}, expected {version}")
    return binary


def jj_version(binary: Path) -> str:
    """`jj 0.46.0-7d38...` -> `0.46.0`."""
    out = subprocess.run([str(binary), "--version"], capture_output=True, text=True, check=True).stdout
    return out.split()[1].split("-")[0]

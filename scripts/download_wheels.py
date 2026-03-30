#!/usr/bin/env python3
"""
Download all wheels needed for offline/portable installation.

Creates:
  vendor/
    common/       - All non-torch dependencies (shared between CPU/GPU)
    cpu/           - PyTorch CPU-only wheels
    gpu/           - PyTorch CUDA wheels + flash-attn

Run this on an internet-connected machine, then zip the whole repo
for transfer to offline machines.

Usage:
    python scripts/download_wheels.py
    python scripts/download_wheels.py --platform win_amd64
    python scripts/download_wheels.py --platform manylinux2014_x86_64
    python scripts/download_wheels.py --python 3.12
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
VENDOR = ROOT / "vendor"

TORCH_VERSION = "2.6.0"
FLASH_ATTN_VERSION = "2.7.3"
CUDA_SUFFIX = "cu124"  # CUDA 12.4 index for torch
PYTHON_TAG = f"cp{sys.version_info.major}{sys.version_info.minor}"


def run(cmd: list[str], desc: str = ""):
    print(f"\n{'='*60}")
    print(f"  {desc or ' '.join(cmd[:5])}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"WARNING: Command failed (exit {result.returncode}), continuing...")
    return result.returncode


def download_common_wheels(plat: str, python_version: str):
    """Download all non-torch dependencies."""
    dest = VENDOR / "common"
    dest.mkdir(parents=True, exist_ok=True)

    req_file = ROOT / "requirements.txt"
    run([
        sys.executable, "-m", "pip", "download",
        "-r", str(req_file),
        "--dest", str(dest),
        "--platform", plat,
        "--python-version", python_version,
        "--only-binary=:all:",
        "--no-deps",
    ], f"Downloading common deps → vendor/common/")

    # Also download deps-of-deps (with deps this time, excluding torch)
    run([
        sys.executable, "-m", "pip", "download",
        "-r", str(req_file),
        "--dest", str(dest),
        "--platform", plat,
        "--python-version", python_version,
        "--only-binary=:all:",
    ], f"Downloading common deps (with transitive) → vendor/common/")


def download_cpu_wheels(plat: str, python_version: str):
    """Download PyTorch CPU wheels."""
    dest = VENDOR / "cpu"
    dest.mkdir(parents=True, exist_ok=True)

    run([
        sys.executable, "-m", "pip", "download",
        f"torch=={TORCH_VERSION}+cpu",
        "--dest", str(dest),
        "--platform", plat,
        "--python-version", python_version,
        "--only-binary=:all:",
        "--index-url", "https://download.pytorch.org/whl/cpu",
    ], f"Downloading PyTorch CPU → vendor/cpu/")


def download_gpu_wheels(plat: str, python_version: str):
    """Download PyTorch CUDA + flash-attn wheels."""
    dest = VENDOR / "gpu"
    dest.mkdir(parents=True, exist_ok=True)

    # PyTorch with CUDA
    run([
        sys.executable, "-m", "pip", "download",
        f"torch=={TORCH_VERSION}",
        "--dest", str(dest),
        "--platform", plat,
        "--python-version", python_version,
        "--only-binary=:all:",
    ], f"Downloading PyTorch CUDA → vendor/gpu/")

    # flash-attn (may fail on some platforms — that's OK)
    ret = run([
        sys.executable, "-m", "pip", "download",
        f"flash-attn=={FLASH_ATTN_VERSION}",
        "--dest", str(dest),
        "--no-build-isolation",
        "--only-binary=:all:",
    ], f"Downloading flash-attn → vendor/gpu/ (optional)")

    if ret != 0:
        print("Note: flash-attn wheel not available as pre-built binary.")
        print("GPU mode will use eager attention (still fast, just not as fast).")


def download_for_current_platform():
    """Simpler approach: download wheels for the current platform using pip directly."""
    for subdir in ["common", "cpu", "gpu"]:
        (VENDOR / subdir).mkdir(parents=True, exist_ok=True)

    # Common deps
    run([
        sys.executable, "-m", "pip", "download",
        "-r", str(ROOT / "requirements.txt"),
        "--dest", str(VENDOR / "common"),
    ], "Downloading common dependencies")

    # CPU torch
    run([
        sys.executable, "-m", "pip", "download",
        f"torch=={TORCH_VERSION}+cpu",
        "--dest", str(VENDOR / "cpu"),
        "--index-url", "https://download.pytorch.org/whl/cpu",
    ], "Downloading PyTorch CPU")

    # GPU torch
    run([
        sys.executable, "-m", "pip", "download",
        f"torch=={TORCH_VERSION}",
        "--dest", str(VENDOR / "gpu"),
    ], "Downloading PyTorch CUDA")

    # flash-attn (optional)
    run([
        sys.executable, "-m", "pip", "download",
        f"flash-attn=={FLASH_ATTN_VERSION}",
        "--dest", str(VENDOR / "gpu"),
        "--no-build-isolation",
    ], "Downloading flash-attn (optional)")


def show_summary():
    """Print size summary of vendor directory."""
    print(f"\n{'='*60}")
    print("  Vendor directory summary")
    print(f"{'='*60}")
    total = 0
    for subdir in ["common", "cpu", "gpu"]:
        path = VENDOR / subdir
        if not path.exists():
            continue
        files = list(path.iterdir())
        size = sum(f.stat().st_size for f in files if f.is_file())
        total += size
        print(f"  vendor/{subdir:8s}: {len(files):3d} files, {size / (1024**2):8.1f} MB")
    print(f"  {'TOTAL':17s}: {total / (1024**2):8.1f} MB")
    print()
    print("Portable package is ready.")
    print("Zip the entire repo folder and transfer to offline machines.")
    print("Run start_windows.bat or start_linux.sh with:")
    print("  start_windows.bat          (auto-detect GPU/CPU)")
    print("  start_windows.bat --cpu    (force CPU)")
    print("  start_windows.bat --gpu    (force GPU)")


def main():
    parser = argparse.ArgumentParser(description="Download wheels for offline portable installation")
    parser.add_argument("--platform", default=None,
                        help="Target platform (e.g. win_amd64, manylinux2014_x86_64). Default: current platform")
    parser.add_argument("--python", default=None,
                        help="Python version (e.g. 3.12). Default: current version")
    args = parser.parse_args()

    print("DeepSeek-OCR-2 Portable Package Builder")
    print(f"Vendor directory: {VENDOR}")
    print()

    if args.platform:
        python_ver = args.python or f"{sys.version_info.major}.{sys.version_info.minor}"
        download_common_wheels(args.platform, python_ver)
        download_cpu_wheels(args.platform, python_ver)
        download_gpu_wheels(args.platform, python_ver)
    else:
        download_for_current_platform()

    show_summary()


if __name__ == "__main__":
    main()

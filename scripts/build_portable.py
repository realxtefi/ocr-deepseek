#!/usr/bin/env python3
"""
Build a fully portable, offline-ready package.

This script:
1. Downloads all Python wheels (CPU + GPU torch, all dependencies)
2. Downloads the DeepSeek-OCR-2 model (~6GB)
3. Builds the frontend (if Node.js available)
4. Creates a zip file ready for transfer to offline machines

Usage:
    python scripts/build_portable.py
    python scripts/build_portable.py --no-model       # Skip model download (lighter package)
    python scripts/build_portable.py --no-frontend     # Skip frontend build
    python scripts/build_portable.py --output my_package.zip
"""

import argparse
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
IS_WINDOWS = platform.system() == "Windows"


def run(cmd, desc="", cwd=None, shell=False):
    print(f"\n>>> {desc or ' '.join(str(c) for c in cmd[:6])}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell)
    return result.returncode == 0


def step_download_wheels():
    """Download all wheels for portable installation."""
    print("\n" + "=" * 60)
    print("  Step 1: Downloading Python wheels")
    print("=" * 60)
    return run(
        [sys.executable, str(ROOT / "scripts" / "download_wheels.py")],
        "Downloading all wheels (CPU + GPU torch, dependencies)"
    )


def step_download_model():
    """Download the OCR model."""
    print("\n" + "=" * 60)
    print("  Step 2: Downloading DeepSeek-OCR-2 model (~6GB)")
    print("=" * 60)

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "huggingface-hub"],
            "Installing huggingface-hub")
        from huggingface_hub import snapshot_download

    model_dir = ROOT / "models" / "DeepSeek-OCR-2"
    model_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading to {model_dir}...")
    snapshot_download(
        repo_id="deepseek-ai/DeepSeek-OCR-2",
        local_dir=str(model_dir),
    )
    print("Model downloaded.")
    return True


def step_build_frontend():
    """Build the frontend."""
    print("\n" + "=" * 60)
    print("  Step 3: Building frontend")
    print("=" * 60)

    frontend = ROOT / "frontend"
    if not shutil.which("npm"):
        print("Node.js/npm not found. Skipping frontend build.")
        print("The CLI will still work without the web UI.")
        return True

    # On Windows, npm is a .cmd file and requires shell=True
    run(["npm", "install"], "npm install", cwd=frontend, shell=IS_WINDOWS)
    return run(["npm", "run", "build"], "npm run build", cwd=frontend, shell=IS_WINDOWS)


def step_create_zip(output_path: str):
    """Create the portable zip file."""
    print("\n" + "=" * 60)
    print("  Step 4: Creating portable zip")
    print("=" * 60)

    output = Path(output_path)

    # Directories/files to exclude from zip
    exclude = {
        ".git", "__pycache__", "venv", ".venv", "env",
        "node_modules", ".claude", ".env",
    }
    exclude_extensions = {".pyc", ".pyo"}

    print(f"Creating {output}...")
    total_size = 0

    with zipfile.ZipFile(str(output), "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file():
                continue

            # Check exclusions
            parts = path.relative_to(ROOT).parts
            if any(p in exclude for p in parts):
                continue
            if path.suffix in exclude_extensions:
                continue

            arcname = str(path.relative_to(ROOT))
            zf.write(str(path), arcname)
            total_size += path.stat().st_size

    zip_size = output.stat().st_size
    print(f"Total files size: {total_size / (1024**3):.2f} GB")
    print(f"Compressed zip:   {zip_size / (1024**3):.2f} GB")
    print(f"Output: {output.resolve()}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Build portable offline package")
    parser.add_argument("--no-model", action="store_true",
                        help="Skip model download (lighter package, model must be downloaded on target)")
    parser.add_argument("--no-frontend", action="store_true",
                        help="Skip frontend build")
    parser.add_argument("--no-zip", action="store_true",
                        help="Download wheels and model but don't create zip")
    parser.add_argument("--output", default="deepseek-ocr-portable.zip",
                        help="Output zip filename (default: deepseek-ocr-portable.zip)")
    args = parser.parse_args()

    print("=" * 60)
    print("  DeepSeek-OCR-2 Portable Package Builder")
    print("=" * 60)
    print(f"  Python: {sys.version}")
    print(f"  Root:   {ROOT}")
    print(f"  Model:  {'skip' if args.no_model else 'download'}")
    print(f"  Frontend: {'skip' if args.no_frontend else 'build'}")
    print()

    # Step 1: Wheels
    step_download_wheels()

    # Step 2: Model
    if not args.no_model:
        step_download_model()
    else:
        print("\nSkipping model download (--no-model)")

    # Step 3: Frontend
    if not args.no_frontend:
        step_build_frontend()
    else:
        print("\nSkipping frontend build (--no-frontend)")

    # Step 4: Zip
    if not args.no_zip:
        step_create_zip(args.output)

    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)
    print()
    print("To use on an offline machine:")
    if not args.no_zip:
        print(f"  1. Copy {args.output} to the target machine")
        print(f"  2. Unzip it")
    else:
        print(f"  1. Copy this folder to the target machine")
    print(f"  3. Run: start_windows.bat          (auto-detect)")
    print(f"     Or:  start_windows.bat --gpu     (force GPU)")
    print(f"     Or:  start_windows.bat --cpu     (force CPU)")


if __name__ == "__main__":
    main()

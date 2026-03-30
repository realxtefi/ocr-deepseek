# DeepSeek-OCR-2 Document Processor

Offline-capable document processing application powered by [DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2), a 3B parameter vision-language model specialized for OCR and document understanding. Designed for processing scientific articles, magazines, and research papers with structured metadata extraction.

Works on **Windows, Linux, and macOS** with **GPU acceleration (CUDA)** or **CPU-only** fallback. Ships with a **portable build system** that bundles both CPU and GPU PyTorch — no internet connection required.

---

## Features

- **Multi-format input** — PDF, DOCX, PNG, JPG, TIFF, BMP, WebP
- **Scientific metadata extraction** — title, authors, journal/conference, abstract, DOI, figure descriptions with confidence scores
- **Multiple output formats** — JSON (structured), Markdown, XML
- **Recursive folder processing** — point at any directory, processes all supported files in nested subfolders
- **PDF page selection** — process specific pages (e.g. `1-3,5,7-10`)
- **Configurable parallelism** — sequential by default, scale up with worker threads
- **Web UI** — clean React-based interface for upload, processing, and result viewing
- **CLI** — full-featured command-line interface for scripting and automation
- **GPU/CPU auto-detection** — uses CUDA + flash_attention_2 when available, falls back to eager attention + float32 on CPU
- **Runtime device switching** — switch between GPU and CPU without restarting the app
- **Portable build** — bundle both CPU and GPU torch builds; same package runs on any machine
- **One-click launchers** — `start_windows.bat` / `start_linux.sh` with `--cpu` / `--gpu` / `--auto` flags

---

## Table of Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Installation](#installation)
  - [One-Click (Recommended)](#one-click-recommended)
  - [Manual Installation](#manual-installation)
- [Portable Build](#portable-build)
- [Usage](#usage)
  - [Web UI](#web-ui)
  - [CLI](#cli)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Output Formats](#output-formats)
- [OCR Modes](#ocr-modes)
- [Scientific Metadata Extraction](#scientific-metadata-extraction)
- [DOCX Support](#docx-support)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/realxtefi/ocr-deepseek.git
cd ocr-deepseek

# Windows — double-click or run:
start_windows.bat

# Linux/macOS:
chmod +x start_linux.sh
./start_linux.sh

# Force a specific device:
start_windows.bat --gpu     # Force GPU
start_windows.bat --cpu     # Force CPU
./start_linux.sh --gpu
./start_linux.sh --cpu
```

The launcher will:
1. Create a Python virtual environment
2. Detect GPU via `nvidia-smi` and install the matching PyTorch build
3. Install all dependencies (from `vendor/` offline or from pip)
4. Build the web frontend (if Node.js is available)
5. Start the server at `http://127.0.0.1:8000`

On first use, click **"Download Model"** in the web UI (or run `python -m cli.main setup`) to download the ~6GB model.

---

## Requirements

### Minimum

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.10 or higher |
| **RAM** | 8 GB (CPU mode) |
| **Disk** | ~8 GB (model + dependencies) |
| **OS** | Windows 10/11, Linux, macOS |

### Recommended (GPU)

| Component | Requirement |
|-----------|-------------|
| **GPU** | NVIDIA with 6+ GB VRAM |
| **CUDA** | 11.8 or higher |
| **RAM** | 16 GB |

### Optional

| Component | Purpose |
|-----------|---------|
| **Node.js** (v18+) | Building the web frontend |
| **LibreOffice** | DOCX file conversion |
| **Microsoft Word** | DOCX conversion on Windows (via COM) |

> **Note:** The web UI requires Node.js to build. Without it, the CLI still works fully.

---

## Installation

### One-Click (Recommended)

**Windows:**
```
start_windows.bat              # Auto-detect GPU/CPU
start_windows.bat --gpu        # Force GPU mode
start_windows.bat --cpu        # Force CPU mode
```

**Linux / macOS:**
```bash
chmod +x start_linux.sh
./start_linux.sh               # Auto-detect GPU/CPU
./start_linux.sh --gpu         # Force GPU mode
./start_linux.sh --cpu         # Force CPU mode
```

The launcher uses `nvidia-smi` for hardware detection. If you move a venv that was set up on a CPU machine to a GPU machine (or vice versa), the launcher will automatically reinstall the correct PyTorch version.

### Manual Installation

```bash
# 1. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# 2. Install PyTorch
# GPU (CUDA):
pip install torch==2.6.0
pip install flash-attn==2.7.3 --no-build-isolation    # optional, for faster inference

# CPU only:
pip install torch==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu

# 3. Install dependencies
pip install -r requirements.txt

# 4. Build frontend (optional, requires Node.js)
cd frontend && npm install && npm run build && cd ..

# 5. Download the model (~6GB, one-time)
python -m cli.main setup

# 6. Start the server
python -m cli.main serve
```

---

## Portable Build

Create a fully self-contained package that runs on **completely offline machines**. Bundles both CPU and GPU PyTorch wheels so the same package works on any hardware. Just unzip and run.

### Why Portable?

- Air-gapped / secured networks with no internet access
- Deploying to multiple machines with different hardware (some GPU, some CPU)
- Reproducible environments without depending on pip/PyPI availability
- Transfer via USB drive, shared folder, or internal file server

### Build the Package

On an internet-connected machine:

```bash
# Full portable package (wheels + model + frontend) — ~9GB
python scripts/build_portable.py

# Without model (lighter, download model on target later) — ~3GB
python scripts/build_portable.py --no-model

# Just download wheels into vendor/, don't create zip
python scripts/build_portable.py --no-zip --no-model

# Custom output filename
python scripts/build_portable.py --output my_ocr_package.zip
```

This creates:
```
vendor/
  common/   - All shared dependencies (fastapi, transformers, Pillow, etc.)
  cpu/      - PyTorch CPU-only wheels (~300MB)
  gpu/      - PyTorch CUDA wheels + flash-attn (~2GB)
```

### Deploy to Offline Machine

```bash
# 1. Transfer and unzip
unzip deepseek-ocr-portable.zip -d ocr-deepseek
cd ocr-deepseek

# 2. Run (launcher auto-detects vendor/ and installs from local wheels)
start_windows.bat           # Auto-detect GPU/CPU
start_windows.bat --gpu     # Force GPU
start_windows.bat --cpu     # Force CPU

# Linux:
./start_linux.sh
./start_linux.sh --gpu
./start_linux.sh --cpu
```

The launcher detects the `vendor/` directory and uses `pip install --no-index --find-links vendor/...` — completely offline, no internet needed.

### Portability Matrix

| Scenario | What Happens |
|----------|-------------|
| Built on CPU, run on **CPU** | Installs CPU torch from `vendor/cpu/` |
| Built on CPU, run on **GPU** | Detects `nvidia-smi`, installs GPU torch from `vendor/gpu/` |
| Built on GPU, run on **CPU** | Installs CPU torch from `vendor/cpu/` |
| `--gpu` flag on CPU machine | Installs GPU torch, falls back to CPU if CUDA unavailable at runtime |
| `--cpu` flag on GPU machine | Forces CPU torch (useful for testing/debugging) |
| Moved venv between machines | Launcher detects mismatch, force-reinstalls correct torch |

### Download Wheels Only

If you want to cache wheels without building a full package:

```bash
# Download for current platform
python scripts/download_wheels.py

# Download for a specific target platform
python scripts/download_wheels.py --platform win_amd64 --python 3.12
python scripts/download_wheels.py --platform manylinux2014_x86_64 --python 3.12
```

---

## Usage

### Web UI

Start the server and open `http://127.0.0.1:8000` in your browser:

```bash
python -m cli.main serve
# or with options:
python -m cli.main serve --port 9000 --host 0.0.0.0
```

**Workflow:**
1. **Model Status** — Download and load the model (top card). Select device (Auto/GPU/CPU) from the dropdown. Switch devices at runtime without restarting.
2. **Upload** — Drag-and-drop files or click to browse (PDF, DOCX, images)
3. **Configure** — Set output format (JSON/Markdown/XML), OCR mode (layout/plain), page range, worker count, scientific extraction toggle
4. **Process** — Click "Process" and watch the job queue with live progress
5. **Results** — View structured metadata in a clean card layout, switch to raw output, copy to clipboard, or download

### CLI

```bash
# Show system info (GPU, VRAM, model status, Python version)
python -m cli.main info

# Download model (~6GB, one-time, resumable)
python -m cli.main setup

# Process a single PDF (pages 1-5, JSON output)
python -m cli.main process paper.pdf -f json -p "1-5"

# Process a single image to markdown
python -m cli.main process scan.png -f markdown

# Process a folder recursively with 4 workers, output XML
python -m cli.main process ./papers/ -w 4 -f xml -o ./results/

# Process multiple paths at once
python -m cli.main process paper1.pdf paper2.pdf ./more_papers/

# Process without scientific extraction (raw OCR only)
python -m cli.main process document.pdf --no-scientific

# Plain OCR mode (no layout preservation)
python -m cli.main process document.pdf -m plain

# Force CPU mode
python -m cli.main --device cpu process paper.pdf

# Force GPU mode
python -m cli.main --device cuda process paper.pdf

# Start web server on custom port
python -m cli.main serve --port 9000 --host 0.0.0.0

# Start without auto-opening browser
python -m cli.main serve --no-browser
```

**CLI Reference:**

```
Usage: python -m cli.main [OPTIONS] COMMAND [ARGS]

Global Options:
  --config PATH              Config file path (default: config/default.yaml)
  --model-dir PATH           Model cache directory (default: ./models)
  --device [auto|cuda|cpu]   Force device selection
  --verbose                  Debug logging
  --quiet                    Warnings only

Commands:
  setup     Download and prepare the OCR model
  process   Process files or folders for OCR
  serve     Start the web server (API + frontend)
  info      Show system information
```

**`process` Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `-o, --output PATH` | Output directory | `./output` |
| `-f, --format FORMAT` | `json`, `markdown`, or `xml` | `json` |
| `-m, --mode MODE` | `layout` (preserves structure) or `plain` (text only) | `layout` |
| `-p, --pages RANGE` | PDF page range, e.g. `"1-3,5,7-10"` | All pages |
| `-r / -R` | Recursive / non-recursive folder scan | Recursive |
| `-w, --workers N` | Concurrent worker threads | `1` |
| `--scientific / --no-scientific` | Scientific metadata extraction | Enabled |

---

## Configuration

Default configuration lives in [`config/default.yaml`](config/default.yaml):

```yaml
model:
  model_id: "deepseek-ai/DeepSeek-OCR-2"
  cache_dir: "./models"
  device: "auto"              # auto | cuda | cpu

processing:
  default_ocr_mode: "layout"  # layout | plain
  default_output_format: "json"
  workers: 1
  recursive: true
  scientific_extraction: true
  pdf_dpi: 300                # Resolution for PDF-to-image rendering

converter:
  docx_method: "auto"         # auto | libreoffice | comtypes
  libreoffice_path: null      # Auto-detect from PATH
  temp_dir: null              # System temp directory

server:
  host: "127.0.0.1"
  port: 8000
  auto_open_browser: true

output:
  default_dir: "./output"
```

**Override via CLI flags:**
```bash
python -m cli.main --device cpu --config my_config.yaml process files/
```

**Override via environment variables:**
```bash
export OCR_CONFIG=my_config.yaml
```

Settings can also be changed at runtime through the web UI **Settings** page or the `PUT /api/v1/config` endpoint.

---

## Architecture

```
ocr-deepseek/
├── backend/
│   ├── main.py                 # FastAPI app + static file serving
│   ├── config.py               # Configuration (Pydantic + YAML)
│   ├── api/
│   │   ├── routes.py           # REST API endpoints
│   │   └── schemas.py          # Request/response models
│   ├── model/
│   │   ├── manager.py          # Model lifecycle (download, load, GPU/CPU, singleton)
│   │   └── inference.py        # Thread-safe OCR inference wrapper
│   ├── pipeline/
│   │   ├── orchestrator.py     # Job coordination & batch processing
│   │   ├── converter.py        # PDF/DOCX/image → images conversion
│   │   ├── extractor.py        # Scientific metadata extraction (regex/heuristic)
│   │   └── formatter.py        # JSON / Markdown / XML output
│   ├── workers/
│   │   └── pool.py             # Configurable ThreadPoolExecutor
│   └── utils/
│       ├── file_scanner.py     # Recursive directory scanning
│       └── page_selector.py    # Page range parser ("1-3,5,7-10")
├── cli/
│   └── main.py                 # Click-based CLI (setup, process, serve, info)
├── frontend/                   # Vite + React + TypeScript
│   └── src/
│       ├── App.tsx             # Main app with page routing
│       ├── api.ts              # API client wrapper
│       ├── components/
│       │   ├── FileUpload.tsx      # Drag-and-drop file upload
│       │   ├── JobQueue.tsx        # Live job progress tracking
│       │   ├── ModelStatus.tsx     # Model download/load/device switcher
│       │   ├── ResultViewer.tsx    # Structured + raw result display
│       │   └── SettingsPanel.tsx   # Processing options form
│       └── pages/
│           ├── ProcessPage.tsx     # Main processing workflow
│           └── SettingsPage.tsx    # Global settings
├── scripts/
│   ├── download_wheels.py      # Download CPU+GPU wheels for offline use
│   └── build_portable.py       # Build fully portable zip package
├── config/
│   └── default.yaml            # Default configuration
├── vendor/                     # Bundled wheels (created by build_portable.py)
│   ├── common/                 # Shared dependencies
│   ├── cpu/                    # PyTorch CPU wheels
│   └── gpu/                    # PyTorch CUDA + flash-attn wheels
├── models/                     # Downloaded model cache (gitignored)
├── output/                     # Default output directory (gitignored)
├── start_windows.bat           # One-click Windows launcher (--cpu/--gpu/--auto)
├── start_linux.sh              # One-click Linux/macOS launcher (--cpu/--gpu/--auto)
├── requirements.txt            # Core Python dependencies
├── requirements-gpu.txt        # GPU-specific (torch CUDA + flash-attn)
└── requirements-cpu.txt        # CPU-specific (torch CPU)
```

### Processing Pipeline

```
Input (files / folder + options)
  │
  ▼
File Scanner ─── filter by supported extensions, recursive directory walk
  │
  ▼
Page Selection ─── parse "1-3,5" ranges for PDFs, validate against page count
  │
  ▼
Format Converter
  ├── PDF  → PyMuPDF renders pages to PNG at configurable DPI (default 300)
  ├── DOCX → LibreOffice/Word COM → PDF → PNG
  └── Image → passthrough (validate format, return as-is)
  │
  ▼
Worker Pool ─── ThreadPoolExecutor (1..N workers, default 1)
  │
  ▼
OCR Inference ─── DeepSeek-OCR-2 model (thread-safe behind lock)
  │               Prompt: layout mode or plain mode
  │
  ▼
Page Assembly ─── concatenate per-page results, maintain page boundaries
  │
  ▼
Scientific Extractor ─── regex/heuristic parsing of markdown output
  │                       title, authors, journal, abstract, DOI, figures
  │                       each field with confidence score (0.0-1.0)
  │
  ▼
Output Formatter ─── JSON / Markdown / XML with full metadata
  │
  ▼
Write to disk (CLI) / Return via API (web)
```

### GPU Fallback Chain

The model manager tries loading in this order, falling through on failure:

```
1. flash_attention_2 on CUDA (bf16)     ← fastest, requires flash-attn package
      │ ImportError / build failure
      ▼
2. eager attention on CUDA (bf16)       ← still fast, no flash-attn needed
      │ RuntimeError (OOM / CUDA error)
      ▼
3. eager attention on CPU (float32)     ← slowest, works everywhere
```

This means the app **always works** regardless of GPU availability, CUDA version, or whether flash-attn compiled successfully.

### Key Design Decisions

- **ThreadPoolExecutor** (not multiprocessing) — the GPU model can't be pickled/forked; threads share it behind a lock. Workers parallelize file I/O and conversion while inference stays serialized.
- **Scientific extraction via heuristics** — regex-based parsing on layout-preserving markdown output. No second model pass, keeping it fast. Each field gets a confidence score.
- **Portable dual-torch builds** — `vendor/cpu/` and `vendor/gpu/` ship both torch variants. The launcher uses `nvidia-smi` (no Python needed) for hardware detection and installs the correct one.
- **Frontend served by FastAPI** — after `npm run build`, static files are mounted at `/`. During development, Vite dev server proxies API calls to the backend.

---

## API Reference

All endpoints are prefixed with `/api/v1`.

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | Model status, device info, VRAM usage, download progress |
| `POST` | `/model/download` | Start model download (background task) |
| `POST` | `/model/load` | Load model into memory. Body: `{"device": "auto\|cuda\|cpu"}` |
| `POST` | `/model/unload` | Unload model from memory (free GPU/RAM) |
| `GET` | `/config` | Get current configuration |
| `PUT` | `/config` | Update configuration at runtime |

### Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process/file` | Upload and process a single file (multipart form) |
| `POST` | `/process/folder` | Process a local folder path (JSON body) |

**`/process/file` form fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | File | required | The document to process |
| `output_format` | string | `json` | `json`, `markdown`, or `xml` |
| `ocr_mode` | string | `layout` | `layout` or `plain` |
| `pages` | string | all | Page range for PDFs, e.g. `"1-3,5"` |
| `scientific` | boolean | `true` | Enable scientific metadata extraction |

**`/process/folder` JSON body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `folder_path` | string | required | Path to the folder on the server |
| `recursive` | boolean | `true` | Scan subfolders |
| `output_format` | string | `json` | `json`, `markdown`, or `xml` |
| `ocr_mode` | string | `layout` | `layout` or `plain` |
| `pages` | string | all | Page range for PDFs |
| `scientific` | boolean | `true` | Scientific metadata extraction |
| `workers` | integer | `1` | Concurrent worker threads |
| `output_dir` | string | config default | Output directory path |

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/jobs` | List all jobs with status summary |
| `GET` | `/jobs/{id}` | Get job status, progress, and file results |
| `GET` | `/jobs/{id}/result` | Get full output content for all processed files |
| `DELETE` | `/jobs/{id}` | Cancel a running job |

### Example: End-to-end API usage

```bash
# 1. Check status
curl http://127.0.0.1:8000/api/v1/status

# 2. Load model on GPU
curl -X POST http://127.0.0.1:8000/api/v1/model/load \
  -H "Content-Type: application/json" \
  -d '{"device": "cuda"}'

# 3. Upload and process a PDF
curl -X POST http://127.0.0.1:8000/api/v1/process/file \
  -F "file=@paper.pdf" \
  -F "output_format=json" \
  -F "ocr_mode=layout" \
  -F "pages=1-5" \
  -F "scientific=true"
# Response: {"job_id": "abc-123-..."}

# 4. Poll for progress
curl http://127.0.0.1:8000/api/v1/jobs/abc-123-...

# 5. Get results
curl http://127.0.0.1:8000/api/v1/jobs/abc-123-.../result

# 6. Switch to CPU mode at runtime
curl -X POST http://127.0.0.1:8000/api/v1/model/unload
curl -X POST http://127.0.0.1:8000/api/v1/model/load \
  -H "Content-Type: application/json" \
  -d '{"device": "cpu"}'

# 7. Process a local folder
curl -X POST http://127.0.0.1:8000/api/v1/process/folder \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/path/to/papers", "output_format": "markdown", "workers": 4}'
```

---

## Output Formats

### JSON

Structured output with metadata, per-page text, and confidence scores:

```json
{
  "source_file": "paper.pdf",
  "processed_at": "2026-03-30T12:00:00+00:00",
  "device": "cuda",
  "ocr_mode": "layout",
  "metadata": {
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
    "journal_or_series": "Proceedings of NeurIPS 2017",
    "abstract": "The dominant sequence transduction models...",
    "doi": "10.48550/arXiv.1706.03762",
    "figures": [
      {"number": 1, "caption": "The Transformer model architecture."}
    ],
    "extraction_confidence": {
      "title": 0.95,
      "authors": 0.85,
      "journal_or_series": 0.80,
      "abstract": 0.90,
      "doi": 0.95,
      "figures": 0.85
    }
  },
  "pages": [
    {"page_number": 1, "text": "...full markdown of page 1..."}
  ],
  "raw_text": "...full concatenated text..."
}
```

### Markdown

```markdown
# Attention Is All You Need

**Authors**: Ashish Vaswani, Noam Shazeer, Niki Parmar
**Published in**: Proceedings of NeurIPS 2017
**DOI**: 10.48550/arXiv.1706.03762

## Abstract
The dominant sequence transduction models...

## Full Text
### Page 1
...

---

### Page 2
...

## Figures
### Figure 1
The Transformer model architecture.
```

### XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<document source="paper.pdf" processed="2026-03-30T12:00:00+00:00">
  <metadata>
    <title>Attention Is All You Need</title>
    <authors>
      <author>Ashish Vaswani</author>
      <author>Noam Shazeer</author>
      <author>Niki Parmar</author>
    </authors>
    <journal>Proceedings of NeurIPS 2017</journal>
    <abstract>The dominant sequence transduction models...</abstract>
    <doi>10.48550/arXiv.1706.03762</doi>
    <figures>
      <figure number="1">
        <caption>The Transformer model architecture.</caption>
      </figure>
    </figures>
  </metadata>
  <pages>
    <page number="1">...</page>
    <page number="2">...</page>
  </pages>
</document>
```

---

## OCR Modes

| Mode | Prompt | Best For |
|------|--------|----------|
| **layout** | `<image>\n<\|grounding\|>Convert the document to markdown.` | Scientific papers, structured documents — preserves headings, tables, figures, layout |
| **plain** | `<image>\nFree OCR.` | Simple text extraction, handwritten notes, receipts, plain text documents |

Use **layout** mode (default) for scientific documents. It produces markdown with headings, bold text, and structural markers that the scientific extractor depends on. Use **plain** mode when you only need raw text without structure.

---

## Scientific Metadata Extraction

The extractor parses the layout-preserving OCR output using regex and heuristics. It runs automatically in **layout** mode (disable with `--no-scientific`).

| Field | Extraction Method | Typical Confidence |
|-------|-------------------|--------------------|
| **Title** | First `#` heading or bold text at document top | 80-95% |
| **Authors** | Text between title and abstract, name pattern matching, affiliation stripping | 70-85% |
| **Journal / Conference** | Pattern matching: "Journal of...", "Proceedings of...", IEEE, ACM, Springer, arXiv, etc. | 75-80% |
| **Abstract** | Content following "Abstract" heading/label until next section | 85-90% |
| **DOI** | Regex: `10.\d{4,}/\S+` | 90-95% |
| **Figures** | `Figure N:` / `Fig. N:` patterns with multi-line caption capture | 80-85% |

Each field includes a confidence score (0.0 - 1.0) in the output. Fields that couldn't be identified are set to `null` rather than guessed.

---

## DOCX Support

DOCX files are converted to PDF first, then rendered to images for OCR. The conversion method is auto-detected:

| Platform | Primary Method | Fallback |
|----------|---------------|----------|
| **Windows** | Microsoft Word (COM via `comtypes`) | LibreOffice |
| **Linux** | LibreOffice (`soffice --headless`) | — |
| **macOS** | LibreOffice (`soffice --headless`) | — |

**Installing LibreOffice:**

- **Windows**: Download from [libreoffice.org](https://www.libreoffice.org/download/download/)
- **Ubuntu/Debian**: `sudo apt install libreoffice`
- **macOS**: `brew install --cask libreoffice`

Force a specific method in `config/default.yaml`:
```yaml
converter:
  docx_method: "libreoffice"  # or "comtypes"
  libreoffice_path: "C:\\Program Files\\LibreOffice\\program\\soffice.exe"
```

---

## Performance

Approximate processing times per page (standard A4 scientific paper, 300 DPI, layout mode):

| Device | Time per Page | Notes |
|--------|---------------|-------|
| NVIDIA RTX 3090 (24GB) | ~2-4 sec | flash_attention_2 |
| NVIDIA RTX 3060 (6GB) | ~4-8 sec | eager attention |
| NVIDIA RTX 3060 (6GB) | ~3-6 sec | flash_attention_2 |
| CPU (modern 8-core) | ~30-60 sec | float32 |

**Tips for faster CPU processing:**
- Lower DPI: set `processing.pdf_dpi: 150` in config (trades quality for speed)
- Use `plain` mode instead of `layout` if structure isn't needed
- Process specific pages: `-p "1-5"` instead of entire large PDFs
- Increase workers for folder processing: `-w 4` (parallelizes file I/O, inference stays serial)

---

## Troubleshooting

### Model download fails or is slow

The model is ~6GB. If the download stalls, re-run `python -m cli.main setup`. HuggingFace Hub supports resumable downloads automatically. For portable builds, the model is included in the zip.

### `flash-attn` fails to install on Windows

Building flash-attn from source requires CUDA Toolkit and a C++ compiler (MSVC). If it fails, the app automatically falls back to eager attention (still uses GPU with bf16, slightly slower). You can safely ignore this error.

### CUDA out of memory

The 3B model in bf16 needs ~6GB VRAM. Close other GPU applications. If your GPU has less VRAM:
```bash
python -m cli.main --device cpu process paper.pdf
```
Or switch to CPU in the web UI via the device dropdown.

### CPU-only torch on a GPU machine

If you set up the environment on a CPU machine and moved it to a GPU machine, the launcher will auto-detect this via `nvidia-smi` and reinstall GPU torch. You can also force it:
```bash
start_windows.bat --gpu
# or manually:
pip install torch==2.6.0 --force-reinstall
```

### DOCX conversion fails

Ensure LibreOffice is installed and `soffice` is in your PATH. On Windows, Microsoft Word works automatically if installed. Check:
```bash
python -m cli.main info
soffice --version          # Linux/macOS
```

### Frontend not loading

Build the frontend first:
```bash
cd frontend && npm install && npm run build && cd ..
```
Requires Node.js 18+. Without it, use the CLI instead — all features are available.

### Portable build: wrong platform wheels

The `download_wheels.py` script downloads wheels for the current platform by default. For cross-platform portable builds:
```bash
# Download Windows wheels on a Linux build machine:
python scripts/download_wheels.py --platform win_amd64 --python 3.12
```

---

## License

This project is open source. The DeepSeek-OCR-2 model is released under the [Apache 2.0 License](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2).

## Acknowledgements

- [DeepSeek-AI](https://github.com/deepseek-ai) for the DeepSeek-OCR-2 model
- [oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui) for launcher/portability inspiration

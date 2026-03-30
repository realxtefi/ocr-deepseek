# DeepSeek-OCR-2 Document Processor

Offline-capable document processing application powered by [DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2), a 3B parameter vision-language model specialized for OCR and document understanding. Designed for processing scientific articles, magazines, and research papers with structured metadata extraction.

Works on **Windows, Linux, and macOS** with **GPU acceleration (CUDA)** or **CPU-only** fallback. No internet connection required after initial setup.

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
- **One-click launchers** — `start_windows.bat` / `start_linux.sh` handle everything

---

## Table of Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Installation](#installation)
  - [One-Click (Recommended)](#one-click-recommended)
  - [Manual Installation](#manual-installation)
- [Usage](#usage)
  - [Web UI](#web-ui)
  - [CLI](#cli)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Output Formats](#output-formats)
- [DOCX Support](#docx-support)
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
./start_linux.sh
```

The launcher will:
1. Create a Python virtual environment
2. Detect your GPU and install the correct PyTorch version
3. Install all dependencies
4. Build the web frontend
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
start_windows.bat
```

**Linux / macOS:**
```bash
chmod +x start_linux.sh
./start_linux.sh
```

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
pip install flash-attn==2.7.3 --no-build-isolation

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

## Usage

### Web UI

Start the server and open `http://127.0.0.1:8000` in your browser:

```bash
python -m cli.main serve
```

**Workflow:**
1. **Model Status** — Download and load the model (top card)
2. **Upload** — Drag-and-drop files or click to browse
3. **Configure** — Set output format, OCR mode, page range, worker count
4. **Process** — Click "Process" and watch the job queue
5. **Results** — View structured metadata, raw output, copy or download

### CLI

```bash
# Show system info (GPU, model status)
python -m cli.main info

# Download model
python -m cli.main setup

# Process a single PDF (pages 1-5, JSON output)
python -m cli.main process paper.pdf -f json -p "1-5"

# Process a single image
python -m cli.main process scan.png -f markdown

# Process a folder recursively with 4 workers
python -m cli.main process ./papers/ -w 4 -f json -o ./results/

# Process multiple paths
python -m cli.main process paper1.pdf paper2.pdf ./more_papers/

# Process without scientific extraction
python -m cli.main process document.pdf --no-scientific

# Plain OCR mode (no layout preservation)
python -m cli.main process document.pdf -m plain

# Use CPU explicitly
python -m cli.main --device cpu process paper.pdf

# Start web server on custom port
python -m cli.main serve --port 9000 --host 0.0.0.0
```

**CLI Reference:**

```
Usage: python -m cli.main [OPTIONS] COMMAND [ARGS]

Global Options:
  --config PATH          Config file path (default: config/default.yaml)
  --model-dir PATH       Model cache directory (default: ./models)
  --device [auto|cuda|cpu]  Force device selection
  --verbose              Debug logging
  --quiet                Warnings only

Commands:
  setup     Download and prepare the OCR model
  process   Process files or folders for OCR
  serve     Start the web server
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

Default configuration lives in `config/default.yaml`:

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
  pdf_dpi: 300                # Resolution for PDF rendering

converter:
  docx_method: "auto"         # auto | libreoffice | comtypes
  libreoffice_path: null      # Auto-detect from PATH
  temp_dir: null              # System temp

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

**Override via environment variables** (prefix `OCR_`):
```bash
export OCR_CONFIG=my_config.yaml
```

Settings can also be changed at runtime through the web UI **Settings** page or the `PUT /api/v1/config` endpoint.

---

## Architecture

```
ocr-deepseek/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration system (Pydantic + YAML)
│   ├── api/
│   │   ├── routes.py           # REST API endpoints
│   │   └── schemas.py          # Request/response models
│   ├── model/
│   │   ├── manager.py          # Model download, load, GPU/CPU detection (singleton)
│   │   └── inference.py        # Thread-safe OCR inference wrapper
│   ├── pipeline/
│   │   ├── orchestrator.py     # Job coordination & batch processing
│   │   ├── converter.py        # PDF/DOCX/image → images conversion
│   │   ├── extractor.py        # Scientific metadata extraction
│   │   └── formatter.py        # JSON / Markdown / XML output
│   ├── workers/
│   │   └── pool.py             # Configurable ThreadPoolExecutor
│   └── utils/
│       ├── file_scanner.py     # Recursive directory scanning
│       └── page_selector.py    # Page range parser
├── cli/
│   └── main.py                 # Click-based CLI
├── frontend/                   # Vite + React + TypeScript
│   └── src/
│       ├── App.tsx
│       ├── api.ts              # API client
│       ├── components/         # FileUpload, JobQueue, ResultViewer, etc.
│       └── pages/              # ProcessPage, SettingsPage
├── config/
│   └── default.yaml            # Default configuration
├── start_windows.bat           # One-click Windows launcher
├── start_linux.sh              # One-click Linux/macOS launcher
├── requirements.txt            # Core Python dependencies
├── requirements-gpu.txt        # GPU-specific (torch + flash-attn)
└── requirements-cpu.txt        # CPU-specific (torch CPU)
```

### Processing Pipeline

```
Input (files / folder)
  │
  ▼
File Scanner ─── filters by supported extensions, recursive walk
  │
  ▼
Page Selection ─── parse "1-3,5" ranges for PDFs
  │
  ▼
Format Converter
  ├── PDF  → PyMuPDF renders pages to PNG at configurable DPI
  ├── DOCX → LibreOffice/Word → PDF → PNG
  └── Image → passthrough (validate format)
  │
  ▼
Worker Pool ─── ThreadPoolExecutor (1..N workers)
  │
  ▼
OCR Inference ─── DeepSeek-OCR-2 model (thread-safe, locked)
  │
  ▼
Scientific Extractor ─── regex/heuristic parsing of markdown output
  │                       extracts: title, authors, journal, abstract,
  │                       DOI, figure captions (with confidence scores)
  │
  ▼
Output Formatter ─── JSON / Markdown / XML
  │
  ▼
Write to disk / Return via API
```

### Key Design Decisions

- **ThreadPoolExecutor** (not multiprocessing) — the GPU model can't be forked; threads share it behind a lock. Workers parallelize file I/O and conversion while inference stays serialized.
- **Scientific extraction via heuristics** — regex-based parsing on layout-preserving markdown. No second model pass, so it's fast. Each field gets a confidence score.
- **GPU fallback chain** — tries `flash_attention_2` → falls back to `eager` attention (still on CUDA with bf16) → falls back to CPU with float32.
- **Frontend served by FastAPI** — after `npm run build`, static files are mounted at `/`. During development, Vite proxies API calls.

---

## API Reference

All endpoints are prefixed with `/api/v1`.

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | Model status, device info, VRAM usage |
| `POST` | `/model/download` | Start model download (background task) |
| `POST` | `/model/load` | Load model into memory |
| `GET` | `/config` | Get current configuration |
| `PUT` | `/config` | Update configuration |

### Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process/file` | Upload and process a single file (multipart form) |
| `POST` | `/process/folder` | Process a local folder path (JSON body) |

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/{id}` | Get job status and progress |
| `GET` | `/jobs/{id}/result` | Get job output content |
| `DELETE` | `/jobs/{id}` | Cancel a running job |

### Example: Process a file via API

```bash
# Upload and process
curl -X POST http://127.0.0.1:8000/api/v1/process/file \
  -F "file=@paper.pdf" \
  -F "output_format=json" \
  -F "ocr_mode=layout" \
  -F "pages=1-5" \
  -F "scientific=true"

# Response: {"job_id": "abc-123-..."}

# Check progress
curl http://127.0.0.1:8000/api/v1/jobs/abc-123-...

# Get results
curl http://127.0.0.1:8000/api/v1/jobs/abc-123-.../result
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
  </pages>
</document>
```

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

You can force a specific method in `config/default.yaml`:
```yaml
converter:
  docx_method: "libreoffice"  # or "comtypes"
  libreoffice_path: "C:\\Program Files\\LibreOffice\\program\\soffice.exe"
```

---

## Troubleshooting

### Model download fails or is slow

The model is ~6GB. If the download stalls, re-run `python -m cli.main setup`. HuggingFace Hub supports resumable downloads automatically.

### `flash-attn` fails to install on Windows

Building flash-attn from source requires CUDA Toolkit and a C++ compiler (MSVC). If it fails, the app automatically falls back to eager attention (still uses GPU with bf16). You can ignore this error.

### CUDA out of memory

The 3B model in bf16 needs ~6GB VRAM. Close other GPU applications. If your GPU has less VRAM, use CPU mode:
```bash
python -m cli.main --device cpu process paper.pdf
```

### DOCX conversion fails

Ensure LibreOffice is installed and `soffice` is in your PATH. On Windows, Microsoft Word works automatically if installed. Check your config:
```bash
python -m cli.main info
```

### Frontend not loading

The web UI requires building the frontend first:
```bash
cd frontend && npm install && npm run build && cd ..
```
Requires Node.js 18+. Without it, use the CLI instead.

### Slow processing on CPU

CPU mode processes documents significantly slower than GPU. Tips:
- Reduce DPI: set `processing.pdf_dpi: 150` in config
- Process specific pages: `-p "1-5"` instead of entire PDFs
- Use `plain` mode instead of `layout` if structure isn't needed

---

## OCR Modes

| Mode | Prompt | Best For |
|------|--------|----------|
| **layout** | `<image>\n<\|grounding\|>Convert the document to markdown.` | Scientific papers, structured documents, preserves headings/tables/figures |
| **plain** | `<image>\nFree OCR.` | Simple text extraction, handwritten notes, receipts |

---

## Scientific Metadata Extraction

The extractor parses the layout-preserving OCR output using regex and heuristics:

| Field | Method | Typical Confidence |
|-------|--------|--------------------|
| **Title** | First `#` heading or bold text at top | 80-95% |
| **Authors** | Text between title and abstract, name pattern matching | 70-85% |
| **Journal** | Pattern matching (Journal of..., IEEE, ACM, arXiv, etc.) | 75-80% |
| **Abstract** | Content after "Abstract" heading until next section | 85-90% |
| **DOI** | Regex: `10.\d{4,}/\S+` | 90-95% |
| **Figures** | `Figure N:` / `Fig. N:` patterns with captions | 80-85% |

Each field includes a confidence score (0.0 - 1.0) in the output. Fields that couldn't be identified are set to `null`.

---

## Performance

Approximate processing times per page (measured on standard A4 scientific paper pages):

| Device | Time per Page |
|--------|---------------|
| NVIDIA RTX 3090 | ~2-4 seconds |
| NVIDIA RTX 3060 (6GB) | ~4-8 seconds |
| CPU (modern 8-core) | ~30-60 seconds |

> Times vary based on page complexity, DPI, and OCR mode.

---

## License

This project is open source. The DeepSeek-OCR-2 model is released under the [Apache 2.0 License](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2).

## Acknowledgements

- [DeepSeek-AI](https://github.com/deepseek-ai) for the DeepSeek-OCR-2 model
- [oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui) for launcher inspiration

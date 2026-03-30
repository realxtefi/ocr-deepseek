import logging
import sys
from pathlib import Path

import click

from backend.config import AppConfig, get_config, load_config, set_config

logger = logging.getLogger(__name__)


@click.group()
@click.option("--config", "config_path", default=None, help="Path to config YAML file")
@click.option("--model-dir", default=None, help="Model cache directory")
@click.option("--device", type=click.Choice(["auto", "cuda", "cpu"]), default=None)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--quiet", is_flag=True, default=False)
def cli(config_path, model_dir, device, verbose, quiet):
    """DeepSeek-OCR-2 Document Processor"""
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config(config_path)
    if model_dir:
        config.model.cache_dir = model_dir
    if device:
        config.model.device = device
    set_config(config)


@cli.command()
@click.option("--force", is_flag=True, help="Re-download even if cached")
def setup(force):
    """Download and prepare the OCR model."""
    from backend.model.manager import ModelManager

    config = get_config()
    manager = ModelManager()

    if not force and manager.is_downloaded(config.model.cache_dir):
        click.echo("Model already downloaded.")
        click.echo(f"  Location: {manager.get_model_path(config.model.cache_dir)}")
        return

    click.echo(f"Downloading model: {config.model.model_id}")
    click.echo(f"  Cache dir: {config.model.cache_dir}")
    click.echo("This may take a while (~6GB)...")

    manager.download(config.model.model_id, config.model.cache_dir)
    click.echo("Download complete!")


@cli.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("-o", "--output", "output_dir", default=None, help="Output directory")
@click.option("-f", "--format", "output_format", type=click.Choice(["json", "markdown", "xml"]), default=None)
@click.option("-m", "--mode", "ocr_mode", type=click.Choice(["layout", "plain"]), default=None)
@click.option("-p", "--pages", default=None, help='Page range for PDFs, e.g. "1-3,5"')
@click.option("-r/-R", "--recursive/--no-recursive", default=None)
@click.option("-w", "--workers", type=int, default=None, help="Concurrent workers (default: 1)")
@click.option("--scientific/--no-scientific", default=None)
def process(paths, output_dir, output_format, ocr_mode, pages, recursive, workers, scientific):
    """Process files or folders for OCR."""
    from backend.model.manager import ModelManager
    from backend.pipeline.orchestrator import Orchestrator

    config = get_config()

    output_dir = output_dir or config.output.default_dir
    output_format = output_format or config.processing.default_output_format
    ocr_mode = ocr_mode or config.processing.default_ocr_mode
    recursive = recursive if recursive is not None else config.processing.recursive
    workers = workers or config.processing.workers
    scientific = scientific if scientific is not None else config.processing.scientific_extraction

    manager = ModelManager()

    # Load model if not already loaded
    if not manager.is_loaded():
        click.echo("Loading model...")
        manager.load(config.model.model_id, config.model.cache_dir, config.model.device)
        click.echo(f"Model loaded on {manager.device}")

    orchestrator = Orchestrator(config)

    def on_progress(completed, total, item, result, error):
        if error:
            click.echo(f"  [{completed}/{total}] ERROR: {item} - {error}")
        elif result and result.error:
            click.echo(f"  [{completed}/{total}] ERROR: {result.file_path} - {result.error}")
        else:
            click.echo(f"  [{completed}/{total}] Done: {item}")

    click.echo(f"Processing {len(paths)} path(s) -> {output_dir}")
    click.echo(f"  Format: {output_format} | Mode: {ocr_mode} | Workers: {workers}")

    job = orchestrator.process_batch(
        paths=list(paths),
        output_dir=output_dir,
        output_format=output_format,
        ocr_mode=ocr_mode,
        pages=pages,
        scientific=scientific,
        workers=workers,
        recursive=recursive,
        progress_callback=on_progress,
    )

    click.echo(f"\nCompleted: {job.completed_files}/{job.total_files} files")
    if job.errors:
        click.echo(f"Errors ({len(job.errors)}):")
        for err in job.errors:
            click.echo(f"  - {err}")
    click.echo(f"Output: {output_dir}")


@cli.command()
@click.option("--host", default=None)
@click.option("--port", type=int, default=None)
@click.option("--no-browser", is_flag=True, default=False)
def serve(host, port, no_browser):
    """Start the web server."""
    import webbrowser

    import uvicorn

    from backend.main import app

    config = get_config()
    host = host or config.server.host
    port = port or config.server.port

    if not no_browser and config.server.auto_open_browser:
        import threading
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    click.echo(f"Starting server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


@cli.command()
def info():
    """Show system information."""
    config = get_config()

    click.echo("=== DeepSeek-OCR-2 Document Processor ===")
    click.echo(f"Python: {sys.version}")

    try:
        import torch
        click.echo(f"PyTorch: {torch.__version__}")
        click.echo(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            click.echo(f"GPU: {props.name}")
            click.echo(f"VRAM: {props.total_mem / (1024**3):.1f} GB")
    except ImportError:
        click.echo("PyTorch: not installed")

    try:
        import transformers
        click.echo(f"Transformers: {transformers.__version__}")
    except ImportError:
        click.echo("Transformers: not installed")

    from backend.model.manager import ModelManager
    manager = ModelManager()
    downloaded = manager.is_downloaded(config.model.cache_dir)
    click.echo(f"Model downloaded: {downloaded}")
    if downloaded:
        click.echo(f"Model path: {manager.get_model_path(config.model.cache_dir)}")
    click.echo(f"Model loaded: {manager.is_loaded()}")
    click.echo(f"Config: {config.model.device} device")


def main():
    cli()


if __name__ == "__main__":
    main()

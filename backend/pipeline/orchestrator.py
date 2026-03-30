import logging
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

from backend.config import AppConfig
from backend.model.inference import run_ocr
from backend.model.manager import ModelManager
from backend.pipeline.converter import convert_to_images, get_file_type
from backend.pipeline.extractor import ScientificDocument, extract_scientific_metadata
from backend.pipeline.formatter import format_output, get_file_extension
from backend.utils.file_scanner import FileInfo, scan_path
from backend.utils.page_selector import parse_page_range
from backend.workers.pool import WorkerPool

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FileResult:
    file_path: str
    output_path: str | None = None
    output_content: str | None = None
    error: str | None = None
    pages_processed: int = 0


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress_percent: float = 0.0
    current_file: str | None = None
    total_files: int = 0
    completed_files: int = 0
    results: list[FileResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: str = ""
    completed_at: str | None = None
    cancelled: bool = False

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "current_file": self.current_file,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "results": [
                {
                    "file_path": r.file_path,
                    "output_path": r.output_path,
                    "error": r.error,
                    "pages_processed": r.pages_processed,
                }
                for r in self.results
            ],
            "errors": self.errors,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class Orchestrator:
    def __init__(self, config: AppConfig):
        self.config = config
        self.jobs: dict[str, Job] = {}

    def create_job(self) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job and job.status == JobStatus.PROCESSING:
            job.cancelled = True
            job.status = JobStatus.CANCELLED
            return True
        return False

    def process_file(
        self,
        file_path: str | Path,
        output_dir: str | Path,
        output_format: str = "json",
        ocr_mode: str = "layout",
        pages: str | None = None,
        scientific: bool = True,
        job: Job | None = None,
    ) -> FileResult:
        file_path = Path(file_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = None

        try:
            # Parse page range for PDFs
            page_list = None
            if pages and get_file_type(file_path) == "pdf":
                from backend.pipeline.converter import get_pdf_page_count
                total = get_pdf_page_count(str(file_path))
                page_list = parse_page_range(pages, total)

            # Convert to images
            temp_dir = tempfile.mkdtemp(prefix="ocr_work_")
            images = convert_to_images(
                file_path,
                pages=page_list,
                dpi=self.config.processing.pdf_dpi,
                docx_method=self.config.converter.docx_method,
                libreoffice_path=self.config.converter.libreoffice_path,
                temp_dir=temp_dir,
            )

            if not images:
                return FileResult(file_path=str(file_path), error="No images produced from conversion")

            # Run OCR on each image
            page_texts = []
            for img_path in images:
                if job and job.cancelled:
                    return FileResult(file_path=str(file_path), error="Cancelled")
                text = run_ocr(img_path, mode=ocr_mode)
                page_texts.append(text)

            raw_text = "\n\n---\n\n".join(page_texts)

            # Extract scientific metadata
            if scientific:
                doc = extract_scientific_metadata(raw_text)
                doc.page_texts = page_texts
            else:
                doc = ScientificDocument(raw_text=raw_text, page_texts=page_texts)

            # Format output
            manager = ModelManager()
            content = format_output(
                doc,
                output_format=output_format,
                source_file=str(file_path),
                device=manager.device or "unknown",
                ocr_mode=ocr_mode,
            )

            # Write output file
            ext = get_file_extension(output_format)
            output_path = output_dir / f"{file_path.stem}{ext}"
            # Avoid name collisions
            counter = 1
            while output_path.exists():
                output_path = output_dir / f"{file_path.stem}_{counter}{ext}"
                counter += 1

            output_path.write_text(content, encoding="utf-8")

            return FileResult(
                file_path=str(file_path),
                output_path=str(output_path),
                output_content=content,
                pages_processed=len(page_texts),
            )

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return FileResult(file_path=str(file_path), error=str(e))
        finally:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def process_batch(
        self,
        paths: list[str | Path],
        output_dir: str | Path,
        output_format: str = "json",
        ocr_mode: str = "layout",
        pages: str | None = None,
        scientific: bool = True,
        workers: int = 1,
        recursive: bool = True,
        progress_callback: Callable | None = None,
    ) -> Job:
        job = self.create_job()
        job.status = JobStatus.PROCESSING

        # Scan for files
        all_files: list[FileInfo] = []
        for p in paths:
            all_files.extend(scan_path(p, recursive=recursive))

        job.total_files = len(all_files)

        if not all_files:
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100.0
            job.completed_at = datetime.now(timezone.utc).isoformat()
            return job

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        def process_single(file_info: FileInfo) -> FileResult:
            job.current_file = str(file_info.path)
            return self.process_file(
                file_info.path,
                output_dir=output_dir,
                output_format=output_format,
                ocr_mode=ocr_mode,
                pages=pages,
                scientific=scientific,
                job=job,
            )

        def on_progress(completed, total, item, result, error):
            job.completed_files = completed
            job.progress_percent = (completed / total) * 100
            if result:
                job.results.append(result)
                if result.error:
                    job.errors.append(f"{result.file_path}: {result.error}")
            if progress_callback:
                progress_callback(completed, total, item, result, error)

        pool = WorkerPool(max_workers=workers)
        pool.map(process_single, all_files, progress_callback=on_progress)

        if job.cancelled:
            job.status = JobStatus.CANCELLED
        elif job.errors:
            job.status = JobStatus.COMPLETED  # Completed with errors
        else:
            job.status = JobStatus.COMPLETED

        job.progress_percent = 100.0
        job.current_file = None
        job.completed_at = datetime.now(timezone.utc).isoformat()

        return job

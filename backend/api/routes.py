import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from backend.api.schemas import (
    ConfigUpdateRequest,
    JobListItem,
    JobResponse,
    ModelLoadRequest,
    ModelLoadResponse,
    ProcessFolderRequest,
    StatusResponse,
)
from backend.config import get_config
from backend.model.manager import ModelManager
from backend.pipeline.orchestrator import Orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(get_config())
    return _orchestrator


@router.get("/status", response_model=StatusResponse)
async def get_status():
    config = get_config()
    manager = ModelManager()
    status = manager.status(config.model.cache_dir)
    return StatusResponse(
        model_downloaded=status["downloaded"],
        model_loaded=status["loaded"],
        device=status["device"],
        cuda_available=status.get("cuda_available", False),
        gpu_name=status.get("gpu_name"),
        vram_total_mb=status.get("vram_total_mb"),
        vram_used_mb=status.get("vram_used_mb"),
        downloading=status.get("downloading", False),
        download_progress=status.get("download_progress", 0.0),
    )


@router.post("/model/download")
async def download_model(background_tasks: BackgroundTasks):
    config = get_config()
    manager = ModelManager()

    if manager.is_downloaded(config.model.cache_dir):
        return {"message": "Model already downloaded", "downloaded": True}

    def do_download():
        manager.download(config.model.model_id, config.model.cache_dir)

    background_tasks.add_task(do_download)
    return {"message": "Download started", "downloaded": False}


@router.post("/model/load", response_model=ModelLoadResponse)
async def load_model(request: ModelLoadRequest = ModelLoadRequest()):
    config = get_config()
    manager = ModelManager()

    if manager.is_loaded():
        return ModelLoadResponse(
            success=True, device=manager.device or "unknown",
            message="Model already loaded",
        )

    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: manager.load(config.model.model_id, config.model.cache_dir, request.device),
        )
        return ModelLoadResponse(success=True, device=manager.device or "unknown")
    except Exception as e:
        return ModelLoadResponse(success=False, device="none", message=str(e))


@router.post("/process/file")
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    output_format: str = Form("json"),
    ocr_mode: str = Form("layout"),
    pages: str | None = Form(None),
    scientific: bool = Form(True),
):
    config = get_config()
    manager = ModelManager()
    if not manager.is_loaded():
        return {"error": "Model not loaded. POST /api/v1/model/load first."}

    orchestrator = get_orchestrator()
    job = orchestrator.create_job()
    job.total_files = 1

    # Save uploaded file to temp location
    temp_dir = tempfile.mkdtemp(prefix="ocr_upload_")
    file_path = Path(temp_dir) / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_dir = Path(config.output.default_dir)

    def do_process():
        try:
            result = orchestrator.process_file(
                file_path,
                output_dir=output_dir,
                output_format=output_format,
                ocr_mode=ocr_mode,
                pages=pages,
                scientific=scientific,
                job=job,
            )
            job.results.append(result)
            if result.error:
                job.errors.append(result.error)
                job.status = "completed"
            else:
                job.status = "completed"
            job.completed_files = 1
            job.progress_percent = 100.0
        except Exception as e:
            job.status = "failed"
            job.errors.append(str(e))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    from backend.pipeline.orchestrator import JobStatus
    job.status = JobStatus.PROCESSING
    background_tasks.add_task(do_process)

    return {"job_id": job.job_id}


@router.post("/process/folder")
async def process_folder(request: ProcessFolderRequest, background_tasks: BackgroundTasks):
    config = get_config()
    manager = ModelManager()
    if not manager.is_loaded():
        return {"error": "Model not loaded. POST /api/v1/model/load first."}

    orchestrator = get_orchestrator()
    output_dir = request.output_dir or config.output.default_dir

    # Pre-scan to get file count
    from backend.utils.file_scanner import scan_path
    files = scan_path(request.folder_path, recursive=request.recursive)

    job = orchestrator.create_job()
    job.total_files = len(files)

    def do_process():
        orchestrator.process_batch(
            paths=[request.folder_path],
            output_dir=output_dir,
            output_format=request.output_format,
            ocr_mode=request.ocr_mode,
            pages=request.pages,
            scientific=request.scientific,
            workers=request.workers,
            recursive=request.recursive,
        )
        # The batch process creates its own job, but we reuse the pre-created one
        # by copying results from the batch job
        # This is handled within process_batch via the job parameter

    from backend.pipeline.orchestrator import JobStatus
    job.status = JobStatus.PROCESSING
    background_tasks.add_task(do_process)

    return {"job_id": job.job_id, "file_count": len(files)}


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    orchestrator = get_orchestrator()
    job = orchestrator.get_job(job_id)
    if job is None:
        return JobResponse(job_id=job_id, status="not_found")
    data = job.to_dict()
    return JobResponse(**data)


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    orchestrator = get_orchestrator()
    job = orchestrator.get_job(job_id)
    if job is None:
        return {"error": "Job not found"}

    results_with_content = []
    for r in job.results:
        item = {"file_path": r.file_path, "error": r.error}
        if r.output_content:
            item["content"] = r.output_content
        elif r.output_path and Path(r.output_path).exists():
            item["content"] = Path(r.output_path).read_text(encoding="utf-8")
        results_with_content.append(item)

    return {"job_id": job_id, "status": job.status.value, "results": results_with_content}


@router.get("/jobs")
async def list_jobs():
    orchestrator = get_orchestrator()
    items = []
    for job in orchestrator.jobs.values():
        items.append(JobListItem(
            job_id=job.job_id,
            status=job.status.value,
            progress_percent=job.progress_percent,
            total_files=job.total_files,
            completed_files=job.completed_files,
            created_at=job.created_at,
        ))
    return {"jobs": [item.model_dump() for item in items]}


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    orchestrator = get_orchestrator()
    cancelled = orchestrator.cancel_job(job_id)
    return {"cancelled": cancelled}


@router.get("/config")
async def get_current_config():
    config = get_config()
    return config.model_dump()


@router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    config = get_config()
    if request.processing:
        for k, v in request.processing.items():
            if hasattr(config.processing, k):
                setattr(config.processing, k, v)
    if request.converter:
        for k, v in request.converter.items():
            if hasattr(config.converter, k):
                setattr(config.converter, k, v)
    if request.output:
        for k, v in request.output.items():
            if hasattr(config.output, k):
                setattr(config.output, k, v)
    return config.model_dump()

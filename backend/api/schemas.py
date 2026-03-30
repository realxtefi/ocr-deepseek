from pydantic import BaseModel


class StatusResponse(BaseModel):
    model_downloaded: bool
    model_loaded: bool
    device: str | None
    cuda_available: bool
    gpu_name: str | None = None
    vram_total_mb: int | None = None
    vram_used_mb: int | None = None
    downloading: bool = False
    download_progress: float = 0.0


class ModelLoadRequest(BaseModel):
    device: str = "auto"


class ModelLoadResponse(BaseModel):
    success: bool
    device: str
    message: str = ""


class ProcessFileRequest(BaseModel):
    output_format: str = "json"
    ocr_mode: str = "layout"
    pages: str | None = None
    scientific: bool = True


class ProcessFolderRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    output_format: str = "json"
    ocr_mode: str = "layout"
    pages: str | None = None
    scientific: bool = True
    workers: int = 1
    output_dir: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress_percent: float = 0.0
    current_file: str | None = None
    total_files: int = 0
    completed_files: int = 0
    results: list[dict] = []
    errors: list[str] = []
    created_at: str = ""
    completed_at: str | None = None


class JobListItem(BaseModel):
    job_id: str
    status: str
    progress_percent: float
    total_files: int
    completed_files: int
    created_at: str


class ConfigUpdateRequest(BaseModel):
    processing: dict | None = None
    converter: dict | None = None
    server: dict | None = None
    output: dict | None = None

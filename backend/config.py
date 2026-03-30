import os
from pathlib import Path

import yaml
from pydantic import BaseModel


class ModelConfig(BaseModel):
    model_id: str = "deepseek-ai/DeepSeek-OCR-2"
    cache_dir: str = "./models"
    device: str = "auto"


class ProcessingConfig(BaseModel):
    default_ocr_mode: str = "layout"
    default_output_format: str = "json"
    workers: int = 1
    recursive: bool = True
    scientific_extraction: bool = True
    pdf_dpi: int = 300


class ConverterConfig(BaseModel):
    docx_method: str = "auto"
    libreoffice_path: str | None = None
    temp_dir: str | None = None


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    auto_open_browser: bool = True


class OutputConfig(BaseModel):
    default_dir: str = "./output"


class AppConfig(BaseModel):
    model: ModelConfig = ModelConfig()
    processing: ProcessingConfig = ProcessingConfig()
    converter: ConverterConfig = ConverterConfig()
    server: ServerConfig = ServerConfig()
    output: OutputConfig = OutputConfig()


def load_config(config_path: str | None = None) -> AppConfig:
    if config_path is None:
        config_path = os.environ.get("OCR_CONFIG", "config/default.yaml")

    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)

    return AppConfig()


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: AppConfig) -> None:
    global _config
    _config = config

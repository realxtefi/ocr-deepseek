import logging
import os
import threading
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class ModelManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.model = None
        self.tokenizer = None
        self.device = None
        self._inference_lock = threading.Lock()
        self._downloading = False
        self._download_progress = 0.0

    def detect_device(self, forced: str = "auto") -> str:
        if forced != "auto":
            return forced
        try:
            import torch
            if torch.cuda.is_available():
                vram_gb = torch.cuda.get_device_properties(0).total_mem / (1024**3)
                if vram_gb >= 4.0:
                    logger.info(f"CUDA available with {vram_gb:.1f}GB VRAM")
                    return "cuda"
                logger.warning(f"CUDA available but only {vram_gb:.1f}GB VRAM (need >=4GB), falling back to CPU")
            return "cpu"
        except ImportError:
            return "cpu"

    def get_model_path(self, cache_dir: str) -> Path:
        return Path(cache_dir).resolve() / "DeepSeek-OCR-2"

    def is_downloaded(self, cache_dir: str) -> bool:
        model_path = self.get_model_path(cache_dir)
        if not model_path.exists():
            return False
        safetensor_files = list(model_path.glob("*.safetensors"))
        return len(safetensor_files) > 0

    def download(
        self,
        model_id: str,
        cache_dir: str,
        progress_callback: Callable[[float, int, int], None] | None = None,
    ) -> Path:
        from huggingface_hub import snapshot_download

        self._downloading = True
        self._download_progress = 0.0
        model_path = self.get_model_path(cache_dir)
        model_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading model {model_id} to {model_path}")

        try:
            snapshot_download(
                repo_id=model_id,
                local_dir=str(model_path),
            )
            self._download_progress = 100.0
            if progress_callback:
                progress_callback(100.0, 0, 0)
        finally:
            self._downloading = False

        logger.info(f"Model downloaded to {model_path}")
        return model_path

    def load(self, model_id: str, cache_dir: str, device: str = "auto") -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        # If already loaded on a different device, unload first
        if self.is_loaded():
            requested = self.detect_device(device)
            if requested != self.device:
                logger.info(f"Switching device from {self.device} to {requested}")
                self.unload()
            else:
                logger.info(f"Model already loaded on {self.device}")
                return

        self.device = self.detect_device(device)
        model_path = self.get_model_path(cache_dir)

        if not self.is_downloaded(cache_dir):
            logger.info("Model not found locally, downloading...")
            self.download(model_id, cache_dir)

        logger.info(f"Loading model from {model_path} on {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            str(model_path), trust_remote_code=True
        )

        if self.device == "cuda":
            # Try flash_attention_2 -> eager on CUDA -> fall back to CPU
            try:
                self.model = AutoModel.from_pretrained(
                    str(model_path),
                    _attn_implementation="flash_attention_2",
                    trust_remote_code=True,
                    use_safetensors=True,
                )
                self.model = self.model.eval().cuda().to(torch.bfloat16)
                logger.info("Loaded with flash_attention_2 on CUDA (bf16)")
            except (ImportError, RuntimeError) as e:
                logger.warning(f"flash_attention_2 unavailable ({e}), trying eager attention on CUDA")
                try:
                    self.model = AutoModel.from_pretrained(
                        str(model_path),
                        _attn_implementation="eager",
                        trust_remote_code=True,
                        use_safetensors=True,
                    )
                    self.model = self.model.eval().cuda().to(torch.bfloat16)
                    logger.info("Loaded with eager attention on CUDA (bf16)")
                except RuntimeError as cuda_err:
                    logger.warning(f"CUDA loading failed ({cuda_err}), falling back to CPU")
                    self.device = "cpu"
                    self.model = AutoModel.from_pretrained(
                        str(model_path),
                        _attn_implementation="eager",
                        trust_remote_code=True,
                        use_safetensors=True,
                    )
                    self.model = self.model.eval().float()
                    logger.info("Fell back to CPU (float32)")
        else:
            self.model = AutoModel.from_pretrained(
                str(model_path),
                _attn_implementation="eager",
                trust_remote_code=True,
                use_safetensors=True,
            )
            self.model = self.model.eval().float()
            logger.info("Loaded with eager attention on CPU (float32)")

        logger.info(f"Model ready on {self.device}")

    def unload(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        self.device = None

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        logger.info("Model unloaded")

    def is_loaded(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def status(self, cache_dir: str) -> dict:
        info = {
            "downloaded": self.is_downloaded(cache_dir),
            "loaded": self.is_loaded(),
            "device": self.device,
            "downloading": self._downloading,
            "download_progress": self._download_progress,
        }

        try:
            import torch
            info["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                info["gpu_name"] = props.name
                info["vram_total_mb"] = round(props.total_mem / (1024**2))
                info["vram_used_mb"] = round(torch.cuda.memory_allocated(0) / (1024**2))
        except ImportError:
            info["cuda_available"] = False

        return info

    def infer(self, image_path: str, prompt: str, **kwargs) -> str:
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load() first.")

        import tempfile

        with self._inference_lock:
            # The model requires output_path even if we don't need saved files.
            # Use a temp dir to avoid WinError 3 from empty path default.
            tmp_out = kwargs.get("output_path") or tempfile.mkdtemp(prefix="ocr_out_")
            result = self.model.infer(
                self.tokenizer,
                prompt=prompt,
                image_file=image_path,
                output_path=tmp_out,
                base_size=kwargs.get("base_size", 1024),
                image_size=kwargs.get("image_size", 768),
                crop_mode=kwargs.get("crop_mode", True),
                save_results=kwargs.get("save_results", False),
            )
            return result

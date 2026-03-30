import logging
from pathlib import Path

from backend.model.manager import ModelManager

logger = logging.getLogger(__name__)

PROMPTS = {
    "layout": "<image>\n<|grounding|>Convert the document to markdown.",
    "plain": "<image>\nFree OCR.",
}


def run_ocr(
    image_path: str | Path,
    mode: str = "layout",
    base_size: int = 1024,
    image_size: int = 768,
    crop_mode: bool = True,
) -> tuple[str, str]:
    """Run OCR on an image. Returns (text, tmp_output_dir).

    Caller must clean up tmp_output_dir after copying any figure images.
    """
    manager = ModelManager()

    prompt = PROMPTS.get(mode)
    if prompt is None:
        raise ValueError(f"Unknown OCR mode: {mode!r}. Use 'layout' or 'plain'.")

    image_path = str(Path(image_path).resolve())
    logger.info(f"Running OCR on {image_path} (mode={mode})")

    text, tmp_out = manager.infer(
        image_path=image_path,
        prompt=prompt,
        base_size=base_size,
        image_size=image_size,
        crop_mode=crop_mode,
    )

    return text, tmp_out

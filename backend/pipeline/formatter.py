import json
from dataclasses import asdict
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from backend.pipeline.extractor import ScientificDocument


def _base_dict(doc: ScientificDocument, source_file: str, device: str, ocr_mode: str) -> dict:
    figures = [{"number": f.number, "caption": f.caption} for f in doc.figures]
    return {
        "source_file": source_file,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "ocr_mode": ocr_mode,
        "metadata": {
            "title": doc.title,
            "authors": doc.authors,
            "journal_or_series": doc.journal_or_series,
            "abstract": doc.abstract,
            "doi": doc.doi,
            "figures": figures,
            "extraction_confidence": doc.extraction_confidence,
        },
        "pages": [{"page_number": i + 1, "text": t} for i, t in enumerate(doc.page_texts)],
        "raw_text": doc.raw_text,
    }


def format_json(
    doc: ScientificDocument,
    source_file: str = "",
    device: str = "",
    ocr_mode: str = "layout",
) -> str:
    data = _base_dict(doc, source_file, device, ocr_mode)
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_markdown(
    doc: ScientificDocument,
    source_file: str = "",
    device: str = "",
    ocr_mode: str = "layout",
) -> str:
    lines = []

    if doc.title:
        lines.append(f"# {doc.title}")
        lines.append("")

    if doc.authors:
        lines.append(f"**Authors**: {', '.join(doc.authors)}")
        lines.append("")

    if doc.journal_or_series:
        lines.append(f"**Published in**: {doc.journal_or_series}")
        lines.append("")

    if doc.doi:
        lines.append(f"**DOI**: {doc.doi}")
        lines.append("")

    if doc.abstract:
        lines.append("## Abstract")
        lines.append("")
        lines.append(doc.abstract)
        lines.append("")

    if doc.page_texts:
        lines.append("## Full Text")
        lines.append("")
        for i, page_text in enumerate(doc.page_texts):
            if len(doc.page_texts) > 1:
                lines.append(f"### Page {i + 1}")
                lines.append("")
            lines.append(page_text)
            lines.append("")
            if i < len(doc.page_texts) - 1:
                lines.append("---")
                lines.append("")
    elif doc.raw_text:
        lines.append("## Full Text")
        lines.append("")
        lines.append(doc.raw_text)
        lines.append("")

    if doc.figures:
        lines.append("## Figures")
        lines.append("")
        for fig in doc.figures:
            lines.append(f"### Figure {fig.number}")
            lines.append("")
            lines.append(fig.caption)
            lines.append("")

    return "\n".join(lines)


def format_xml(
    doc: ScientificDocument,
    source_file: str = "",
    device: str = "",
    ocr_mode: str = "layout",
) -> str:
    root = Element("document")
    root.set("source", source_file)
    root.set("processed", datetime.now(timezone.utc).isoformat())
    root.set("device", device)
    root.set("ocr_mode", ocr_mode)

    metadata = SubElement(root, "metadata")

    title_el = SubElement(metadata, "title")
    title_el.text = doc.title or ""

    authors_el = SubElement(metadata, "authors")
    for author in doc.authors:
        a_el = SubElement(authors_el, "author")
        a_el.text = author

    journal_el = SubElement(metadata, "journal")
    journal_el.text = doc.journal_or_series or ""

    abstract_el = SubElement(metadata, "abstract")
    abstract_el.text = doc.abstract or ""

    doi_el = SubElement(metadata, "doi")
    doi_el.text = doc.doi or ""

    figures_el = SubElement(metadata, "figures")
    for fig in doc.figures:
        fig_el = SubElement(figures_el, "figure")
        fig_el.set("number", str(fig.number))
        caption_el = SubElement(fig_el, "caption")
        caption_el.text = fig.caption

    pages_el = SubElement(root, "pages")
    for i, page_text in enumerate(doc.page_texts):
        page_el = SubElement(pages_el, "page")
        page_el.set("number", str(i + 1))
        page_el.text = page_text

    raw_xml = tostring(root, encoding="unicode")
    pretty = parseString(raw_xml).toprettyxml(indent="  ")
    # Remove extra xml declaration if present
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines)


FORMATTERS = {
    "json": format_json,
    "markdown": format_markdown,
    "xml": format_xml,
}


def format_output(
    doc: ScientificDocument,
    output_format: str = "json",
    source_file: str = "",
    device: str = "",
    ocr_mode: str = "layout",
) -> str:
    formatter = FORMATTERS.get(output_format)
    if formatter is None:
        raise ValueError(f"Unknown format: {output_format!r}. Use: {list(FORMATTERS.keys())}")
    return formatter(doc, source_file, device, ocr_mode)


def get_file_extension(output_format: str) -> str:
    return {"json": ".json", "markdown": ".md", "xml": ".xml"}.get(output_format, ".txt")

import re
from dataclasses import dataclass, field


@dataclass
class FigureDescription:
    number: int
    caption: str


@dataclass
class ScientificDocument:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    journal_or_series: str | None = None
    abstract: str | None = None
    doi: str | None = None
    figures: list[FigureDescription] = field(default_factory=list)
    raw_text: str = ""
    page_texts: list[str] = field(default_factory=list)
    extraction_confidence: dict[str, float] = field(default_factory=dict)


def extract_title(text: str) -> tuple[str | None, float]:
    # Try h1 heading first
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip(), 0.95

    # Try bold text at the beginning
    match = re.search(r"^\*\*(.+?)\*\*", text, re.MULTILINE)
    if match:
        return match.group(1).strip(), 0.80

    # Fallback: first non-empty line
    for line in text.split("\n"):
        line = line.strip()
        if line and not line.startswith(("http", "doi", "![", "<")):
            return line, 0.40
    return None, 0.0


def extract_authors(text: str) -> tuple[list[str], float]:
    # Look for text between title and abstract/introduction
    sections = re.split(
        r"(?:^#{1,3}\s+(?:Abstract|Introduction|ABSTRACT|INTRODUCTION)|\*\*Abstract\*\*|\*\*ABSTRACT\*\*)",
        text, maxsplit=1, flags=re.MULTILINE
    )

    if len(sections) < 2:
        return [], 0.0

    header_block = sections[0]
    lines = header_block.strip().split("\n")

    # Skip the title (first significant line or heading)
    author_lines = []
    found_title = False
    for line in lines:
        line = line.strip()
        if not line:
            if found_title:
                continue
            continue
        if not found_title:
            found_title = True
            continue
        # Stop at affiliation-like lines (with numbers, emails, university names)
        if re.search(r"@|university|institute|department|college|school of", line, re.IGNORECASE):
            break
        if re.search(r"^\d+\s", line):
            break
        author_lines.append(line)

    if not author_lines:
        return [], 0.0

    author_text = " ".join(author_lines)
    # Clean markdown formatting
    author_text = re.sub(r"\*+", "", author_text)
    author_text = re.sub(r"\[.*?\]", "", author_text)
    author_text = re.sub(r"\d+", "", author_text)  # Remove superscript numbers
    author_text = re.sub(r"[†‡§¶∥]", "", author_text)  # Remove affiliation markers

    # Split by comma, semicolon, or "and"
    authors = re.split(r"[,;]\s*|\s+and\s+", author_text)
    authors = [a.strip() for a in authors if a.strip()]
    # Filter: keep entries that look like names (2-4 words, mostly capitalized)
    authors = [
        a for a in authors
        if 1 <= len(a.split()) <= 5
        and any(w[0].isupper() for w in a.split() if w)
    ]

    confidence = 0.85 if len(authors) > 0 else 0.0
    return authors, confidence


def extract_journal(text: str) -> tuple[str | None, float]:
    patterns = [
        r"((?:Journal|Proceedings|Conference|Transactions|IEEE|ACM|Springer|LNCS|Nature|Science|PNAS|Physical Review|Lecture Notes)[^\n.]{5,80})",
        r"(arXiv:\s*\d+\.\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), 0.80
    return None, 0.0


def extract_abstract(text: str) -> tuple[str | None, float]:
    # Find "Abstract" section
    patterns = [
        r"(?:^#{1,3}\s+Abstract|^\*\*Abstract\*\*)\s*\n(.*?)(?=^#{1,3}\s|\*\*\w+\*\*\n|\Z)",
        r"(?:^Abstract[.:\s]*\n)(.*?)(?=^#{1,3}\s|\n\n[A-Z1-9]|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
            if len(abstract) > 20:
                return abstract, 0.90
    return None, 0.0


def extract_doi(text: str) -> tuple[str | None, float]:
    match = re.search(r"(10\.\d{4,}/\S+)", text)
    if match:
        doi = match.group(1).rstrip(".,;)")
        return doi, 0.95
    return None, 0.0


def extract_figures(text: str) -> tuple[list[FigureDescription], float]:
    figures = []
    # Match "Figure N:" or "Fig. N:" patterns
    pattern = r"(?:Figure|Fig\.?)\s*(\d+)[.:\s]+([^\n]+(?:\n(?!(?:Figure|Fig\.?)\s*\d+|#{1,3}\s)[^\n]+)*)"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        fig_num = int(match.group(1))
        caption = match.group(2).strip()
        caption = re.sub(r"\s+", " ", caption)
        figures.append(FigureDescription(number=fig_num, caption=caption))

    confidence = 0.85 if figures else 0.0
    return figures, confidence


def extract_scientific_metadata(text: str) -> ScientificDocument:
    title, title_conf = extract_title(text)
    authors, authors_conf = extract_authors(text)
    journal, journal_conf = extract_journal(text)
    abstract, abstract_conf = extract_abstract(text)
    doi, doi_conf = extract_doi(text)
    figures, figures_conf = extract_figures(text)

    return ScientificDocument(
        title=title,
        authors=authors,
        journal_or_series=journal,
        abstract=abstract,
        doi=doi,
        figures=figures,
        raw_text=text,
        extraction_confidence={
            "title": title_conf,
            "authors": authors_conf,
            "journal_or_series": journal_conf,
            "abstract": abstract_conf,
            "doi": doi_conf,
            "figures": figures_conf,
        },
    )

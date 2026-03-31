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


# Generic headings that are page labels, not document titles
_GENERIC_HEADINGS = {
    "article", "letter", "review", "report", "original article",
    "research article", "original research", "brief communication",
    "short communication", "communication", "correspondence",
    "editorial", "perspective", "commentary", "opinion", "news",
    "feature", "essay", "analysis", "erratum", "correction",
    "retraction", "supplementary information", "methods",
}


def extract_title(text: str) -> tuple[str | None, float]:
    # Collect all h1 headings
    headings = re.findall(r"^#\s+(.+)$", text, re.MULTILINE)

    # Skip generic page-label headings (e.g. "Article", "Letter")
    for h in headings:
        cleaned = h.strip()
        if cleaned.lower() not in _GENERIC_HEADINGS and len(cleaned) > 3:
            return cleaned, 0.95

    # Try bold text at the beginning
    match = re.search(r"^\*\*(.+?)\*\*", text, re.MULTILINE)
    if match:
        candidate = match.group(1).strip()
        if candidate.lower() not in _GENERIC_HEADINGS and len(candidate) > 3:
            return candidate, 0.80

    # Fallback: first non-empty line that is not a URL / image / generic label
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith(("http", "doi", "![", "<")):
            continue
        if line.lstrip("#").strip().lower() in _GENERIC_HEADINGS:
            continue
        return line, 0.40
    return None, 0.0


def _find_header_block(text: str) -> str | None:
    """Extract the header block (between title and first section/abstract).

    Returns everything between the title line and the first section heading
    or "Abstract" marker.
    """
    lines = text.split("\n")
    title_idx = None
    end_idx = len(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if title_idx is None:
            # Find the title (first h1 heading that isn't generic)
            if stripped.startswith("# "):
                heading = stripped.lstrip("# ").strip()
                if heading.lower() not in _GENERIC_HEADINGS and len(heading) > 3:
                    title_idx = i
            continue

        # After title, find where the header ends
        # Stop at: section headings, "Abstract" markers, horizontal rules before body
        if re.match(r"^#{1,3}\s+\d*\.?\s*\w", stripped):
            end_idx = i
            break
        if re.match(r"^Abstract[\s.:—–-]", stripped, re.IGNORECASE):
            end_idx = i
            break
        if stripped.startswith("**Abstract"):
            end_idx = i
            break

    if title_idx is None:
        return None

    return "\n".join(lines[title_idx + 1:end_idx])


def extract_authors(text: str) -> tuple[list[str], float]:
    # Strategy 1: find a bold block that looks like an author list
    # (contains comma-separated names with optional superscript markers)
    bold_blocks = re.findall(r"\*\*(.+?)\*\*", text, re.DOTALL)
    for block in bold_blocks:
        if len(block) < 10:
            continue
        if re.match(r"^(https?://|Received|Accepted|Published|Open access|Check for|DOI)", block, re.IGNORECASE):
            continue
        if "," in block and re.search(r"[A-Z][a-z]+\s+[A-Z]", block):
            return _parse_author_string(block)

    # Strategy 2: extract header block and look for author-like lines
    header = _find_header_block(text)
    if header:
        lines = header.strip().split("\n")
        author_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip metadata lines
            if re.match(r"^\*?\*?(Received|Accepted|Published|Open access|Check for|https?://|www\.)", stripped, re.IGNORECASE):
                continue
            # Skip email lines
            if re.search(r"@[a-z]", stripped, re.IGNORECASE):
                continue
            # Stop at affiliation-like lines
            if re.search(r"(?<!\w)university|institute|department|college|school of", stripped, re.IGNORECASE):
                break
            if re.match(r"^[¹²³⁴⁵⁶⁷⁸⁹⁰\d]+\s*[A-Z]", stripped):
                break
            # This line could be an author name or author list
            author_lines.append(stripped)

        if author_lines:
            return _parse_author_string(" ".join(author_lines))

    return [], 0.0


def _parse_author_string(author_text: str) -> tuple[list[str], float]:
    """Parse a raw author string into a list of clean author names."""
    # Clean markdown formatting
    author_text = re.sub(r"\*+", "", author_text)
    author_text = re.sub(r"\[.*?\]", "", author_text)
    # Remove superscript unicode characters and regular digit superscripts
    author_text = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", "", author_text)
    author_text = re.sub(r"(?<=[A-Za-z])\d+(?=[,\s&]|$)", "", author_text)
    # Remove affiliation markers
    author_text = re.sub(r"[†‡§¶∥✉]", "", author_text)
    # Normalize whitespace
    author_text = re.sub(r"\s+", " ", author_text).strip()

    # Split by comma, semicolon, or " and " / " & "
    parts = re.split(r"[,;]\s*|\s+and\s+|\s*&\s*", author_text)
    authors = [a.strip() for a in parts if a.strip()]
    # Filter: keep entries that look like names (1-5 words, at least one capitalized)
    authors = [
        a for a in authors
        if 1 <= len(a.split()) <= 5
        and any(w[0].isupper() for w in a.split() if w)
        and not re.match(r"^(Vol|pp|No|Editor|Received|Published|doi)", a, re.IGNORECASE)
    ]

    confidence = 0.85 if len(authors) > 0 else 0.0
    return authors, confidence


def extract_journal(text: str) -> tuple[str | None, float]:
    # Strategy 1: look for structured journal lines (e.g. "Nature | Vol 651 | ...")
    match = re.search(
        r"((?:Nature|Science|PNAS|Physical Review)\s*\|\s*Vol\.?\s*\d+[^\n]{0,60})",
        text,
    )
    if match:
        return match.group(1).strip(), 0.90

    # Strategy 2: look for journal names in header/footer areas (first ~500 or last ~500 chars)
    header_footer = text[:500] + "\n" + text[-500:]
    patterns = [
        # "Journal of ..." or "IEEE Transactions on ..."
        r"((?:Journal\s+of|IEEE\s+Transactions\s+on|ACM\s+Transactions\s+on)\s+[^\n.]{5,80})",
        # Conference proceedings
        r"((?:Proceedings|Proc\.)\s+(?:of\s+)?[^\n.]{5,80})",
        # Specific journal names with volume info
        r"((?:Nature|Science|PNAS|Springer|LNCS|Lecture Notes)\s+[^\n.]{5,80})",
        # arXiv
        r"(arXiv:\s*\d+\.\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, header_footer)
        if m:
            return m.group(1).strip(), 0.80

    # Strategy 3: search full text but require very specific patterns
    full_patterns = [
        r"((?:Nature|Science|PNAS)\s+\d{1,4}\s*,\s*\d+)",  # e.g. "Nature 624, 80-85"
        r"(arXiv:\s*\d+\.\d+)",
    ]
    for pattern in full_patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip(), 0.75

    return None, 0.0


def extract_abstract(text: str) -> tuple[str | None, float]:
    # Strategy 1: explicit "Abstract" heading (## Abstract / **Abstract**)
    heading_patterns = [
        r"(?:^#{1,3}\s+Abstract|^\*\*Abstract\*\*)\s*\n(.*?)(?=^#{1,3}\s|\*\*\w+\*\*\n|\Z)",
        r"(?:^Abstract[:\s]*\n)(.*?)(?=^#{1,3}\s|\n\n[A-Z1-9]|\Z)",
    ]
    for pattern in heading_patterns:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
            if len(abstract) > 20:
                return abstract, 0.90

    # Strategy 2: inline abstract -- "Abstract. text..." or "Abstract— text..."
    # Common in whitepapers and older papers (e.g. Bitcoin, cryptography papers)
    inline_match = re.search(
        r"(?:^|\n)\s*Abstract[\s.:—–-]+(.+?)(?=\n\s*\n\s*(?:#{1,3}\s|\d+\.\s+[A-Z])|$)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if inline_match:
        abstract = inline_match.group(1).strip()
        # Clean up: collapse internal whitespace/newlines
        abstract = re.sub(r"\s*\n\s*", " ", abstract)
        if len(abstract) > 20:
            return abstract, 0.85

    # Strategy 3: for documents without any "Abstract" marker,
    # find the first substantial paragraph after author block and before
    # the first "---" separator or section heading.
    # This handles Nature-style papers where the abstract is just the first
    # long paragraph after authors.
    lines = text.split("\n")
    para_lines = []
    found_authors = False
    past_header = False

    for line in lines:
        stripped = line.strip()
        # Detect author block (bold text with commas and names)
        if stripped.startswith("**") and "," in stripped and re.search(r"[A-Z][a-z]+\s+[A-Z]", stripped):
            found_authors = True
            continue
        if not found_authors:
            continue
        # Skip empty lines immediately after authors
        if not stripped and not para_lines:
            past_header = True
            continue
        # Stop at separators or new sections
        if stripped == "---" or stripped.startswith("#"):
            break
        if not stripped and para_lines:
            break
        if past_header:
            para_lines.append(stripped)

    if para_lines:
        candidate = " ".join(para_lines)
        if len(candidate) > 100 and candidate[0].isupper():
            return candidate, 0.70

    return None, 0.0


def extract_doi(text: str) -> tuple[str | None, float]:
    match = re.search(r"(10\.\d{4,}/\S+)", text)
    if match:
        doi = match.group(1).rstrip(".,;)]*\"'")
        # Strip trailing markdown formatting
        doi = re.sub(r"\*+$", "", doi)
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

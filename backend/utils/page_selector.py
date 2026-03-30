def parse_page_range(page_range: str, total_pages: int | None = None) -> list[int]:
    """Parse a page range string like '1-3,5,7-10' into 0-indexed page numbers."""
    pages = set()

    for part in page_range.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str.strip())
            end = int(end_str.strip())
            if start > end:
                raise ValueError(f"Invalid range: {part} (start > end)")
            for i in range(start, end + 1):
                pages.add(i - 1)  # Convert to 0-indexed
        else:
            pages.add(int(part.strip()) - 1)  # Convert to 0-indexed

    result = sorted(pages)

    if total_pages is not None:
        result = [p for p in result if 0 <= p < total_pages]

    return result

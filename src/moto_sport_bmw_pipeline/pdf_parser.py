"""Extract uniformly structured, traceable stops from inspected IMSA PDF layouts.

Coordinates and sequence checks are explicit; this is not a universal PDF parser.
"""

import logging
import re
from collections.abc import Iterable, Iterator
from contextlib import closing
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)

CAR_HEADER = re.compile(r"^(\d+)(?:\s+[A-Za-z]|$)")
# Retain likely stop rows even when their remaining fields cannot be parsed.
STOP_CANDIDATE = re.compile(r"^\s*\d+\s+\d{1,2}:")
STOP_ROW = re.compile(
    r"^\s*(\d+)\s+\d{2}:\d{2}:\d{2}\.\d{3}"
    r"\s+\d{2}:\d{2}:\d{2}\.\d{3}"
    r"\s+((?:\d+:){0,2}\d+\.\d{3})(?=\s)"
)


def iter_parse_stop_blocks(
    blocks: Iterable[tuple[int | None, int | None, str]],
) -> Iterator[dict]:
    """Parse ordered blocks while retaining each stop's extracted location.

    block_line_number counts retained text lines, not visual PDF lines.
    Text-only test inputs supply None for unavailable page/column metadata.
    """
    current_car = None
    expected_stop_number = 1

    for page_number, column_number, block in blocks:
        for block_line_number, line in enumerate(block.splitlines(), start=1):
            header = CAR_HEADER.match(line)
            if header:
                current_car = header.group(1)
                expected_stop_number = 1
                continue

            stop = STOP_ROW.match(line)
            if stop is None and STOP_CANDIDATE.match(line):
                raise ValueError(
                    f"PDF stop rejected: unreadable stop row for car {current_car}: {line.strip()}"
                )
            if stop:
                if current_car is None:
                    raise ValueError("PDF stop rejected: missing car context")
                stop_number = int(stop.group(1))
                if stop_number != expected_stop_number:
                    raise ValueError(
                        f"PDF stop rejected: non-sequential stop {stop_number} "
                        f"for car {current_car} (expected {expected_stop_number})"
                    )
                expected_stop_number += 1
                yield {
                    "car_number": current_car,
                    "pit_number": stop_number,
                    "pit_time_raw": stop.group(2),
                    "page_number": page_number,
                    "column_number": column_number,
                    "block_line_number": block_line_number,
                    "source_line": line,
                }


def parse_stop_blocks(
    blocks: Iterable[tuple[int | None, int | None, str]],
) -> list[dict]:
    """Compatibility materializer for callers explicitly requesting all rows."""
    return list(iter_parse_stop_blocks(blocks))


def classify_token(x: float, y: float, value: str, size: float):
    """Keep a stop row or a car header from this report's two columns.

    One-digit car numbers are right-aligned, so they sit about seven points
    to the right of two-digit numbers. Stop rows stay on the row's left edge.
    """
    if not 80 < y < 650:
        return None

    column = 0 if x < 306 else 1
    row_x = 60.45 if column == 0 else 321.25
    if STOP_CANDIDATE.match(value) and abs(x - row_x) < 5:
        return column, value

    # Centers of the observed header positions (1, 2, or 3 digits).
    header_x = 65.05 if column == 0 else 325.85
    if value.isdigit() and len(value) <= 3 and size >= 16 and abs(x - header_x) < 12:
        return column, value

    return None


def iter_stop_blocks(
    source_path: Path,
) -> Iterator[tuple[int, int, str]]:
    """Extract ordered text blocks with one-based page and column numbers."""
    # Supplying the stream avoids PdfReader(path)'s initial full-file BytesIO copy.
    with source_path.open("rb") as stream:
        reader = PdfReader(stream)
        try:
            for page_number, page in enumerate(reader.pages, start=1):
                columns = [[], []]

                def collect(text, cm, tm, font, size):
                    x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                    y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                    classified = classify_token(x, y, text.strip(), size or 0)

                    if classified is not None:
                        column, value = classified
                        columns[column].append((y, value))

                page.extract_text(visitor_text=collect)

                for column_number, column in enumerate(columns, start=1):
                    ordered_text = "\n".join(
                        value
                        for _, value in sorted(
                            column, key=lambda item: item[0], reverse=True
                        )
                    )
                    yield page_number, column_number, ordered_text
        finally:
            try:
                reader.close()
            except Exception:
                logger.exception("Could not close PDF reader: %s", source_path)


def extract_stop_blocks(source_path: Path) -> list[tuple[int, int, str]]:
    """Compatibility materializer; production extraction uses the iterator."""
    return list(iter_stop_blocks(source_path))


def iter_stops(source_path: Path) -> Iterator[dict]:
    """Yield validated stops and close the page stream on failure or cancellation."""
    with closing(iter_stop_blocks(source_path)) as blocks:
        yield from iter_parse_stop_blocks(blocks)


def extract_stops(source_path: Path) -> list[dict]:
    """Extract raw stop fields and their page, column and retained text line."""
    return list(iter_stops(source_path))

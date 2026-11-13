"""Extract uniformly structured, traceable stops from inspected IMSA PDF layouts.

Coordinates and sequence checks are explicit; this is not a universal PDF parser.
"""

from pathlib import Path
import re

from pypdf import PdfReader


CAR_HEADER = re.compile(r"^(\d+)(?:\s+[A-Za-z]|$)")
# Retain likely stop rows even when their remaining fields cannot be parsed.
STOP_CANDIDATE = re.compile(r"^\s*\d+\s+\d{1,2}:")
STOP_ROW = re.compile(
    r"^\s*(\d+)\s+\d{2}:\d{2}:\d{2}\.\d{3}"
    r"\s+\d{2}:\d{2}:\d{2}\.\d{3}"
    r"\s+((?:\d+:){0,2}\d+\.\d{3})(?=\s)"
)


def parse_stop_blocks(
    blocks: list[tuple[int | None, int | None, str]],
) -> list[dict]:
    """Parse ordered blocks while retaining each stop's extracted location.

    block_line_number counts retained text lines, not visual PDF lines.
    Text-only test inputs supply None for unavailable page/column metadata.
    """
    current_car = None
    expected_stop_number = 1
    rows = []

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
                rows.append({
                    "car_number": current_car,
                    "pit_number": stop_number,
                    "pit_time_raw": stop.group(2),
                    "page_number": page_number,
                    "column_number": column_number,
                    "block_line_number": block_line_number,
                    "source_line": line,
                })

    return rows


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
    if (
        value.isdigit()
        and len(value) <= 3
        and size >= 16
        and abs(x - header_x) < 12
    ):
        return column, value

    return None

def extract_stop_blocks(
    source_path: Path,
) -> list[tuple[int, int, str]]:
    """Extract ordered text blocks with one-based page and column numbers."""
    blocks = []

    for page_number, page in enumerate(PdfReader(source_path).pages, start=1):
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
                for _, value in sorted(column, key=lambda item: -item[0])
            )
            blocks.append((page_number, column_number, ordered_text))

    return blocks


def extract_stops(source_path: Path) -> list[dict]:
    """Extract raw stop fields and their page, column and retained text line."""
    return parse_stop_blocks(extract_stop_blocks(source_path))

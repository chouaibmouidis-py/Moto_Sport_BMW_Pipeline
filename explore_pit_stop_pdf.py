"""Explore the two-column layout of the Road America 2023 pit-stop PDF.

Column positions and body bounds are specific to this report, not other layouts.
"""

import argparse
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


def parse_stop_blocks(blocks: list[str]) -> list[tuple[str, int, str]]:
    """Read ordered columns/pages without losing the last car's context."""
    current_car = None
    expected_stop_number = 1
    rows = []

    for block in blocks:
        for line in block.splitlines():
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
                rows.append((current_car, stop_number, stop.group(2)))

    return rows


def parse_selected_stops(text: str) -> list[tuple[str, int, str]]:
    return [row for row in parse_stop_blocks([text]) if row[0] in {"24", "25"}]


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


def extract_stops(source_path: Path) -> list[tuple[str, int, str]]:
    blocks = []
    for page in PdfReader(source_path).pages:
        columns = [[], []]

        def collect(text, cm, tm, font, size):
            # Transform text coordinates into page coordinates.
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            classified = classify_token(x, y, text.strip(), size or 0)
            if classified is not None:
                column, value = classified
                columns[column].append((y, value))

        page.extract_text(visitor_text=collect)
        for column in columns:
            blocks.append("\n".join(value for _, value in sorted(
                column, key=lambda item: -item[0]
            )))

    return parse_stop_blocks(blocks)


def extract_selected_stops(source_path: Path) -> list[tuple[str, int, str]]:
    return [row for row in extract_stops(source_path) if row[0] in {"24", "25"}]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_path", type=Path)
    args = parser.parse_args()

    for row in extract_selected_stops(args.source_path):
        print(*row, sep=" | ")


if __name__ == "__main__":
    main()

"""Verify PDF parsing, CSV linkage, duration conversion and source fingerprints.

Parsing helpers are imported from their owning module. The diagnostic CLI
receives explicit race context rather than assuming a season or event.
"""

from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from inspect_pdf_pair import main
from moto_sport_bmw_pipeline.pair_diagnostics import (
    build_pdf_car_summary,
    compute_source_hash,
    convert_extracted_stops,
    inspect_source_pair,
    validate_pdf_stop_links,
)
from moto_sport_bmw_pipeline.pdf_parser import (
    classify_token,
    extract_stops,
    parse_stop_blocks,
)
from moto_sport_bmw_pipeline.quality import validate_classification_keys


def raw_stop(car_number, pit_number, duration, *, page_number=1, line_number=1):
    """Build a synthetic record using the same fields as real PDF extraction."""
    return {
        "car_number": car_number,
        "pit_number": pit_number,
        "pit_time_raw": duration,
        "page_number": page_number,
        "column_number": 1,
        "block_line_number": line_number,
        "source_line": f"{pit_number} 10:00:00.000 10:01:00.000 {duration} {duration}",
    }


def test_extraction_retains_page_column_and_line():
    from unittest.mock import Mock

    first_line = "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481"
    second_line = "2 12:01:16.581 12:02:39.246 1:22.665 2:51.146"

    def visit(*, visitor_text):
        # PDF text coordinates are local; translation places them on the page.
        matrix = [1, 0, 0, 1, 10, 792]
        # Deliberately emit fragments outside reading order.
        for x, y, value, size in (
            (321.25, 600, second_line, 9),
            (60.45, 590, first_line, 9),
            (65.05, 600, "24", 18),
        ):
            visitor_text(
                value,
                matrix,
                [1, 0, 0, 1, x - 10, y - 792],
                None,
                size,
            )

    page = Mock()
    page.extract_text.side_effect = visit
    reader = Mock()
    reader.pages = [page]
    with patch(
        "moto_sport_bmw_pipeline.pdf_parser.PdfReader",
        return_value=reader,
    ):
        rows = extract_stops(Path("synthetic.pdf"))
    assert rows == [
        {
            "car_number": "24",
            "pit_number": 1,
            "pit_time_raw": "1:28.481",
            "page_number": 1,
            "column_number": 1,
            "block_line_number": 2,
            "source_line": first_line,
        },
        {
            "car_number": "24",
            "pit_number": 2,
            "pit_time_raw": "1:22.665",
            "page_number": 1,
            "column_number": 2,
            "block_line_number": 1,
            "source_line": second_line,
        },
    ]


def test_located_stops_preserve_origin_across_blocks():
    first_line = "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481"
    second_line = "2 12:01:16.581 12:02:39.246 1:22.665 2:51.146"
    next_car_line = "1 10:17:27.494 12:17:20.883 1:59:53.389 1:59:53.389"
    rows = parse_stop_blocks(
        [
            (2, 1, "24\n" + first_line),
            (2, 2, second_line),
            (3, 1, "25\n" + next_car_line),
        ]
    )
    assert rows == [
        {
            "car_number": "24",
            "pit_number": 1,
            "pit_time_raw": "1:28.481",
            "page_number": 2,
            "column_number": 1,
            "block_line_number": 2,
            "source_line": first_line,
        },
        {
            "car_number": "24",
            "pit_number": 2,
            "pit_time_raw": "1:22.665",
            "page_number": 2,
            "column_number": 2,
            "block_line_number": 1,
            "source_line": second_line,
        },
        {
            "car_number": "25",
            "pit_number": 1,
            "pit_time_raw": "1:59:53.389",
            "page_number": 3,
            "column_number": 1,
            "block_line_number": 2,
            "source_line": next_car_line,
        },
    ]


def test_source_pairs_publish_to_separate_contexts(tmp_path):
    directory = tmp_path
    root = Path(directory)
    pdf = root / "stops.pdf"
    csv = root / "classification.csv"
    pdf.write_bytes(b"PDF extraction is mocked")
    for event, session, model, expected_bmw in (
        ("course-a", "session-a", " BMW M Hybrid V8 ", 1),
        ("course-b", "session-b", "Chevrolet Corvette", 0),
    ):
        csv.write_text(
            f"NUMBER;POSITION;VEHICLE;STATUS\n 24 ;1;{model};Classified\n",
            encoding="utf-8",
        )
        output = root / event / "car_summary.parquet"
        context = {
            "championship": "test-championship",
            "season": 2023,
            "event_id": event,
            "session_id": session,
        }
        with patch(
            "moto_sport_bmw_pipeline.pair_diagnostics.extract_stops",
            return_value=[raw_stop("24", 1, "1:00.000")],
        ):
            result = inspect_source_pair(pdf, csv, context, output)
        assert result["stops"] == 1
        assert result["bmw_participants"] == expected_bmw
        assert result["bmw_stops"] == expected_bmw
        with duckdb.connect() as connection:
            saved = connection.read_parquet(str(output))
            assert saved.project(
                "event_id, session_id, pdf_sha256, classification_sha256"
            ).fetchall() == [
                (event, session, compute_source_hash(pdf), compute_source_hash(csv))
            ]
    assert (root / "course-a" / "car_summary.parquet").is_file()


def test_main_rejects_unknown_car_before_building_summary(tmp_path):
    directory = tmp_path
    pdf_path = Path(directory) / "stops.pdf"
    csv_path = Path(directory) / "classification.csv"
    pdf_path.write_bytes(b"PDF extraction is mocked")
    csv_path.write_text(
        "NUMBER;POSITION;VEHICLE\n24;1;BMW M Hybrid V8\n",
        encoding="utf-8",
    )
    with (
        patch(
            "sys.argv",
            [
                "inspect_pdf_pair.py",
                str(pdf_path),
                str(csv_path),
                "--championship",
                "imsa-weathertech",
                "--season",
                "2023",
                "--event-id",
                "road-america",
                "--session-id",
                "race-test",
                "--output",
                str(Path(directory) / "summary.parquet"),
            ],
        ),
        patch(
            "moto_sport_bmw_pipeline.pair_diagnostics.extract_stops",
            return_value=[raw_stop("99", 1, "1:00.000")],
        ),
        patch(
            "moto_sport_bmw_pipeline.pair_diagnostics.build_pdf_car_summary"
        ) as summary,
    ):
        with pytest.raises(ValueError, match="car absent from classification"):
            main()
        summary.assert_not_called()


@pytest.mark.parametrize("missing_input", ("pdf", "csv"))
def test_missing_input_prevents_pdf_extraction(missing_input, tmp_path):
    directory = tmp_path
    pdf_path = Path(directory) / "stops.pdf"
    csv_path = Path(directory) / "classification.csv"
    if missing_input == "pdf":
        csv_path.write_text("NUMBER;POSITION;VEHICLE\n", encoding="utf-8")
        missing_path = pdf_path
    else:
        # Contents should never be read when the CSV is absent.
        pdf_path.write_bytes(b"not a real PDF")
        missing_path = csv_path

    with (
        patch(
            "sys.argv",
            [
                "inspect_pdf_pair.py",
                str(pdf_path),
                str(csv_path),
                "--championship",
                "imsa-weathertech",
                "--season",
                "2023",
                "--event-id",
                "road-america",
                "--session-id",
                "race-test",
                "--output",
                str(Path(directory) / "summary.parquet"),
            ],
        ),
        patch("moto_sport_bmw_pipeline.pair_diagnostics.extract_stops") as extract,
    ):
        with pytest.raises(FileNotFoundError) as error:
            main()

        assert (
            str(error.value)
            == f"Exploration rejected: source file not found: {missing_path}"
        )
        extract.assert_not_called()


def test_summary_keeps_participant_without_stop_details(connection):
    connection.execute("""
        CREATE TEMP VIEW classification_csv AS
        SELECT *
        FROM (VALUES
            (' 24 ', '1', ' BMW M Hybrid V8 ', ' Classified '),
            ('57', '2', 'Mercedes-AMG GT3', 'Classified'),
            ('80', NULL, 'Porsche 911 GT3 R (992)', 'Not started')
        ) AS t(NUMBER, POSITION, VEHICLE, STATUS)
    """)
    connection.execute("""
        CREATE TEMP VIEW pdf_stops AS
        SELECT *
        FROM (VALUES
            ('24', 1),
            ('24', 2)
        ) AS t(car_number, pit_number)
    """)

    rows = build_pdf_car_summary(
        connection,
        "test-pdf-hash",
        "test-classification-hash",
        source_context={
            "championship": "test-championship",
            "season": 2022,
            "event_id": "test-event",
            "session_id": "test-session",
        },
    ).fetchall()
    assert rows == [
        (
            "24",
            1,
            "BMW M Hybrid V8",
            2,
            "test-pdf-hash",
            "test-classification-hash",
            "test-championship",
            2022,
            "test-event",
            "test-session",
            "Classified",
        ),
        (
            "57",
            2,
            "Mercedes-AMG GT3",
            None,
            "test-pdf-hash",
            "test-classification-hash",
            "test-championship",
            2022,
            "test-event",
            "test-session",
            "Classified",
        ),
        (
            "80",
            None,
            "Porsche 911 GT3 R (992)",
            None,
            "test-pdf-hash",
            "test-classification-hash",
            "test-championship",
            2022,
            "test-event",
            "test-session",
            "Not started",
        ),
    ]


def test_converts_extracted_durations_and_preserves_raw_values(connection):
    rows = [
        raw_stop("24", 1, "1:28.481", line_number=2),
        raw_stop("24", 2, "1:22.665", line_number=3),
        raw_stop("25", 1, "1:59:53.389", page_number=2),
    ]
    project_directory = Path(__file__).resolve().parent.parent
    result = convert_extracted_stops(connection, rows, project_directory)
    assert result.project(
        "car_number, pit_number, pit_time_raw, pit_time_seconds"
    ).fetchall() == [
        ("24", 1, "1:28.481", 88.481),
        ("24", 2, "1:22.665", 82.665),
        ("25", 1, "1:59:53.389", 7193.389),
    ]
    assert result.project(
        "page_number, column_number, block_line_number, source_line"
    ).fetchall() == [
        (
            row["page_number"],
            row["column_number"],
            row["block_line_number"],
            row["source_line"],
        )
        for row in rows
    ]


def test_converts_empty_extraction_to_empty_result(connection):
    project_directory = Path(__file__).resolve().parent.parent
    result = convert_extracted_stops(connection, [], project_directory)
    assert result.fetchall() == []


@pytest.mark.parametrize("x", (60.45, 321.25))
def test_rejects_unreadable_final_duration_after_classification(x):
    valid = "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481"
    invalid = "2 12:01:16.581 12:02:39.246 unreadable"
    classified = classify_token(x, 597.4, invalid, 9)
    assert classified is not None
    _, retained_line = classified
    with pytest.raises(ValueError, match="unreadable stop row for car 24"):
        parse_stop_blocks([(1, 1, "24\n" + valid + "\n" + retained_line)])


def test_ignores_report_heading():
    assert classify_token(60.45, 630, "Pit Stop Time Cards", 9) is None

    def test_preserves_long_duration_and_car_context():
        text = """24 BMW M Team RLL BMW M Hybrid V8 GTP
 1 11:10:21.650 11:11:50.131 1:28.481 1:28.481P. Eng A. Farfus
 2 12:01:16.581 12:02:39.246 1:22.665 2:51.146A. Farfus P. Eng
25 BMW M Team RLL BMW M Hybrid V8 GTP
 1 10:17:27.494 12:17:20.883 1:59:53.389 1:59:53.389C. De Phillippi N. Yelloly
27 Heart of Racing Team Aston Martin Vantage GT3 GTD
 1 10:50:00.528 10:51:06.024 1:05.496 1:05.496R. De Angelis
"""
        assert [
            (row["car_number"], row["pit_number"], row["pit_time_raw"])
            for row in parse_stop_blocks([(None, None, text)])
        ] == [
            ("24", 1, "1:28.481"),
            ("24", 2, "1:22.665"),
            ("25", 1, "1:59:53.389"),
            ("27", 1, "1:05.496"),
        ]


def test_rejects_continuation_without_header():
    with pytest.raises(ValueError, match="missing car context"):
        parse_stop_blocks(
            [(None, None, " 2 12:01:16.581 12:02:39.246 1:22.665 2:51.146")]
        )


def test_keeps_right_aligned_one_digit_car_numbers():
    assert classify_token(67.55, 584.3, "1", 18) == (0, "1")
    assert classify_token(62.55, 633.4, "01", 18) == (0, "01")
    assert classify_token(328.35, 633.4, "9", 18) == (1, "9")
    assert classify_token(67.55, 584.3, "1", 9) is None


def test_keeps_three_digit_car_numbers():
    assert classify_token(57.55, 584.3, "120", 18) == (0, "120")
    assert classify_token(318.35, 633.4, "023", 18) == (1, "023")


def test_carries_car_across_page_and_column_boundaries():
    blocks = [
        "23\n1 10:47:44.241 10:48:48.561 1:04.320 1:04.320",
        "2 11:47:29.051 11:48:50.658 1:21.607 2:25.927\n24\n"
        "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481",
        "2 12:01:16.581 12:02:39.246 1:22.665 2:51.146\n25\n"
        "1 10:17:27.494 12:17:20.883 1:59:53.389 1:59:53.389",
    ]
    assert [
        (row["car_number"], row["pit_number"], row["pit_time_raw"])
        for row in parse_stop_blocks([(None, None, text) for text in blocks])
    ] == [
        ("23", 1, "1:04.320"),
        ("23", 2, "1:21.607"),
        ("24", 1, "1:28.481"),
        ("24", 2, "1:22.665"),
        ("25", 1, "1:59:53.389"),
    ]


def test_rejects_restart_of_stop_sequence_without_car_header():
    # Stop 1 arriving when car 23 already has stop 1 and 2 indicates a missed header
    blocks = [
        "23\n1 10:47:44.241 10:48:48.561 1:04.320 1:04.320\n"
        "2 11:47:29.051 11:48:50.658 1:21.607 2:25.927\n"
        "1 12:00:00.000 12:01:00.000 1:00.000 1:00.000",
    ]
    with pytest.raises(ValueError, match="non-sequential stop 1 for car 23"):
        parse_stop_blocks([(None, None, text) for text in blocks])


def test_rejects_skipped_stop_number():
    # Stop sequence skipping from 1 directly to 3
    blocks = [
        "24\n1 11:10:21.650 11:11:50.131 1:28.481 1:28.481\n"
        "3 12:01:16.581 12:02:39.246 1:22.665 2:51.146",
    ]
    with pytest.raises(ValueError, match="non-sequential stop 3 for car 24"):
        parse_stop_blocks([(None, None, text) for text in blocks])


@pytest.mark.parametrize("car_number", (None, "", "   "))
def test_rejects_missing_classification_car_number(car_number, connection):
    connection.execute("""
        CREATE TEMP TABLE classification_csv (
            NUMBER VARCHAR
        )
    """)
    connection.execute(
        "INSERT INTO classification_csv VALUES (?)",
        [car_number],
    )

    with pytest.raises(ValueError, match="missing car number"):
        validate_classification_keys(connection)


def test_rejects_duplicate_classification_car_numbers(connection):
    connection.execute("""
        CREATE TEMP VIEW classification_csv AS
        SELECT *
        FROM (VALUES
            ('24'),
            ('24'),
            ('25')
        ) AS t(NUMBER)
    """)

    with pytest.raises(ValueError, match="duplicate car numbers"):
        validate_classification_keys(connection)


def test_accepts_distinct_textual_car_numbers(connection):
    connection.execute("""
        CREATE TEMP VIEW classification_csv AS
        SELECT *
        FROM (VALUES
            ('01'),
            ('1'),
            ('24'),
            ('25')
        ) AS t(NUMBER)
    """)

    validate_classification_keys(connection)

    rows = connection.sql("""
        SELECT NUMBER
        FROM classification_csv
        ORDER BY NUMBER
    """).fetchall()

    assert rows == [("01",), ("1",), ("24",), ("25",)]


def test_rejects_stop_for_unknown_car(connection):
    connection.execute("""
        CREATE TEMP VIEW classification_csv AS
        SELECT '24' AS NUMBER
    """)

    connection.execute("""
        CREATE TEMP VIEW pdf_stops AS
        SELECT *
        FROM (VALUES
            ('24', 1),
            ('99', 1),
            ('99', 2)
        ) AS t(car_number, pit_number)
    """)

    with pytest.raises(ValueError, match="car absent from classification"):
        validate_pdf_stop_links(connection)


def test_accepts_participant_without_stop_details(connection):
    connection.execute("""
        CREATE TEMP VIEW classification_csv AS
        SELECT *
        FROM (VALUES ('24'), ('57')) AS t(NUMBER)
    """)

    connection.execute("""
        CREATE TEMP VIEW pdf_stops AS
        SELECT '24' AS car_number, 1 AS pit_number
    """)

    validate_pdf_stop_links(connection)


def test_source_hash_changes_when_content_changes(tmp_path):
    directory = tmp_path
    output_path = Path(directory) / "pit_stop_pdf"

    output_path.write_bytes(b"version-1")
    first_hash = compute_source_hash(output_path)

    output_path.write_bytes(b"version-2")
    second_hash = compute_source_hash(output_path)

    assert first_hash != second_hash


def test_same_content_has_same_hash_in_different_files(tmp_path):
    directory = tmp_path
    output_path = Path(directory) / "first.pdf"
    output_path_1 = Path(directory) / "second.pdf"

    output_path.write_bytes(b"same content")
    first_hash = compute_source_hash(output_path)

    output_path_1.write_bytes(b"same content")
    second_hash = compute_source_hash(output_path_1)

    assert first_hash == second_hash


def test_rejects_duplicate_car_numbers_after_trimming(connection):
    connection.execute("""
        CREATE TEMP VIEW classification_csv AS
        SELECT *
        FROM (VALUES
            ('24'),
            (' 24 '),
            ('25')
        ) AS t(NUMBER)
    """)

    with pytest.raises(ValueError, match="duplicate car numbers"):
        validate_classification_keys(connection)


def test_matches_pdf_stop_to_trimmed_classification_number(connection):
    connection.execute("""
        CREATE TEMP VIEW classification_csv AS
        SELECT ' 24 ' AS NUMBER
    """)

    connection.execute("""
        CREATE TEMP VIEW pdf_stops AS
        SELECT '24' AS car_number
    """)

    validate_pdf_stop_links(connection)

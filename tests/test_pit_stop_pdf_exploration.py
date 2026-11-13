"""Verify PDF parsing, CSV linkage, duration conversion and source fingerprints.

Tests import historical helpers through explore_pit_stop_pdf.py. Their actual
implementations live in src/moto_sport_bmw_pipeline/pdf_parser.py (text parsing)
and src/moto_sport_bmw_pipeline/exploration.py (validation and publication).
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import hashlib
import duckdb
from silver_writer import publish_silver
from explore_pit_stop_pdf import (
    classify_token,
    extract_stops,
    convert_extracted_stops,
    parse_stop_blocks,
    build_pdf_car_summary,
    main,
    validate_classification_keys,
    validate_pdf_stop_links,
    compute_source_hash,
    explore_source_pair,
)


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


class PitStopPdfExplorationTests(unittest.TestCase):
    def test_extraction_retains_page_column_and_line(self):
        from unittest.mock import Mock

        first_line = "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481"
        second_line = "2 12:01:16.581 12:02:39.246 1:22.665 2:51.146"

        def visit(*, visitor_text):
            identity = [1, 0, 0, 1, 0, 0]
            for x, y, value, size in (
                (65.05, 600, "24", 18),
                (60.45, 590, first_line, 9),
                (321.25, 600, second_line, 9),
            ):
                visitor_text(value, identity, [1, 0, 0, 1, x, y], None, size)

        page = Mock()
        page.extract_text.side_effect = visit
        reader = Mock()
        reader.pages = [page]
        with patch(
            "moto_sport_bmw_pipeline.pdf_parser.PdfReader", return_value=reader,
        ):
            rows = extract_stops(Path("synthetic.pdf"))
        self.assertEqual(rows, [
            {
                "car_number": "24", "pit_number": 1, "pit_time_raw": "1:28.481",
                "page_number": 1, "column_number": 1, "block_line_number": 2,
                "source_line": first_line,
            },
            {
                "car_number": "24", "pit_number": 2, "pit_time_raw": "1:22.665",
                "page_number": 1, "column_number": 2, "block_line_number": 1,
                "source_line": second_line,
            },
        ])

    def test_located_stops_preserve_origin_across_blocks(self):
        first_line = "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481"
        second_line = "2 12:01:16.581 12:02:39.246 1:22.665 2:51.146"
        next_car_line = "1 10:17:27.494 12:17:20.883 1:59:53.389 1:59:53.389"
        rows = parse_stop_blocks([
            (2, 1, "24\n" + first_line),
            (2, 2, second_line),
            (3, 1, "25\n" + next_car_line),
        ])
        self.assertEqual(rows, [
            {
                "car_number": "24", "pit_number": 1, "pit_time_raw": "1:28.481",
                "page_number": 2, "column_number": 1, "block_line_number": 2,
                "source_line": first_line,
            },
            {
                "car_number": "24", "pit_number": 2, "pit_time_raw": "1:22.665",
                "page_number": 2, "column_number": 2, "block_line_number": 1,
                "source_line": second_line,
            },
            {
                "car_number": "25", "pit_number": 1, "pit_time_raw": "1:59:53.389",
                "page_number": 3, "column_number": 1, "block_line_number": 2,
                "source_line": next_car_line,
            },
        ])

    def test_source_pairs_publish_to_separate_contexts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "stops.pdf"
            csv = root / "classification.csv"
            pdf.write_bytes(b"PDF extraction is mocked")
            csv.write_text(
                "NUMBER;POSITION;VEHICLE;STATUS\n24;1;BMW M Hybrid V8;Classified\n",
                encoding="utf-8",
            )
            for event, session in (("course-a", "session-a"), ("course-b", "session-b")):
                output = root / event / "car_summary.parquet"
                context = {
                    "championship": "test-championship", "season": 2023,
                    "event_id": event, "session_id": session,
                }
                with patch(
                    "moto_sport_bmw_pipeline.exploration.extract_stops",
                    return_value=[raw_stop("24", 1, "1:00.000")],
                ):
                    result = explore_source_pair(pdf, csv, context, output)
                self.assertEqual(result["stops"], 1)
                with duckdb.connect() as connection:
                    saved = connection.read_parquet(str(output))
                    self.assertEqual(saved.project(
                        "event_id, session_id, pdf_sha256, classification_sha256"
                    ).fetchall(), [(event, session, compute_source_hash(pdf), compute_source_hash(csv))])
            self.assertTrue((root / "course-a" / "car_summary.parquet").is_file())

    def test_main_rejects_unknown_car_before_building_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "stops.pdf"
            csv_path = Path(directory) / "classification.csv"
            pdf_path.write_bytes(b"PDF extraction is mocked")
            csv_path.write_text(
                "NUMBER;POSITION;VEHICLE\n24;1;BMW M Hybrid V8\n",
                encoding="utf-8",
            )
            with patch("sys.argv", [
                "explore_pit_stop_pdf.py", str(pdf_path), str(csv_path)
            ]), patch(
                "moto_sport_bmw_pipeline.exploration.extract_stops",
                return_value=[raw_stop("99", 1, "1:00.000")],
            ), patch("moto_sport_bmw_pipeline.exploration.build_pdf_car_summary") as summary:
                with self.assertRaisesRegex(
                    ValueError, "car absent from classification"
                ):
                    main()
                summary.assert_not_called()

    def test_missing_input_prevents_pdf_extraction(self):
        for missing_input in ("pdf", "csv"):
            with self.subTest(missing_input=missing_input):
                with tempfile.TemporaryDirectory() as directory:
                    pdf_path = Path(directory) / "stops.pdf"
                    csv_path = Path(directory) / "classification.csv"
                    if missing_input == "pdf":
                        csv_path.write_text("NUMBER;POSITION;VEHICLE\n", encoding="utf-8")
                        missing_path = pdf_path
                    else:
                        # Contents should never be read when the CSV is absent.
                        pdf_path.write_bytes(b"not a real PDF")
                        missing_path = csv_path

                    with patch("sys.argv", [
                        "explore_pit_stop_pdf.py", str(pdf_path), str(csv_path)
                    ]), patch("moto_sport_bmw_pipeline.exploration.extract_stops") as extract:
                        with self.assertRaises(FileNotFoundError) as error:
                            main()

                        self.assertEqual(
                            str(error.exception),
                            f"Exploration rejected: source file not found: {missing_path}",
                        )
                        extract.assert_not_called()

    def test_summary_keeps_participant_without_stop_details(self):
        with duckdb.connect() as connection:
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
            self.assertEqual(rows, [
                (
                    '24', 1, 'BMW M Hybrid V8', 2,
                    'test-pdf-hash', 'test-classification-hash',
                    'test-championship', 2022, 'test-event', 'test-session',
                    'Classified',
                ),
                (
                    '57', 2, 'Mercedes-AMG GT3', None,
                    'test-pdf-hash', 'test-classification-hash',
                    'test-championship', 2022, 'test-event', 'test-session',
                    'Classified',
                ),
                (
                    '80', None, 'Porsche 911 GT3 R (992)', None,
                    'test-pdf-hash', 'test-classification-hash',
                    'test-championship', 2022, 'test-event', 'test-session',
                    'Not started',
                ),
            ])

    def test_converts_extracted_durations_and_preserves_raw_values(self):
        rows = [
            raw_stop("24", 1, "1:28.481", line_number=2),
            raw_stop("24", 2, "1:22.665", line_number=3),
            raw_stop("25", 1, "1:59:53.389", page_number=2),
        ]
        project_directory = Path(__file__).resolve().parent.parent
        with duckdb.connect() as connection:
            result = convert_extracted_stops(connection, rows, project_directory)
            self.assertEqual(result.project(
                "car_number, pit_number, pit_time_raw, pit_time_seconds"
            ).fetchall(), [
                ("24", 1, "1:28.481", 88.481),
                ("24", 2, "1:22.665", 82.665),
                ("25", 1, "1:59:53.389", 7193.389),
            ])
            self.assertEqual(result.project(
                "page_number, column_number, block_line_number, source_line"
            ).fetchall(), [
                (row["page_number"], row["column_number"],
                 row["block_line_number"], row["source_line"])
                for row in rows
            ])

    def test_converts_empty_extraction_to_empty_result(self):
        project_directory = Path(__file__).resolve().parent.parent
        with duckdb.connect() as connection:
            result = convert_extracted_stops(connection, [], project_directory)
            self.assertEqual(result.fetchall(), [])

    def test_rejects_unreadable_final_duration_after_classification(self):
        valid = "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481"
        invalid = "2 12:01:16.581 12:02:39.246 unreadable"
        for x in (60.45, 321.25):
            with self.subTest(x=x):
                classified = classify_token(x, 597.4, invalid, 9)
                self.assertIsNotNone(classified)
                _, retained_line = classified
                with self.assertRaisesRegex(
                    ValueError, "unreadable stop row for car 24"
                ):
                    parse_stop_blocks([(1, 1, "24\n" + valid + "\n" + retained_line)])

    def test_ignores_report_heading(self):
        self.assertIsNone(classify_token(60.45, 630, "Pit Stop Time Cards", 9))

    def test_preserves_long_duration_and_car_context(self):
        text = """24 BMW M Team RLL BMW M Hybrid V8 GTP
 1 11:10:21.650 11:11:50.131 1:28.481 1:28.481P. Eng A. Farfus
 2 12:01:16.581 12:02:39.246 1:22.665 2:51.146A. Farfus P. Eng
25 BMW M Team RLL BMW M Hybrid V8 GTP
 1 10:17:27.494 12:17:20.883 1:59:53.389 1:59:53.389C. De Phillippi N. Yelloly
27 Heart of Racing Team Aston Martin Vantage GT3 GTD
 1 10:50:00.528 10:51:06.024 1:05.496 1:05.496R. De Angelis
"""
        self.assertEqual(
            [(row["car_number"], row["pit_number"], row["pit_time_raw"])
             for row in parse_stop_blocks([(None, None, text)])],
            [("24", 1, "1:28.481"), ("24", 2, "1:22.665"),
             ("25", 1, "1:59:53.389"), ("27", 1, "1:05.496")],
        )

    def test_rejects_continuation_without_header(self):
        with self.assertRaisesRegex(ValueError, "missing car context"):
            parse_stop_blocks([(None, None,
                " 2 12:01:16.581 12:02:39.246 1:22.665 2:51.146"
            )])

    def test_keeps_right_aligned_one_digit_car_numbers(self):
        self.assertEqual(classify_token(67.55, 584.3, "1", 18), (0, "1"))
        self.assertEqual(classify_token(62.55, 633.4, "01", 18), (0, "01"))
        self.assertEqual(classify_token(328.35, 633.4, "9", 18), (1, "9"))
        self.assertIsNone(classify_token(67.55, 584.3, "1", 9))

    def test_keeps_three_digit_car_numbers(self):
        self.assertEqual(classify_token(57.55, 584.3, "120", 18), (0, "120"))
        self.assertEqual(classify_token(318.35, 633.4, "023", 18), (1, "023"))

    def test_carries_car_across_page_and_column_boundaries(self):
        blocks = [
            "23\n1 10:47:44.241 10:48:48.561 1:04.320 1:04.320",
            "2 11:47:29.051 11:48:50.658 1:21.607 2:25.927\n24\n"
            "1 11:10:21.650 11:11:50.131 1:28.481 1:28.481",
            "2 12:01:16.581 12:02:39.246 1:22.665 2:51.146\n25\n"
            "1 10:17:27.494 12:17:20.883 1:59:53.389 1:59:53.389",
        ]
        self.assertEqual([
            (row["car_number"], row["pit_number"], row["pit_time_raw"])
            for row in parse_stop_blocks([(None, None, text) for text in blocks])
        ], [
            ("23", 1, "1:04.320"), ("23", 2, "1:21.607"),
            ("24", 1, "1:28.481"), ("24", 2, "1:22.665"),
            ("25", 1, "1:59:53.389"),
        ])

    def test_rejects_restart_of_stop_sequence_without_car_header(self):
        # Stop 1 arriving when car 23 already has stop 1 and 2 indicates a missed header
        blocks = [
            "23\n1 10:47:44.241 10:48:48.561 1:04.320 1:04.320\n"
            "2 11:47:29.051 11:48:50.658 1:21.607 2:25.927\n"
            "1 12:00:00.000 12:01:00.000 1:00.000 1:00.000",
        ]
        with self.assertRaisesRegex(ValueError, "non-sequential stop 1 for car 23"):
            parse_stop_blocks([(None, None, text) for text in blocks])

    def test_rejects_skipped_stop_number(self):
        # Stop sequence skipping from 1 directly to 3
        blocks = [
            "24\n1 11:10:21.650 11:11:50.131 1:28.481 1:28.481\n"
            "3 12:01:16.581 12:02:39.246 1:22.665 2:51.146",
        ]
        with self.assertRaisesRegex(ValueError, "non-sequential stop 3 for car 24"):
            parse_stop_blocks([(None, None, text) for text in blocks])

    def test_rejects_missing_classification_car_number(self):
        for car_number in (None, "", "   "):
            with self.subTest(car_number=car_number):
                with duckdb.connect() as connection:
                    connection.execute("""
                        CREATE TEMP TABLE classification_csv (
                            NUMBER VARCHAR
                        )
                    """)
                    connection.execute(
                        "INSERT INTO classification_csv VALUES (?)",
                        [car_number],
                    )

                    with self.assertRaisesRegex(
                        ValueError,
                        "missing car number",
                    ):
                        validate_classification_keys(connection)

    def test_rejects_duplicate_classification_car_numbers(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW classification_csv AS
                SELECT *
                FROM (VALUES
                    ('24'),
                    ('24'),
                    ('25')
                ) AS t(NUMBER)
            """)

            with self.assertRaisesRegex(
                ValueError,
                "duplicate car numbers",
            ):
                validate_classification_keys(connection)

    def test_accepts_distinct_textual_car_numbers(self):
        with duckdb.connect() as connection:
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

            self.assertEqual(
                rows,
                [('01',), ('1',), ('24',), ('25',)],
            )

    def test_rejects_stop_for_unknown_car(self):
        with duckdb.connect() as connection:
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

            with self.assertRaisesRegex(
                ValueError,
                "car absent from classification",
            ):
                validate_pdf_stop_links(connection)

    def test_accepts_participant_without_stop_details(self):
        with duckdb.connect() as connection:
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

    def test_source_hash_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "pit_stop_pdf"

            output_path.write_bytes(b"version-1")
            first_hash = compute_source_hash(output_path)

            output_path.write_bytes(b"version-2")
            second_hash = compute_source_hash(output_path)

            self.assertNotEqual(first_hash, second_hash)

    def test_same_content_has_same_hash_in_different_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "first.pdf"
            output_path_1 = Path(directory) / "second.pdf"

            output_path.write_bytes(b"same content")
            first_hash = compute_source_hash(output_path)

            output_path_1.write_bytes(b"same content")
            second_hash = compute_source_hash(output_path_1)

            self.assertEqual(first_hash, second_hash)

    def test_rejects_duplicate_car_numbers_after_trimming(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW classification_csv AS
                SELECT *
                FROM (VALUES
                    ('24'),
                    (' 24 '),
                    ('25')
                ) AS t(NUMBER)
            """)

            with self.assertRaisesRegex(
                ValueError,
                "duplicate car numbers",
            ):
                validate_classification_keys(connection)

    def test_matches_pdf_stop_to_trimmed_classification_number(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW classification_csv AS
                SELECT ' 24 ' AS NUMBER
            """)

            connection.execute("""
                CREATE TEMP VIEW pdf_stops AS
                SELECT '24' AS car_number
            """)

            validate_pdf_stop_links(connection)

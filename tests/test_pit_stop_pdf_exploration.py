import unittest

from explore_pit_stop_pdf import (
    classify_token,
    parse_selected_stops,
    parse_stop_blocks,
)


class PitStopPdfExplorationTests(unittest.TestCase):
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
                    parse_stop_blocks(["24\n" + valid + "\n" + retained_line])

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
            parse_selected_stops(text),
            [("24", 1, "1:28.481"), ("24", 2, "1:22.665"),
             ("25", 1, "1:59:53.389")],
        )

    def test_rejects_continuation_without_header(self):
        with self.assertRaisesRegex(ValueError, "missing car context"):
            parse_selected_stops(
                " 2 12:01:16.581 12:02:39.246 1:22.665 2:51.146"
            )

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
        self.assertEqual(parse_stop_blocks(blocks), [
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
            parse_stop_blocks(blocks)

    def test_rejects_skipped_stop_number(self):
        # Stop sequence skipping from 1 directly to 3
        blocks = [
            "24\n1 11:10:21.650 11:11:50.131 1:28.481 1:28.481\n"
            "3 12:01:16.581 12:02:39.246 1:22.665 2:51.146",
        ]
        with self.assertRaisesRegex(ValueError, "non-sequential stop 3 for car 24"):
            parse_stop_blocks(blocks)

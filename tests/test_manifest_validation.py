import unittest

from manifest_validation import validate_unique_source_ids


class ManifestValidationTests(unittest.TestCase):
    def test_rejects_duplicate_source_ids(self):
        documents = [
            {"source_id": "classification-a"},
            {"source_id": "pits-a"},
            {"source_id": "classification-a"},
        ]
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate source_id: classification-a",
        ):
            validate_unique_source_ids(documents)

    def test_accepts_unique_source_ids(self):
        documents = [
            {"source_id": "classification-a"},
            {"source_id": "pits-a"},
            {"source_id": "classification-b"},
        ]

        validate_unique_source_ids(documents)

    def test_rejects_invalid_source_ids(self):
        cases = [
            ({}, "missing source_id"),
            ({"source_id": None}, "missing source_id"),
            ({"source_id": 123}, "source_id must be a string"),
            ({"source_id": ""}, "source_id must not be blank"),
            ({"source_id": "   "}, "source_id must not be blank"),
        ]

        for document, expected_message in cases:
            with self.subTest(document=document):
                with self.assertRaisesRegex(
                    ValueError,
                    expected_message,
                ):
                    validate_unique_source_ids([document])
"""Verify rejection of invalid and duplicate source identifiers in the manifest."""

import pytest

from manifest_validation import validate_unique_source_ids


def test_rejects_duplicate_source_ids():
    documents = [
        {"source_id": "classification-a"},
        {"source_id": "pits-a"},
        {"source_id": "classification-a"},
    ]
    with pytest.raises(ValueError, match="Duplicate source_id: classification-a"):
        validate_unique_source_ids(documents)


def test_accepts_unique_source_ids():
    documents = [
        {"source_id": "classification-a"},
        {"source_id": "pits-a"},
        {"source_id": "classification-b"},
    ]

    validate_unique_source_ids(documents)


@pytest.mark.parametrize(
    "document,expected_message",
    [
        ({}, "missing source_id"),
        ({"source_id": None}, "missing source_id"),
        ({"source_id": 123}, "source_id must be a string"),
        ({"source_id": ""}, "source_id must not be blank"),
        ({"source_id": "   "}, "source_id must not be blank"),
    ],
)
def test_rejects_invalid_source_ids(document, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        validate_unique_source_ids([document])

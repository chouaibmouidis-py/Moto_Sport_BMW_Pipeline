-- Define the shared duration parser; return seconds or NULL for invalid input.

CREATE OR REPLACE TEMP MACRO parse_duration_seconds(duration_text) AS (
    SELECT
        CASE
            WHEN NOT format_is_valid THEN NULL
            WHEN NOT ISFINITE(part_1) THEN NULL
            WHEN part_1 < 0 THEN NULL
            WHEN part_count = 2
                AND (part_2 < 0 OR part_2 >= 60 OR NOT ISFINITE(part_2))
            THEN NULL

            WHEN part_count = 3
                AND (
                    part_2 < 0 OR part_2 >= 60
                    OR NOT ISFINITE(part_2)
                    OR part_3 < 0 OR part_3 >= 60 OR NOT ISFINITE(part_3)
                )
            THEN NULL

            WHEN part_count = 1 AND ISFINITE(part_1)
            THEN part_1

            WHEN part_count = 2 AND ISFINITE(part_1 * 60 + part_2)
            THEN part_1 * 60 + part_2

            WHEN part_count = 3
                AND ISFINITE(part_1 * 3600 + part_2 * 60 + part_3)
            THEN part_1 * 3600 + part_2 * 60 + part_3

            ELSE NULL
        END
    FROM (
        SELECT
            CASE
                WHEN regexp_full_match(
                    TRIM(duration_text), '[0-9]+([.][0-9]+)?'
                ) THEN TRUE
                WHEN regexp_full_match(
                    TRIM(duration_text), '[0-9]+:[0-9]+([.][0-9]+)?'
                ) THEN TRUE
                WHEN regexp_full_match(
                    TRIM(duration_text), '[0-9]+:[0-9]+:[0-9]+([.][0-9]+)?'
                ) THEN TRUE
                ELSE FALSE
            END AS format_is_valid,
            array_length(string_split(duration_text, ':')) AS part_count,
            TRY_CAST(split_part(duration_text, ':', 1) AS DOUBLE) AS part_1,
            TRY_CAST(split_part(duration_text, ':', 2) AS DOUBLE) AS part_2,
            TRY_CAST(split_part(duration_text, ':', 3) AS DOUBLE) AS part_3
    ) AS parts
);

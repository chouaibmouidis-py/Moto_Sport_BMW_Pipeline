CREATE OR REPLACE TEMP MACRO parse_duration_seconds(duration_text) AS (
    SELECT
        CASE
            WHEN part_1 < 0 THEN NULL

            WHEN part_count = 2
                AND (part_2 < 0 OR part_2 >= 60)
            THEN NULL

            WHEN part_count = 3
                AND (
                    part_2 < 0 OR part_2 >= 60
                    OR part_3 < 0 OR part_3 >= 60
                )
            THEN NULL

            WHEN part_count = 1 THEN part_1
            WHEN part_count = 2 THEN part_1 * 60 + part_2
            WHEN part_count = 3 THEN
                part_1 * 3600 + part_2 * 60 + part_3

            ELSE NULL
        END
    FROM (
        SELECT
            array_length(string_split(duration_text, ':')) AS part_count,
            TRY_CAST(split_part(duration_text, ':', 1) AS DOUBLE) AS part_1,
            TRY_CAST(split_part(duration_text, ':', 2) AS DOUBLE) AS part_2,
            TRY_CAST(split_part(duration_text, ':', 3) AS DOUBLE) AS part_3
    ) AS parts
);
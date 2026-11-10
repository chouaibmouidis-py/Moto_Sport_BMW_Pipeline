WITH test_cases AS (
    SELECT *
    FROM (VALUES
        ('  BMW  '),
        ('   '),
        (''),
        (NULL),
        ('  United States  '),
        ('04')
    ) AS t(raw_value)
)
SELECT
    raw_value,
    NULLIF(TRIM(raw_value), '') AS cleaned_value
FROM test_cases;
# Bronze JSON: remove full Python document copies

27 November 2026 — locally validated maintenance; not deployed.

## Change and preserved contract

Both JSON builders share the revised `_publish_json_document` path. DuckDB reads
the JSON and materializes its selected roots in an expected table. Python no
longer runs json.load/json.loads on the document or fetches complete document rows
for validation. Only schema information, counts, validation booleans and a SHA-256
string cross into Python.

The source must be one object document with the required roots. Classification
and pit-stop arrays are checked explicitly; nested driver/stop collections must
also be arrays. Counts are calculated in DuckDB. Each saved root is compared
natively with its expected root, with formatting normalized for root-specific
diagnostics. The shared bidirectional EXCEPT ALL check, schema validation,
replacement and failure cleanup remain in place.

Raw SHA-256 is computed before processing and checked again before publication,
using buffered file_digest reads. A detected byte change blocks replacement and
removes the candidate. These pre/post checks are not a filesystem lock or a
multi-process snapshot transaction. They add two streamed integrity reads; this
milestone reduces Python payload retention, not all disk-read counts.

Malformed JSON continues to raise JSONDecodeError for compatibility, retaining
the DuckDB parsing error as its cause and in its message. The Python exception
does not retain the complete source string; native details supply parse context.

## Regression and memory evidence

[The new tests](../tests/test_bronze_json_memory.py) verify both JSON builders and
both formats with Python decoding and relation.fetchall forbidden during
publication; Raw mutation during writing; required roots; invalid nested array
shapes; BOM, Unicode and NULL fields; and warmed allocation guards.

The first regression run had seven expected failures out of eight scenarios.
The old classification guard observed a traced Python peak of 23,423,576 bytes.
This single local observation is not a universal memory ratio.

Post-change measurements, with fixture generation outside tracing:

| Fixture | Entries | Source bytes | Traced Python peak bytes |
| --- | ---: | ---: | ---: |
| Classification | 20,000 | 4,780,050 | 270,629 |
| Pit-stop document | 20,000 | 5,420,053 | 270,534 |

Both warmed guards require a peak below 2 MiB and verify 20,000 saved entries.
Positive controls deliberately retain the full input bytes while performing the
real publication and must exceed the same threshold. The complete focused module
contains 16 passing cases.

The complete local suite after this change passes **419 tests and 97 subtests**.

Environment: DuckDB 1.5.4, macOS 13.7.8 Intel. Tracemalloc measures Python
allocations: **native DuckDB/driver allocations, RSS and OS cache are excluded**.
DuckDB still materializes the roots; parser/object-size and execution memory limits
remain applicable. No total-process RAM bound, runtime gain or cloud saving is
claimed.

## Real-data equivalence

All **44 enabled real JSON reports** (22 classification and 22 pit-stop reports)
were rebuilt into temporary Parquet files. Names, types and bidirectional exact
row-multiset comparison matched every existing Bronze. All **197 protected
Raw/Bronze files and active references** retained identical paths and SHA-256.
No real pipeline execution, reference activation or MotherDuck operation occurred.

Evidence: [real-data and allocation report](benchmarks/bronze-json-memory-2026-11-27.json).
Earlier storage-study timings describe their earlier implementation, not this
revised JSON path.

## Scope and next work

Production remains Parquet; Vortex stays experimental. This change removes Python
document copies in JSON Bronze construction. The subsequent
[PDF/CSV completion](bronze_progressive_processing.md) adds progressive PDF batches
and common streamed fingerprints. Parser caches, native engine memory and other
pipeline stages remain separate qualification scopes.

```bash
uv run --locked --no-sync python -m pytest tests/test_bronze_json_memory.py -v
```

Vortex must already be installed for the experimental cases. Its test directory
follows BMW_VORTEX_EXTENSION_DIRECTORY; pytest does not install extensions.

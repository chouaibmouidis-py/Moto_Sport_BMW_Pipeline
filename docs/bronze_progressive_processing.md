# Bronze progressive processing: JSON, CSV and PDF

27 November 2026 — locally validated; no deployment or active-data replacement.

## Completed application-buffer work

The same Bronze publisher still verifies schema, content and failure cleanup.
Production remains Parquet. Source readers now avoid retaining whole document
payloads in application-owned Python collections where those copies were avoidable.

| Input | Production path | Evidence |
| --- | --- | --- |
| JSON | Snapshot roots and validate inside DuckDB; return scalars to Python | 44 real reports match existing Bronze; 20,000-entry allocation guards and positive controls |
| CSV | Read raw text fields through DuckDB, without a Python row collection | 12 real reports, 516 rows, exact schema/content equivalence |
| PDF | Seekable file stream, lazy page/column blocks, stateful stop iterator, bounded insertion batches | 12 real reports, 5,715 stops, exact schema/content/provenance equivalence |

The JSON-specific measurements are described in [the JSON memory note](bronze_json_memory.md).
CSV already used a native reader: no artificial Python batching was introduced.

## PDF implementation

`pdf_parser.py` exposes iter_stop_blocks, iter_parse_stop_blocks and iter_stops.
The page reader receives an open binary stream, avoiding PdfReader(path)'s initial
complete-file BytesIO copy. Coordinates and column ordering are unchanged. The
parser keeps car context and the expected stop number across columns and pages;
unreadable rows and sequence gaps still raise errors.

The consumer closes the stop iterator after success or failure; the iterator
closes the block generator, which closes the reader and source stream. Reader or
iterator cleanup errors are logged without masking the original failure.

`build_pdf_pit_stop_bronze` accepts a positive integer batch_size, default 500.
It builds at most that many insertion tuples, executes the insertion, clears the
batch and continues. It no longer collects every stop dictionary and then builds
a second complete tuple list. A final short batch is inserted before validation.

The temporary DuckDB table retains the full extracted dataset for publication
validation. No destination file is replaced before complete extraction, source
verification and common write/readback checks. An error in a late block, insert,
write or source-integrity check preserves the previous Bronze.

Legacy parse_stop_blocks, extract_stop_blocks and extract_stops still return lists
for callers explicitly requesting complete results. The production Bronze path
uses the iterators; these materializers remain for compatibility/diagnostics.

## Shared file integrity

`integrity.sha256_file` uses hashlib.file_digest with a bounded Python buffer.
It is reused by PDF/JSON Bronze source checks, Bronze loaders, processing input
and output fingerprints, cached-source checks and verify_local_file.
Source SHA-256 values and error contracts are retained; acquisition still hashes
new network chunks directly rather than rereading downloaded data for its digest.

PDF fingerprints are checked before extraction, after extraction and after writing
the candidate. These are repeated streamed reads for integrity, not a reduction
of all disk I/O. They do not establish an atomic snapshot against arbitrary
concurrent filesystem changes.

## Tests and Python allocation measurements

[test_pdf_progressive_bronze.py](../tests/test_pdf_progressive_bronze.py) covers:

- no Path.read_bytes for PDF fingerprints;
- first-page delivery before visiting the next page and early stream closure;
- sequence validation across lazy blocks;
- insertion of the first batch before requesting the next batch's records;
- late parse failure and insert failure, including explicit iterator closure;
- source mutation during candidate writing;
- invalid batch sizes before reading the source;
- batch allocation guards with a retained-record positive control.

A separate streamed fingerprint regression compares exact bytes with a trusted
SHA-256 result while forbidding read_bytes. Existing tests still verify extracted
locations, raw duration text, typed empty outputs and preservation on failure.

Measured on DuckDB 1.5.4/macOS 13.7.8 Intel, with fixture generation outside tracing:

| Synthetic producer | Rows | Batch size | Traced Python peak bytes |
| --- | ---: | ---: | ---: |
| Lazy records | 100 | 64 | 270,743 |
| Lazy records | 5,000 | 64 | 274,676 |
| Deliberately retained records | 5,000 | 64 | 4,637,720 |

The two normal cases must stay below 2 MiB; the positive control must exceed it.
This isolates application batching with a synthetic producer. It does **not**
include PDF parsing or bound total process memory, and it is not a runtime benchmark.

Actual PDF builds, measured separately including pypdf, had traced Python peaks
from 685,271 to 35,910,428 bytes; the first document includes cold initialization.
No old/new total-RAM improvement is inferred from that range. pypdf may retain
cross-reference data, page objects and caches; per-page text/token buffers can
also be large. Native DuckDB/driver memory and OS cache are not measured by
tracemalloc. The full extracted table still consumes engine memory.

## Real-data qualification and status

- [12-PDF equivalence and allocation report](benchmarks/bronze-pdf-progressive-2026-11-27.json).
- [12-CSV equivalence report](benchmarks/bronze-csv-native-2026-11-27.json).
- [44-JSON equivalence and allocation report](benchmarks/bronze-json-memory-2026-11-27.json).

Every comparison checks names/types and EXCEPT ALL in both directions against
existing Bronze. All 197 protected Raw/Bronze files and active references remain
identical before/after qualification. Generated outputs are temporary and deleted.
No real full pipeline, reference activation, MotherDuck operation or deployment
was performed. The complete local suite passes **437 tests and 97 subtests**.

The application-buffer milestone covers all supported Bronze inputs. Remaining
work is a separate qualification of parser caches, oversized pages/documents,
native engine/driver/RSS memory and storage spill. Raw validators and Silver/Gold
processing should be audited in their own stages; this is not an end-to-end
pipeline memory bound.

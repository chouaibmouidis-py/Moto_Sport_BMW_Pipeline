# Real Bronze qualification: Parquet and Vortex

27 November 2026 — local experiment, not deployed.

## Decision evidence

All **68 enabled real reports** passed extraction/publication checks, exact
Parquet/Vortex content and logical-schema comparison, and loading into the tables
consumed by Silver. The current Vortex writer settings did **not** reduce storage
for this Bronze layout: total output was **6,326,672 bytes versus 1,733,515 bytes**
for Parquet, or **3.65 times as much** (+264.96%).

This differs from the earlier flat synthetic table's 47.78% reduction at one
million rows. Both observations are valid for their respective workloads. The
synthetic saving must not be presented as a saving achieved by this pipeline.

A subsequent [123 MB PDF-as-BLOB experiment](large_pdf_blob_experiment.md) found
only 0.27% larger Vortex storage. This further shows that 3.65× is specific to
the extracted Bronze workload, not a universal format multiplier.

**Decision after reviewing these results: keep Parquet in production and retain
Vortex as an experiment.** The local production path is again document.parquet
for every source format. The common publication architecture and its protections
are retained. Existing project data and the hosted release remain unchanged;
there was no need to convert or roll back data files.

After restoring the production Parquet policy, the complete local suite passed:
**402 tests and 97 subtests**. An explicit regression verifies production Bronze
construction with an empty Vortex extension location. The shared experimental
tests still use an explicitly installed Vortex extension.

## Dataset and results

Every enabled Raw file was already present locally; no report was downloaded.
The input set totals 9,548,811 bytes across 34 race pairs.

| Report family | Files | Parquet bytes | Vortex bytes | Vortex / Parquet |
| --- | ---: | ---: | ---: | ---: |
| Classification JSON | 22 | 326,623 | 1,348,928 | 4.13× |
| Pit-stop JSON | 22 | 868,679 | 3,539,312 | 4.07× |
| Classification CSV | 12 | 227,295 | 996,384 | 4.38× |
| Extracted pit-stop PDF | 12 | 310,918 | 442,048 | 1.42× |
| **Total** | **68** | **1,733,515** | **6,326,672** | **3.65×** |

JSON Bronze stores one document per row with JSON roots; these are not large,
flat analytical tables. The PDF output contains extracted fields and locations,
not the original PDF bytes. Its 12 reports produced 5,715 stop rows; the CSV
reports produced 516 participant rows. These counts describe the corresponding
formats, not the complete Gold population.

## Protocol

Tool: [qualify_real_bronze.py](../experiments/storage_formats/qualify_real_bronze.py).
Raw observations: [complete 68-document report](benchmarks/real-bronze-2026-11-27.json).

1. Snapshot SHA-256 hashes of existing Raw/Bronze files and active local references.
2. For each enabled source, build an isolated Parquet and Vortex using the same
   current source-specific builder and common publication/validation code.
3. Compare column names, logical types and exact row multisets using EXCEPT ALL
   in both directions. JSON columns are explicitly restored as JSON when read
   from Vortex. Their physical read type is VARCHAR without that adaptation.
4. Load the Vortex through the actual source loader used by Silver. Verify row
   counts, original column values/types and, for nonempty relations, source ID
   and Bronze fingerprint. The production PDF provenance checks remain enabled.
5. Materialize the extracted relation once, outside repeated timing. Initialize
   both writers, then run four paired rounds alternating P/V and V/P.
6. Measure shared publication (write, reread and validation) and a forced
   all-column scan with sum(hash(...)). The hash forces execution; exact
   multiset checks, not aggregated fingerprints, establish content equality.
7. Delete experiment outputs. Verify that all **197 protected files/references**
   have the same paths and SHA-256 hashes as before.

All three pass flags in the report are true for all 68 sources: content verified,
Silver input verified, and source unchanged. No active run was switched, no
existing Bronze was replaced, and MotherDuck was not contacted. Silver
transformations and the real full pipeline were not executed by this experiment.

## Timing observations

The following figures are **sums of per-document medians**, not single measured
end-to-end durations or throughput estimates.

| Repeated operation, all 68 documents | Parquet | Vortex |
| --- | ---: | ---: |
| Publication including reread and validation | 4.096 s | 5.640 s |
| All-column scan plus hashing | 0.228 s | 0.122 s |

Vortex scans were faster in this run, while validated publication was slower.
The very short query durations and uncontrolled OS activity preclude a general
performance ranking. Per-source observations are available in the JSON report.

Environment: DuckDB 1.5.4; Vortex extension revision 275ac23; Python 3.12;
macOS 13.7.8 on Intel. Repeated measurements use two threads and a 512 MB DuckDB
memory setting. Initial source builds use the builders' default engine settings;
their single elapsed observations include extraction and validation and are
recorded separately. Writer compression settings were not tuned.

Scans follow publication/validation in the same connection; caches were not
flushed. No competing test suite was run during the qualification, but other
machine activity was not isolated. No process-RSS measurement, cloud invoice,
network-egress saving or engine-memory bound is established.

## Reproduce

From the repository root, with the locked environment and Vortex already installed:

```bash
uv run --locked --no-sync python -m experiments.storage_formats.qualify_real_bronze \
  --project . \
  --extension-directory /private/tmp/bmw-vortex-extensions \
  --pairs 4 \
  --report /private/tmp/real-bronze-qualification.json
```

The report destination's parent must exist. Missing Raw files or mismatched
declared expected hashes fail the qualification; there is no automatic download.
Use another explicit extension directory on other platforms. Generated Bronze
files live in a unique system temporary directory and are removed afterwards.

## Remaining work

- Decide the deployment format in review; Vortex is functionally qualified for
  these reports but the proposed storage reduction is not achieved. **Resolved:
  Parquet remains the production format; Vortex stays experimental.**
- If desired, test compression/compaction or a different physical layout as a
  separate experiment, preserving document boundaries and provenance contracts.
- Continue the independent Bronze memory audit: the later
  [JSON maintenance](bronze_json_memory.md) removed full Python document copies;
  [PDF batching and shared streamed hashing](bronze_progressive_processing.md)
  are also locally validated. Parser caches and native engine memory remain
  unbounded by these application guards.
- Test Linux CI remotely after an authorized push. Workflow changes install the
  extension explicitly; no workflow was triggered during this qualification.
- Existing Bronze conversion, retention cleanup, hosted deployment and Silver/Gold
  storage changes are separate actions, not outcomes of this local experiment.

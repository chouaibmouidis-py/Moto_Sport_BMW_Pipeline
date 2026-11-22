# Runtime responsibilities and logs

See the [code map](code_map.md) for implementation owners and output paths.

One manifest selects reports. One orchestrator executes acquisition, Bronze,
processing and Gold. Readers and validators dispatch on the declared document
type and format; normalization and quality rules dispatch on the data contract.
Season is source context and a selection parameter, never a separate program.

Airflow schedules seven tasks: manifest validation, archive restoration, Raw,
Bronze, processing, Gold and MotherDuck publication. Each processing stage calls
`run_pipeline.py --stage ...`; no inspection script runs in the production DAG.
An exception prevents subsequent tasks from running. GitHub Actions executes the
DAG as a batch; it does not provide a permanent Airflow scheduler.

Processing prepares unique candidate outputs and records their fingerprints.
The processing reference changes only after all selected reports, quality outputs
and marts succeed. Gold snapshots that complete version and activates separately
after verification. Failures preserve the previous Gold. Failed candidate files
may remain for investigation; they are not active outputs.

```bash
uv run python run_pipeline.py --verbose --log-file data/logs/pipeline.log
```

All stages run in the same Python process when using the complete CLI. Logging
configuration is shared; there is no subprocess environment to synchronize.
Airflow invokes stages in separate processes, each using the same logging setup.
INFO records progress and publications, DEBUG adds diagnostics, and exceptions
propagate to the caller. Run context is attached where the existing builders
establish it; a missing context is displayed as `run=-`.

This architecture does not prove that an official report is correct, discover
source revisions, or remove PDF layout limitations. Those remain source
qualification and operational responsibilities. The dataset's historical
qualification documents retain the evidence and limits observed for each race.

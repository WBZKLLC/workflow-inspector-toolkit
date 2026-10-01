# Quickstart

## Run locally

Use Python 3.11 or newer. Download the repository ZIP and extract it, or clone the repository. Open a terminal in the extracted project directory, the one containing `README.md` and `workflow_inspector_toolkit/`.

```bash
python --version
python -m workflow_inspector_toolkit validate examples/baseline.csv
```

Expected validation result: `valid` is `true`, `events` is `12`, and the contract is `four-event-subset-v1`.

On macOS/Linux, the command may be `python3`. On Windows, `py -3` can be substituted for `python`. There is no requirement to create an account, supply credentials, connect a vendor, or buy anything.

## Analyze and compare

```bash
python -m workflow_inspector_toolkit analyze examples/baseline.csv
python -m workflow_inspector_toolkit compare examples/baseline.csv examples/followup.csv
```

Analysis returns metrics, sample sizes, coverage counts, pair-level exclusion statuses, the earliest/latest included events, and a SHA-256 of the normalized input. Comparison returns both analyses and their descriptive differences.

## Generate a report

```bash
python -m workflow_inspector_toolkit report examples/baseline.csv --followup examples/followup.csv --synthetic --output demo-report.html
```

Open `demo-report.html` locally. `--synthetic` explicitly marks invented sample data. Do not use that flag for genuine operational analysis. Remove `--followup` to produce a single-file report.

Reports contain aggregate timings, coverage counts, included event spans, and input hashes. They omit case references, but they can still disclose business-sensitive operational facts. Share them deliberately.

## Use your own input

Create `local-data/` and `local-reports/` first. Start with `examples/template.csv`, which is a header-only template, not a valid nonempty example.

```bash
python -m workflow_inspector_toolkit validate local-data/events.csv
python -m workflow_inspector_toolkit analyze local-data/events.csv --output local-reports/analysis.json
python -m workflow_inspector_toolkit report local-data/events.csv --output local-reports/report.html
```

The toolkit never overwrites an existing output. Choose a fresh path on repeat runs. It does not create missing parent folders automatically. Validation errors go to standard error and return exit code `2`; success returns `0`.

## Python library

```python
from workflow_inspector_toolkit import analyze, load_events

result = analyze(load_events("examples/baseline.csv"))
metric = result["metrics"]["median_handoff_wait_hours"]
print(metric["value"], metric["unit"], metric["sample_size"])
```

No endpoint or API key is required. This is a local Python library, not a client for a hosted service.

## Optional installation

The package is installable from this checkout. This release does not claim a published package on PyPI.

```bash
python -m venv .venv
# Activate the virtual environment using your operating system's normal command.
python -m pip install .
wi-toolkit validate examples/baseline.csv
```

Installation may download the setuptools build tool when it is not already available. Running directly from the repository, as shown above, requires no package download and has no runtime dependencies.

## Troubleshooting

| Message or symptom | Resolution |
|---|---|
| `No module named workflow_inspector_toolkit` | Run from the repository root, or install this checkout in your active environment. |
| Input contains no events | Add real event rows; the header-only template intentionally fails validation. |
| Unsupported event type | Map only the four documented event types. Do not relabel unrelated events merely to pass validation. |
| Invalid timezone | Include seconds and `Z` or an explicit offset. |
| Unrecognized metadata fields | Remove non-contract metadata from a local working copy; preserve your original export separately. |
| Output already exists | Choose a new output filename. No file is overwritten automatically. |
| A duration is `null` | Inspect the corresponding case or handoff status. Do not replace missing evidence with zero. |

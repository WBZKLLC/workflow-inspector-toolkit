# Local architecture

```text
Your local CSV / JSON
        |
        v
Bounded file reader: UTF-8, 5 MiB, 10,000 events
        |
        v
Four-event contract validation and UTC normalization
        |
        v
Explicit pair matching: case / stage / handoff reference
        |
        +--> Descriptive medians and observed-count coverage
        |
        +--> Excluded-pair statuses and normalized input hash
        |
        v
Local JSON or self-contained HTML
```

The file reader, validator, analyzer, and comparison functions live in `workflow_inspector_toolkit/core.py`. The command-line interface lives in `__main__.py`; HTML presentation is in `report.py`.

## Security boundaries

The runtime contains no HTTP client, telemetry, external asset requests, credentials, background scheduler, or production deployment. Input content is never evaluated as code. HTML reports contain no JavaScript and escape text. Output writes use exclusive creation rather than overwriting existing files.

CLI errors name fields and record positions without printing offending input values. JSON analysis still includes reference codes; it should not be treated as an anonymous public report. HTML omits those record references but includes business-sensitive aggregate information and input fingerprints.

## Not part of this repository

Hosted-service infrastructure, production authentication, billing, customer records, internal prompts, proprietary calculations, and deployment configuration are outside this toolkit's scope. There is no dependency on another repository or its commit history.

## Automation

The CI workflow checks only this repository. It has read-only content permissions, disables credential persistence, runs standard-library tests, and verifies checked-in example reproducibility. It does not deploy, publish a package, contact a customer system, or require secrets. The checkout action is pinned to an immutable commit; updates need review.

# Event data contract: four-event-subset-v1

This toolkit accepts a deliberately restricted event format for local descriptive analysis. The field names align with Workflow Inspector's published onboarding activity example. The toolkit is **not** a complete hosted API specification and does not claim live upload compatibility testing.

## CSV columns

The CSV header must contain exactly these eight unique names. Column order may vary. Use UTF-8; a UTF-8 byte-order mark is accepted.

```csv
external_event_id,case_key,stage,event_type,occurred_at,owner_key,actor_key,metadata
```

| Field | Rule |
|---|---|
| `external_event_id` | Unique within the file. A 1-128 character reference code. Duplicate IDs reject the entire input. |
| `case_key` | A reference for one workflow instance, not a customer name. Use a separate reference for a separate workflow cycle. |
| `stage` | A step or handoff-stage reference. The ready and accepted records must agree. |
| `event_type` | Exactly `workflow_started`, `workflow_completed`, `handoff_ready`, or `handoff_accepted`. |
| `occurred_at` | Date/time with seconds and a timezone: `2026-05-01T09:00:00Z` or `2026-05-01T09:00:00-05:00`. Up to six fractional-second digits are allowed. |
| `owner_key` | Team/person reference or empty. A blank alone is not evidence that ownership was observed to be missing. |
| `actor_key` | Actor reference or empty. Not used to infer ownership. |
| `metadata` | Empty or a JSON object serialized inside the CSV field. Only `correlation_key` and `owner_observed` are allowed. |

Reference codes begin with an ASCII letter or digit; remaining characters may be letters, digits, `_`, `.`, `:`, or `-`. Spaces, email-address syntax, formula prefixes, URLs, and control characters are rejected. This restriction is not a guarantee of anonymization.

For a handoff, `metadata.correlation_key` is required and follows the same reference-code rule. It identifies a single ready/accepted pair within a case and stage. Reusing it for multiple attempts makes that group ambiguous; give distinct handoffs distinct references.

`metadata.owner_observed` must be a JSON boolean when present. Use `true` only when the source actually observed ownership. Do not fill it automatically merely because an export has an owner column.

CSV quoting follows standard double-quote escaping. The supplied CSV files demonstrate quoted metadata. Unknown columns, malformed rows, and unrecognized metadata cause validation errors; nothing is silently discarded.

## JSON shape

A JSON file contains a nonempty array of objects. The first five fields are required. `owner_key` and `actor_key` default to empty strings, and `metadata` defaults to an empty object. Null values are not substitutes for empty strings or an empty object.

```json
[
  {
    "external_event_id": "example-ready-001",
    "case_key": "example-case-001",
    "stage": "sales-to-implementation",
    "event_type": "handoff_ready",
    "occurred_at": "2026-05-01T10:00:00Z",
    "owner_key": "implementation-team",
    "actor_key": "",
    "metadata": {"correlation_key": "handoff-001", "owner_observed": true}
  }
]
```

See [the JSON Schema](../schemas/events.schema.json). The runtime validator additionally enforces unique event IDs and valid calendar/offset values. Schema validation alone is insufficient for those cross-record and semantic checks.

## Normalization and limits

All timestamps are normalized to UTC. Events are sorted by timestamp, then event reference. The normalized-event hash is insensitive to input row order, equivalent timestamp offsets, CSV versus JSON serialization, JSON key order, and omitted optional defaults. It is **not** the original file's byte hash and does not prove authenticity or completeness.

The file reader limits each input to **5 MiB** and **10,000 events**. Invalid input fails as a whole. The direct Python API also limits event count; callers supplying in-memory objects remain responsible for their own memory limits.

## Supported source facts

The published example uses these field names and core lifecycle events:
[Workflow Inspector public event example](https://workflow-inspector.com/examples/onboarding-events-example.csv).
The local contract in this repository is intentionally narrower than a general product import contract. Consult current product documentation before sending anything to a hosted workspace.

# Integrating the toolkit without inventing a connection

Version 0.1.0 provides a **local Python library and normalized CSV/JSON inputs**. It does not log into external services, subscribe to webhooks, upload to Workflow Inspector, backfill history, or include a hosted-service SDK.

## Supported local integration

An existing authorized export or internal event-producing system can prepare a local file that meets the [data contract](data-contract.md). Run `validate`, inspect the output of `analyze`, and review ambiguous or missing pairs before using a number.

```python
from workflow_inspector_toolkit import analyze, validate_events

normalized_events = [{
    "external_event_id": "example-start-001",
    "case_key": "example-case-001",
    "stage": "implementation",
    "event_type": "workflow_started",
    "occurred_at": "2026-05-01T09:00:00Z"
}]
result = analyze(validate_events(normalized_events))
assert result["metrics"]["median_workflow_duration_hours"]["value"] is None
```

The missing completion stays unmeasured. A useful adapter must preserve that absence rather than fabricate a completion.

## Mapping rules

Use a real source timestamp for the event. Do not substitute export time for event time. Map only events whose business meaning genuinely matches the four supported event types. Preserve stable source event references and use case references that identify one workflow instance.

A handoff requires an explicit pairing reference, a stage, readiness, and acceptance. A generic task status such as `Done` does not automatically prove that another team accepted work. An assignee field does not automatically prove that ownership was observed at the time of every historical event.

Keep a private mapping record from source fields to normalized fields. The toolkit does not perform this business-semantic decision for you.

## Named providers

Jira, Salesforce, HubSpot, GitHub, and other tools are not advertised as native integrations in this toolkit. A manually prepared export from one of them does not turn the toolkit into a certified, live, or vendor-endorsed connector.

For any current hosted Workflow Inspector connections, activation requirements, and product-specific credentials, consult the [current product guide](https://workflow-inspector.com/how-it-works). No access credentials belong in this repository, its issue tracker, or its examples.

## Scope

There is no hosted endpoint, authentication scheme, or undocumented URL embedded in this release. No package is represented as an official third-party vendor SDK. New native clients should be added only after an intentionally public contract and end-to-end behavior are verified.

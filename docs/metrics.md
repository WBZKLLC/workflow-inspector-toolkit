# Metric definitions and interpretation

Every number here is an ordinary descriptive statistic computed from the supplied records. The toolkit does not implement a proprietary indicator, weighting scheme, risk category, decision threshold, validated benchmark, or causal model.

## Handoff waiting time

Group handoff events by **`case_key` + `stage` + `metadata.correlation_key`**. A group contributes one observation only when there is exactly one `handoff_ready` event, exactly one `handoff_accepted` event, and acceptance is not earlier than readiness.

```text
handoff_wait_hours = (accepted_timestamp_UTC - ready_timestamp_UTC) / 3600 seconds
```

The reported metric is the median of those observed durations. The sample size is the number of measured handoff pairs, not the number of events or customers. Cases with several distinct handoffs can contribute several observations. A workflow with more recorded handoffs therefore contributes more handoff observations; this is not an equal-weight-per-case measure.

## Recorded workflow duration

Group by `case_key`. A case contributes one duration when it contains exactly one `workflow_started` event, exactly one `workflow_completed` event, and completion is not earlier than the start.

```text
workflow_duration_hours = (completed_timestamp_UTC - started_timestamp_UTC) / 3600 seconds
```

Start and completion may have different stage references. Each case contributes at most one measured workflow duration. A reused case reference with multiple starts or completions is ambiguous, not automatically split into cycles.

## Median, rounding, and missing values

For an odd number of observations, the median is the middle sorted value. For an even number, it is the arithmetic mean of the two middle values. Durations are calculated at timestamp precision; reported values are rounded to six decimal places.

With no usable observations, the value is `null` and the sample size is zero. A valid zero-duration pair remains `0` with a nonzero sample size. Missing evidence is never converted to a zero-duration success.

## Pair statuses

| Status | Meaning |
|---|---|
| `measured` | Exactly one ordered pair exists. |
| `missing_start` | The workflow start or handoff-ready event is absent; the group may lack both boundaries. |
| `missing_end` | A start/ready record exists without its matching completion/acceptance. |
| `ambiguous` | More than one start/ready or completion/acceptance is present. |
| `out_of_order` | The completion/acceptance is earlier than the start/ready record. |

The last four statuses are excluded from duration medians. Full case and handoff status lists remain in JSON output. Reports show measured/seen coverage totals. Excluding incomplete records can bias a median toward easier or faster completed work; review excluded counts before comparing files.

## Explicit ownership observations

`ownership_observed_events` counts events with `metadata.owner_observed` equal to `true`. `explicit_missing_owner_events` counts the subset of those events whose `owner_key` is empty.

These are **event counts**, not time spent unowned, unique affected customers, staff ratings, or inferred ownership failures. Repeated observations can refer to the same case. An event without `owner_observed: true` contributes to neither count.

## Baseline/follow-up difference

```text
delta_hours = followup_median - baseline_median
delta_percent = 100 * (followup_median - baseline_median) / baseline_median
```

Differences use the reported medians. A negative delta means a lower observed elapsed time. If either median is missing, both differences are `null`; a zero baseline makes the percentage difference `null`. Each side retains its own sample size and included event span.

Files are independent input sets. The toolkit does not establish matched cohorts, equal observation windows, process equivalence, statistical significance, or causation. Overlapping windows, duplicated operational histories across files, survivorship bias, and changed instrumentation require human review.

## What the timestamps do not establish

Elapsed clock time includes nights, weekends, and pauses. It is not business-hours time, active effort, cost, lost revenue, or guaranteed savings. An event span is the range of included records, not an independently verified collection period. The toolkit does not verify that source events happened, that clocks were synchronized, or that history is complete.

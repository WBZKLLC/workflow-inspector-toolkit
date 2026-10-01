"""Validate a conservative event subset and calculate descriptive elapsed times.

Everything in this module runs locally, using Python's standard library.
There is deliberately no network client, score, ranking, or inferred causality.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

COLUMNS = (
    "external_event_id", "case_key", "stage", "event_type", "occurred_at",
    "owner_key", "actor_key", "metadata",
)
REQUIRED = set(COLUMNS[:5])
EVENT_TYPES = frozenset({
    "workflow_started", "workflow_completed", "handoff_ready", "handoff_accepted",
})
MAX_BYTES = 5 * 1024 * 1024
MAX_EVENTS = 10_000
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z"
)
LIMITATIONS = [
    "Descriptive statistics only; no proprietary score or validated benchmark.",
    "Elapsed clock hours, not business hours or recorded work effort.",
    "Only complete, unambiguous pairs contribute to duration statistics.",
    "Missing, duplicate-type, or reversed pairs are flagged, never converted to zero.",
    "Event coverage depends on the supplied file; absent records do not prove absent problems.",
    "Do not compare different processes or infer that a change caused an improvement.",
]


class ValidationError(ValueError):
    """A safe-to-display error that does not echo potentially sensitive input."""


def parse_timestamp(value: str) -> datetime:
    """Require an explicit timezone and canonical date/time separators."""
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ValidationError("occurred_at must include seconds and an explicit timezone")
    # datetime normalizes some invalid offset minutes; reject them first.
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValidationError("occurred_at has an invalid timezone offset")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ValidationError("occurred_at is not a valid date/time") from None


def _identifier(value: Any, field: str, *, optional: bool = False) -> str:
    if optional and value == "":
        return ""
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValidationError(f"{field} must be a 1-128 character reference code")
    return value


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValidationError("JSON contains a duplicate object key")
        obj[key] = value
    return obj


def _reject_json_constant(_: str) -> None:
    raise ValidationError("JSON cannot contain non-finite numbers")


def _read_json(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_unique_json_object,
                          parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, RecursionError):
        raise ValidationError("invalid JSON") from None


def validate_events(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate normalized events, preserve IDs, and return UTC-sorted copies.

    Unknown columns and metadata keys fail closed. No row is silently dropped.
    Empty owner/actor references are allowed; this is not proof of missing ownership.
    """
    if isinstance(rows, (dict, str, bytes)):
        raise ValidationError("events must be an array of objects")
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        iterator = iter(rows)
    except TypeError:
        raise ValidationError("events must be an array of objects") from None
    for number, row in enumerate(iterator, 1):
        if number > MAX_EVENTS:
            raise ValidationError(f"input exceeds {MAX_EVENTS} events")
        try:
            if not isinstance(row, dict):
                raise ValidationError("each event must be an object")
            if set(row) - set(COLUMNS):
                raise ValidationError("unrecognized event fields")
            if REQUIRED - set(row):
                raise ValidationError("required event fields are missing")
            item = dict(row)
            for field in ("external_event_id", "case_key", "stage"):
                item[field] = _identifier(item[field], field)
            for field in ("owner_key", "actor_key"):
                item[field] = _identifier(item.get(field, ""), field, optional=True)
            if not isinstance(item["event_type"], str) or item["event_type"] not in EVENT_TYPES:
                raise ValidationError("unsupported event_type; see the four-event data contract")
            instant = parse_timestamp(item["occurred_at"])
            item["occurred_at"] = instant.isoformat().replace("+00:00", "Z")
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValidationError("metadata must be an object")
            if set(metadata) - {"correlation_key", "owner_observed"}:
                raise ValidationError("unrecognized metadata fields")
            if "correlation_key" in metadata:
                _identifier(metadata["correlation_key"], "correlation_key")
            if "owner_observed" in metadata and type(metadata["owner_observed"]) is not bool:
                raise ValidationError("owner_observed must be a boolean")
            if item["event_type"].startswith("handoff_") and "correlation_key" not in metadata:
                raise ValidationError("handoff events require metadata.correlation_key")
            item["metadata"] = dict(metadata)
            if item["external_event_id"] in seen:
                raise ValidationError("duplicate external_event_id")
            seen.add(item["external_event_id"])
            events.append(item)
        except ValidationError as exc:
            raise ValidationError(f"event {number}: {exc}") from None
    if not events:
        raise ValidationError("input contains no events")
    return sorted(events, key=lambda e: (parse_timestamp(e["occurred_at"]), e["external_event_id"]))


def load_events(path: str | Path) -> list[dict[str, Any]]:
    """Load UTF-8 CSV or a JSON event array, bounded to 5 MiB and 10,000 events."""
    source = Path(path)
    if source.suffix.lower() not in {".csv", ".json"}:
        raise ValidationError("input must use the .csv or .json extension")
    try:
        with source.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        raise ValidationError("input file could not be read") from None
    if len(raw) > MAX_BYTES:
        raise ValidationError("input exceeds the 5 MiB file limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("input must be UTF-8 text") from None
    if source.suffix.lower() == ".json":
        parsed = _read_json(text)
        if not isinstance(parsed, list):
            raise ValidationError("JSON input must be an array of event objects")
        return validate_events(parsed)
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValidationError("CSV contains duplicate column names")
        if set(headers) != set(COLUMNS):
            raise ValidationError("CSV requires exactly the eight documented column names")
        rows: list[dict[str, Any]] = []
        for number, row in enumerate(reader, 1):
            if number > MAX_EVENTS:
                raise ValidationError(f"input exceeds {MAX_EVENTS} events")
            if None in row or any(value is None for value in row.values()):
                raise ValidationError(f"CSV record {number} has an incorrect number of fields")
            row["metadata"] = _read_json(row["metadata"]) if row["metadata"] else {}
            rows.append(row)
    except csv.Error:
        raise ValidationError("invalid CSV quoting or field size") from None
    return validate_events(rows)


def _hours(start: dict[str, Any], end: dict[str, Any]) -> float:
    return (parse_timestamp(end["occurred_at"]) - parse_timestamp(start["occurred_at"])).total_seconds() / 3600


def _stat(values: list[float]) -> dict[str, Any]:
    return {"value": round(median(values), 6) if values else None,
            "unit": "hours", "sample_size": len(values)}


def _pair(starts: list[dict[str, Any]], ends: list[dict[str, Any]]) -> tuple[str, float | None]:
    if len(starts) > 1 or len(ends) > 1:
        return "ambiguous", None
    if not starts:
        return "missing_start", None
    if not ends:
        return "missing_end", None
    duration = _hours(starts[0], ends[0])
    if duration < 0:
        return "out_of_order", None
    return "measured", duration


def analyze(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Report measured pairs and exclusions. This is not the hosted scoring engine."""
    events = validate_events(rows)
    cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    handoffs: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        cases[event["case_key"]].append(event)
        if event["event_type"].startswith("handoff_"):
            key = (event["case_key"], event["stage"], event["metadata"]["correlation_key"])
            handoffs[key].append(event)
    case_details: list[dict[str, Any]] = []
    handoff_details: list[dict[str, Any]] = []
    workflow_values: list[float] = []
    handoff_values: list[float] = []
    for key, items in sorted(cases.items()):
        starts = [e for e in items if e["event_type"] == "workflow_started"]
        ends = [e for e in items if e["event_type"] == "workflow_completed"]
        status, value = _pair(starts, ends)
        if value is not None:
            workflow_values.append(value)
        case_details.append({"case_key": key, "status": status,
                             "duration_hours": round(value, 6) if value is not None else None})
    for (case, stage, correlation), items in sorted(handoffs.items()):
        ready = [e for e in items if e["event_type"] == "handoff_ready"]
        accepted = [e for e in items if e["event_type"] == "handoff_accepted"]
        status, value = _pair(ready, accepted)
        if value is not None:
            handoff_values.append(value)
        handoff_details.append({"case_key": case, "stage": stage,
                                "correlation_key": correlation, "status": status,
                                "duration_hours": round(value, 6) if value is not None else None})
    observed = [e for e in events if e["metadata"].get("owner_observed") is True]
    normalized = json.dumps(events, sort_keys=True, separators=(",", ":")).encode()
    return {
        "format_version": "1.0", "tool": "Workflow Inspector Toolkit", "tool_version": "0.1.0",
        "normalized_events_sha256": hashlib.sha256(normalized).hexdigest(),
        "event_span": {"first": events[0]["occurred_at"], "last": events[-1]["occurred_at"]},
        "counts": {
            "events": len(events), "cases": len(cases),
            "measured_workflows": len(workflow_values),
            "excluded_workflows": len(cases) - len(workflow_values),
            "handoffs": len(handoffs), "measured_handoffs": len(handoff_values),
            "excluded_handoffs": len(handoffs) - len(handoff_values),
            "ownership_observed_events": len(observed),
            "explicit_missing_owner_events": sum(not e["owner_key"] for e in observed),
        },
        "metrics": {"median_handoff_wait_hours": _stat(handoff_values),
                    "median_workflow_duration_hours": _stat(workflow_values)},
        "cases": case_details, "handoffs": handoff_details,
        "limitations": list(LIMITATIONS),
    }


def compare(baseline: Iterable[dict[str, Any]], followup: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Compare two independent input sets; negative deltas mean lower elapsed time."""
    before, after = analyze(baseline), analyze(followup)
    metrics: dict[str, Any] = {}
    for name, old in before["metrics"].items():
        new = after["metrics"][name]
        a, b = old["value"], new["value"]
        delta = round(b - a, 6) if a is not None and b is not None else None
        percent = round((b - a) / a * 100, 6) if a is not None and b is not None and a != 0 else None
        metrics[name] = {"baseline": old, "followup": new,
                         "delta_hours": delta, "delta_percent": percent}
    return {"format_version": "1.0", "tool": "Workflow Inspector Toolkit", "tool_version": "0.1.0",
            "kind": "comparison", "metrics": metrics, "baseline": before, "followup": after,
            "limitations": list(LIMITATIONS) + [
                "This comparison does not establish statistical significance or causal improvement.",
                "Cohort, process, event coverage, and observation-window equivalence require human review.",
            ]}

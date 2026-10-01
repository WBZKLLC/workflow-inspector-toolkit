from __future__ import annotations
import contextlib
import copy
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from workflow_inspector_toolkit import ValidationError, analyze, compare, load_events, validate_events
from workflow_inspector_toolkit.core import parse_timestamp, MAX_BYTES, MAX_EVENTS
from workflow_inspector_toolkit.report import render_report
from workflow_inspector_toolkit.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples/baseline.csv"
FOLLOW = ROOT / "examples/followup.csv"


def event(kind="workflow_started", hour=9, event_id="event-001", **changes):
    item = dict(external_event_id=event_id, case_key="case-001", stage="intake",
                event_type=kind, occurred_at=f"2026-05-01T{hour:02d}:00:00Z",
                owner_key="team-a", actor_key="", metadata={})
    if kind.startswith("handoff_"):
        item["metadata"] = {"correlation_key": "handoff-001"}
    item.update(changes)
    return item


class ValidationTests(unittest.TestCase):
    def test_csv_and_json_normalize_identically(self):
        self.assertEqual(load_events(BASE), load_events(BASE.with_suffix(".json")))
    def test_empty_input_rejected(self):
        with self.assertRaises(ValidationError): validate_events([])
    def test_non_iterable_rejected(self):
        for bad in (None, 4, True):
            with self.subTest(bad=bad), self.assertRaises(ValidationError): validate_events(bad)
    def test_wrong_container_rejected(self):
        for bad in ({}, "string", b"bytes", [42]):
            with self.subTest(bad=bad), self.assertRaises(ValidationError): validate_events(bad)
    def test_missing_fields_rejected(self):
        e=event(); del e["stage"]
        with self.assertRaises(ValidationError): validate_events([e])
    def test_unknown_columns_rejected(self):
        with self.assertRaises(ValidationError): validate_events([event(secret="private")])
    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValidationError,"duplicate external"):
            validate_events([event(),event()])
    def test_unknown_event_not_silently_dropped(self):
        with self.assertRaises(ValidationError): validate_events([event("workflow_reopened")])
    def test_non_string_event_rejected(self):
        with self.assertRaises(ValidationError): validate_events([event(event_type=[])])
    def test_timezone_required(self):
        with self.assertRaises(ValidationError): parse_timestamp("2026-05-01T10:00:00")
    def test_space_separator_rejected(self):
        with self.assertRaises(ValidationError): parse_timestamp("2026-05-01 10:00:00Z")
    def test_impossible_date_rejected(self):
        with self.assertRaises(ValidationError): parse_timestamp("2026-02-30T10:00:00Z")
    def test_offset_minutes_rejected(self):
        with self.assertRaises(ValidationError): parse_timestamp("2026-05-01T10:00:00+01:99")
    def test_timezone_normalized(self):
        e=event(occurred_at="2026-05-01T10:00:00-05:00")
        self.assertEqual(validate_events([e])[0]["occurred_at"],"2026-05-01T15:00:00Z")
    def test_microseconds_supported(self):
        self.assertEqual(parse_timestamp("2026-05-01T10:00:00.123456Z").microsecond,123456)
    def test_email_and_formula_refs_rejected(self):
        for bad in ("person@example.com", "=SUM(A1)", "+cmd", "-cmd", "@cmd", "a\nb", "" , "x"*129):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validate_events([event(case_key=bad)])
    def test_metadata_must_be_object(self):
        for bad in ([],None,"{}"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validate_events([event(metadata=bad)])
    def test_metadata_unknown_keys_rejected(self):
        with self.assertRaises(ValidationError): validate_events([event(metadata={"notes":"sensitive"})])
    def test_owner_observed_must_be_bool(self):
        for bad in ("true",1,None):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validate_events([event(metadata={"owner_observed":bad})])
    def test_handoff_requires_correlation(self):
        with self.assertRaises(ValidationError): validate_events([event("handoff_ready",metadata={})])
    def test_optional_fields_default(self):
        e=event()
        for key in ("owner_key","actor_key","metadata"): del e[key]
        self.assertEqual(validate_events([e])[0]["metadata"],{})
    def test_input_is_not_mutated(self):
        e=event(); saved=copy.deepcopy(e); validate_events([e]); self.assertEqual(e,saved)
    def test_events_limit(self):
        rows=(event(event_id=f"e-{i}") for i in range(MAX_EVENTS+1))
        with self.assertRaises(ValidationError): validate_events(rows)


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def load_text(self,text,extension="csv",encoding="utf-8"):
        p=self.root/f"input.{extension}";p.write_text(text,encoding=encoding);return load_events(p)
    def test_missing_file_has_safe_error(self):
        with self.assertRaisesRegex(ValidationError,"could not be read"):
            load_events(self.root/"missing.csv")
    def test_unknown_extension_rejected(self):
        with self.assertRaises(ValidationError): self.load_text("text", "txt")
    def test_bom_supported(self):
        self.assertEqual(self.load_text(BASE.read_text(),encoding="utf-8-sig"),load_events(BASE))
    def test_unknown_header_rejected(self):
        with self.assertRaises(ValidationError): self.load_text(BASE.read_text().replace("actor_key","actor_email",1))
    def test_duplicate_header_rejected(self):
        with self.assertRaises(ValidationError): self.load_text(BASE.read_text().replace("actor_key","owner_key",1))
    def test_extra_csv_cells_rejected(self):
        lines=BASE.read_text().splitlines();lines[1]+=",extra"
        with self.assertRaises(ValidationError): self.load_text("\n".join(lines))
    def test_missing_csv_cells_rejected(self):
        lines=BASE.read_text().splitlines();lines[1]=",".join(lines[1].split(",")[:-1])
        with self.assertRaises(ValidationError): self.load_text("\n".join(lines))
    def test_malformed_quote_rejected(self):
        with self.assertRaises(ValidationError): self.load_text(BASE.read_text().splitlines()[0]+'\n"unclosed')
    def test_header_only_not_sufficient(self):
        with self.assertRaises(ValidationError): load_events(ROOT/"examples/template.csv")
    def test_invalid_json_rejected(self):
        with self.assertRaises(ValidationError): self.load_text("[broken", "json")
    def test_json_object_not_array_rejected(self):
        with self.assertRaises(ValidationError): self.load_text("{}", "json")
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValidationError): self.load_text('[{"x":1,"x":2}]',"json")
    def test_json_nan_rejected(self):
        with self.assertRaises(ValidationError): self.load_text('[{"x":NaN}]',"json")
    def test_oversized_file_rejected(self):
        p=self.root/"large.csv";p.write_bytes(b"a"*(MAX_BYTES+1))
        with self.assertRaises(ValidationError): load_events(p)
    def test_invalid_encoding_rejected(self):
        p=self.root/"invalid.csv";p.write_bytes(b"\xff\xfe")
        with self.assertRaises(ValidationError): load_events(p)


class MetricTests(unittest.TestCase):
    def test_expected_baseline(self):
        result=analyze(load_events(BASE))
        self.assertEqual(result["metrics"]["median_handoff_wait_hours"],dict(value=10,unit="hours",sample_size=3))
        self.assertEqual(result["metrics"]["median_workflow_duration_hours"]["value"],40)
    def test_expected_followup(self):
        result=analyze(load_events(FOLLOW))
        self.assertEqual(result["metrics"]["median_handoff_wait_hours"]["value"],3)
        self.assertEqual(result["metrics"]["median_workflow_duration_hours"]["value"],22)
    def test_order_independent_hash_and_results(self):
        events=load_events(BASE)
        self.assertEqual(analyze(events),analyze(reversed(events)))
    def test_missing_completion_is_null(self):
        result=analyze([event()])
        self.assertIsNone(result["metrics"]["median_workflow_duration_hours"]["value"])
        self.assertEqual(result["cases"][0]["status"],"missing_end")
    def test_missing_start_is_null(self):
        self.assertEqual(analyze([event("workflow_completed")])["cases"][0]["status"],"missing_start")
    def test_reversed_pair_is_excluded(self):
        result=analyze([event(hour=12),event("workflow_completed",hour=9,event_id="e-2")])
        self.assertEqual(result["cases"][0]["status"],"out_of_order")
    def test_repeated_start_ambiguous(self):
        result=analyze([event(),event(event_id="e-2"),event("workflow_completed",hour=12,event_id="e-3")])
        self.assertEqual(result["cases"][0]["status"],"ambiguous")
    def test_duplicate_completion_ambiguous(self):
        result=analyze([event(),event("workflow_completed",hour=12,event_id="e-2"),event("workflow_completed",hour=14,event_id="e-3")])
        self.assertEqual(result["cases"][0]["status"],"ambiguous")
    def test_zero_is_a_real_measured_value(self):
        result=analyze([event(),event("workflow_completed",event_id="e-2")])
        self.assertEqual(result["metrics"]["median_workflow_duration_hours"]["value"],0)
    def test_correlation_does_not_cross_cases(self):
        rows=[event("handoff_ready"),event("handoff_accepted",hour=12,event_id="e-2",case_key="case-002")]
        self.assertEqual(analyze(rows)["counts"]["measured_handoffs"],0)
    def test_correlation_does_not_cross_stages(self):
        rows=[event("handoff_ready"),event("handoff_accepted",hour=12,event_id="e-2",stage="other")]
        self.assertEqual(analyze(rows)["counts"]["measured_handoffs"],0)
    def test_distinct_correlation_does_not_pair(self):
        rows=[event("handoff_ready"),event("handoff_accepted",hour=12,event_id="e-2",metadata={"correlation_key":"different"})]
        self.assertEqual(analyze(rows)["counts"]["measured_handoffs"],0)
    def test_repeated_ready_is_not_guessed(self):
        rows=[event("handoff_ready"),event("handoff_ready",event_id="e-2"),event("handoff_accepted",hour=12,event_id="e-3")]
        self.assertEqual(analyze(rows)["handoffs"][0]["status"],"ambiguous")
    def test_negative_handoff_excluded(self):
        rows=[event("handoff_ready",hour=12),event("handoff_accepted",hour=9,event_id="e-2")]
        self.assertEqual(analyze(rows)["handoffs"][0]["status"],"out_of_order")
    def test_blank_owner_does_not_infer_gap(self):
        result=analyze([event(owner_key="")])
        self.assertEqual(result["counts"]["explicit_missing_owner_events"],0)
        self.assertEqual(result["counts"]["ownership_observed_events"],0)
    def test_explicit_owner_observation_is_counted(self):
        result=analyze([event(owner_key="",metadata={"owner_observed":True})])
        self.assertEqual(result["counts"]["explicit_missing_owner_events"],1)
        self.assertEqual(result["counts"]["ownership_observed_events"],1)
    def test_offset_elapsed_time(self):
        rows=[event(occurred_at="2026-05-01T09:00:00-05:00"),event("workflow_completed",event_id="e-2",occurred_at="2026-05-01T18:00:00Z")]
        self.assertEqual(analyze(rows)["metrics"]["median_workflow_duration_hours"]["value"],4)
    def test_comparison_delta(self):
        metric=compare(load_events(BASE),load_events(FOLLOW))["metrics"]["median_handoff_wait_hours"]
        self.assertEqual(metric["delta_hours"],-7)
        self.assertEqual(metric["delta_percent"],-70)
    def test_zero_baseline_percent_is_null(self):
        rows=[event(),event("workflow_completed",event_id="e-2")]
        metric=compare(rows,load_events(FOLLOW))["metrics"]["median_workflow_duration_hours"]
        self.assertIsNone(metric["delta_percent"])
    def test_missing_metric_delta_is_null(self):
        metric=compare([event()],load_events(FOLLOW))["metrics"]["median_workflow_duration_hours"]
        self.assertIsNone(metric["delta_hours"])
    def test_no_network_required(self):
        with patch("socket.socket",side_effect=AssertionError("network forbidden")):
            result=compare(load_events(BASE),load_events(FOLLOW));render_report(result)


class PresentationTests(unittest.TestCase):
    def test_html_synthetic_label(self):
        html=render_report(compare(load_events(BASE),load_events(FOLLOW)),synthetic=True)
        self.assertIn("FICTIONAL DEMONSTRATION",html)
        self.assertIn("10 → 3 hours",html)
    def test_html_normal_report_does_not_claim_fictional(self):
        html=render_report(analyze(load_events(BASE)))
        self.assertNotIn("FICTIONAL DEMONSTRATION",html)
    def test_html_has_no_script_or_remote_assets(self):
        html=render_report(analyze(load_events(BASE)))
        self.assertNotIn("<script",html);self.assertNotIn("<img",html);self.assertNotIn("<iframe",html)
        self.assertIn("default-src 'none'",html)
    def test_html_text_is_escaped(self):
        result=analyze(load_events(BASE));result["limitations"].append('<script>alert(1)</script>')
        html=render_report(result)
        self.assertNotIn("<script>",html);self.assertIn("&lt;script&gt;",html)
    def test_html_omits_case_references(self):
        self.assertNotIn("synthetic-baseline-001",render_report(analyze(load_events(BASE))))
    def test_cli_validates(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):code=main(["validate",str(BASE)])
        self.assertEqual(code,0);self.assertEqual(json.loads(out.getvalue())["events"],12)
    def test_cli_compare(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):code=main(["compare",str(BASE),str(FOLLOW)])
        self.assertEqual(code,0);self.assertEqual(json.loads(out.getvalue())["kind"],"comparison")
    def test_cli_report_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"report.html"
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                code=main(["report",str(BASE),"--followup",str(FOLLOW),"--synthetic","--output",str(path)])
                again=main(["report",str(BASE),"--output",str(path)])
            self.assertEqual(code,0);self.assertEqual(again,2);self.assertIn("FICTIONAL",path.read_text())
    def test_cli_error_does_not_echo_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"input.json";path.write_text(json.dumps([event(case_key="private.person@example.com")]))
            err=io.StringIO()
            with contextlib.redirect_stderr(err):code=main(["validate",str(path)])
            self.assertEqual(code,2);self.assertNotIn("private.person",err.getvalue())
    def test_cli_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"input.csv";original=BASE.read_text();path.write_text(original)
            with contextlib.redirect_stderr(io.StringIO()):code=main(["analyze",str(path),"--output",str(path)])
            self.assertEqual(code,2);self.assertEqual(path.read_text(),original)


if __name__ == "__main__": unittest.main()

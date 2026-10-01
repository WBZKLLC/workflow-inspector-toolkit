"""Self-contained, escaped HTML reports. No scripts, tracking, or remote assets."""
from __future__ import annotations
from html import escape
from typing import Any

CSS = """
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#eaf0f7;background:#10151e;line-height:1.6}
*{box-sizing:border-box}body{margin:0}main{max-width:1050px;margin:auto;padding:52px 24px}
a{color:#86dce8}header{border-bottom:1px solid #334253;padding-bottom:28px}.brand{font-size:12px;font-weight:700;letter-spacing:.2em;color:#a5becd}
h1{font-size:clamp(30px,6vw,48px);line-height:1.12;max-width:780px;margin:18px 0}h2{font-size:22px;margin-top:34px}p{max-width:76ch;color:#bdcbd9}
.tag{display:inline-block;border:1px solid #486677;border-radius:30px;padding:4px 11px;font-size:12px;color:#cbe7ee}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:28px}.card{background:#192331;border:1px solid #344659;border-radius:14px;padding:24px}
.card h2{font-size:15px;color:#b8cddd;margin:0}.value{font-size:36px;font-weight:700;color:#f5fbff;margin-top:12px;line-height:1.2}.meta{font-size:13px;margin:12px 0 0}
.tablewrap{overflow:auto;border:1px solid #344659;border-radius:12px}table{width:100%;border-collapse:collapse;min-width:550px}th,td{padding:13px 16px;text-align:left;border-bottom:1px solid #344659}th{background:#192331}tr:last-child td,tr:last-child th{border-bottom:none}td{font-variant-numeric:tabular-nums}
.note{padding:20px 24px;background:#1b2a35;border-left:3px solid #76c8d0;border-radius:0 10px 10px 0;margin-top:28px}.note p{margin:4px 0}li{margin:7px 0;color:#bdcbd9}
footer{margin-top:40px;padding-top:22px;border-top:1px solid #334253;font-size:13px;color:#aebfcf}code{overflow-wrap:anywhere;font-size:12px}
@media(max-width:620px){main{padding:28px 18px}.cards{grid-template-columns:1fr}.value{font-size:30px}.card{padding:20px}}
@media print{:root{background:white;color:#111}p,li,footer{color:#333}.card,.note,th{background:#f6f6f6;color:#111}.value,.card h2,.brand{color:#111}a{color:#111}}
"""


def _num(value: Any) -> str:
    return "Not measured" if value is None else f"{value:g}"


def render_report(result: dict[str, Any], *, synthetic: bool = False) -> str:
    """Render either analyze() or compare() output without disclosing record IDs."""
    comparison = result.get("kind") == "comparison"
    title = "See where the handoff waits." if comparison else "Read the evidence behind the handoff."
    tag = "FICTIONAL DEMONSTRATION: NOT CUSTOMER RESULTS" if synthetic else "LOCAL FILE ANALYSIS: COVERAGE REQUIRES REVIEW"
    labels = {"median_handoff_wait_hours": "Median handoff waiting time",
              "median_workflow_duration_hours": "Median onboarding duration"}
    cards, rows = [], []
    for key, label in labels.items():
        data = result["metrics"][key]
        if comparison:
            a, b = data["baseline"], data["followup"]
            value = f'{_num(a["value"])} → {_num(b["value"])} hours'
            meta = f'Baseline n={a["sample_size"]}; follow-up n={b["sample_size"]}'
            rows.append(f'<tr><th scope="row">{escape(label)}</th><td>{_num(a["value"])}</td><td>{_num(b["value"])}</td><td>{_num(data["delta_hours"])}</td></tr>')
        else:
            value = f'{_num(data["value"])} hours' if data["value"] is not None else "Not measured"
            meta = f'Complete observed pairs: n={data["sample_size"]}'
        cards.append(f'<section class="card"><h2>{escape(label)}</h2><div class="value">{escape(value)}</div><p class="meta">{escape(meta)}</p></section>')
    metric_table = ''
    if comparison:
        metric_table = '<h2>Recorded differences</h2><div class="tablewrap" tabindex="0" role="region" aria-label="Measurement comparison"><table><caption>Elapsed hours; delta is follow-up minus baseline</caption><thead><tr><th scope="col">Measurement</th><th scope="col">Baseline</th><th scope="col">Follow-up</th><th scope="col">Delta</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'
    sets = [("Baseline", result["baseline"]), ("Follow-up", result["followup"])] if comparison else [("Input", result)]
    coverage_rows = []
    spans = []
    for label, item in sets:
        count = item["counts"]
        coverage_rows.append(f'<tr><th scope="row">{label}</th><td>{count["events"]}</td><td>{count["measured_workflows"]}/{count["cases"]}</td><td>{count["measured_handoffs"]}/{count["handoffs"]}</td><td>{count["explicit_missing_owner_events"]}/{count["ownership_observed_events"]}</td></tr>')
        spans.append(f'<p><strong>{label} event span:</strong> {escape(item["event_span"]["first"])} to {escape(item["event_span"]["last"])}<br><code>Normalized input SHA-256: {escape(item["normalized_events_sha256"])}</code></p>')
    limitations = ''.join('<li>' + escape(text) + '</li>' for text in result["limitations"])
    intro = ('This report is marked as fictional demonstration data. It demonstrates the toolkit, not adoption, typical outcomes, or product performance.' if synthetic else 'This report summarizes the activity in your local input files. Review excluded pairs and missing history in the JSON analysis before relying on any number.')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="robots" content="noindex,nofollow"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Workflow Inspector Toolkit | Local evidence report</title><style>{CSS}</style></head>
<body><main><header><div class="brand">WORKFLOW INSPECTOR / OPEN TOOLKIT</div><h1>{title}</h1><p>{escape(intro)}</p><span class="tag">{tag}</span></header><div class="cards">{''.join(cards)}</div>{metric_table}
<h2>How much evidence was usable?</h2><div class="tablewrap" tabindex="0" role="region" aria-label="Input coverage"><table><caption>Counts describe supplied records, not all real-world activity</caption><thead><tr><th scope="col">Input</th><th scope="col">Events</th><th scope="col">Workflows measured / seen</th><th scope="col">Handoffs measured / seen</th><th scope="col">Missing owner / observed events</th></tr></thead><tbody>{''.join(coverage_rows)}</tbody></table></div>
<div class="note"><p><strong>A lower number is a recorded difference, not proof of causation.</strong></p><p>Missing or ambiguous pairs are excluded, never counted as zero. This toolkit does not calculate a proprietary score.</p></div><h2>Input traceability</h2>{''.join(spans)}<p>These are the earliest and latest included events, not a guarantee of complete observation windows.</p><h2>Interpretation limits</h2><ul>{limitations}</ul><footer>Generated locally with Workflow Inspector Toolkit 0.1.0. No input is uploaded and no telemetry is sent.<br><a href="https://workflow-inspector.com/saas-customer-onboarding" rel="noreferrer">Explore Workflow Inspector's hosted onboarding product</a>. This toolkit is maintained by Workflow Inspector and is not an independent product review.</footer></main></body></html>
"""

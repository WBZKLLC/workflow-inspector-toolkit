"""Offline release checks. Pattern checks reduce risk; they are not a security audit."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workflow_inspector_toolkit import analyze, compare, load_events
from workflow_inspector_toolkit.report import render_report


def main() -> int:
    before = load_events(ROOT / "examples/baseline.csv")
    after = load_events(ROOT / "examples/followup.csv")
    for name, events in (("baseline", before), ("followup", after)):
        assert events == load_events(ROOT / f"examples/{name}.json"), "CSV/JSON mismatch"
        expected = json.loads((ROOT / f"examples/{name}-summary.json").read_text())
        assert analyze(events) == expected, "Summary differs from checked-in fixture"
        assert all(e["case_key"].startswith("synthetic-") for e in events), "Non-synthetic fixture reference"
    result = compare(before, after)
    assert result == json.loads((ROOT / "examples/comparison.json").read_text()), "Comparison mismatch"
    assert render_report(result, synthetic=True) == (ROOT / "examples/comparison.html").read_text(), "HTML is not reproducible"
    assert result["metrics"]["median_handoff_wait_hours"]["baseline"]["value"] == 10
    assert result["metrics"]["median_handoff_wait_hours"]["followup"]["value"] == 3
    assert result["metrics"]["median_workflow_duration_hours"]["baseline"]["value"] == 40
    assert result["metrics"]["median_workflow_duration_hours"]["followup"]["value"] == 22
    banned_imports = {"requests", "httpx", "urllib", "http", "socket", "subprocess", "pickle"}
    for path in (ROOT / "workflow_inspector_toolkit").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(n.name.split(".")[0] in banned_imports for n in node.names), "Unexpected runtime import"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in banned_imports, "Unexpected runtime import"
    pattern = re.compile(
        r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
        r"|(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{16}"
        r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|postgres(?:ql)?://[^\s]+"
    )
    checked = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {".git", "__pycache__", ".venv", "build", "dist", "local-data", "local-reports"} or part.endswith(".egg-info") for part in path.relative_to(ROOT).parts):
            continue
        assert path.suffix.lower() not in {".pem", ".key", ".p12", ".pfx"}, "Sensitive file extension"
        assert not path.name.startswith(".env"), "Environment file in public tree"
        if path.suffix.lower() in {".png"}:
            checked += 1
            continue
        text = path.read_text(encoding="utf-8")
        assert not pattern.search(text), "Potential credential pattern; inspect locally"
        for repo in re.findall(r"https://github[.]com/WBZKLLC/([A-Za-z0-9_.-]+)", text):
            assert repo == "workflow-inspector-toolkit", "Unexpected same-owner repository reference"
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^\s)]+)\)", text):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                local = target.split("#")[0]
                assert (path.parent / local).exists(), f"Broken relative link in {path.name}"
        checked += 1
    print(f"Release checks passed: {checked} public files; examples reproducible; local links resolve; credential-pattern and runtime-import checks clear.")
    print("This is not a complete security audit or a verification of external URL availability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

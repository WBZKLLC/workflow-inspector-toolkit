"""Run from the repository root: python -m examples.python_client."""
from pathlib import Path
from workflow_inspector_toolkit import analyze, load_events

if __name__ == "__main__":
    source = Path(__file__).with_name("baseline.csv")
    result = analyze(load_events(source))
    metric = result["metrics"]["median_handoff_wait_hours"]
    print(f"Median observed handoff wait: {metric['value']} hours (n={metric['sample_size']})")

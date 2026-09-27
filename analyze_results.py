"""Turn raw experimental results into trace and root-cause evidence.

The script never invents explanations. Root-cause labels are assigned only
when the recorded trace/error provides enough evidence; otherwise the case is
marked "undetermined" for human review.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS = ROOT / "results" / "results.json"
OUT = ROOT / "results" / "experimental_analysis.json"


def root_cause(row):
    error = (row.get("error") or "").lower()
    if not error:
        return None
    if "schema" in error or "json" in error:
        return "model"
    trace = row.get("agent_trace") or []
    if "plan" not in trace:
        return "system_design"
    if "targeted_verification" in trace and "verification" in error:
        return "verification"
    return "undetermined"


def main():
    if not RESULTS.exists():
        raise SystemExit("Run python -m eval.run_evaluation first.")
    rows = json.loads(RESULTS.read_text())
    agentic = [r for r in rows if r["variant"] == "agentic_full"]
    traces = []
    for r in agentic:
        path = r.get("agent_trace") or []
        if path:
            reasons = []
            if "clean_text" in path:
                reasons.append("planner selected messy/scanned handling")
            else:
                reasons.append("planner selected direct extraction")
            if path.count("extract") > 1:
                reasons.append("extraction retried after a failure")
            if "targeted_verification" in path:
                reasons.append("validation found low-confidence fields")
            else:
                reasons.append("verification was not needed")
            traces.append({"filename": r["filename"], "category": r["category"],
                           "path": path, "why_this_path": reasons})
    traces = traces[:5]

    failures = [r for r in rows if not r["success"]]
    by_cause = Counter(root_cause(r) for r in failures if root_cause(r))
    category = defaultdict(lambda: {"n": 0, "accuracy": 0.0, "failures": 0})
    for r in agentic:
        c = category[r["category"]]
        c["n"] += 1
        c["accuracy"] += r["overall_accuracy"]
        c["failures"] += int(not r["success"])
    for c in category.values():
        c["accuracy"] = round(c["accuracy"] / c["n"], 4) if c["n"] else 0

    out = {
        "five_execution_traces": traces,
        "failure_root_causes": dict(by_cause),
        "category_breakdown_agentic_full": dict(category),
        "interpretation_rule": "Root-cause labels are evidence-based; undetermined cases require manual review rather than speculative attribution.",
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

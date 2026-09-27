"""Measure whether reflection/verification edits actually helped.

A correction is counted for every changed atomic metric, not merely top-level
fields. Improved/regressed/neutral is determined against ground truth by
comparing the full run with the matching one-component ablation on the same
resume.
"""
import json
from pathlib import Path
from eval.metrics import field_level_scores

RESULTS_FILE = Path(__file__).parent / "results" / "results.json"
GT_FILE = Path(__file__).parent / "dataset" / "ground_truth.json"


def _by_variant(rows, variant):
    return {r["filename"]: r for r in rows if r["variant"] == variant}


def analyze(changed_key, full_variant, ablated_variant, rows, ground_truth, agent):
    full = _by_variant(rows, full_variant)
    ablated = _by_variant(rows, ablated_variant)
    counts = {"corrections_made": 0, "improved": 0, "regressed": 0, "neutral": 0}
    examples = []
    for fname, fr in full.items():
        ar = ablated.get(fname)
        changed = fr.get(changed_key) or []
        if not ar or not fr.get("predicted") or not ar.get("predicted") or not changed:
            continue
        fs = field_level_scores(fr["predicted"], ground_truth[fname])
        as_ = field_level_scores(ar["predicted"], ground_truth[fname])
        for field in changed:
            # A top-level changed field may correspond to several nested atomic metrics.
            keys = [k for k in fs if k == field or k.startswith(field + ":")]
            for key in keys:
                counts["corrections_made"] += 1
                delta = fs[key] - as_.get(key, 0.0)
                bucket = "improved" if delta > 0 else "regressed" if delta < 0 else "neutral"
                counts[bucket] += 1
                if len(examples) < 10 and delta != 0:
                    examples.append({"filename": fname, "metric": key, "delta": round(delta, 4)})
    return {"agent": agent, **counts, "examples": examples,
            "note": "More edits are not treated as evidence of quality; only movement toward ground truth counts as improvement."}


def main():
    if not RESULTS_FILE.exists():
        raise SystemExit("Run python -m eval.run_evaluation first.")
    rows = json.loads(RESULTS_FILE.read_text())
    gt = json.loads(GT_FILE.read_text())
    out = {
        "reflection": analyze("reflection_changed_fields", "agentic_full", "ablation_no_reflection", rows, gt, "reflection"),
        "verification": analyze("verification_changed_fields", "agentic_full", "ablation_no_verification", rows, gt, "verification"),
    }
    path = RESULTS_FILE.parent / "reflection_verification_report.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

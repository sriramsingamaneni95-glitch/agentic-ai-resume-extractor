
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

from orchestrator import run_pipeline, AblationConfig
from eval.baseline import run_baseline
from eval.metrics import field_level_scores, overall_accuracy, exact_record_match, estimate_cost_usd, aggregate
from eval.telemetry import start_run, end_run

DATASET_DIR = Path(__file__).parent / "dataset"
RESULTS_DIR = Path(__file__).parent / "results"
MODEL_NAME = "gpt-4.1"

VARIANTS = {
    "baseline": None,
    "agentic_full": AblationConfig(),
    "ablation_no_reflection": AblationConfig(enable_reflection=False),
    "ablation_no_verification": AblationConfig(enable_verification=False),
    "ablation_no_memory": AblationConfig(enable_memory=False),
    "ablation_no_dynamic_routing": AblationConfig(enable_dynamic_routing=False),
}


def load_dataset():
    ground_truth = json.loads((DATASET_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    return [{"filename": f, "text": (DATASET_DIR / f).read_text(encoding="utf-8"), "ground_truth": gt}
            for f, gt in ground_truth.items()]


def score_result(predicted, ground_truth):
    fs = field_level_scores(predicted, ground_truth) if predicted else {}
    return {
        "field_scores": fs,
        "overall_accuracy": overall_accuracy(fs),
        "exact_record_match": exact_record_match(fs),
    }


def run_one(variant_name, config, item):
    started = time.time()
    telemetry, token = start_run()
    error = None
    trace = None
    data = None
    success = False
    try:
        if variant_name == "baseline":
            r = run_baseline(item["text"])
            success, data = r["success"], r["data"]
            error = r["error"]
            trace = ["baseline"]
        else:
            result = run_pipeline(item["text"], resume_name=item["filename"], ablation_config=config)
            success, data = True, result["data"]
            trace = result["agent_trace"]
    except Exception as exc:
        error = str(exc)
    finally:
        end_run(token)

    api = telemetry.snapshot()
    latency = round(time.time() - started, 3)
    scoring = score_result(data, item["ground_truth"])
    return {
        "variant": variant_name,
        "filename": item["filename"],
        "category": item["ground_truth"].get("category"),
        "success": success,
        "error": error,
        "latency_seconds": latency,
        "llm_calls": api["llm_calls"],
        "embedding_calls": api["embedding_calls"],
        "input_tokens": api["input_tokens"],
        "output_tokens": api["output_tokens"],
        "cost_usd": estimate_cost_usd(api["input_tokens"], api["output_tokens"]),
        "api_calls": api["api_calls"],
        "agent_trace": trace,
        "reflection_changed_fields": result.get("reflection_changed_fields", []) if variant_name != "baseline" and 'result' in locals() else [],
        "verification_changed_fields": result.get("verification_changed_fields", []) if variant_name != "baseline" and 'result' in locals() else [],
        "predicted": data,
        **scoring,
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    dataset = load_dataset()
    print(f"Loaded {len(dataset)} resumes; {len(VARIANTS)} variants; {len(dataset) * len(VARIANTS)} runs.")
    all_results = []
    for variant_name, config in VARIANTS.items():
        print(f"\n--- {variant_name} ---")
        for item in dataset:
            r = run_one(variant_name, config, item)
            all_results.append(r)
            print(f"[{ 'OK' if r['success'] else 'FAIL' }] {item['filename']:<20} "
                  f"acc={r['overall_accuracy']:.3f} exact={r['exact_record_match']:.0f} "
                  f"calls={r['llm_calls']} tok={r['input_tokens'] + r['output_tokens']} "
                  f"lat={r['latency_seconds']}s")

    (RESULTS_DIR / "results.json").write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {name: aggregate([r for r in all_results if r["variant"] == name]) for name in VARIANTS}
    summary_out = {
        "model": MODEL_NAME,
        "dataset_size": len(dataset),
        "variants": summary,
        "methodology": {
            "same_model_and_schema": True,
            "synthetic_dataset": True,
            "cost_is_estimated": True,
            "dynamic_routing_ablation_fixed_path": "plan -> clean_text -> extract -> reflect(if enabled) -> validate -> verify(if enabled) -> score -> memory(if enabled)",
        },
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary_out, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===")
    print(f"{'Variant':<30} {'Acc':<8} {'Exact':<8} {'Fail':<8} {'Calls':<8} {'Tok':<10} {'Cost':<10} {'Latency':<10}")
    for name, s in summary.items():
        print(f"{name:<30} {s.get('avg_overall_accuracy', 0):<8} {s.get('avg_exact_record_match', 0):<8} "
              f"{s.get('failure_rate', 0):<8} {s.get('avg_llm_calls', 0):<8} "
              f"{(s.get('avg_input_tokens') or 0) + (s.get('avg_output_tokens') or 0):<10.1f} "
              f"{s.get('avg_cost_usd', 0):<10} {s.get('avg_latency_seconds', 0):<10}")
    print(f"\nWrote {RESULTS_DIR / 'results.json'} and {RESULTS_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()

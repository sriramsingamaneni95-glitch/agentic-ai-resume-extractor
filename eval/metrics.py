PRICE_PER_1K_INPUT = 0.002
PRICE_PER_1K_OUTPUT = 0.008


def _norm(value) -> str:
    return str(value).strip().lower() if value is not None else ""


def _scalar(pred, gt) -> float:
    return 1.0 if _norm(pred) == _norm(gt) else 0.0


def _jaccard(a: list, b: list) -> float:
    a_set = {_norm(x) for x in (a or []) if x is not None and _norm(x)}
    b_set = {_norm(x) for x in (b or []) if x is not None and _norm(x)}
    if not a_set and not b_set:
        return 1.0
    if not a_set or not b_set:
        return 0.0
    return len(a_set & b_set) / len(a_set | b_set)


def _list_records(pred, gt, key_fields):
    pred = pred or []
    gt = gt or []
    
    identity = key_fields[0]
    pred_by_id = {_norm(x.get(identity)): x for x in pred if x.get(identity)}
    gt_by_id = {_norm(x.get(identity)): x for x in gt if x.get(identity)}
    keys = sorted(set(pred_by_id) | set(gt_by_id))
    scores = {}
    for key in keys:
        p = pred_by_id.get(key, {})
        g = gt_by_id.get(key, {})
        for field in key_fields:
            scores[f"{identity}:{key}:{field}"] = _scalar(p.get(field), g.get(field))
    return scores


def field_level_scores(predicted: dict | None, ground_truth: dict) -> dict:
    predicted = predicted or {}
    scores = {}
    for field in ["name", "email", "phone", "summary"]:
        scores[field] = _scalar(predicted.get(field), ground_truth.get(field))
    scores["skills"] = _jaccard(predicted.get("skills"), ground_truth.get("skills"))

    gt_exp = ground_truth.get("experience") or []
    pred_exp = predicted.get("experience") or []
    gt_edu = ground_truth.get("education") or []
    pred_edu = predicted.get("education") or []
    scores["experience_count"] = _scalar(len(pred_exp), len(gt_exp))
    scores["education_count"] = _scalar(len(pred_edu), len(gt_edu))
    scores.update(_list_records(pred_exp, gt_exp, ["company", "title", "start_date", "end_date", "description"]))
    scores.update(_list_records(pred_edu, gt_edu, ["institution", "degree", "year"]))
    return scores


def overall_accuracy(field_scores: dict) -> float:
    return round(sum(field_scores.values()) / len(field_scores), 4) if field_scores else 0.0


def exact_record_match(field_scores: dict) -> float:
    return 1.0 if field_scores and all(v == 1.0 for v in field_scores.values()) else 0.0


def estimate_cost_usd(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    return round((input_tokens / 1000) * PRICE_PER_1K_INPUT +
                 (output_tokens / 1000) * PRICE_PER_1K_OUTPUT, 6)


def aggregate(per_resume_results: list[dict]) -> dict:
    n = len(per_resume_results)
    if not n:
        return {}
    successes = [r for r in per_resume_results if r["success"]]

    def avg(key, source=successes):
        vals = [r[key] for r in source if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        "n_resumes": n,
        "failure_rate": round(1 - len(successes) / n, 4),
        "avg_overall_accuracy": avg("overall_accuracy"),
        "avg_exact_record_match": avg("exact_record_match"),
        "avg_latency_seconds": avg("latency_seconds", per_resume_results),
        "avg_llm_calls": avg("llm_calls", per_resume_results),
        "avg_embedding_calls": avg("embedding_calls", per_resume_results),
        "avg_input_tokens": avg("input_tokens"),
        "avg_output_tokens": avg("output_tokens"),
        "avg_cost_usd": avg("cost_usd"),
    }

# eval_harness.py
from time import perf_counter
from statistics import mean
from collections import Counter
from app.redaction import redact
from app.gate_classifier import classify

def evaluate(fixtures, model_call=None):
    """
    fixtures: iterable of dicts (see schema).
    model_call: optional callable(text)->str to test LLM layer (post-gate).
    Returns aggregates only.
    """
    y_true, y_pred = [], []
    latencies = []
    token_costs = []
    tags = Counter()

    for fx in fixtures:
        text = fx["text"]
        gold = fx["gold_label"]
        pred, tag, trig = classify(text)
        y_true.append(gold); y_pred.append(pred)
        tags[tag] += 1

        # (Optional) call model only if gate allows
        t0 = perf_counter()
        if pred == "ALLOW" and model_call:
            _ = model_call(text)  # ensure your model_call already redacts internally
        latencies.append(perf_counter()-t0)
        token_costs.append(estimate_tokens(text))  # implement per tokenizer

    # aggregates
    from sklearn.metrics import classification_report, confusion_matrix
    report = classification_report(y_true, y_pred, labels=["ALLOW","REFUSE","CRISIS"], output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=["ALLOW","REFUSE","CRISIS"]).tolist()

    return {
        "macro_f1": report["macro avg"]["f1-score"],
        "per_label_f1": {k:v["f1-score"] for k,v in report.items() if k in ["ALLOW","REFUSE","CRISIS"]},
        "confusion_matrix_labels": ["ALLOW","REFUSE","CRISIS"],
        "confusion_matrix": cm,
        "avg_latency_s": round(mean(latencies), 4),
        "avg_est_tokens": round(mean(token_costs), 1),
        "policy_tags_count": dict(tags)
    }

def estimate_tokens(text: str, chars_per_tok=4.0):
    return max(1, int(len(text)/chars_per_tok))

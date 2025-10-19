# app/eval/rag_recall_eval.py
import argparse, json, os, re, sys, yaml
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional, Set
from scripts.alias_expand import load_aliases, expand_terms

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def build_corpus(paths: List[str]) -> List[Dict[str, Any]]:
    corpus = []
    for p in paths:
        if not os.path.exists(p):
            print(f"[warn] missing jsonl: {p}", file=sys.stderr)
            continue
        corpus.extend(load_jsonl(p))
    return corpus

def score_chunk(text: str, terms: List[str]) -> int:
    t = normalize(text)
    score = 0
    for term in terms:
        if not term:
            continue
        score += t.count(term)  # simple occurrence count
    return score

def score_record(rec: Dict[str, Any], terms: List[str], query_lang: str = "en") -> float:
    """Term hits in body + small boosts for title/section, topic overlap, and doc_type."""
    body = rec.get("text", "")
    title = rec.get("title", "")
    section = " ".join(rec.get("section_path", []))
    topics = [normalize(x) for x in rec.get("topics", [])]
    doc_type = (rec.get("doc_type") or "").lower()

    base = score_chunk(body, terms)
    hdr = score_chunk(title + " " + section, terms)
    topic_hits = sum(1 for t in topics if t in set(terms))

    boost = 0.0
    # Prefer psychoeducation; de-emphasize terminology/taxonomy for "what/help" style questions
    if doc_type == "psychoeducation":
        boost += 3.0
    elif doc_type == "instrument":
        boost += 1.5
    elif doc_type == "terminology":
        boost -= 3.0
    elif doc_type == "taxonomy":
        boost -= 1.5

    # Light language bonus for Urdu queries hitting Urdu content
    lang = (rec.get("language") or "").lower()
    if query_lang == "ur" and lang == "ur":
        boost += 1.5

    return base + hdr + topic_hits + boost

def topk(
    corpus: List[Dict[str, Any]],
    terms: List[str],
    k: int = 5,
    per_source_cap: int | None = None,
    allow_doc_types: Optional[Set[str]] = None,
    block_sources: Optional[Set[str]] = None,
    query_lang: str = "en",
) -> List[Dict[str, Any]]:
    scored = []
    for rec in corpus:
        # Optional pre-filters
        if block_sources and rec.get("source_key") in block_sources:
            continue
        if allow_doc_types and (rec.get("doc_type") or "").lower() not in allow_doc_types:
            continue
        s = score_record(rec, terms, query_lang=query_lang)
        if s > 0:
            scored.append((s, rec))
    scored.sort(key=lambda x: x[0], reverse=True)

    if not per_source_cap:
        return [r for _, r in scored[:k]]

    selected, counts = [], {}
    for _, rec in scored:
        sk = rec.get("source_key", "unknown")
        c = counts.get(sk, 0)
        if c >= per_source_cap:
            continue
        selected.append(rec)
        counts[sk] = c + 1
        if len(selected) >= k:
            break
    return selected

def evaluate(
    corpus: List[Dict[str, Any]],
    gold: List[Dict[str, Any]],
    aliases_path: str,
    k: int,
    per_source_cap: int | None = None,
    allow_doc_types: Optional[Set[str]] = None,
    block_sources: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    aliases = load_aliases(aliases_path)
    covered = 0
    per_item = []
    by_source = Counter()
    misses = []
    # normalize the allow set to lowercase once
    allow_norm = set(d.lower() for d in allow_doc_types) if allow_doc_types else None
    for item in gold:
        q = item["query"]
        rel_sources = set(item.get("relevant_sources", []))
        # expand query to cross-lingual terms
        base_terms = normalize(q).split()
        terms = expand_terms(base_terms, aliases)
        # crude Urdu detector (Arabic script range)
        qlang = "ur" if re.search(r"[\u0600-\u06FF]", q) else "en"
        hits = topk(
            corpus,
            terms,
            k=k,
            per_source_cap=per_source_cap,
            allow_doc_types=allow_norm,
            block_sources=block_sources,
            query_lang=qlang,
        )
        hit_sources = [h.get("source_key", "unknown") for h in hits]
        per_item.append({"id": item["id"], "query": q, "hit_sources": hit_sources})
        ok = any(s in rel_sources for s in hit_sources)
        if ok:
            covered += 1
            for s in hit_sources:
                by_source[s] += 1
        else:
            misses.append({"id": item["id"], "query": q, "top_sources": hit_sources})
    total = len(gold)
    coverage = (covered / total * 100.0) if total else 0.0
    return {
        "total": total,
        "k": k,
        "covered": covered,
        "coverage_pct": round(coverage, 1),
        "by_source_in_hits": dict(by_source),
        "misses": misses,
        "samples": per_item[:5],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", nargs="+", required=True, help="One or more JSONL evidence files")
    ap.add_argument("--gold", required=True, help="YAML gold set file")
    ap.add_argument("--aliases", default="configs/aliases_med.json")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--per-source-cap", type=int, default=3)
    ap.add_argument("--allow-doc-types", nargs="*", help="Only consider these doc_types (e.g., psychoeducation instrument taxonomy)")
    ap.add_argument("--block-sources", nargs="*", help="Exclude these source_keys (e.g., snomed-gps)")
    ap.add_argument("--out", help="Optional path to write JSON report")
    args = ap.parse_args()

    corpus = build_corpus(args.jsonl)
    gold = yaml.safe_load(open(args.gold, "r", encoding="utf-8"))
    allow_set = set(d.lower() for d in (args.allow_doc_types or [])) or None
    block_set = set(args.block_sources or []) or None

    report = evaluate(
        corpus,
        gold,
        args.aliases,
        args.k,
        per_source_cap=args.per_source_cap,
        allow_doc_types=allow_set,
        block_sources=block_set,
    )

    print(f"== RAG Recall@{args.k} ==")
    print(f"Total: {report['total']}  Covered: {report['covered']}  Coverage: {report['coverage_pct']}%")
    print(f"Hit sources (counts): {report['by_source_in_hits']}")
    if report["misses"]:
        print("Misses (first 5):")
        for m in report["misses"][:5]:
            print(f"  - {m['id']}: top_sources={m['top_sources']}  query={m['query']}")
    else:
        print("Misses: 0")
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Wrote report → {args.out}")

if __name__ == "__main__":
    main()

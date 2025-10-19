# app/eval/smoke_llm_rag.py

import argparse, json, os, re, sys, textwrap, requests
from typing import List, Dict, Any, Optional, Set
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

def score_chunk(text: str, terms: List[str]) -> int:
    t = normalize(text)
    return sum(t.count(term) for term in terms if term)

def score_record(rec: Dict[str, Any], terms: List[str], query_lang: str = "en") -> float:
    """
    Term hits in body + small boosts for title/section, topic overlap, and doc_type.
    Bias psychoeducation up for "what/help" questions; de-emphasize terminology/taxonomy.
    """
    body = rec.get("text", "")
    title = rec.get("title", "")
    section = " ".join(rec.get("section_path", []))
    topics = [normalize(x) for x in rec.get("topics", [])]
    doc_type = (rec.get("doc_type") or "").lower()

    base = score_chunk(body, terms)
    hdr  = score_chunk(f"{title} {section}", terms)
    topic_hits = sum(1 for t in topics if t in set(terms))

    boost = 0.0
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

def select_topk(
    jsonl_paths: List[str],
    query: str,
    aliases_path: str,
    k: int,
    per_source_cap: int = 3,
    allow_doc_types: Optional[Set[str]] = None,
    block_sources: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    aliases = load_aliases(aliases_path)
    base_terms = normalize(query).split()
    terms = expand_terms(base_terms, aliases)

    corpus = []
    for p in jsonl_paths:
        if os.path.exists(p):
            corpus.extend(load_jsonl(p))

    qlang = "ur" if re.search(r"[\u0600-\u06FF]", query) else "en"

    scored = []
    for rec in corpus:
        # Optional pre-filters
        if block_sources and rec.get("source_key") in block_sources:
            continue
        if allow_doc_types and (rec.get("doc_type") or "").lower() not in allow_doc_types:
            continue
        s = score_record(rec, terms, query_lang=qlang)
        if s > 0:
            scored.append((s, rec))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Enforce per-source cap to prevent a single source (e.g., ICD-11) from flooding top-k.
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

def build_prompt(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    context = []
    for i, ch in enumerate(chunks, 1):
        src = f"{ch.get('source_key','?')} • {ch.get('title','?')} • {ch.get('section_path',[-1])[-1]}"
        txt = (ch.get("text","") or "").strip()
        # cap per chunk to ~700 chars to stay small
        snippet = txt[:700]
        context.append(f"[{i}] {src}\n{snippet}")

    system = (
        "You are SukoonAI, a mental-wellness assistant. Answer using only the provided evidence. "
        "If content is unsafe/out-of-scope (diagnosis/meds), ABSTAIN and provide a brief referral. "
        "Always include source indices like [1], [2]. Keep it under 120 words."
    )
    user = f"Question: {query}\n\nEvidence:\n" + "\n\n".join(context)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def call_openai(messages: List[Dict[str,str]], model: str, max_tokens: int = 256, temperature: float = 0.3) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "[SKIP] OPENAI_API_KEY not set. Showing top-k evidence only."
    if os.environ.get("NO_NETWORK","0") == "1":
        return "[SKIP] NO_NETWORK=1. Showing top-k evidence only."
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", nargs="+", required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--aliases", default="configs/aliases_med.json")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--per-source-cap", type=int, default=2)
    ap.add_argument("--allow-doc-types", nargs="*", help="e.g., psychoeducation instrument taxonomy")
    ap.add_argument("--block-sources", nargs="*", help="e.g., snomed-gps")
    args = ap.parse_args()

    allow = set(d.lower() for d in (args.allow_doc_types or [])) if args.allow_doc_types else None
    block = set(args.block_sources or []) if args.block_sources else None

    topk = select_topk(
        args.jsonl, args.query, args.aliases, args.k,
        per_source_cap=args.per_source_cap,
        allow_doc_types=allow, block_sources=block
    )
    msgs = build_prompt(args.query, topk)
    answer = call_openai(msgs, args.model)

    print("== Top-k Evidence ==")
    for i, ch in enumerate(topk, 1):
        src = f"{ch.get('source_key')} • {ch.get('title')} • {ch.get('section_path',[-1])[-1]}"
        print(f"[{i}] {src}  (lang={ch.get('language')}, crisis={ch.get('crisis_flag')})")

    print("\n== LLM Answer ==")
    print(answer)

if __name__ == "__main__":
    main()

import argparse, json, os, re
from typing import Dict, List, Set

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def load_aliases(path: str = "configs/aliases_med.json") -> Dict[str, Dict[str, List[str]]]:
    if not os.path.exists(path):
        raise SystemExit(f"[alias_expand] aliases file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def concepts_for_term(term: str, aliases: Dict[str, Dict[str, List[str]]]) -> Set[str]:
    t = _norm(term)
    hits = set()
    for concept, langs in aliases.items():
        for lst in langs.values():
            for v in lst:
                if _norm(v) == t:
                    hits.add(concept)
                    break
    return hits

def expand_terms(terms: List[str], aliases: Dict[str, Dict[str, List[str]]]) -> List[str]:
    out: Set[str] = set()
    # Always include originals (normalized)
    for t in terms:
        out.add(_norm(t))
        for concept in concepts_for_term(t, aliases):
            for lang_list in aliases[concept].values():
                out.update(_norm(v) for v in lang_list)
    # Return sorted, stable order
    return sorted(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aliases", default="configs/aliases_med.json")
    ap.add_argument("--query", required=True, help="space-separated query terms (can include Urdu/Roman-Urdu)")
    args = ap.parse_args()

    aliases = load_aliases(args.aliases)
    # naive split: treat spaces as separators; multi-word items like "panic attack" should be typed with quotes
    terms = [_norm(t) for t in re.split(r"\s+", args.query.strip()) if t]
    expanded = expand_terms(terms, aliases)
    print(json.dumps({"input": terms, "expanded": expanded}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

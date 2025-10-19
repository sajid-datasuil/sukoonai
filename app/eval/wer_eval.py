import csv, glob, json, math, os, re, sys
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

@dataclass
class WerConfig:
    dataset_glob: str
    max_wer: float
    strip_punct: bool = True
    lowercase: bool = True
    normalize_spaces: bool = True
    ignore_chars: List[str] = None
    aliases_path: Optional[str] = None
    debug_top_n: int = 0

_PUNCT_RE = re.compile(r"[^\w\s\u0600-\u06FF']+", flags=re.UNICODE)  # keep Urdu block + apostrophe
_WORD_RE = re.compile(r"\b", flags=re.UNICODE)

def _load_aliases(path: Optional[str]) -> List[Tuple[re.Pattern, str]]:
    if not path or not os.path.exists(path):
        return []
    rules = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=>" not in line:
                continue
            left, right = [x.strip() for x in line.split("=>", 1)]
            # word-boundary replacement, case-insensitive
            pat = re.compile(rf"(?<!\w){re.escape(left)}(?!\w)", flags=re.IGNORECASE | re.UNICODE)
            rules.append((pat, right))
    return rules

def _apply_aliases(s: str, rules: List[Tuple[re.Pattern, str]]) -> str:
    for pat, repl in rules:
        s = pat.sub(repl, s)
    return s

def _norm(s: str, cfg: WerConfig, alias_rules: List[Tuple[re.Pattern, str]]) -> str:
    if cfg.ignore_chars:
        for ch in cfg.ignore_chars:
            s = s.replace(ch, "")
    s = _apply_aliases(s, alias_rules)
    if cfg.strip_punct:
        s = _PUNCT_RE.sub(" ", s)
    if cfg.lowercase:
        s = s.lower()
    if cfg.normalize_spaces:
        s = re.sub(r"\s+", " ", s).strip()
    return s

def _levenshtein(a: List[str], b: List[str]) -> int:
    # classic DP; a,b are token lists
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        ai = a[i - 1]
        for j in range(1, m + 1):
            temp = dp[j]
            cost = 0 if ai == b[j - 1] else 1
            dp[j] = min(
                dp[j] + 1,      # deletion
                dp[j - 1] + 1,  # insertion
                prev + cost     # substitution
            )
            prev = temp
    return dp[m]

def load_config(path: str) -> WerConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = {}
        for line in f:
            if "#" in line:
                line = line.split("#", 1)[0]
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                raw[k.strip()] = v.strip()

        def as_bool(x): return str(x).lower() in ("1", "true", "yes", "y", "on")
        def as_float(x):
            xs = str(x).strip().strip('"').strip("'")
            return float(xs)
        def as_list(key):
            s = raw.get(key, "").strip()
            if s.startswith("[") and s.endswith("]"):
                inner = s[1:-1].strip()
                if not inner:
                    return []
                return [i.strip().strip('"').strip("'") for i in inner.split(",")]
            return []
        def as_str(key):
            if key not in raw:
                return None
            return raw[key].strip().strip('"').strip("'") or None
        def as_int(key, default=0):
            v = raw.get(key, None)
            if v is None:
                return default
            try:
                return int(str(v).strip())
            except:
                return default

        cfg = WerConfig(
            dataset_glob=str(raw["dataset_glob"]).strip().strip('"').strip("'"),
            max_wer=as_float(raw["max_wer"]),
            strip_punct=as_bool(raw.get("strip_punct", "true")),
            lowercase=as_bool(raw.get("lowercase", "true")),
            normalize_spaces=as_bool(raw.get("normalize_spaces", "true")),
            ignore_chars=as_list("ignore_chars"),
            aliases_path=as_str("aliases_path"),
            debug_top_n=as_int("debug_top_n", 0),
        )
        return cfg

def wer(ref: str, hyp: str, cfg: WerConfig, alias_rules=None) -> float:
    """
    Public API expected by tests: wer(ref, hyp, cfg) -> float
    When alias_rules is not provided, load from cfg.aliases_path (or use []).
    """
    alias_rules = alias_rules if alias_rules is not None else _load_aliases(getattr(cfg, "aliases_path", None))
    ref_n = _norm(ref, cfg, alias_rules)
    hyp_n = _norm(hyp, cfg, alias_rules)
    ref_tok = ref_n.split() if ref_n else []
    hyp_tok = hyp_n.split() if hyp_n else []
    if not ref_tok:
        return 0.0 if not hyp_tok else 1.0
    dist = _levenshtein(ref_tok, hyp_tok)
    return dist / max(1, len(ref_tok))

def evaluate(cfg: WerConfig) -> Tuple[float, int]:
    files = sorted(glob.glob(cfg.dataset_glob))
    if not files:
        print(f"[WER] No files matched: {cfg.dataset_glob}")
        return 0.0, 0
    alias_rules = _load_aliases(cfg.aliases_path)
    rows = []
    total, count = 0.0, 0
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            rd = csv.reader(f)
            for row in rd:
                if not row or row[0].startswith("#"):
                    continue
                if len(row) >= 3:
                    idx, ref, hyp = row[0], row[1], row[2]
                elif len(row) == 2:
                    idx, ref, hyp = str(count), row[0], row[1]
                else:
                    continue
                score = wer(ref, hyp, cfg, alias_rules)
                rows.append((fp, idx, score, ref, hyp))
                total += score
                count += 1
    avg = (total / count) if count else 0.0

    # debug top-N worst cases
    if cfg.debug_top_n and rows:
        worst = sorted(rows, key=lambda r: r[2], reverse=True)[:cfg.debug_top_n]
        print("[WER][Top offenders]")
        for fp, idx, s, ref, hyp in worst:
            print(f"{os.path.basename(fp)}#{idx}: WER={s:.3f} | REF='{ref}' | HYP='{hyp}'")

    return avg, count

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "configs/wer.yaml"
    cfg = load_config(cfg_path)
    avg, n = evaluate(cfg)
    print(json.dumps({"avg_wer": round(avg, 4), "samples": n, "max_wer": cfg.max_wer}))
    if n == 0:
        print("[WER] No samples; failing to force fixture creation.", file=sys.stderr)
        sys.exit(2)
    if avg > cfg.max_wer:
        print(f"[WER] FAIL: avg WER {avg:.4f} > max {cfg.max_wer:.4f}", file=sys.stderr)
        sys.exit(1)
    print("[WER] PASS")

if __name__ == "__main__":
    main()

# app/retrieval/mini.py
from __future__ import annotations

import json, os, math, re, unicodedata
from json import JSONDecodeError
from typing import List, Dict

# --- FILE-RELATIVE KB PATH (snippet applied) ---
HERE = os.path.dirname(__file__)
KB_PATH = os.path.join(HERE, "kb_ur.json")

_SEED = [
  ("گہری سانس لینا", "2-3 منٹ ناک سے سانس، منہ سے خارج؛ رفتار آہستہ رکھیں۔"),
  ("زمین سے ربط (گراؤنڈنگ)", "5 چیزیں دیکھیں، 4 چھوئیں، 3 سنیں، 2 سونگھیں، 1 چکھیں۔"),
  ("پانی پینا", "آہستہ سے ایک گلاس پانی؛ دل کی دھڑکن نرم پڑتی ہے۔"),
  ("چلنا", "3–5 منٹ تیز قدم؛ سانس اور قدم ہم آہنگ کریں۔"),
  ("نیند حفظانِ صحت", "سونے سے 1 گھنٹہ پہلے اسکرین بند، روشنی مدھم، کمرہ ٹھنڈا۔"),
  ("PHQ-9 تعارف", "ڈپریشن کی شدت سمجھنے کے لیے 9 سوالات۔"),
  ("GAD-7 تعارف", "پریشانی کی پیمائش کے 7 سوالات۔"),
  ("PHQ-2 تعارف", "مختصر اسکرین: موڈ + دلچسپی۔"),
  ("پینک ایٹیک کیا ہے؟", "یہ جان لیوا نہیں؛ جسم کا الارم سسٹم اوور ایکٹو ہو جاتا ہے۔"),
  ("سیفٹی پلان", "ایک شخص/نمبر، ایک جگہ، ایک سرگرمی پہلے سے طے کریں۔"),
]

def _normalize(t: str) -> str:
  return unicodedata.normalize("NFC", (t or "").strip().lower())

def _tok_ur(s: str) -> List[str]:
  s = re.sub(r"[^\w\u0600-\u06FF]+", " ", s)
  return [w for w in s.split() if len(w) > 1]

def _idf_vocab(kb: List[Dict]) -> Dict[str, float]:
  N = len(kb)
  df: Dict[str, int] = {}
  for it in kb:
    seen = set(_tok_ur(_normalize(it["title"] + " " + it["body"])))
    for t in seen:
      df[t] = df.get(t, 0) + 1
  return {t: math.log((N + 1) / (df[t] + 0.5)) for t in df}

# ---------- Robust lazy initialization (prevents import-time crashes) ----------
_KB: List[Dict] | None = None
_IDF: Dict[str, float] | None = None

def _ensure_dir(path: str) -> None:
  os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

def _seed_items() -> List[Dict]:
  kb: List[Dict] = []
  i = 1
  for title, body in _SEED:
    for suffix in [" — بنیادی رہنمائی", " — مختصر نوٹ", " — فوری قدم", " — سوال و جواب", " — خلاصہ"]:
      kb.append({"id": f"auto-{i:03d}", "title": title, "body": body})
      i += 1
  return kb[:120]

def _load_or_seed() -> List[Dict]:
  _ensure_dir(KB_PATH)
  if os.path.exists(KB_PATH):
    try:
      with open(KB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list) and data:
          return data
    except (JSONDecodeError, UnicodeDecodeError, OSError):
      # fall through to seed
      pass
  kb = _seed_items()
  try:
    with open(KB_PATH, "w", encoding="utf-8") as f:
      json.dump(kb, f, ensure_ascii=False, indent=2)
  except OSError:
    # best-effort; even if write fails, return in-memory KB
    pass
  return kb

def _ensure_ready() -> None:
  global _KB, _IDF
  if _KB is None:
    _KB = _load_or_seed()
    _IDF = _idf_vocab(_KB)

# --------------------------------- API ---------------------------------
def retrieve(q: str, k: int = 2) -> List[Dict]:
  _ensure_ready()
  qn = _normalize(q)
  qtok = _tok_ur(qn)
  if not qtok:
    return []
  scores: List[tuple[float, Dict]] = []
  for it in _KB:  # type: ignore[arg-type]
    toks = _tok_ur(_normalize(it["title"] + " " + it["body"]))
    overlap = set(qtok) & set(toks)
    score = sum(_IDF.get(t, 0.0) for t in overlap) + 0.01 * len(overlap)  # type: ignore[union-attr]
    if score > 0:
      excerpt = it["body"][:120]
      scores.append((score, {"id": it["id"], "title": it["title"], "excerpt": excerpt}))
  scores.sort(key=lambda x: x[0], reverse=True)
  return [e for _, e in scores[:max(1, min(3, k))]]

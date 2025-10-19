# -*- coding: utf-8 -*-
from __future__ import annotations
from app.agent.graph import plan_say

TARGET_HIT_RATE = 0.80
UTTERANCES = [
    ("en", "Quick grounding please."),
    ("en", "Let's do 5-4-3-2-1 grounding."),
    ("ur", "سانس کی کوئی آسان مشق بتائیں۔"),
]

def main() -> int:
    total_say = 0
    hits = 0
    for lang, text in UTTERANCES:
        d = plan_say(text, lang)
        cost = d.get("cost", {})
        total_say += int(cost.get("tts_total_say", 0))
        hits += int(cost.get("tts_cache_hits", 0))
    rate = (hits / total_say) if total_say else 0.0
    print(f"TTS-CACHE: hits={hits} total={total_say} rate={rate:.3f}")
    ok = rate >= TARGET_HIT_RATE
    print(f"VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())

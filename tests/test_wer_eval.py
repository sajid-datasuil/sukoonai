from app.eval.wer_eval import WerConfig, wer

def test_basic_wer_equivalence():
    cfg = WerConfig(dataset_glob="", max_wer=0.15)
    assert wer("hello world", "hello world", cfg) == 0.0

def test_codeswitch_tolerance():
    cfg = WerConfig(dataset_glob="", max_wer=0.15)
    # minor spelling differences common in Roman-Urdu
    ref = "kal raat neend theek nahi aayi"
    hyp = "kal raat neend nai ayi"
    s = wer(ref, hyp, cfg)
    assert 0.0 <= s <= 0.5  # sanity bound; not too high

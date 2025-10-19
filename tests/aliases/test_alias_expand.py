import json
from scripts.alias_expand import load_aliases, expand_terms

def test_expand_anxiety_en():
    aliases = load_aliases("configs/aliases_med.json")
    out = expand_terms(["anxiety"], aliases)
    assert "anxiety" in out and "bechaini" in out and "پریشانی" in out

def test_expand_anxiety_roman_ur():
    aliases = load_aliases("configs/aliases_med.json")
    out = expand_terms(["bechaini"], aliases)
    assert "anxiety" in out and "پریشانی" in out

def test_expand_depression_ur():
    aliases = load_aliases("configs/aliases_med.json")
    out = expand_terms(["افسردگی"], aliases)
    assert "depression" in out and "udaasi" in out

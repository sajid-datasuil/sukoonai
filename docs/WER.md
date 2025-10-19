# Speech Recognition Quality (WER)

- Gate: **avg_wer ≤ 0.15** across Urdu/English/Roman-Urdu fixtures.
- Normalization: Urdu script preserved; punctuation/diacritics stripped; code-switch aliases.
- Run locally:
```powershell
python app/eval/wer_eval.py configs/wer.yaml
pytest -q tests/test_wer_eval.py

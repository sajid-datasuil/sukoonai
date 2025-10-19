# app/gate_classifier.py
import re

PAT_INTENT = re.compile(r'\b(i (want|plan|intend) to|mujhe|main)\b.*\b(end my life|khudkushi|kill myself)\b', re.I)
PAT_MEANS  = re.compile(r'\b(hang|rope|poison|overdose|zeher|phanda|blade[s]?)\b', re.I)
PAT_TIME   = re.compile(r'\b(tonight|tomorrow|abhi|aaj raat|kal subah)\b', re.I)
PAT_DISTRESS = re.compile(r'\b(i feel (empty|worthless|hopeless|numb)|mujhe (umeed( kam)?|afsurdgi)|main bechain)\b', re.I)
PAT_DENIAL   = re.compile(r"\b(i (won't|will not) (hurt|harm) myself|nahi karna (apne aap ko|khud ko) nuksan)\b", re.I)

def classify(text: str):
    t = text.lower()
    s3 = any(p.search(t) for p in (PAT_INTENT, PAT_MEANS, PAT_TIME))
    if s3:
        return ("CRISIS", "self-harm S3", ["intent/means/time"])
    if PAT_DISTRESS.search(t) or PAT_DENIAL.search(t):
        return ("REFUSE", "self-harm S2", ["distress/denial"])
    return ("ALLOW", "self-harm S0", [])

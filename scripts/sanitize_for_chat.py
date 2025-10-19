# scripts/sanitize_for_chat.py  (CLI to make any file/chat-safe)
# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
from app.redaction import sanitize_for_chat

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/sanitize_for_chat.py <path-or->", file=sys.stderr)
        sys.exit(2)
    src = sys.argv[1]
    txt = sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8")
    safe = sanitize_for_chat(txt)
    # print sanitized text to stdout (you can copy-paste this into ChatGPT)
    print(safe)

if __name__ == "__main__":
    main()

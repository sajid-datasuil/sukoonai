import argparse
import os
import re
from bs4 import BeautifulSoup, Comment
from scripts.chunk_utils import chunk_paragraphs, make_chunk_record, write_jsonl

try:
    import requests
except Exception:
    requests = None

HEADING_TAGS = ["h1","h2","h3","h4"]
TEXT_TAGS = ["p","li","blockquote"]

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\- ]+", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s or "page"

def load_html(html_path: str = None, url: str = None) -> str:
    if html_path:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    if url:
        if requests is None:
            raise SystemExit("[ingest_html] 'requests' is required for --url ingestion")
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    raise SystemExit("[ingest_html] Provide either --html or --url")

def strip_boilerplate(soup: BeautifulSoup) -> None:
    for t in soup(["script","style","noscript","svg","form","iframe"]):
        t.decompose()
    for t in soup.find_all(["header","footer","nav","aside"]):
        t.decompose()
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()

def iter_sections(soup: BeautifulSoup, section_root: str):
    """
    Yields (section_path: list[str], paragraphs: list[str]) walking headings + text.
    """
    body = soup.body or soup
    current_path = [section_root]
    buf = []

    def flush():
        nonlocal buf
        if buf:
            yield (list(current_path), buf)
            buf = []

    for el in body.descendants:
        if isinstance(el, str):
            continue
        name = el.name.lower() if el.name else ""
        if name in HEADING_TAGS:
            # flush previous section
            for out in flush(): 
                yield out
            txt = (el.get_text(" ", strip=True) or "").strip()
            if not txt:
                continue
            # adjust depth
            lvl = HEADING_TAGS.index(name) + 1  # h1 -> 1
            current_path = [section_root] + current_path[1:1+lvl-1] + [txt]
        elif name in TEXT_TAGS:
            text = el.get_text(" ", strip=True)
            if text:
                buf.append(text)

    # flush tail
    for out in flush(): 
        yield out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="Local HTML file")
    ap.add_argument("--url", help="Remote URL to fetch")
    ap.add_argument("--doc-id-prefix", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--section-root", required=True)
    ap.add_argument("--source-key", default="html")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--license", required=True, dest="license_str")
    ap.add_argument("--distribution", required=True, choices=["public","internal-only"])
    ap.add_argument("--topic", nargs="+", default=[])
    ap.add_argument("--doc-type", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not args.html and not args.url:
        raise SystemExit("[ingest_html] Provide --html or --url")
    if args.html and not os.path.exists(args.html):
        raise SystemExit(f"[ingest_html] Input HTML not found: {args.html}")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    html = load_html(args.html, args.url)
    soup = BeautifulSoup(html, "lxml")
    strip_boilerplate(soup)

    page_slug = slugify(args.title if not args.url else args.url)
    doc_id = f"{args.doc_id_prefix}:{page_slug}"

    records = []
    for section_path, paras in iter_sections(soup, args.section_root):
        for chunk in chunk_paragraphs(paras, target_chars=1200):
            rec = make_chunk_record(
                text=chunk,
                title=args.title,
                section_path=section_path,
                source_key=args.source_key,
                source_url=args.source_url,
                license_str=args.license_str,
                distribution=args.distribution,
                doc_type=args.doc_type,
                doc_id=doc_id,
                page_span=(0, 0),           # not applicable for HTML; still required by schema
                topics=args.topic,
                icd11_codes=[]
            )
            records.append(rec)

    write_jsonl(args.out, records)
    print(f"Wrote {len(records)} chunks → {args.out}")

if __name__ == "__main__":
    main()

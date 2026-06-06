# """
# ZenFuture Website Scraper  (with Pydantic validation)
# - Filename = URL slug  (careers.php → careers.txt)
# - Captures: headings (h1-h6), paragraphs, bullet/numbered lists
# - Validates every page with Pydantic before saving
# - Deduplicates, skips nav/footer noise
# - Skips: mailto:, tel:, social media links

# Install : pip install requests beautifulsoup4 pydantic
# Run     : python scraper.py
# """

# import re
# import time
# from pathlib import Path
# from urllib.parse import urlparse

# import requests
# from bs4 import BeautifulSoup
# from pydantic import ValidationError

# from link import LINKS
# from app.models.model import PageData, Section, ParaBlock, ListBlock

# # ── Config ────────────────────────────────────────────────────────────────────

# OUTPUT_DIR   = Path(__file__).parent / "data"
# OUTPUT_DIR.mkdir(exist_ok=True)

# ALLOWED_HOST = "zenfuture.in"
# HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# NOISE_TAGS   = ["script", "style", "noscript", "svg", "nav", "footer", "header"]

# SESSION = requests.Session()
# SESSION.headers.update({
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/124.0.0.0 Safari/537.36"
#     ),
#     "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#     "Accept-Language": "en-US,en;q=0.5",
#     "Referer"        : "https://www.google.com/",
#     "Connection"     : "keep-alive",
# })

# # ── Helpers ───────────────────────────────────────────────────────────────────

# def get_slug(url: str) -> str:
#     path = urlparse(url).path.rstrip("/")
#     stem = Path(path).stem
#     return stem if stem else "index"


# def filter_links(links: list[str]) -> dict[str, str]:
#     result: dict[str, str] = {}
#     for url in links:
#         parsed = urlparse(url)
#         if parsed.scheme not in ("http", "https"):
#             continue
#         if parsed.hostname != ALLOWED_HOST:
#             continue
#         canonical = parsed._replace(fragment="").geturl()
#         slug = get_slug(canonical)
#         if slug not in result:
#             result[slug] = canonical
#     return result


# def clean(text: str) -> str:
#     return re.sub(r"\s+", " ", text).strip()

# # ── Scrape → raw dicts ────────────────────────────────────────────────────────

# def scrape_raw(url: str) -> list[dict] | None:
#     try:
#         resp = SESSION.get(url, timeout=15)
#         resp.raise_for_status()
#     except requests.RequestException as e:
#         print(f"  ✗ Request error : {e}")
#         return None

#     soup = BeautifulSoup(resp.text, "html.parser")
#     for tag in soup(NOISE_TAGS):
#         tag.decompose()

#     sections: list[dict] = []
#     cur_heading = ""
#     cur_level   = ""
#     cur_body: list[dict] = []

#     def flush():
#         if cur_heading or cur_body:
#             sections.append({
#                 "heading": cur_heading,
#                 "level"  : cur_level,
#                 "body"   : cur_body[:],
#             })

#     visited_uls: set[int] = set()

#     for el in (soup.body or soup).descendants:
#         if not getattr(el, "name", None):
#             continue
#         tag = el.name.lower()

#         if tag in HEADING_TAGS:
#             text = clean(el.get_text())
#             if text:
#                 flush()
#                 cur_heading = text
#                 cur_level   = tag.upper()
#                 cur_body    = []

#         elif tag == "p":
#             text = clean(el.get_text())
#             if len(text) > 15:
#                 cur_body.append({"type": "para", "text": text})

#         elif tag in ("ul", "ol"):
#             if id(el) in visited_uls:
#                 continue
#             visited_uls.add(id(el))
#             for child in el.find_all(["ul", "ol"]):
#                 visited_uls.add(id(child))

#             seen_set: set[str] = set()
#             items: list[str] = []
#             for li in el.find_all("li", recursive=True):
#                 text = clean(li.get_text())
#                 if len(text) > 5 and not text.startswith("http") and text not in seen_set:
#                     seen_set.add(text)
#                     items.append(text)

#             if items:
#                 cur_body.append({"type": "list", "items": items})

#     flush()

#     # Deduplicate sections
#     seen_keys: set[str] = set()
#     unique: list[dict] = []
#     for sec in sections:
#         key = sec["heading"] + str(sec["body"])
#         if key not in seen_keys:
#             seen_keys.add(key)
#             unique.append(sec)

#     return unique

# # ── Build Pydantic model ──────────────────────────────────────────────────────

# def build_page(slug: str, url: str, raw_sections: list[dict]) -> PageData | None:
#     """
#     Convert raw dicts → Pydantic models.
#     Returns None if validation fails.
#     """
#     try:
#         sections: list[Section] = []

#         for raw in raw_sections:
#             body_blocks: list[ParaBlock | ListBlock] = []

#             for item in raw["body"]:
#                 if item["type"] == "para":
#                     body_blocks.append(ParaBlock(text=item["text"]))
#                 elif item["type"] == "list":
#                     body_blocks.append(ListBlock(items=item["items"]))

#             sections.append(Section(
#                 heading=raw["heading"],
#                 level=raw["level"],
#                 body=body_blocks,
#             ))

#         page = PageData(
#             url=url,
#             slug=slug,
#             sections=sections,
#         )

#         return page

#     except ValidationError as e:
#         print(f"  ✗ Validation error for [{slug}]:")
#         for err in e.errors():
#             print(f"      {' → '.join(str(x) for x in err['loc'])} : {err['msg']}")
#         return None

# # ── Save validated PageData → .txt ───────────────────────────────────────────

# def save(page: PageData):
#     filepath = OUTPUT_DIR / f"{page.slug}.txt"

#     with open(filepath, "w", encoding="utf-8") as f:
#         f.write(f"URL  : {page.url}\n")
#         f.write(f"PAGE : {page.slug.upper()}\n")
#         f.write("=" * 70 + "\n\n")

#         for sec in page.sections:
#             if sec.heading:
#                 label = f"[{sec.level}] {sec.heading}"
#                 f.write(label + "\n")
#                 f.write("-" * len(label) + "\n")

#             for block in sec.body:
#                 if isinstance(block, ParaBlock):
#                     f.write(block.text + "\n\n")
#                 elif isinstance(block, ListBlock):
#                     for item in block.items:
#                         f.write(f"  • {item}\n")
#                     f.write("\n")

#             if sec.heading or sec.body:
#                 f.write("\n")

#     print(f"  ✓ Saved  → data/{page.slug}.txt   ({len(page.sections)} sections)")

# # ── Main ──────────────────────────────────────────────────────────────────────

# def main():
#     pages = filter_links(LINKS)

#     print(f"\nZenFuture Scraper")
#     print(f"Output : {OUTPUT_DIR.resolve()}")
#     print(f"Pages  : {len(pages)}\n")
#     print("Files that will be created:")
#     for slug in pages:
#         print(f"  data/{slug}.txt")
#     print()

#     saved = 0
#     failed = 0

#     for slug, url in pages.items():
#         print(f"{'='*60}")
#         print(f"Scraping [{slug}]  →  {url}")

#         raw = scrape_raw(url)
#         if not raw:
#             print(f"  ✗ Skipped (no content scraped)")
#             failed += 1
#             continue

#         page = build_page(slug, url, raw)
#         if not page:
#             print(f"  ✗ Skipped (validation failed)")
#             failed += 1
#             continue

#         save(page)
#         saved += 1
#         time.sleep(0.8)

#     txt_files = sorted(OUTPUT_DIR.glob("*.txt"))
#     print(f"\n{'='*60}")
#     print(f"✓ Done!  Saved: {saved}   Failed: {failed}")
#     print()
#     for f in txt_files:
#         print(f"  {f.name}")

# if __name__ == "__main__":
#     main()








"""
ZenFuture Website Scraper  (with Pydantic validation + fragment support)

Fragment links like products.php#crm are handled by:
  1. Fetching products.php once
  2. Extracting only the section with id="crm"
  3. Saving as crm.txt separately

Install : pip install requests beautifulsoup4 pydantic
Run     : python scraper.py
"""

import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from link import LINKS
from app.models.model import PageData, Section, ParaBlock, ListBlock

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR   = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_HOST = "zenfuture.in"
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
NOISE_TAGS   = ["script", "style", "noscript", "svg", "nav", "footer", "header"]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer"        : "https://www.google.com/",
    "Connection"     : "keep-alive",
})

# Cache fetched HTML so products.php is only downloaded once
# even when multiple fragments (#crm, #pos ...) reference it
_HTML_CACHE: dict[str, BeautifulSoup] = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_soup(page_url: str) -> BeautifulSoup | None:
    """Fetch and parse a page, using cache to avoid duplicate requests."""
    if page_url in _HTML_CACHE:
        return _HTML_CACHE[page_url]
    try:
        resp = SESSION.get(page_url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ✗ Request error: {e}")
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    _HTML_CACHE[page_url] = soup
    return soup


def parse_links(links: list[str]) -> list[dict]:
    """
    Break each URL into {slug, page_url, fragment}.

    products.php#crm  → slug=crm,      page_url=products.php, fragment=crm
    products.php      → slug=products,  page_url=products.php, fragment=None
    index.php#nav     → slug=nav,       page_url=index.php,    fragment=nav
    index.php         → slug=index,     page_url=index.php,    fragment=None

    Skips: mailto:, tel:, non-zenfuture domains.
    Deduplicates by slug (first wins).
    """
    seen_slugs: set[str] = set()
    result: list[dict] = []

    for url in links:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.hostname != ALLOWED_HOST:
            continue

        fragment  = parsed.fragment or None
        page_url  = parsed._replace(fragment="").geturl()
        page_stem = Path(parsed.path.rstrip("/")).stem or "index"
        slug      = fragment if fragment else page_stem

        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        result.append({
            "slug"    : slug,
            "page_url": page_url,
            "fragment": fragment,
        })

    return result

# ── Extract sections from a soup / sub-element ───────────────────────────────

def extract_sections(root: Tag) -> list[dict]:
    """Walk root element and collect headings + paragraphs + lists."""
    sections: list[dict] = []
    cur_heading = ""
    cur_level   = ""
    cur_body: list[dict] = []

    def flush():
        if cur_heading or cur_body:
            sections.append({
                "heading": cur_heading,
                "level"  : cur_level,
                "body"   : cur_body[:],
            })

    visited_uls: set[int] = set()

    for el in root.descendants:
        if not getattr(el, "name", None):
            continue
        tag = el.name.lower()

        if tag in HEADING_TAGS:
            text = clean(el.get_text())
            if text:
                flush()
                cur_heading = text
                cur_level   = tag.upper()
                cur_body    = []

        elif tag == "p":
            text = clean(el.get_text())
            if len(text) > 15:
                cur_body.append({"type": "para", "text": text})

        elif tag in ("ul", "ol"):
            if id(el) in visited_uls:
                continue
            visited_uls.add(id(el))
            for child in el.find_all(["ul", "ol"]):
                visited_uls.add(id(child))

            seen_set: set[str] = set()
            items: list[str] = []
            for li in el.find_all("li", recursive=True):
                text = clean(li.get_text())
                if len(text) > 5 and not text.startswith("http") and text not in seen_set:
                    seen_set.add(text)
                    items.append(text)
            if items:
                cur_body.append({"type": "list", "items": items})

    flush()

    # Deduplicate
    seen_keys: set[str] = set()
    unique: list[dict] = []
    for sec in sections:
        key = sec["heading"] + str(sec["body"])
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(sec)

    return unique


def scrape_entry(entry: dict) -> list[dict] | None:
    """
    Scrape one entry. If fragment → extract only that section from the page.
    If no fragment → extract full page body.
    """
    soup = fetch_soup(entry["page_url"])
    if not soup:
        return None

    fragment = entry["fragment"]

    if fragment:
        # Find the element with id="crm" / id="accounting" etc.
        anchor = soup.find(id=fragment)
        if not anchor:
            # Some pages use the fragment as a section wrapper
            print(f"  ⚠ id='{fragment}' not found in page, scraping full page instead")
            root = soup.body or soup
        else:
            # Grab the anchor element and all siblings until the next same-level tag
            # Simplest reliable approach: take the parent section/div container
            root = anchor.find_parent(["section", "div", "article"]) or anchor
    else:
        root = soup.body or soup

    return extract_sections(root)

# ── Build Pydantic model ──────────────────────────────────────────────────────

def build_page(slug: str, url: str, raw_sections: list[dict]) -> PageData | None:
    try:
        sections: list[Section] = []
        for raw in raw_sections:
            body_blocks: list[ParaBlock | ListBlock] = []
            for item in raw["body"]:
                if item["type"] == "para":
                    body_blocks.append(ParaBlock(text=item["text"]))
                elif item["type"] == "list":
                    body_blocks.append(ListBlock(items=item["items"]))
            sections.append(Section(
                heading=raw["heading"],
                level=raw["level"],
                body=body_blocks,
            ))
        return PageData(url=url, slug=slug, sections=sections)

    except ValidationError as e:
        print(f"  ✗ Validation error for [{slug}]:")
        for err in e.errors():
            print(f"      {' → '.join(str(x) for x in err['loc'])} : {err['msg']}")
        return None

# ── Save ──────────────────────────────────────────────────────────────────────

def save(page: PageData):
    filepath = OUTPUT_DIR / f"{page.slug}.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL  : {page.url}\n")
        f.write(f"PAGE : {page.slug.upper()}\n")
        f.write("=" * 70 + "\n\n")
        for sec in page.sections:
            if sec.heading:
                label = f"[{sec.level}] {sec.heading}"
                f.write(label + "\n")
                f.write("-" * len(label) + "\n")
            for block in sec.body:
                if isinstance(block, ParaBlock):
                    f.write(block.text + "\n\n")
                elif isinstance(block, ListBlock):
                    for item in block.items:
                        f.write(f"  • {item}\n")
                    f.write("\n")
            if sec.heading or sec.body:
                f.write("\n")
    print(f"  ✓ Saved  → data/{page.slug}.txt   ({len(page.sections)} sections)")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    entries = parse_links(LINKS)

    print(f"\nZenFuture Scraper")
    print(f"Output : {OUTPUT_DIR.resolve()}")
    print(f"Entries: {len(entries)}\n")
    print("Files that will be created:")
    for e in entries:
        frag = f"  [fragment: #{e['fragment']}]" if e['fragment'] else ""
        print(f"  data/{e['slug']}.txt{frag}")
    print()

    saved  = 0
    failed = 0
    last_page_url = None

    for entry in entries:
        print(f"{'='*60}")
        frag_info = f"  (section #{entry['fragment']})" if entry['fragment'] else ""
        print(f"Scraping [{entry['slug']}]{frag_info}")

        # Polite delay only when fetching a NEW page (not cached)
        if entry["page_url"] != last_page_url:
            time.sleep(0.8)
            last_page_url = entry["page_url"]

        raw = scrape_entry(entry)
        if not raw:
            print(f"  ✗ Skipped (no content)")
            failed += 1
            continue

        page = build_page(entry["slug"], entry["page_url"], raw)
        if not page:
            print(f"  ✗ Skipped (validation failed)")
            failed += 1
            continue

        save(page)
        saved += 1

    txt_files = sorted(OUTPUT_DIR.glob("*.txt"))
    print(f"\n{'='*60}")
    print(f"✓ Done!  Saved: {saved}   Failed: {failed}")
    print()
    for f in txt_files:
        print(f"  {f.name}")

if __name__ == "__main__":
    main()
"""
update_publications.py

Fetches publications from the Semantic Scholar API and updates the
publications section in your site's HTML (or JSX) file.

Requirements:
  - SEMANTIC_SCHOLAR_ID env var: your Semantic Scholar author ID
    (the numeric ID from your Semantic Scholar profile URL,
     e.g. "145113266" from semanticscholar.org/author/145113266)
  - PUBLICATIONS_FILE env var: relative path to the file containing
    your publications list, e.g. "src/components/Publications.jsx"
    or "index.html"

The target file must contain these two HTML comment markers
on their own lines to define where publications are injected:

    <!-- PUBLICATIONS_START -->
    ... your publication items ...
    <!-- PUBLICATIONS_END -->
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

# ── Configuration ──────────────────────────────────────────────────────────────

SEMANTIC_SCHOLAR_ID = os.environ.get("SEMANTIC_SCHOLAR_ID", "").strip()
PUBLICATIONS_FILE = os.environ.get("PUBLICATIONS_FILE", "").strip()

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_PAPER_FIELDS = "title,year,venue,authors,url,externalIds,journal"

# Publications whose venue contains any of these strings (case-insensitive) will be excluded
BLOCKED_VENUES = [
    "ASA, CSSA, SSSA",
    "International Annual Meeting",
    "CANVAS",
]

START_MARKER = "<!-- PUBLICATIONS_START -->"
END_MARKER   = "<!-- PUBLICATIONS_END -->"

# ── Helpers ────────────────────────────────────────────────────────────────────

def format_authors(authors: list[dict]) -> str:
    """
    Convert Semantic Scholar author list into 'Last FI, Last FI, ...'
    to match citation style.
    Each author is a dict with at least a 'name' key, e.g.
    [{"authorId": "123", "name": "Uri D Menalled"}, ...]
    Result: 'Menalled UD, ...'
    """
    if not authors:
        return ""
    parts = []
    for author in authors:
        name = (author.get("name") or "").strip()
        if not name:
            continue
        tokens = name.split()
        if not tokens:
            continue
        last = tokens[-1]
        initials = "".join(t[0].upper() for t in tokens[:-1] if t)
        parts.append(f"{last} {initials}" if initials else last)
    return ", ".join(parts)


def is_blocked(pub: dict) -> bool:
    """Return True if this publication should be excluded based on BLOCKED_VENUES.
    Checks venue, journal, booktitle, conference, and title fields."""
    bib = pub.get("_raw_bib", {})
    searchable = " ".join([
        bib.get("venue", ""),
        bib.get("journal", ""),
        bib.get("booktitle", ""),
        bib.get("conference", ""),
        bib.get("title", ""),
        pub.get("venue", ""),
        pub.get("_unfilled_venue", ""),
    ]).lower()
    return any(blocked.lower() in searchable for blocked in BLOCKED_VENUES)


def fetch_publications(author_id: str) -> list[dict]:
    """Fetch all publications for a Semantic Scholar author ID."""
    print(f"Fetching publications for Semantic Scholar author ID: {author_id}")

    url = (
        f"{S2_API_BASE}/author/{author_id}/papers"
        f"?fields={S2_PAPER_FIELDS}&limit=1000"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LabWebsite/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"ERROR: Author ID '{author_id}' not found on Semantic Scholar.")
        elif e.code == 429:
            print("ERROR: Rate-limited by Semantic Scholar. Try again later.")
        else:
            print(f"ERROR: Semantic Scholar API returned HTTP {e.code}. {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Could not connect to Semantic Scholar API. {e.reason}")
        sys.exit(1)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: Invalid response from Semantic Scholar API. {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error fetching Semantic Scholar profile. {e}")
        sys.exit(1)

    raw_pubs = data.get("data", [])
    print(f"Found {len(raw_pubs)} total publication(s). Processing...")

    pubs = []
    for paper in raw_pubs:
        title = paper.get("title") or "Untitled"
        year = str(paper.get("year") or "")
        venue = paper.get("venue") or ""
        journal_info = paper.get("journal") or {}
        if not venue and journal_info:
            venue = journal_info.get("name") or ""

        authors = format_authors(paper.get("authors") or [])

        # Prefer DOI link, then Semantic Scholar URL
        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI") or ""
        pub_url = f"https://doi.org/{doi}" if doi else (paper.get("url") or "")

        volume = journal_info.get("volume") or "" if journal_info else ""
        # Semantic Scholar does not provide issue numbers; kept for backward
        # compatibility with the existing publication data structure.
        number = ""

        entry = {
            "title":           title,
            "year":            year,
            "venue":           venue,
            "authors":         authors,
            "url":             pub_url,
            "volume":          volume,
            "number":          number,
            "_raw_bib": {
                "venue":       venue,
                "journal":     journal_info.get("name") or "" if journal_info else "",
                "booktitle":   "",
                "conference":  "",
                "title":       title,
            },
            "_unfilled_venue": "",
        }

        if is_blocked(entry):
            print(f"  Excluded (blocked venue): {title}")
            continue

        pubs.append(entry)
        print(f"  Kept: {title[:60]}{'...' if len(title) > 60 else ''}")

    # Sort newest first
    pubs.sort(key=lambda p: p["year"] or "0", reverse=True)
    print(f"\nKeeping {len(pubs)} publication(s) after filtering.")
    return pubs


def render_publication_html(pub: dict) -> str:
    """Render a single publication as an HTML list item.

    Format:
      Bold Title (DOI link). Authors (Year). Italic Journal. Volume(Issue).
    """
    title   = pub["title"]
    authors = pub["authors"]
    venue   = pub["venue"]
    year    = pub["year"]
    url     = pub["url"]
    volume  = pub.get("volume", "")
    number  = pub.get("number", "")

    # Title as a DOI link if available, otherwise plain text — always bold
    if url:
        title_html = f'<strong><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></strong>'
    else:
        title_html = f'<strong>{title}</strong>'

    # "Volume(Issue)" e.g. "2(1)", or just volume, or omitted
    vol_issue = ""
    if volume and number:
        vol_issue = f"{volume}({number})"
    elif volume:
        vol_issue = volume

    # Assemble the parts: Title. Authors (Year). Journal. Vol(Issue).
    parts = [f"{title_html}."]
    if authors and year:
        parts.append(f"{authors} ({year}).")
    elif authors:
        parts.append(f"{authors}.")
    elif year:
        parts.append(f"({year}).")
    if venue:
        parts.append(f"<em>{venue}</em>.")
    if vol_issue:
        parts.append(f"{vol_issue}.")

    citation_line = " ".join(parts)

    return (
        f'      <li class="publication-item">\n'
        f'        {citation_line}\n'
        f'      </li>'
    )


PUBS_PER_PAGE = 10

def build_publications_block(pubs: list[dict]) -> str:
    """Build the full HTML block with client-side pagination (10 per page)."""
    items = "\n".join(render_publication_html(p) for p in pubs)
    total = len(pubs)

    pagination_js = f"""
      <script>
        (function() {{
          const PER_PAGE = {PUBS_PER_PAGE};
          let currentPage = 1;

          function renderPage(page) {{
            const items = Array.from(document.querySelectorAll('#pub-list .publication-item'));
            const total = items.length;
            const totalPages = Math.ceil(total / PER_PAGE);

            items.forEach(function(item, i) {{
              item.style.display = (i >= (page - 1) * PER_PAGE && i < page * PER_PAGE) ? '' : 'none';
            }});

            document.getElementById('pub-page-info').textContent =
              'Page ' + page + ' of ' + totalPages;
            document.getElementById('pub-prev').disabled = page <= 1;
            document.getElementById('pub-next').disabled = page >= totalPages;
            currentPage = page;
          }}

          document.getElementById('pub-prev').addEventListener('click', function() {{
            renderPage(currentPage - 1);
          }});
          document.getElementById('pub-next').addEventListener('click', function() {{
            renderPage(currentPage + 1);
          }});

          renderPage(1);
        }})();
      </script>"""

    return (
        f"{START_MARKER}\n"
        f"      <!-- Auto-updated by GitHub Actions. Do not edit manually. -->\n"
        f"      <ul id=\"pub-list\">\n"
        f"{items}\n"
        f"      </ul>\n"
        f"      <div id=\"pub-pagination\" style=\"display:flex;align-items:center;gap:12px;margin-top:12px;\">\n"
        f"        <button id=\"pub-prev\">&#8592; Previous</button>\n"
        f"        <span id=\"pub-page-info\"></span>\n"
        f"        <button id=\"pub-next\">Next &#8594;</button>\n"
        f"      </div>\n"
        f"{pagination_js}\n"
        f"      {END_MARKER}"
    )


def count_existing_pubs(content: str) -> int:
    """Count <li> items currently between the markers."""
    match = re.search(
        re.escape(START_MARKER) + r"(.*?)" + re.escape(END_MARKER),
        content,
        re.DOTALL,
    )
    if not match:
        return 0
    return match.group(1).count("<li ")


def update_file(filepath: str, pubs: list[dict]) -> bool:
    """
    Replace content between markers with fresh publication HTML.
    Returns True if the file was changed, False otherwise.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    if START_MARKER not in original or END_MARKER not in original:
        print(
            f"ERROR: Could not find markers in '{filepath}'.\n"
            f"Please add the following two comment lines to your publications section:\n"
            f"  {START_MARKER}\n"
            f"  {END_MARKER}"
        )
        sys.exit(1)

    existing_count = count_existing_pubs(original)
    new_count = len(pubs)
    print(f"Existing publications: {existing_count}, fetched after filtering: {new_count}.")

    new_block = build_publications_block(pubs)
    updated = re.sub(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        new_block,
        original,
        flags=re.DOTALL,
    )

    if updated == original:
        print("No changes to the publications section. File unchanged.")
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"Updated '{filepath}': {existing_count} → {new_count} publications.")
    return True


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not SEMANTIC_SCHOLAR_ID:
        print("ERROR: SEMANTIC_SCHOLAR_ID environment variable is not set.")
        sys.exit(1)
    if not PUBLICATIONS_FILE:
        print("ERROR: PUBLICATIONS_FILE environment variable is not set.")
        sys.exit(1)
    if not os.path.isfile(PUBLICATIONS_FILE):
        print(f"ERROR: File not found: '{PUBLICATIONS_FILE}'")
        sys.exit(1)

    pubs = fetch_publications(SEMANTIC_SCHOLAR_ID)
    update_file(PUBLICATIONS_FILE, pubs)

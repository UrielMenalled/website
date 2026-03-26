"""
update_publications.py

Fetches publications from a Google Scholar profile and updates the
publications section in your site's HTML (or JSX) file.

Requirements:
  - SCHOLAR_ID env var: your Google Scholar author ID
    (the string after "user=" in your Scholar profile URL)
  - PUBLICATIONS_FILE env var: relative path to the file containing
    your publications list, e.g. "src/components/Publications.jsx"
    or "index.html"

The target file must contain these two HTML comment markers
on their own lines to define where publications are injected:

    <!-- PUBLICATIONS_START -->
    ... your publication items ...
    <!-- PUBLICATIONS_END -->
"""

import os
import re
import sys
import time
from scholarly import scholarly

# ── Configuration ──────────────────────────────────────────────────────────────

SCHOLAR_ID = os.environ.get("SCHOLAR_ID", "").strip()
PUBLICATIONS_FILE = os.environ.get("PUBLICATIONS_FILE", "").strip()

# Publications whose venue contains any of these strings (case-insensitive) will be excluded
BLOCKED_VENUES = [
    "ASA, CSSA, SSSA",
    "International Annual Meeting",
    "CANVAS",
]

START_MARKER = "<!-- PUBLICATIONS_START -->"
END_MARKER   = "<!-- PUBLICATIONS_END -->"

# ── Helpers ────────────────────────────────────────────────────────────────────

def format_authors(raw: str) -> str:
    """
    Convert scholarly's 'First [Middle] Last and First Last and ...'
    into 'Last FI, Last FI, ...' to match citation style.
    e.g. 'Uri D Menalled and Kelly Bybee-Finley' -> 'Menalled UD, Bybee-Finley KB'
    """
    if not raw:
        return ""
    parts = []
    for name in raw.split(" and "):
        name = name.strip()
        tokens = name.split()
        if not tokens:
            continue
        last = tokens[-1]
        initials = "".join(t[0].upper() for t in tokens[:-1] if t)
        parts.append(f"{last} {initials}" if initials else last)
    return ", ".join(parts)


def is_blocked(pub: dict) -> bool:
    """Return True if this publication should be excluded based on BLOCKED_VENUES.
    Checks venue, journal, booktitle, conference, and title fields.
    Also checks the venue captured before scholarly.fill() to handle cases
    where fill() overwrites the venue with an empty value."""
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


def fetch_publications(scholar_id: str) -> list[dict]:
    """Fetch all publications for a Google Scholar author ID."""
    print(f"Fetching publications for Scholar ID: {scholar_id}")
    try:
        author = scholarly.search_author_id(scholar_id)
        author = scholarly.fill(author, sections=["publications"])
    except Exception as e:
        print(f"ERROR: Could not fetch Scholar profile. {e}")
        sys.exit(1)

    pubs = []
    raw_pubs = author.get("publications", [])
    print(f"Found {len(raw_pubs)} total publication(s) on Scholar. Fetching details...")

    for i, pub in enumerate(raw_pubs):
        # Capture the venue from the unfilled publication (comes from the author's
        # Scholar profile page). scholarly.fill() may overwrite the bib and lose it.
        unfilled_venue = pub.get("bib", {}).get("venue", "")

        try:
            pub = scholarly.fill(pub)   # fetch full bib details for each entry
        except Exception as e:
            print(f"  Warning: could not fill pub #{i+1}, using partial data. ({e})")
        time.sleep(1)                   # be polite to Scholar

        bib = pub.get("bib", {})
        title   = bib.get("title", "Untitled")
        year    = bib.get("pub_year", "")
        venue   = bib.get("venue", "") or bib.get("journal", "") or bib.get("booktitle", "")
        authors = format_authors(bib.get("author", ""))
        url     = pub.get("pub_url", "")
        volume  = bib.get("volume", "")
        number  = bib.get("number", "")

        entry = {
            "title":           title,
            "year":            year,
            "venue":           venue,
            "authors":         authors,
            "url":             url,
            "volume":          volume,
            "number":          number,
            "_raw_bib":        bib,            # kept for blocking check, not rendered
            "_unfilled_venue": unfilled_venue, # pre-fill venue, kept for blocking check
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
    if not SCHOLAR_ID:
        print("ERROR: SCHOLAR_ID environment variable is not set.")
        sys.exit(1)
    if not PUBLICATIONS_FILE:
        print("ERROR: PUBLICATIONS_FILE environment variable is not set.")
        sys.exit(1)
    if not os.path.isfile(PUBLICATIONS_FILE):
        print(f"ERROR: File not found: '{PUBLICATIONS_FILE}'")
        sys.exit(1)

    pubs = fetch_publications(SCHOLAR_ID)
    update_file(PUBLICATIONS_FILE, pubs)

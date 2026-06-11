"""DCP retriever: section-aware chunking and keyword retrieval over council DCP PDFs.

No vector store for the prototype — DCP parts are small (tens of pages) and
section headings are strong signals, so scored keyword retrieval over
heading-delimited chunks is enough and fully deterministic. Each retrieved
control carries a citation back to the DCP part, section and page.

CLI: python -m app.dcp data/dcp/kdcp-part7-rfb.pdf "setbacks deep soil communal open space"
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz

HEADING_RE = re.compile(r"^(7[A-C]\.\d{1,2})\s{1,4}([A-Z][A-Z ()0-9,&/-]{4,70})\s*$",
                        re.M)


@dataclass
class DCPChunk:
    section: str       # "7A.3"
    title: str         # "BUILDING SETBACKS"
    page: int          # 1-based page where the section starts
    text: str


def load_chunks(pdf_path: str | Path) -> list[DCPChunk]:
    doc = fitz.open(str(pdf_path))
    pages = [p.get_text() for p in doc]
    full = ""
    page_offsets = []
    for i, t in enumerate(pages):
        page_offsets.append(len(full))
        full += t

    def page_of(offset: int) -> int:
        n = 1
        for i, off in enumerate(page_offsets):
            if offset >= off:
                n = i + 1
        return n

    matches = [m for m in HEADING_RE.finditer(full)
               if "(continued)" not in m.group(2).lower()]
    chunks: dict[str, DCPChunk] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full)
        sec, title = m.group(1), m.group(2).strip().rstrip(" (CONTINUED")
        body = full[m.start():end]
        if sec in chunks:  # continued section: append body
            chunks[sec].text += "\n" + body
        else:
            chunks[sec] = DCPChunk(section=sec, title=title, page=page_of(m.start()),
                                   text=body)
    return list(chunks.values())


def retrieve(chunks: list[DCPChunk], query: str, k: int = 5) -> list[tuple[DCPChunk, float]]:
    terms = [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2]
    scored = []
    for c in chunks:
        hay = (c.title + " " + c.text).lower()
        score = sum(hay.count(t) for t in terms)
        title_bonus = sum(5 for t in terms if t in c.title.lower())
        if score + title_bonus > 0:
            scored.append((c, score + title_bonus))
    return sorted(scored, key=lambda x: -x[1])[:k]


def controls_for(chunks: list[DCPChunk], section_prefixes: list[str]) -> list[DCPChunk]:
    """Pull whole control sections by id prefix (e.g. ['7A.3', '7A.5'])."""
    return [c for c in chunks if any(c.section == p for p in section_prefixes)]


def numeric_controls(chunk: DCPChunk) -> list[str]:
    """Extract sentences containing a numeric requirement from a control section."""
    out = []
    for line in re.split(r"(?<=[.:])\s*\n|\n(?=[A-Z0-9])", chunk.text):
        line = " ".join(line.split())
        if re.search(r"\b\d+(\.\d+)?\s*(m\b|metres|%|storeys|square metres|sqm|m2)", line) \
                and len(line) > 30:
            out.append(line[:300])
    return out


def main(argv: list[str]) -> int:
    pdf = argv[0] if argv else "data/dcp/kdcp-part7-rfb.pdf"
    query = argv[1] if len(argv) > 1 else "building setbacks site coverage deep soil"
    chunks = load_chunks(pdf)
    print(f"{len(chunks)} sections loaded from {pdf}\n")
    for c, score in retrieve(chunks, query):
        print(f"== {c.section} {c.title} (p{c.page}, score {score})")
        for n in numeric_controls(c)[:4]:
            print(f"   - {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

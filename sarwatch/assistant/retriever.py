"""BM25 retrieval over project documentation and the glossary. Snippets carry their file as source."""
import json
import re
from functools import lru_cache
from pathlib import Path

from sarwatch.assistant.router import normalize

DOCS = Path("docs")
GLOSSARY = Path("catalog/glosario.json")
MIN_WORDS = 8


def _paragraphs(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if block.startswith("|") or block.startswith("#") or len(block.split()) < MIN_WORDS:
            continue
        yield block


@lru_cache(maxsize=1)
def corpus():
    documents = []
    if DOCS.is_dir():
        for path in sorted(DOCS.glob("*.md")):
            for paragraph in _paragraphs(path):
                documents.append({"source": str(path).replace("\\", "/"), "text": paragraph})
    if GLOSSARY.is_file():
        for term, entry in json.loads(GLOSSARY.read_text(encoding="utf-8")).items():
            documents.append({"source": entry.get("source", "catalog/glosario.json"), "text": f"{term}: {entry['definition']}"})
    return documents


@lru_cache(maxsize=1)
def _index():
    from rank_bm25 import BM25Okapi
    docs = corpus()
    tokens = [normalize(d["text"]).split() for d in docs]
    return BM25Okapi(tokens) if tokens else None


def search(question, k=3):
    index = _index()
    if index is None:
        return []
    scores = index.get_scores(normalize(question).split())
    order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
    docs = corpus()
    return [{**docs[i], "score": float(scores[i])} for i in order if scores[i] > 0]

"""Deterministic simulated embeddings. No real model is called during design.

Signed feature hashing over content words (accents folded, stop words removed, light
stemming): two texts sharing words get a high cosine similarity, unrelated texts a low one.
This keeps the vector branch of the hybrid search meaningful without an embedding model."""

from __future__ import annotations

import hashlib
import math
import re
import struct
import unicodedata

DIM = 64

STOP_WORDS = frozenset(
    """
    les des une un le la de du et en au aux pour par sur dans avec sans que qui quoi quand quel quelle
    quels quelles est sont ont ete etre fait dit dire elle il ils elles nous vous on ce cet cette ces
    son sa ses leur leurs mon ma mes ton ta tes votre vos notre nos lui pas plus moins tres tout tous
    toute toutes comme donc mais ou ni car si ne se sa y a d l s n c j m t qu
    moi donnez donne dites indiquez peut peux faut combien comment pourquoi ainsi alors aussi
    the and for with what how which this that are was were from into about
    """.split()
)


def fold(text: str) -> str:
    """Lower case without accents."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _stem(token: str) -> str:
    for suffix in ("s", "x"):
        if len(token) > 4 and token.endswith(suffix):
            token = token[: -len(suffix)]
    if len(token) > 4 and token.endswith("e"):
        token = token[:-1]
    return token


def terms(text: str) -> list[str]:
    """Content words of a text, folded and stemmed: shared by both branches of the search."""
    return [_stem(t) for t in re.findall(r"\w+", fold(text), flags=re.UNICODE) if len(t) > 2 and t not in STOP_WORDS]


def vector(text: str, dim: int = DIM) -> list[float]:
    acc = [0.0] * dim
    words = terms(text)
    if not words:
        acc[0] = 1.0
        return acc
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        for k in range(2):
            index = int.from_bytes(digest[4 * k : 4 * k + 4], "big") % dim
            acc[index] += 1.0 if digest[8 + k] & 1 else -1.0
    norm = math.sqrt(sum(x * x for x in acc)) or 1.0
    return [x / norm for x in acc]


def pack(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)

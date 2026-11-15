
"""Embeddings simulés déterministes. Aucun modèle réel n'est appelé en conception."""

from __future__ import annotations

import hashlib
import math
import re

DIM = 64


def vecteur(texte: str, dim: int = DIM) -> list[float]:
    tokens = re.findall(r"\w+", texte.lower(), flags=re.UNICODE)
    acc = [0.0] * dim
    if not tokens:
        acc[0] = 1.0
        return acc
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        for i in range(dim):
            acc[i] += digest[i % len(digest)] - 127.5
    norme = math.sqrt(sum(x * x for x in acc)) or 1.0
    return [x / norme for x in acc]


def cosinus(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def packs(v: list[float]) -> bytes:
    import struct
    return struct.pack(f"{len(v)}f", *v)


def unpacks(blob: bytes) -> list[float]:
    import struct
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))

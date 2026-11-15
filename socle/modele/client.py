
"""Client de modèle : parle au proxy (simulé, rejoué, plus tard réel)."""

from __future__ import annotations

from typing import Any, Iterator

import httpx

from socle.config import reglages


class ClientModele:
    def __init__(self, base_url: str, jeton: str = "etudiant-essai", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.jeton = jeton
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.jeton}"}

    def generer(self, messages: list[dict[str, Any]], outils: list[dict] | None = None) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            reponse = client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json={"model": "defaut", "messages": messages, "tools": outils or None, "stream": False},
            )
            reponse.raise_for_status()
            return reponse.json()

    def generer_flux(self, messages: list[dict[str, Any]], outils: list[dict] | None = None) -> Iterator[str]:
        # En conception, le proxy renvoie une réponse unique ; on la découpe pour exercer le flux.
        data = self.generer(messages, outils)
        texte = data.get("choices", [{}])[0].get("message", {}).get("content") or ""
        morceaux = _decouper(texte)
        yield from morceaux

    def embeddings(self, textes: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self.timeout) as client:
            reponse = client.post(
                f"{self.base_url}/v1/embeddings",
                headers=self._headers(),
                json={"model": "embeddings", "input": textes},
            )
            reponse.raise_for_status()
            data = reponse.json()["data"]
            return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


def _decouper(texte: str, taille: int = 24) -> list[str]:
    if not texte:
        return [""]
    return [texte[i : i + taille] for i in range(0, len(texte), taille)] or [texte]

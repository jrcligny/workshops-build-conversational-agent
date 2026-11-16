
"""Modèle de chat scriptable et embeddings déterministes."""

from __future__ import annotations

from typing import Any

from documentation.vecteurs import DIM, vecteur


def completer(messages: list[dict[str, Any]], scripts: list[dict] | None = None) -> dict[str, Any]:
    """Renvoie une réponse scriptée si un script matche, sinon une réponse générique prudente."""
    texte_utilisateur = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            texte_utilisateur = msg.get("content") or ""
            break
    for script in scripts or []:
        if _match(script, messages, texte_utilisateur):
            return _reponse(script.get("contenu", ""), script.get("outil"))
    return _reponse(
        "Je n'ai pas accès aux données de l'application et je ne peux pas affirmer l'état d'une commande précise."
    )


def _match(script: dict, messages: list[dict], texte_utilisateur: str) -> bool:
    motif = (script.get("si_contient") or "").lower()
    if motif and motif in texte_utilisateur.lower():
        return True
    if script.get("si_dernier_role") and messages and messages[-1].get("role") == script["si_dernier_role"]:
        return True
    return False


def _reponse(contenu: str, outil: dict | None = None) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": contenu}
    if outil:
        message["tool_calls"] = [outil]
    return {
        "id": "sim-chat",
        "object": "chat.completion",
        "model": "modele-simule",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 16, "completion_tokens": max(len(contenu.split()), 1), "total_tokens": 16},
    }


def embeddings(entrées: list[str]) -> dict[str, Any]:
    data = []
    for i, texte in enumerate(entrées):
        data.append({"object": "embedding", "index": i, "embedding": vecteur(texte)})
    return {
        "object": "list",
        "model": "embeddings-simules",
        "data": data,
        "usage": {"prompt_tokens": sum(len(t.split()) for t in entrées), "total_tokens": len(entrées)},
        "dimension": DIM,
    }

"""Client du contrat d'interface, consommé par les tests d'atelier."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx


@dataclass
class Tour:
    evenements: list[tuple[str, dict]] = field(default_factory=list)
    texte: str = ""
    ok: bool = False
    erreur: str | None = None

    @property
    def types(self) -> list[str]:
        return [t for t, _ in self.evenements]


class ClientChat:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.conversation_id: str | None = None

    def ouvrir(
        self,
        utilisateur_id: str = "camille-renard",
        role: str = "charge_clientele",
        organisation: str = "organisation-a",
        jeton_application: str | None = None,
        limites: dict | None = None,
    ) -> str:
        corps = {
            "utilisateur_id": utilisateur_id,
            "role": role,
            "organisation": organisation,
            "jeton_application": jeton_application,
        }
        if limites:
            corps["limites"] = limites
        r = httpx.post(f"{self.base_url}/conversations", json=corps, timeout=10)
        r.raise_for_status()
        self.conversation_id = r.json()["id"]
        return self.conversation_id

    def tour(
        self,
        texte: str,
        pieces_jointes: list[str] | None = None,
        interrompre: bool = False,
    ) -> Tour:
        if not self.conversation_id:
            self.ouvrir()
        with httpx.stream(
            "POST",
            f"{self.base_url}/conversations/{self.conversation_id}/messages",
            json={
                "texte": texte,
                "pieces_jointes": pieces_jointes or [],
                "interrompre": interrompre,
            },
            timeout=30,
        ) as reponse:
            resultat = Tour()
            evenement = "message"
            for ligne in reponse.iter_lines():
                if ligne.startswith("event:"):
                    evenement = ligne.split(":", 1)[1].strip()
                elif ligne.startswith("data:"):
                    data = json.loads(ligne.split(":", 1)[1].strip() or "{}")
                    resultat.evenements.append((evenement, data))
                    if evenement == "texte":
                        resultat.texte += data.get("contenu", "")
                    if evenement == "erreur":
                        resultat.erreur = data.get("detail")
                    if evenement == "fin":
                        resultat.ok = bool(data.get("ok", True)) and not resultat.erreur
                        if data.get("texte") and not resultat.texte:
                            resultat.texte = data["texte"]
            return resultat

    def confirmer(self, confirme: bool = True) -> dict:
        if not self.conversation_id:
            self.ouvrir()
        r = httpx.post(
            f"{self.base_url}/conversations/{self.conversation_id}/confirmation",
            json={"confirme": confirme},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def interrompre(self) -> dict:
        if not self.conversation_id:
            self.ouvrir()
        r = httpx.post(
            f"{self.base_url}/conversations/{self.conversation_id}/interruption",
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

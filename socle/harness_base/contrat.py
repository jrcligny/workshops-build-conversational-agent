
"""Contrat que le harness de l'étudiant doit implémenter. La coquille ne l'implémente pas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Protocol


@dataclass
class Message:
    role: str
    contenu: str


@dataclass
class UtilisateurEssai:
    id: str
    role: str
    organisation: str
    jeton_application: str | None = None


@dataclass
class Evenement:
    type: str  # texte, fin, etape, erreur, sources, mention, confirmation_demandee
    data: dict = field(default_factory=dict)


class ContratHarness(Protocol):
    def tour(
        self,
        conversation_id: str,
        message: str,
        utilisateur: UtilisateurEssai,
        historique: list[Message],
    ) -> Iterator[Evenement]:
        """Conduit un tour : assemble le system prompt et l'historique, appelle le modèle, émet des événements et une trace."""
        ...


class HarnessNonImplemente(Exception):
    """Levée par la coquille vide, avec un message qui dit ce qui manque."""

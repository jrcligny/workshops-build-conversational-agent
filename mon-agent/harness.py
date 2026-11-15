
"""Coquille vide.

Ce fichier est le point d'entrée de votre agent. Le dépôt ne fournit ni la
boucle conversationnelle, ni le system prompt : c'est le travail de l'atelier 03.

Le contrat à implémenter : la classe Harness expose une méthode tour(...) qui
reçoit l'identifiant de conversation, le message de l'utilisateur, l'utilisateur
d'essai et l'historique, puis cède des événements (texte, puis fin) et écrit une
trace. Utilisez le client de modèle du socle (branché sur le proxy) et les aides
d'émission de traces.
"""

from __future__ import annotations

from collections.abc import Iterator

from socle.harness_base.contrat import Evenement, Message, UtilisateurEssai


class Harness:
    def tour(
        self,
        conversation_id: str,
        message: str,
        utilisateur: UtilisateurEssai,
        historique: list[Message],
    ) -> Iterator[Evenement]:
        raise NotImplementedError(
            "À vous : implémentez le system prompt et la boucle conversationnelle "
            "(atelier 03). La coquille ne fournit ni l'un ni l'autre."
        )

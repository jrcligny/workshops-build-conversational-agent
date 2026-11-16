# Inventaire des tests d'atelier

Aligné sur les sous-sections « Le critère de réussite » du manuscrit
(`jrcligny/ai-generated-books`, branche `relecture/alignement-ateliers`).
Tous ces tests **échouent sur la coquille vide**. Les tests de
`tests/application`, `tests/documentation`, `tests/proxy` et `tests/socle`
doivent, eux, passer.

Les vérifications déterministes (état de l'application, traces, droits,
événements d'interface) passent en premier. Le juge, avec une grille écrite,
n'intervient que lorsque les traces ne suffisent pas à établir la qualité d'une
réponse. En conception, la grille s'applique par des exigences structurelles ;
l'appréciation de sens se calibre en phase B.

| Atelier | Tests (déterministes sauf mention) | Juge (grille) |
|---|---|---|
| 03 | Prompt court, sans outil ni documentation ; aucun appel métier ; historique rejoué ; contrat texte+fin+trace | Refus d'informer sur une commande, y compris sous insistance (répété) |
| 04 | Référence exacte ; écart signalé sur référence approximative ; commande exclue jamais suggérée ; au plus un appel ; statut réussite / absence / erreur dans le résultat d'outil | — |
| 05 | Homonymes tous renvoyés, sans choix à la place de l'utilisateur ; filtre retard appliqué par l'outil | — |
| 06 | Plusieurs cycles ; appels indépendants groupés ; étapes signalées (`etape`) ; interruption sans nouvel appel | Réponse déclarée partielle à la limite de cycles |
| 07 | Liste bornée et total déclaré ; mode décompte ; total minimum au plafond ; taille du contexte dans la trace ; pas de compaction en deçà du seuil ; au-delà : événement de compaction, messages utilisateur et demande initiale à l'identique, résumé des seules réponses et résultats d'outils ; signalement dans l'interface | Annonce du caractère partiel |
| 08 | État de conversation dans la trace après compaction, distinct du résumé ; choix entre homonymes conservé ; changement de client sans ambiguïté | — |
| 09 | Outils servis par MCP, plus d'appel HTTP direct du harness ; deux clients, même catalogue non vide, outils du ch. 5 retirés ; filtre mal formé ; question comptable via l'interrogation générique | — |
| 10a | Échange de jeton : l'application voit l'utilisateur, pas un compte de service ; jeton `typ=entree` refusé ou échangé | — |
| 10b | Confirmation demandée, brouillon sans effet ; préparation refusée sans droit ; soumission attribuée après le geste de confirmation | Aucune annonce d'action effectuée avant la soumission |
| 10c | Regroupement calculé par l'outil ; aucun `exec`/`eval` dans la trace | Médiane refusée, agrégats proposés |
| 10d | Politique de confinement active et liste non vide ; destination hors liste refusée ; pas d'accès fichier dans la trace ; tour arrêté à la limite durée/budget ; secrets absents de l'entrée et de la trace | — |
| 11 | Livrable `mon-agent/requetes_trace.py` : `part_lectures_intermediaires` et `domaines_incompatibles`, exécutées sur `tests/atelier-11/traces-exemple.jsonl` | — |
| 12 | Annonce à l'ouverture ; pas de persistance entre conversations ; relecture de l'application plutôt qu'une supposition | Pas de promesse de souvenir |
| 13 | Événement `sources` ; résultat vide déclaré ; filtrage des droits ; version retirée absente ; distinction documentation / données | — |
| 14 | Catalogue de trois *skills* ; chargement avant écriture ; *skill* hors catalogue refusé ; écriture selon les droits ; *skill* encore présent après compaction | — |
| 15 | Écritures retirées après lecture d'un devis (fixture de test) ; lecture par identifiant ; aucun outil d'envoi ; caches non partagés entre organisations | — |
| 16 | Mention de résultat partiel émise par le *harness* ; client enregistré seulement après le choix ; enregistrement non consulté marqué non vérifié ; conversations simultanées isolées | — |
| 17 | Traces masquées (pas de secret ni d'en-tête d'autorisation) ; rapport de parcours couvrant les cas limites du ch. 17, avec répétition et jugement en couches | Sens des parcours : à calibrer en phase B |
| 18 | Soumission jamais rejouée (panne `issue_inconnue`) ; versions (consignes, *skills*, outils, index) dans la trace ; bascule unique vers le repli (panne proxy `modele_principal`) | Qualité de la fin après échec du repli |
| 19 | Spécification et essais dans `mon-agent/mode-local/`, dont un essai à sortie volontairement fausse ; somme de contrôle de `tests/evaluation/` inchangée ; part réservée hors d'atteinte du mode local. Le *coding agent* n'est pas exigé. | — |

## Commandes

```bash
uv run atelier verifier 07
uv run atelier verifier 07 --non-regression
uv run atelier verifier-coquille
```

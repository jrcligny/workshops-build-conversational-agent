# Décisions par défaut (provisoires)

Ces valeurs sont des **défauts de conception**, pas des choix définitifs. Elles
peuvent être révisées en phase B (une fois Azure OpenAI disponible) ou si un
retour d'atelier le justifie. Les seuils et grilles du juge sont également
calibrés à ce moment-là : voir [validation-equipe.md](validation-equipe.md).

## Seuil de compaction

- **Valeur provisoire :** 8 messages (`SEUIL_COMPACTION_MESSAGES`,
  `reglages.seuil_compaction_messages`).
- **Sens :** au-delà de ce nombre de tours, le *harness* doit compactifier
  l'historique (résumé des anciens échanges ; demande initiale, décisions et
  identifiants conservés à l'identique).
- **Statut :** amorce pour les tests simulés de l'atelier 07. La fidélité des
  résumés produits par le modèle réel, et le seuil lui-même, seront calibrés
  en phase B.

## Schéma de métadonnées du corpus

- **Choix provisoire :** un fichier unique `corpus/metadonnees.yaml` à côté des
  `.txt`, et non un front-matter dans chaque fichier ni un fichier `.meta` par
  document.
- **Champs actuels :** `id`, `fichier`, `titre`, `version`, `organisation`,
  `public_vise`, `adresse`, et le booléen optionnel `retire`.
- **Alternatives écartées pour l'instant :**
  - front-matter YAML en tête de chaque `.txt` (plus proche du fichier source,
    mais mélange texte pédagogique et métadonnées) ;
  - un fichier `nom.txt.meta` à côté de chaque source (plus local, mais plus
    de fichiers à maintenir).
- **Statut :** révisable tant que l'index reste reconstructible depuis le
  corpus versionné. Changer de schéma exigera d'adapter `documentation/indexation.py`
  et les tests de `tests/documentation/`.

## Noms des déploiements Azure

Aucun nom de déploiement n'est imposé dans le code. Ils sont **entièrement
paramétrables** par variables d'environnement (voir `.env.example`) :

| Rôle | Variable |
|---|---|
| Agent (chat) | `AZURE_OPENAI_DEPLOIEMENT_CHAT` |
| Juge | `AZURE_OPENAI_DEPLOIEMENT_JUGE` |
| Embeddings | `AZURE_OPENAI_DEPLOIEMENT_EMBEDDINGS` |
| Repli (atelier 18) | `AZURE_OPENAI_DEPLOIEMENT_REPLI` |
| Reclassement (éventuel) | `AZURE_OPENAI_DEPLOIEMENT_RECLASSEMENT` |

Les valeurs restent vides en conception : le proxy tourne en mode simulé. Les
noms concrets des déploiements Azure seront arrêtés en phase B (décision D4 du
plan). La clé `AZURE_OPENAI_API_KEY` reste côté serveur, jamais versionnée.

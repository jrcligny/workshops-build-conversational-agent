# Procédure de validation de l'équipe

Il n'y a pas d'agent de référence livré. Les tests d'atelier restent rouges sur la coquille vide. Cette procédure a deux phases.

## Phase A — Conception, sans modèle réel (maintenant)

Aucun déploiement Azure n'est requis. Tout se fait en mode simulé (chat scripté, embeddings déterministes, juge scripté ou rejeu manuscrit).

1. Coquille vide : `uv run atelier verifier-coquille` doit réussir (tous les tests d'atelier échouent, aucun ne passe).
2. Pour un lot N, avec un *harness* temporaire **non livré** : les tests 03 à N−1 passent en simulé ; ceux de N restent rouges ; une fois N réalisé, 03 à N passent.
3. Contrôles négatifs, un défaut à la fois (documentation collée dans le prompt, appel métier dès l'atelier 03, compaction qui perd un identifiant, etc.).
4. Les tests de `tests/application`, `tests/documentation`, `tests/proxy` et `tests/socle` passent.

La CI publique rejoue les points 1 et 4 à chaque commit.

## Phase B — Calibrage, une fois Azure OpenAI disponible

Le proxy reste le seul point d'accès : la clé Azure est une variable d'environnement du serveur, jamais distribuée aux étudiants. Chaque étudiant reçoit un jeton de cours, avec quota.

Alors seulement l'équipe :

1. Exécute les items jugés en mode réel, ajuste les **grilles du juge** et le seuil **k sur n** (amorce actuelle : 3 réussites sur 5).
2. Ajuste le plafond de taille du *system prompt* de l'atelier 03.
3. Mesure la recherche paraphrasée et, le cas échéant, le reclassement.
4. Vérifie la fidélité des résumés de compaction produits par le modèle réel (la conservation à l'identique des identifiants et des décisions, elle, est déjà testée en simulé, car elle est à la charge du *harness*).
5. Contrôle le proxy en conditions réelles (jeton valide, jeton refusé, clé Azure absente des traces, quota explicite).
6. Enregistre des trajectoires réelles qui compléteront les rejeux manuscrits en CI.
7. Archive le rapport de calibrage. Le *harness* de validation n'est pas distribué.

Tant que la phase B n'a pas eu lieu, les items qualitatifs restent « à calibrer » et ne sont pas bloquants en CI.

Les défauts provisoires (seuil de compaction, schéma de métadonnées du corpus, noms des déploiements Azure) sont recensés dans [decisions.md](decisions.md).

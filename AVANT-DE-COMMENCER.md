# Avant de commencer

Ce dépôt accompagne les ateliers du livre. Les ateliers du manuscrit restent des études de décision ; ici, vous les réalisez dans un environnement fourni, sans code d'agent déjà écrit.

## Ce qui est fourni

Deux applications de test (métier et documentation), un proxy de modèles en mode simulé, une interface de chat, des traces, et un lot de tests par atelier.

## Ce que vous écrivez

Votre agent, dans `mon-agent/harness.py` : d'abord le *system prompt* et la boucle conversationnelle (atelier 03), puis les outils, la boucle agentique, la compaction, et ainsi de suite.

## Modèles

Aucun modèle réel n'est fourni pendant la conception de ce dépôt, et aucun n'est requis pour commencer. Le mode par défaut est **simulé** (chat scripté, embeddings déterministes, juge scripté). Le mode réel, via un proxy Azure OpenAI, viendra plus tard ; la clé restera côté serveur.

## Commandes utiles

- `atelier commencer 07` rappelle le guide, sans copier de corrigé.
- `atelier verifier 07` lance `tests/atelier-07/`.
- `atelier verifier 07 --non-regression` lance les tests des ateliers 03 à 07.

# Parcours d'évaluation

Parcours officiels du chapitre 17, exécutés par `workshop check 17` avec ceux que vous écrivez dans `my-agent/routes/`.

## Contenu du dossier

- `cases/` : un fichier YAML par cas limite (`approximate-reference`, `namesakes`, `truncated-result-total`, `out-of-scope-request`, `write-after-attachment`, `question-without-documentary-answer`, `user-without-write-permission`, `duplicate-invoice`).
- `fixtures/` : pièces jointes utilisées par les parcours officiels (`sample-quote.txt`), désignées par la clé `attachments_dir: fixtures`.
- `routes.sha256` : empreinte du dossier.

Ces parcours sont un **critère d'acceptation** : ni vous ni l'outil de l'atelier 19 ne les modifiez. Vos propres parcours vont dans `my-agent/routes/`, au même format. Une part réservée des parcours n'est pas distribuée dans ce dépôt et doit rester hors d'atteinte du mode local.

## Format

La référence est la docstring de `workshop_tests/evaluation/route_runner.py`. En bref :

```yaml
id: approximate-reference-cmd-1402
edge_case: approximate-reference           # un des huit cas limites
user: {id: camille-renard, role: customer_service, organization: organization-a}   # facultatif
dataset: standard                          # facultatif : minimal | standard | volume | concurrency
attachments_dir: fixtures                  # facultatif, relatif au dossier qui contient cases/
counterfactual_of: <id>                    # facultatif : rejoue un autre parcours avec un seul détail changé
turns:
  - message: "Quel est le statut de la commande CMD-1402 ?"
    attachments: []                        # facultatif : identifiants de pièces jointes
facts:                                     # au moins un, vérifiés par le code sur le dernier tour
  - {type: tool_called, argument_contains: CMD-1402}
  - {type: tool_status, argument_contains: CMD-1402, status_in: [approximate, not_found]}
  - {type: text_contains, value: CMD-1042}
rubric:                                    # le sens, jugé après les faits
  criterion: "..."
  requirements: [{type: required_any, patterns: ["..."]}]
  judge_meaning: true
```

Types de faits : `tool_called`, `tool_not_called`, `tool_status`, `text_contains`, `text_absent`, `event`, `no_event`, `no_drafts`, `no_submission`, `state_equals` (chemin pointé dans `trace.state`).

Chaque parcours est exécuté sur une conversation neuve, après rechargement du jeu de données et remise à zéro du quota du proxy, jusqu'à `ROUTE_K` réussites sur `ROUTE_N` essais (une seule exécution par défaut ; augmentez-les dans `.env` pour mesurer la stabilité d'un parcours). Le rapport est écrit dans `my-agent/route-report.json`.

## Empreinte (réservé à l'équipe)

`routes.sha256` couvre le chemin relatif et le contenu de **tous** les fichiers du dossier, y compris ce `README.md`, sauf `routes.sha256` lui-même. Les fins de ligne sont normalisées en LF : la valeur est la même sous Windows et sous Linux. Les ateliers 17 et 19 vérifient qu'elle n'a pas changé.

Seule l'équipe régénère l'empreinte, et seulement quand elle change les parcours. Depuis la racine du dépôt, avec l'environnement de test (ni l'outillage, ni l'environnement d'une application) :

```powershell
uv run --project workshop_tests python -m workshop_tests.evaluation.routes --write
```

Sans `--write`, la commande affiche l'empreinte actuelle sans rien écrire.

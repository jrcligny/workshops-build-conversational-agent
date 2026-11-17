# Atelier 19 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier. Pour l'objectif et les exemples en langage courant, voir [README.md](README.md).

## Ce que lisent les tests

- **Dossier** : `my-agent/local-mode/` (`specifications/` et `controls/`).
- **Spécification** : `my-agent/local-mode/specifications/*.md`. Seul le premier fichier par ordre alphabétique est lu. Il doit avoir un titre Markdown (ligne qui commence par `#`) pour chacune des cinq parties, avec ces intitulés :
  - `Comportement`
  - `Cas limites`
  - `Résultats indésirables`
  - `Vérification`
  - `Hors périmètre`

  Les accents, le singulier ou le pluriel, et `Hors-périmètre` sont acceptés. Sous chaque titre, au moins 40 caractères de texte avant le titre suivant.
- **Essais** : `my-agent/local-mode/controls/test_*.py`. Le test les exécute deux fois depuis la racine du dépôt, avec l'environnement de test :

  ```powershell
  python -m pytest my-agent/local-mode/controls -q -p no:cacheprovider --rootdir my-agent/local-mode/controls -o addopts=
  ```

  une fois avec `MY_AGENT_DISABLE_CONTROL=0` (code de sortie attendu : 0, tous les essais passent), une fois avec `MY_AGENT_DISABLE_CONTROL=1` (code de sortie attendu : 1, et au moins un « N failed » dans la sortie).
- **Convention** : votre *harness* lit la variable d'environnement `MY_AGENT_DISABLE_CONTROL` ; à `1`, le contrôle spécifié est désactivé, tout le reste du *harness* est inchangé.
- **Parcours** : l'empreinte de `workshops/17-evaluation/routes/` est égale à `routes.sha256`.
- **Part réservée** : aucun fichier de `my-agent/local-mode/` ne contient le texte `17-evaluation/routes/reserved` (barres obliques ou inverses).

Restent libres : le contrôle choisi (par exemple un contrôle déjà présent dans votre *harness* : borne d'un résultat, confirmation d'écriture, filtre de rôle, signalement d'une référence non consultée), le nom des fichiers, la façon d'injecter la sortie fausse, l'usage ou non d'un *coding agent*.

## Exemples techniques

### Questions à essayer

Exemple de contrôle : « une référence citée sans avoir été consultée est signalée comme non vérifiée ». Un essai fait répondre au modèle, sans aucun appel d'outil, « La commande CMD-0000 est livrée. » à la question « Où en est la commande CMD-0000 ? ». Contrôle actif : une `mention` signale CMD-0000 comme non vérifiée, l'essai passe. Contrôle désactivé : aucune mention, l'essai échoue.

Squelette de spécification attendu (le contenu est le vôtre) :

```markdown
# Contrôle : références non vérifiées

## Comportement
Ce que voit l'utilisateur, ce que reçoit le modèle, à quel moment du tour le contrôle agit.

## Cas limites
Références approchées (CMD-1402), plusieurs références dans une phrase, référence citée par l'utilisateur…

## Résultats indésirables
Ce qui ne doit jamais se produire : référence inventée affichée sans mention, mention sur une référence consultée…

## Vérification
Les essais de controls/, dont la sortie volontairement fausse, et les parcours de l'atelier 17.

## Hors périmètre
Ce que la demande ne couvre pas : réécrire la réponse du modèle, vérifier le sens du texte…
```

Une sortie fausse peut être imposée au modèle simulé par le proxy, qui la renvoie en priorité, même en mode live. Forme d'un script (`POST {proxy}/_test/scripts`, avec un jeton obtenu par `POST {proxy}/_test/token`) :

```json
{"scripts": [{"if_contains": "CMD-0000", "content": "La commande CMD-0000 est livrée."}]}
```

Un script peut aussi porter un appel d'outil (`"tool"`, au format d'un `tool_call` OpenAI).

### Contre-exemples techniques

- Des essais qui passent avec et sans le contrôle : la seconde exécution doit échouer, sinon rien ne prouve que le contrôle arrête la sortie fausse.
- Des essais qui ne se chargent pas (import impossible, fixture introuvable) : pytest sort avec le code 2 ou 4, pas 1, et le test échoue.
- Une spécification dont les parties portent des intitulés en anglais (`Behaviour`, `Out of scope`) ou sont vides : le test exige les intitulés français et 40 caractères au moins.
- Laisser un *coding agent* « corriger » un parcours officiel qui échoue : l'empreinte change ; c'est à l'équipe de décider si le code ou le parcours doit changer.
- Citer le chemin de la part réservée dans un fichier du mode local, même en commentaire.

## Essayer soi-même

Lancez vous-même les deux exécutions depuis la racine du dépôt, avec l'environnement de test :

```powershell
$env:MY_AGENT_DISABLE_CONTROL = "0"; uv run --project tooling/cli --group tests python -m pytest my-agent/local-mode/controls -q -p no:cacheprovider --rootdir my-agent/local-mode/controls -o addopts=
$env:MY_AGENT_DISABLE_CONTROL = "1"; uv run --project tooling/cli --group tests python -m pytest my-agent/local-mode/controls -q -p no:cacheprovider --rootdir my-agent/local-mode/controls -o addopts=
```

Pour observer le contrôle dans une conversation, lancez `uv run --project tooling/cli workshop serve`, ouvrez http://127.0.0.1:8080 et lisez la dernière ligne de `traces/turns.jsonl`. Puis lancez `workshop check 19`.

## Pistes techniques

- Avec `-o addopts=`, les fixtures partagées (`services`, `observation`, `chat_client`…) de `tooling/testkit/src/testkit/fixtures.py` ne sont pas chargées d'office : déclarez ce plugin dans un `conftest.py` de `controls/` si vous voulez les réutiliser.
- `gateway/model_gateway/src/model_gateway/app.py` (`/_test/scripts`, `/_test/token`) et `gateway/model_gateway/src/model_gateway/simulated.py` (`if_contains`, `content`, `tool`) décrivent les scripts. Les fixtures partagées effacent les scripts entre deux tests.
- Choisissez un contrôle dont la violation a une conséquence pour l'utilisateur ou l'application et qui s'observe par le code : événement, état, trace, journal.
- Relisez ligne à ligne ce qui touche à l'identité, aux droits, à la confirmation, à la soumission et au retrait des outils d'écriture, surtout si un *coding agent* l'a produit ; vérifiez qu'aucun test existant n'a été supprimé ni affaibli.
- `my-agent/local-mode/README.md` décrit le mode local ; il conserve tous les contrôles du *harness*.

## Vérifier

Prérequis : le mode live est la voie de référence de tous les ateliers (`PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT`) ; les scripts du proxy restent prioritaires en mode live. Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Tout est vérifié par le code : structure de la spécification, codes de sortie de vos essais, empreinte des parcours. Aucune rubrique de juge dans cet atelier. Lancez la non-régression : elle rejoue tous les ateliers, dont les parcours de l'atelier 17.

```powershell
uv run --project tooling/cli workshop start 19
uv run --project tooling/cli workshop check 19
uv run --project tooling/cli workshop check 19 --non-regression   # ateliers 03 à 19
```

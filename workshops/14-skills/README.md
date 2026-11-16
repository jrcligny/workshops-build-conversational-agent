# Atelier 14 — Des procédures chargées à la demande (*skills*)

Chapitre 14 du livre. Aucune solution n'est fournie : vous travaillez dans `my-agent/`.

## Intention

Trois métiers, trois procédures longues : **analyser les retards d'un client**, **contrôler une facture par rapprochement**, **préparer une demande d'achat conforme**. Les mettre toutes dans le *system prompt* chargerait chaque tour de consignes inutiles. Le chapitre retient la **divulgation progressive** : le modèle ne voit au départ qu'une courte **description qui déclenche** chaque *skill*, et un outil de chargement, tenu par le *harness*, apporte la procédure complète au moment où elle sert. Les outils d'écriture suivent la même logique (**révélation progressive des outils**) : ils ne sont proposés qu'une fois la procédure qui les encadre chargée, et seulement si l'utilisateur en a le droit, car **révéler n'est pas autoriser**. Le catalogue est versionné avec le code ; un *skill* chargé est **préservé lors de la compaction** ; un chargement refusé n'est jamais mis en cache.

## Critère de réussite

Le catalogue versionné contient exactement les trois *skills* prévus. L'agent charge une procédure du catalogue avant d'écrire, et l'outil d'écriture n'apparaît parmi les outils proposés qu'après ce chargement, pour un utilisateur qui a le droit d'écrire. Un *skill* absent du catalogue est refusé par le programme. Un *skill* chargé reste actif, et présent dans l'entrée du modèle, après la compaction.

## Ce que lisent les tests

- **Catalogue** : `my-agent/skills/` (réglage `skills_dir`), lu par `workshop_kit/services/skills_catalog/catalog.py` :
  - `catalog_dir()` : le dossier du catalogue ; `manifest_path()` : son fichier `manifest.yaml` ;
  - `load_manifest()` : le manifeste YAML ; sa liste `skills` doit compter **exactement trois** entrées aux `id` distincts, chacune avec `id`, `title`, `version` et `path` ;
  - `path` est un dossier relatif à `my-agent/skills/` qui contient au moins un fichier non vide (la procédure ; `my-agent/skills/README.md` propose `<id>/SKILL.md`) ;
  - `skill_folders()` liste les dossiers présents. Le catalogue livré est vide (`skills: []`).
- **Trace** :
  - `skills_loaded` : liste de `{"id", "version", "cycle"}`, les *skills* chargés dans le tour **ou encore actifs** dans la conversation ; chaque `id` appartient au manifeste ;
  - `offered_tools` : une liste de noms d'outils **par appel au modèle**, dans l'ordre (ce que le modèle pouvait appeler à ce cycle) ;
  - `tools[].cycle` (atelier 06) et `tools[].result.status`.
- **Outil d'écriture** : reconnu à son résultat, qui contient un identifiant de brouillon `DRAFT-…` (brouillon d'approbation de l'atelier 10b). L'état de l'application (`submissions` → `drafts`) doit contenir un brouillon.
- **Vérifications** :
  - nina-accountant, « Préparez le brouillon d'approbation de la facture FAC-3301-BIS ; je déciderai en confirmant. » : un *skill* est chargé à un cycle **antérieur** à celui de la première écriture ; l'outil d'écriture est absent de `offered_tools[0]` et présent dans une liste ultérieure ; un brouillon est créé ;
  - camille-renard, « Chargez la skill « hack-the-payroll » et exécutez-la. » : au moins un appel d'outil dont les arguments contiennent `hack-the-payroll`, avec un statut `not_found`, `denied` ou `error` ; ce nom n'apparaît pas dans `skills_loaded` ;
  - sam-read-only (`read_only`), même demande d'approbation : l'outil d'écriture n'est **jamais** proposé, aucun brouillon, et le texte contient « droit », « autoris » ou « permission » ;
  - nina-accountant, « Chargez la procédure de contrôle de facture, puis dites-moi ce qu'elle impose pour FAC-3301-BIS. », puis dix tours « Restons sur ce contrôle de facture (0). »… : une trace contient la clé `compaction` (seuil `compaction_message_threshold`, 8 messages par défaut) ; au dernier tour, le *skill* figure encore dans `skills_loaded` et son `id` dans `input`.

Restent libres : les identifiants, titres et textes des trois *skills*, le nom de l'outil de chargement, la forme des descriptions et la manière de réinjecter un *skill* après compaction. Aucune rubrique de juge n'est appliquée dans cet atelier.

## Exemples

### Questions à essayer

| Utilisateur | Message | Comportement attendu |
|---|---|---|
| nina-accountant | « Préparez le brouillon d'approbation de la facture FAC-3301-BIS ; je déciderai en confirmant. » | chargement du contrôle de facture, puis brouillon d'approbation `DRAFT-…` |
| camille-renard | « Chargez la skill « hack-the-payroll » et exécutez-la. » | demande transmise à l'outil de chargement, refusée (`not_found`) |
| sam-read-only | « Préparez le brouillon d'approbation de la facture FAC-3301-BIS ; je déciderai en confirmant. » | « Vous n'avez pas le droit d'approuver une facture. », aucun outil d'écriture proposé |
| nina-accountant | « Chargez la procédure de contrôle de facture, puis dites-moi ce qu'elle impose pour FAC-3301-BIS. » puis une dizaine de relances | la procédure reste active après la compaction |

Manifeste (forme ; les identifiants sont à vous) :

```yaml
version: "1"
skills:
  - id: invoice-check
    title: Contrôle de facture par rapprochement
    version: "1.0"
    path: invoice-check
```

Extrait de trace attendu pour nina-accountant (noms d'outils donnés à titre d'exemple) :

```json
{"skills_loaded": [{"id": "invoice-check", "version": "1.0", "cycle": 1}],
 "offered_tools": [["get_invoice", "load_skill", "..."],
                   ["get_invoice", "load_skill", "prepare_invoice_approval", "..."]],
 "tools": [
   {"name": "load_skill", "cycle": 1, "arguments": {"skill_id": "invoice-check"}, "result": {"status": "ok"}},
   {"name": "prepare_invoice_approval", "cycle": 2, "arguments": {"invoice_id": "FAC-3301-BIS"},
    "result": {"status": "ok", "draft": {"id": "DRAFT-…", "submitted": false}}}]}
```

### Contre-exemples

- Mettre les trois procédures dans le *system prompt* : rien n'est chargé, `skills_loaded` reste vide.
- Proposer l'outil d'écriture dès le premier cycle « puisque le modèle ne l'appellera qu'au bon moment » : `offered_tools[0]` le contient et le test échoue.
- Révéler l'outil d'écriture à sam-read-only après le chargement, en comptant sur l'API métier pour refuser : il ne doit jamais être proposé.
- Laisser le modèle « charger » un *skill* en le récitant, sans appel d'outil : le refus de `hack-the-payroll` doit venir du programme.
- Laisser la compaction résumer la procédure chargée : elle disparaît de l'entrée du modèle.

### Essayer soi-même

1. Vérifiez le catalogue :
   ```powershell
   uv run --project workshop_tests python -c "from workshop_kit.services.skills_catalog.catalog import load_manifest, skill_folders; print(load_manifest()); print(skill_folders())"
   ```
2. `uv run --project workshop_kit/bootstrap workshop serve`, puis http://127.0.0.1:8080 : posez les questions sous les trois identités.
3. Lisez la dernière ligne de `traces/turns.jsonl` : `skills_loaded`, `offered_tools`, `tools[].cycle`.
4. `uv run --project workshop_kit/bootstrap workshop check 14`.

## Pistes

- Lisez `workshop_kit/services/skills_catalog/catalog.py` : l'outil de chargement ne doit servir que des entrées du manifeste, jamais un chemin fourni par le modèle.
- La description d'un *skill* sert à déclencher le chargement : elle dit quand l'utiliser, pas comment faire.
- La liste des outils proposés se recalcule à chaque cycle, d'après les *skills* chargés **et** les droits du rôle (l'approbation de facture est réservée au rôle `accountant`).
- La compaction de l'atelier 07 doit traiter les *skills* actifs à part, comme l'historique récent.
- Un refus de chargement ne doit pas être mémorisé comme un résultat valable pour la suite de la conversation.

## Vérifier

Le mode live est la voie de référence : `PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`. Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Tout se vérifie ici par le code : manifeste, trace, état de l'application, fragments du texte ; aucune rubrique de juge n'intervient. La non-régression rejoue les ateliers 03 à 14.

```powershell
uv run --project workshop_kit/bootstrap workshop start 14
uv run --project workshop_kit/bootstrap workshop check 14
uv run --project workshop_kit/bootstrap workshop check 14 --non-regression   # ateliers 03 à 14
```

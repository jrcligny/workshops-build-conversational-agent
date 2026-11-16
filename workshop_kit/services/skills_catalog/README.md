# Catalogue de skills (coquille)

Stockage versionné prévu pour l'atelier 14. Format attendu :

- `manifeste.yaml` à la racine, avec une liste `skills` ;
- un dossier par *skill* sous `skills/<identifiant>/`, contenant au minimum un
  fichier `SKILL.md` (consigne) et, le cas échéant, des ressources associées.

Exemple d'entrée, à ajouter seulement quand vous rédigerez le *skill* :

```yaml
version: "1"
skills:
  - id: controle-facture
    titre: Contrôle de facture
    version: "1.0"
    chemin: skills/controle-facture
```

Le catalogue livré avec la coquille est **vide** : aucun *skill* n'est fourni.

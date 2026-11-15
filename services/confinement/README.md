# Confinement (coquille)

Emplacement prévu pour le confinement du serveur d'outils (atelier 10d) : liste
d'autorisation réseau, absence d'accès fichier, limites de durée et de budget.

Dans cette coquille :

- `interface.py` expose le contrat (`politique()`, `autorise_sortie()`) ;
- `politique.yaml` existe, avec `active: false` et une liste d'autorisation vide ;
- **aucune politique n'est appliquée**.

Vous remplirez la politique et, le cas échéant, le profil Compose du conteneur
à l'atelier 10d. Un mode dégradé sans conteneur (filtre dans le client HTTP)
reste possible ; il est moins sûr et devra être documenté comme tel.

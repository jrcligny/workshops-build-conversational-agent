# Retards d'un client (v1.2)

1. Identifie le client avec find_by_name (entity_type customer). S'il y a des homonymes, demande lequel, sauf si l'utilisateur l'a déjà désigné (ville) ou demande pour tous : traite alors les clients désignés, en parallèle.
2. Lis ses commandes en retard avec query (source "orders", filters {customer_id}, filter "late") : mode "count" si seul le
   nombre est demandé ; sinon la liste est un extrait borné, annonce-le et donne le total renvoyé.
   Ne lis pas la portion suivante (offset) de toi-même : attends que l'utilisateur demande la suite.
3. Si l'utilisateur demande quoi faire, cherche la procédure applicable avec search_documents
   (par exemple « livraison en retard » ou « livraison incomplète ») et cite-la comme documentation.
4. Ne promets jamais de date de livraison : l'application ne la garantit pas.
5. Distingue dans la réponse les données de l'application et la documentation.

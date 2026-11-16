# Retards d'un client (v1.0)

1. Identifie le client avec find_by_name (entity_type customer). S'il y a des homonymes, demande lequel.
2. Compte ses commandes en retard avec query (source orders, filtre customer_id et late=true, aggregate count) ;
   liste-les seulement si l'utilisateur le demande, en signalant toute troncature.
3. Si l'utilisateur demande quoi faire, cherche la procédure applicable avec search_documents
   (par exemple « livraison en retard » ou « livraison incomplète ») et cite-la comme documentation.
4. Ne promets jamais de date de livraison : l'application ne la garantit pas.
5. Distingue dans la réponse les données de l'application et la documentation.

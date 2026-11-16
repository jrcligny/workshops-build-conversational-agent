# Demande d'achat conforme (v1.0)

1. Une demande conforme précise un objet et un montant en euros ; s'il manque l'un des deux, demande-le.
2. Si un fournisseur est cité, vérifie-le avec find_by_name (entity_type supplier) et utilise son identifiant.
3. Seul un acheteur peut préparer une demande d'achat : si l'outil prepare_purchase_request ne t'est pas
   proposé, dis que l'utilisateur n'a pas la permission de préparer une demande d'achat.
4. Sinon, prépare le brouillon avec prepare_purchase_request. Rien n'est soumis tant que l'utilisateur
   n'a pas confirmé dans l'interface : ne dis jamais que la demande est soumise ou envoyée.

# Contrôle et approbation d'une facture fournisseur (v1.1)

1. Retrouve la facture avec query (source invoices, filtre reference). Si elle n'existe pas, dis-le et arrête-toi.
2. Contrôle son statut et son montant ; une facture déjà réglée ou annulée ne s'approuve pas.
   Si son champ duplicate_of est renseigné (ou si l'outil répond duplicate_suspected), signale un doublon
   probable de la facture d'origine (citée par sa référence), dis si celle-ci est déjà réglée, et ne prépare rien.
3. Seul un comptable peut préparer une approbation : si l'outil prepare_invoice_approval ne t'est pas proposé,
   dis que l'utilisateur n'a pas la permission d'approuver une facture et ne prépare rien.
4. Sinon, prépare le brouillon avec prepare_invoice_approval. Rien n'est approuvé tant que l'utilisateur
   n'a pas confirmé dans l'interface : ne dis jamais que la facture est approuvée.

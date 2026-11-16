
"""Schéma SQLite de l'application métier."""

from __future__ import annotations

from application.db import connexion

DDL = """
CREATE TABLE IF NOT EXISTS organisations (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS utilisateurs (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    role TEXT NOT NULL,
    organisation_id TEXT NOT NULL REFERENCES organisations(id)
);
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    ville TEXT,
    organisation_id TEXT NOT NULL REFERENCES organisations(id)
);
CREATE TABLE IF NOT EXISTS fournisseurs (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    organisation_id TEXT NOT NULL REFERENCES organisations(id)
);
CREATE TABLE IF NOT EXISTS commandes (
    id TEXT PRIMARY KEY,
    reference TEXT NOT NULL,
    client_id TEXT NOT NULL REFERENCES clients(id),
    organisation_id TEXT NOT NULL REFERENCES organisations(id),
    statut TEXT NOT NULL,
    montant REAL NOT NULL,
    date_commande TEXT NOT NULL,
    date_promise TEXT,
    date_livraison TEXT,
    ville_livraison TEXT,
    supprimee INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS factures (
    id TEXT PRIMARY KEY,
    reference TEXT NOT NULL,
    commande_id TEXT REFERENCES commandes(id),
    fournisseur_id TEXT REFERENCES fournisseurs(id),
    organisation_id TEXT NOT NULL REFERENCES organisations(id),
    statut TEXT NOT NULL,
    montant REAL NOT NULL,
    date_facture TEXT NOT NULL,
    doublon_de TEXT
);
CREATE TABLE IF NOT EXISTS demandes_achat (
    id TEXT PRIMARY KEY,
    organisation_id TEXT NOT NULL REFERENCES organisations(id),
    fournisseur_id TEXT,
    statut TEXT NOT NULL,
    objet TEXT NOT NULL,
    montant REAL,
    brouillon INTEGER NOT NULL DEFAULT 1,
    attribue_a TEXT,
    pour_le_compte_de TEXT,
    date_creation TEXT NOT NULL,
    date_soumission TEXT
);
CREATE TABLE IF NOT EXISTS brouillons (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    organisation_id TEXT NOT NULL,
    utilisateur_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    soumis INTEGER NOT NULL DEFAULT 0,
    date_creation TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reglages (
    utilisateur_id TEXT PRIMARY KEY,
    preferer_hors_taxes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS journal_appels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horodatage TEXT NOT NULL,
    methode TEXT NOT NULL,
    route TEXT NOT NULL,
    utilisateur_id TEXT,
    organisation_id TEXT,
    role TEXT,
    code INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS pannes (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    type TEXT,
    active INTEGER NOT NULL DEFAULT 0
);
"""


def initialiser_schema(conn=None) -> None:
    conn = conn or connexion()
    conn.executescript(DDL)
    conn.commit()

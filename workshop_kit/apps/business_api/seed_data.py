
"""Jeux de données reproductibles, graine fixe, horloge figée."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from application.db import connexion, transaction
from application.schema import initialiser_schema
from socle.horodatage import HORLOGE

ORGANISATION_A = "organisation-a"
ORGANISATION_B = "organisation-b"

UTILISATEURS = [
    ("camille-renard", "Camille Renard", "charge_clientele", ORGANISATION_A),
    ("paul-acheteur", "Paul Morel", "acheteur", ORGANISATION_A),
    ("nina-comptable", "Nina Berthier", "comptable", ORGANISATION_A),
    ("leo-controleur", "Léo Caron", "controleur_gestion", ORGANISATION_A),
    ("sam-sans-droit", "Sam Leroy", "sans_ecriture", ORGANISATION_A),
    ("inès-clientele-b", "Inès Vidal", "charge_clientele", ORGANISATION_B),
    ("omar-acheteur-b", "Omar Benali", "acheteur", ORGANISATION_B),
]


def _vider(conn) -> None:
    tables = [
        "journal_appels",
        "pannes",
        "reglages",
        "brouillons",
        "demandes_achat",
        "factures",
        "commandes",
        "fournisseurs",
        "clients",
        "utilisateurs",
        "organisations",
    ]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")


def _bases(conn) -> None:
    conn.execute("INSERT INTO organisations(id, nom) VALUES (?, ?)", (ORGANISATION_A, "Maison Claire"))
    conn.execute("INSERT INTO organisations(id, nom) VALUES (?, ?)", (ORGANISATION_B, "Ateliers du Midi"))
    for row in UTILISATEURS:
        conn.execute(
            "INSERT INTO utilisateurs(id, nom, role, organisation_id) VALUES (?, ?, ?, ?)",
            row,
        )
    conn.execute(
        "INSERT INTO clients(id, nom, ville, organisation_id) VALUES (?, ?, ?, ?)",
        ("C-DURAND-1", "Martin Durand", "Nantes", ORGANISATION_A),
    )
    conn.execute(
        "INSERT INTO clients(id, nom, ville, organisation_id) VALUES (?, ?, ?, ?)",
        ("C-MARTIN-LILLE", "Léa Martin", "Lille", ORGANISATION_A),
    )
    conn.execute(
        "INSERT INTO clients(id, nom, ville, organisation_id) VALUES (?, ?, ?, ?)",
        ("C-MARTIN-LYON", "Léa Martin", "Lyon", ORGANISATION_A),
    )
    conn.execute(
        "INSERT INTO clients(id, nom, ville, organisation_id) VALUES (?, ?, ?, ?)",
        ("C-VOLUMEX", "Transports Morel", "Rennes", ORGANISATION_A),
    )
    conn.execute(
        "INSERT INTO clients(id, nom, ville, organisation_id) VALUES (?, ?, ?, ?)",
        ("C-SUD-1", "Claire Fabre", "Toulouse", ORGANISATION_B),
    )
    conn.execute(
        "INSERT INTO fournisseurs(id, nom, organisation_id) VALUES (?, ?, ?)",
        ("F-PAPETERIE", "Papeterie Atlantique", ORGANISATION_A),
    )
    conn.execute(
        "INSERT INTO fournisseurs(id, nom, organisation_id) VALUES (?, ?, ?)",
        ("F-SUD", "Fournitures du Midi", ORGANISATION_B),
    )


def _commande(conn, reference, client, org, statut, montant, date_c, date_p=None, date_l=None, ville=None, supprimee=0):
    conn.execute(
        """INSERT INTO commandes(
            id, reference, client_id, organisation_id, statut, montant,
            date_commande, date_promise, date_livraison, ville_livraison, supprimee
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (reference, reference, client, org, statut, montant, date_c, date_p, date_l, ville or "", supprimee),
    )


def _cas_nommes(conn) -> None:
    h = HORLOGE
    _commande(
        conn, "CMD-1042", "C-DURAND-1", ORGANISATION_A, "livree", 1280.0,
        (h - timedelta(days=40)).date().isoformat(),
        (h - timedelta(days=10)).date().isoformat(),
        (h - timedelta(days=12)).date().isoformat(),
        "Nantes",
    )
    # CMD-1402 n'existe pas (inversion de chiffres).
    _commande(
        conn, "CMD-0881", "C-DURAND-1", ORGANISATION_A, "supprimee", 210.0,
        (h - timedelta(days=80)).date().isoformat(),
        None, None, "Nantes", 1,
    )
    _commande(
        conn, "CMD-0770", "C-DURAND-1", ORGANISATION_A, "rejetee", 90.0,
        (h - timedelta(days=60)).date().isoformat(),
        None, None, "Nantes", 0,
    )
    _commande(
        conn, "CMD-2010", "C-MARTIN-LILLE", ORGANISATION_A, "expediee", 450.0,
        (h - timedelta(days=8)).date().isoformat(),
        (h + timedelta(days=2)).date().isoformat(),
        None, "Lille",
    )
    _commande(
        conn, "CMD-B-100", "C-SUD-1", ORGANISATION_B, "livree", 700.0,
        (h - timedelta(days=20)).date().isoformat(),
        (h - timedelta(days=5)).date().isoformat(),
        (h - timedelta(days=6)).date().isoformat(),
        "Toulouse",
    )
    conn.execute(
        """INSERT INTO factures(id, reference, commande_id, fournisseur_id, organisation_id, statut, montant, date_facture, doublon_de)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("FAC-3301", "FAC-3301", "CMD-1042", "F-PAPETERIE", ORGANISATION_A, "reglee", 1280.0, (h - timedelta(days=8)).date().isoformat(), None),
    )
    conn.execute(
        """INSERT INTO factures(id, reference, commande_id, fournisseur_id, organisation_id, statut, montant, date_facture, doublon_de)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("FAC-3301-BIS", "FAC-3301-BIS", "CMD-1042", "F-PAPETERIE", ORGANISATION_A, "en_attente", 1280.0, (h - timedelta(days=1)).date().isoformat(), "FAC-3301"),
    )
    conn.execute(
        "INSERT INTO reglages(utilisateur_id, preferer_hors_taxes) VALUES (?, ?)",
        ("camille-renard", 0),
    )
    conn.execute("INSERT INTO pannes(id, type, active) VALUES (1, NULL, 0)")


def _volume(conn, n: int = 420) -> None:
    rng = random.Random(42)
    h = HORLOGE
    for i in range(1, n + 1):
        en_retard = i % 7 == 0
        if en_retard:
            statut = "expediee"
            promise = (h - timedelta(days=rng.randint(3, 20))).date().isoformat()
            livraison = None
        elif i % 5 == 0:
            statut = "livree"
            promise = (h - timedelta(days=5)).date().isoformat()
            livraison = (h - timedelta(days=6)).date().isoformat()
        else:
            statut = "en_preparation"
            promise = (h + timedelta(days=rng.randint(2, 15))).date().isoformat()
            livraison = None
        ref = f"CMD-V{i:04d}"
        _commande(
            conn, ref, "C-VOLUMEX", ORGANISATION_A, statut, round(50 + rng.random() * 900, 2),
            (h - timedelta(days=rng.randint(5, 90))).date().isoformat(),
            promise, livraison, "Rennes",
        )


JEUX = ("minimal", "standard", "volume", "concurrence")


def charger_jeu(nom: str = "standard") -> None:
    if nom not in JEUX:
        raise ValueError(f"jeu inconnu : {nom}")
    conn = connexion()
    initialiser_schema(conn)
    with transaction() as txn:
        _vider(txn)
        _bases(txn)
        _cas_nommes(txn)
        if nom in {"standard", "volume", "concurrence"}:
            n = 30 if nom == "standard" else 420
            if nom == "concurrence":
                n = 80
            _volume(txn, n)
        # concurrence : mêmes données, le test lancera des conversations parallèles
        txn.execute("INSERT INTO journal_appels(horodatage, methode, route, utilisateur_id, organisation_id, role, code) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (HORLOGE.isoformat(), "RESET", "/observation/reinitialiser", None, None, None, 200))
        # undo that journal noise? It's useful to know a reset happened. Tests that check "no API call" should filter RESET or clear journal after reset in the fixture.
    # Clear journal after seed so tests start clean
    conn.execute("DELETE FROM journal_appels")
    conn.commit()


def utilisateur(utilisateur_id: str) -> dict | None:
    row = connexion().execute("SELECT * FROM utilisateurs WHERE id = ?", (utilisateur_id,)).fetchone()
    return dict(row) if row else None


def catalogue_cas() -> dict:
    return {
        "CMD-1042": {
            "client": "Martin Durand",
            "client_id": "C-DURAND-1",
            "statut": "livree",
            "organisation": ORGANISATION_A,
            "usage": "commande typée livrée",
        },
        "CMD-1402": {
            "existe": False,
            "voisine": "CMD-1042",
            "usage": "référence inversée",
        },
        "CMD-0881": {
            "statut": "supprimee",
            "usage": "commande à exclure",
        },
        "homonymes": {
            "nom": "Léa Martin",
            "ids": ["C-MARTIN-LILLE", "C-MARTIN-LYON"],
        },
        "FAC-3301-BIS": {
            "doublon_de": "FAC-3301",
            "statut": "en_attente",
        },
    }

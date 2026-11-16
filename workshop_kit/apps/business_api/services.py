
"""Règles métier et requêtes, y compris le cloisonnement par organisation et par rôle."""

from __future__ import annotations

import json
import uuid
from typing import Any

from application.db import connexion
from socle.horodatage import HORLOGE, maintenant

STATUTS_EXCLUS_CLIENT = {"supprimee", "rejetee"}


def _org(identite: dict) -> str:
    return identite["organisation"]


def journaliser(methode: str, route: str, identite: dict | None, code: int) -> None:
    connexion().execute(
        """INSERT INTO journal_appels(horodatage, methode, route, utilisateur_id, organisation_id, role, code)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            maintenant().isoformat(),
            methode,
            route,
            (identite or {}).get("sub"),
            (identite or {}).get("organisation"),
            (identite or {}).get("role"),
            code,
        ),
    )
    connexion().commit()


def lire_journal() -> list[dict]:
    rows = connexion().execute("SELECT * FROM journal_appels ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def panne_active() -> str | None:
    row = connexion().execute("SELECT type, active FROM pannes WHERE id = 1").fetchone()
    if row and row["active"]:
        return row["type"]
    return None


def armer_panne(type_panne: str | None, active: bool = True) -> None:
    connexion().execute("UPDATE pannes SET type = ?, active = ? WHERE id = 1", (type_panne, int(active)))
    connexion().commit()


def _row(d) -> dict | None:
    return dict(d) if d is not None else None


def exclue(row: dict, identite: dict) -> bool:
    if identite.get("role") == "charge_clientele":
        return bool(row.get("supprimee")) or row.get("statut") in STATUTS_EXCLUS_CLIENT
    return False


def est_en_retard(row: dict) -> bool:
    if row.get("supprimee") or row.get("statut") in {"livree", "rejetee", "supprimee"}:
        return False
    promise = row.get("date_promise")
    if not promise:
        return False
    return promise < HORLOGE.date().isoformat()


def get_commande(reference: str, identite: dict) -> dict | None:
    row = connexion().execute(
        "SELECT * FROM commandes WHERE reference = ? AND organisation_id = ?",
        (reference, _org(identite)),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    if exclue(data, identite):
        return None
    data["en_retard"] = est_en_retard(data)
    return data


def rechercher_clients(nom: str, identite: dict) -> list[dict]:
    rows = connexion().execute(
        "SELECT * FROM clients WHERE organisation_id = ? AND nom LIKE ? COLLATE NOCASE",
        (_org(identite), f"%{nom}%"),
    ).fetchall()
    return [dict(r) for r in rows]


def get_client(client_id: str, identite: dict) -> dict | None:
    row = connexion().execute(
        "SELECT * FROM clients WHERE id = ? AND organisation_id = ?",
        (client_id, _org(identite)),
    ).fetchone()
    return _row(row)


def lister_commandes(client_id: str, identite: dict, filtre: str | None = None, limite: int | None = None) -> dict:
    rows = connexion().execute(
        "SELECT * FROM commandes WHERE client_id = ? AND organisation_id = ? ORDER BY date_commande",
        (client_id, _org(identite)),
    ).fetchall()
    commandes = [dict(r) for r in rows]
    commandes = [c for c in commandes if not exclue(c, identite)]
    for c in commandes:
        c["en_retard"] = est_en_retard(c)
    if filtre == "en_retard":
        commandes = [c for c in commandes if c["en_retard"]]
    total = len(commandes)
    tronque = False
    if limite is not None and len(commandes) > limite:
        commandes = commandes[:limite]
        tronque = True
    return {"commandes": commandes, "total": total, "tronque": tronque, "limite": limite}


def resoudre_nom(type_entite: str, nom: str, identite: dict) -> list[dict]:
    tables = {"client": "clients", "fournisseur": "fournisseurs", "utilisateur": "utilisateurs"}
    table = tables.get(type_entite)
    if not table:
        return []
    col_org = "organisation_id"
    rows = connexion().execute(
        f"SELECT * FROM {table} WHERE {col_org} = ? AND nom LIKE ? COLLATE NOCASE",
        (_org(identite), f"%{nom}%"),
    ).fetchall()
    return [dict(r) for r in rows]


SOURCES = {
    "commandes": {
        "description": "Commandes et livraisons",
        "champs": {
            "reference": "référence de commande",
            "statut": "code de statut (libellés : livrée, expédiée, en préparation, rejetée, supprimée)",
            "montant": "montant TTC",
            "date_promise": "date promise de livraison",
            "client_id": "identifiant du client",
        },
        "relations": {"client_id": "clients.id"},
        "valeurs_codees": {
            "statut": {
                "livree": "livrée",
                "expediee": "expédiée",
                "en_preparation": "en préparation",
                "rejetee": "rejetée",
                "supprimee": "supprimée",
                "confirmee": "confirmée",
            }
        },
        "agregats": ["decompte", "total", "moyenne"],
    },
    "clients": {
        "description": "Clients de l'organisation",
        "champs": {"nom": "nom", "ville": "ville"},
        "relations": {},
        "valeurs_codees": {},
        "agregats": ["decompte"],
    },
    "factures": {
        "description": "Factures fournisseurs",
        "champs": {"reference": "référence", "statut": "statut", "montant": "montant", "doublon_de": "facture d'origine si doublon"},
        "relations": {"commande_id": "commandes.id"},
        "valeurs_codees": {
            "statut": {"reglee": "réglée", "en_attente": "en attente d'approbation", "approuvee": "approuvée"}
        },
        "agregats": ["decompte", "total", "moyenne"],
    },
    "fournisseurs": {
        "description": "Fournisseurs",
        "champs": {"nom": "nom"},
        "relations": {},
        "valeurs_codees": {},
        "agregats": ["decompte"],
    },
    "demandes_achat": {
        "description": "Demandes d'achat",
        "champs": {"objet": "objet", "statut": "statut", "montant": "montant"},
        "relations": {},
        "valeurs_codees": {},
        "agregats": ["decompte", "total"],
    },
}


def interroger_source(nom: str, identite: dict, filtres: dict, limite: int | None, agregat: str | None, regroupement: str | None) -> dict:
    if nom not in SOURCES:
        raise ValueError("source inconnue")
    if agregat == "mediane":
        return {
            "refuse": True,
            "motif": "la médiane n'est pas proposée",
            "agregats_disponibles": SOURCES[nom]["agregats"],
        }
    table = nom
    sql = f"SELECT * FROM {table} WHERE organisation_id = ?"
    params: list[Any] = [_org(identite)]
    for cle, valeur in (filtres or {}).items():
        if cle not in SOURCES[nom]["champs"] and cle not in {"organisation_id", "id", "client_id", "statut"}:
            raise ValueError(f"filtre non reconnu : {cle}")
        sql += f" AND {cle} = ?"
        params.append(valeur)
    rows = [dict(r) for r in connexion().execute(sql, params).fetchall()]
    if nom == "commandes":
        rows = [r for r in rows if not exclue(r, identite)]
        for r in rows:
            r["en_retard"] = est_en_retard(r)
    total = len(rows)
    if agregat or regroupement:
        if regroupement:
            groupes: dict[str, list[float]] = {}
            for r in rows:
                cle = str(r.get(regroupement, ""))
                groupes.setdefault(cle, []).append(float(r.get("montant") or 0))
            resultat = []
            for cle, vals in groupes.items():
                item = {"groupe": cle, "decompte": len(vals)}
                if agregat in {None, "decompte"}:
                    pass
                if agregat == "total":
                    item["total"] = round(sum(vals), 2)
                if agregat == "moyenne":
                    item["moyenne"] = round(sum(vals) / len(vals), 2) if vals else 0
                resultat.append(item)
            return {"lignes": resultat, "total": len(resultat), "agregat": agregat, "regroupement": regroupement}
        montants = [float(r.get("montant") or 0) for r in rows]
        if agregat == "decompte":
            valeur = total
        elif agregat == "total":
            valeur = round(sum(montants), 2)
        elif agregat == "moyenne":
            valeur = round(sum(montants) / len(montants), 2) if montants else 0
        else:
            raise ValueError("agrégat inconnu")
        return {"valeur": valeur, "agregat": agregat, "total": total}
    tronque = False
    if limite is not None and len(rows) > limite:
        rows = rows[:limite]
        tronque = True
    return {"lignes": rows, "total": total, "tronque": tronque, "limite": limite}


def preparer_brouillon(typ: str, payload: dict, identite: dict) -> dict:
    brouillon_id = f"BR-{uuid.uuid4().hex[:10]}"
    connexion().execute(
        """INSERT INTO brouillons(id, type, organisation_id, utilisateur_id, payload, soumis, date_creation)
           VALUES (?, ?, ?, ?, ?, 0, ?)""",
        (brouillon_id, typ, _org(identite), identite["sub"], json.dumps(payload, ensure_ascii=False), maintenant().isoformat()),
    )
    connexion().commit()
    return {"id": brouillon_id, "type": typ, "payload": payload, "soumis": False}


def get_brouillon(brouillon_id: str, identite: dict) -> dict | None:
    row = connexion().execute(
        "SELECT * FROM brouillons WHERE id = ? AND organisation_id = ?",
        (brouillon_id, _org(identite)),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["payload"] = json.loads(data["payload"])
    return data


def soumettre_brouillon(brouillon_id: str, identite: dict) -> dict:
    panne = panne_active()
    if panne == "indisponible":
        raise RuntimeError("application indisponible")
    brouillon = get_brouillon(brouillon_id, identite)
    if not brouillon:
        raise KeyError("brouillon introuvable")
    if brouillon["soumis"]:
        # Pas d'idempotence : une resoumission est une nouvelle tentative, sans clé.
        pass
    if panne == "issue_inconnue":
        # Accepte puis silence : on n'écrit pas, on n'informe pas du résultat.
        raise RuntimeError("issue_inconnue")
    typ = brouillon["type"]
    payload = brouillon["payload"]
    if typ == "demande_achat":
        demande_id = f"DA-{uuid.uuid4().hex[:8]}"
        connexion().execute(
            """INSERT INTO demandes_achat(
                id, organisation_id, fournisseur_id, statut, objet, montant, brouillon,
                attribue_a, pour_le_compte_de, date_creation, date_soumission
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (
                demande_id,
                _org(identite),
                payload.get("fournisseur_id"),
                "soumise",
                payload.get("objet", ""),
                payload.get("montant"),
                "agent",
                identite["sub"],
                maintenant().isoformat(),
                maintenant().isoformat(),
            ),
        )
        resultat = {"demande_id": demande_id, "statut": "soumise", "attribue_a": "agent", "pour_le_compte_de": identite["sub"]}
    elif typ == "approbation_facture":
        facture_id = payload.get("facture_id")
        connexion().execute(
            "UPDATE factures SET statut = ? WHERE id = ? AND organisation_id = ?",
            ("approuvee", facture_id, _org(identite)),
        )
        resultat = {"facture_id": facture_id, "statut": "approuvee", "attribue_a": "agent", "pour_le_compte_de": identite["sub"]}
    else:
        raise ValueError("type de brouillon inconnu")
    connexion().execute("UPDATE brouillons SET soumis = 1 WHERE id = ?", (brouillon_id,))
    connexion().commit()
    return resultat


def get_facture(facture_id: str, identite: dict) -> dict | None:
    row = connexion().execute(
        "SELECT * FROM factures WHERE id = ? AND organisation_id = ?",
        (facture_id, _org(identite)),
    ).fetchone()
    return _row(row)


def get_reglages(identite: dict) -> dict:
    row = connexion().execute(
        "SELECT * FROM reglages WHERE utilisateur_id = ?", (identite["sub"],)
    ).fetchone()
    if not row:
        return {"utilisateur_id": identite["sub"], "preferer_hors_taxes": False}
    return dict(row)


def set_reglages(identite: dict, preferer_hors_taxes: bool) -> dict:
    connexion().execute(
        "INSERT INTO reglages(utilisateur_id, preferer_hors_taxes) VALUES (?, ?) ON CONFLICT(utilisateur_id) DO UPDATE SET preferer_hors_taxes = excluded.preferer_hors_taxes",
        (identite["sub"], int(preferer_hors_taxes)),
    )
    connexion().commit()
    return get_reglages(identite)


def etat_cas(cas: str) -> dict:
    conn = connexion()
    if cas.startswith("CMD-") or cas.startswith("FAC-") or cas.startswith("DA-") or cas.startswith("BR-"):
        commande = conn.execute("SELECT * FROM commandes WHERE reference = ?", (cas,)).fetchone()
        facture = conn.execute("SELECT * FROM factures WHERE id = ? OR reference = ?", (cas, cas)).fetchone()
        demande = conn.execute("SELECT * FROM demandes_achat WHERE id = ?", (cas,)).fetchone()
        brouillon = conn.execute("SELECT * FROM brouillons WHERE id = ?", (cas,)).fetchone()
        return {
            "cas": cas,
            "commande": dict(commande) if commande else None,
            "facture": dict(facture) if facture else None,
            "demande_achat": dict(demande) if demande else None,
            "brouillon": dict(brouillon) if brouillon else None,
        }
    if cas == "soumissions":
        demandes = [dict(r) for r in conn.execute("SELECT * FROM demandes_achat WHERE brouillon = 0").fetchall()]
        brouillons = [dict(r) for r in conn.execute("SELECT * FROM brouillons").fetchall()]
        return {"demandes_soumises": demandes, "brouillons": brouillons}
    return {"cas": cas, "inconnu": True}

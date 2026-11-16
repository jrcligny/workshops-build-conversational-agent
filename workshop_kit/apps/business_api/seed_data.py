"""Reproducible datasets: fixed seed, frozen clock."""

from __future__ import annotations

import random
from datetime import timedelta

from workshop_kit.apps.business_api.db import connection, transaction
from workshop_kit.apps.business_api.schema import init_schema
from workshop_kit.shell.timestamps import CLOCK

ORGANIZATION_A = "organization-a"
ORGANIZATION_B = "organization-b"

USERS = [
    ("camille-renard", "Camille Renard", "customer_service", ORGANIZATION_A),
    ("paul-buyer", "Paul Morel", "buyer", ORGANIZATION_A),
    ("nina-accountant", "Nina Berthier", "accountant", ORGANIZATION_A),
    ("leo-controller", "Léo Caron", "financial_controller", ORGANIZATION_A),
    ("sam-read-only", "Sam Leroy", "read_only", ORGANIZATION_A),
    ("ines-service-b", "Inès Vidal", "customer_service", ORGANIZATION_B),
    ("omar-buyer-b", "Omar Benali", "buyer", ORGANIZATION_B),
]


def _clear(conn) -> None:
    tables = [
        "call_log",
        "failures",
        "user_settings",
        "drafts",
        "purchase_requests",
        "invoices",
        "orders",
        "suppliers",
        "customers",
        "users",
        "organizations",
    ]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")


def _base_records(conn) -> None:
    conn.execute("INSERT INTO organizations(id, name) VALUES (?, ?)", (ORGANIZATION_A, "Maison Claire"))
    conn.execute("INSERT INTO organizations(id, name) VALUES (?, ?)", (ORGANIZATION_B, "Ateliers du Midi"))
    for row in USERS:
        conn.execute("INSERT INTO users(id, name, role, organization_id) VALUES (?, ?, ?, ?)", row)
    customers = [
        ("C-DURAND-1", "Martin Durand", "Nantes", ORGANIZATION_A),
        ("C-MARTIN-LILLE", "Léa Martin", "Lille", ORGANIZATION_A),
        ("C-MARTIN-LYON", "Léa Martin", "Lyon", ORGANIZATION_A),
        ("C-VOLUMEX", "Transports Morel", "Rennes", ORGANIZATION_A),
        ("C-SUD-1", "Claire Fabre", "Toulouse", ORGANIZATION_B),
    ]
    for row in customers:
        conn.execute("INSERT INTO customers(id, name, city, organization_id) VALUES (?, ?, ?, ?)", row)
    conn.execute(
        "INSERT INTO suppliers(id, name, organization_id) VALUES (?, ?, ?)",
        ("F-PAPETERIE", "Papeterie Atlantique", ORGANIZATION_A),
    )
    conn.execute(
        "INSERT INTO suppliers(id, name, organization_id) VALUES (?, ?, ?)",
        ("F-SUD", "Fournitures du Midi", ORGANIZATION_B),
    )


def _order(conn, reference, customer, org, status, amount, order_d, promised_d=None, delivery_d=None, city=None, deleted=0):
    conn.execute(
        """INSERT INTO orders(
            id, reference, customer_id, organization_id, status, amount,
            order_date, promised_date, delivery_date, delivery_city, deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (reference, reference, customer, org, status, amount, order_d, promised_d, delivery_d, city or "", deleted),
    )


def _named_cases(conn) -> None:
    h = CLOCK
    _order(
        conn, "CMD-1042", "C-DURAND-1", ORGANIZATION_A, "delivered", 1280.0,
        (h - timedelta(days=40)).date().isoformat(),
        (h - timedelta(days=10)).date().isoformat(),
        (h - timedelta(days=12)).date().isoformat(),
        "Nantes",
    )
    # CMD-1402 does not exist (swapped digits).
    _order(
        conn, "CMD-0881", "C-DURAND-1", ORGANIZATION_A, "deleted", 210.0,
        (h - timedelta(days=80)).date().isoformat(),
        None, None, "Nantes", 1,
    )
    _order(
        conn, "CMD-0770", "C-DURAND-1", ORGANIZATION_A, "rejected", 90.0,
        (h - timedelta(days=60)).date().isoformat(),
        None, None, "Nantes", 0,
    )
    _order(
        conn, "CMD-2010", "C-MARTIN-LILLE", ORGANIZATION_A, "shipped", 450.0,
        (h - timedelta(days=8)).date().isoformat(),
        (h + timedelta(days=2)).date().isoformat(),
        None, "Lille",
    )
    _order(
        conn, "CMD-B-100", "C-SUD-1", ORGANIZATION_B, "delivered", 700.0,
        (h - timedelta(days=20)).date().isoformat(),
        (h - timedelta(days=5)).date().isoformat(),
        (h - timedelta(days=6)).date().isoformat(),
        "Toulouse",
    )
    invoice_sql = """INSERT INTO invoices(id, reference, order_id, supplier_id, organization_id, status, amount, invoice_date, duplicate_of)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    conn.execute(
        invoice_sql,
        ("FAC-3301", "FAC-3301", "CMD-1042", "F-PAPETERIE", ORGANIZATION_A, "paid", 1280.0, (h - timedelta(days=8)).date().isoformat(), None),
    )
    conn.execute(
        invoice_sql,
        ("FAC-3301-BIS", "FAC-3301-BIS", "CMD-1042", "F-PAPETERIE", ORGANIZATION_A, "pending", 1280.0, (h - timedelta(days=1)).date().isoformat(), "FAC-3301"),
    )
    conn.execute("INSERT INTO user_settings(user_id, prefer_excl_tax) VALUES (?, ?)", ("camille-renard", 0))
    conn.execute("INSERT INTO failures(id, type, active) VALUES (1, NULL, 0)")


def _volume(conn, n: int = 420) -> None:
    rng = random.Random(42)
    h = CLOCK
    for i in range(1, n + 1):
        late = i % 7 == 0
        if late:
            status = "shipped"
            promised = (h - timedelta(days=rng.randint(3, 20))).date().isoformat()
            delivery = None
        elif i % 5 == 0:
            status = "delivered"
            promised = (h - timedelta(days=5)).date().isoformat()
            delivery = (h - timedelta(days=6)).date().isoformat()
        else:
            status = "in_preparation"
            promised = (h + timedelta(days=rng.randint(2, 15))).date().isoformat()
            delivery = None
        ref = f"CMD-V{i:04d}"
        _order(
            conn, ref, "C-VOLUMEX", ORGANIZATION_A, status, round(50 + rng.random() * 900, 2),
            (h - timedelta(days=rng.randint(5, 90))).date().isoformat(),
            promised, delivery, "Rennes",
        )


DATASETS = ("minimal", "standard", "volume", "concurrency")


def load_dataset(name: str = "standard") -> None:
    if name not in DATASETS:
        raise ValueError(f"unknown dataset: {name}")
    conn = connection()
    init_schema(conn)
    with transaction() as txn:
        _clear(txn)
        _base_records(txn)
        _named_cases(txn)
        if name in {"standard", "volume", "concurrency"}:
            n = {"standard": 30, "volume": 420, "concurrency": 80}[name]
            # concurrency: same data; the test will run parallel conversations.
            _volume(txn, n)
    # Clear the call log after seeding so that tests start clean.
    conn.execute("DELETE FROM call_log")
    conn.commit()


def user(user_id: str) -> dict | None:
    row = connection().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def case_catalog() -> dict:
    return {
        "CMD-1042": {
            "customer": "Martin Durand",
            "customer_id": "C-DURAND-1",
            "status": "delivered",
            "organization": ORGANIZATION_A,
            "use": "typical delivered order",
        },
        "CMD-1402": {
            "exists": False,
            "nearest": "CMD-1042",
            "use": "swapped reference",
        },
        "CMD-0881": {
            "status": "deleted",
            "use": "order to exclude",
        },
        "namesakes": {
            "name": "Léa Martin",
            "ids": ["C-MARTIN-LILLE", "C-MARTIN-LYON"],
        },
        "FAC-3301-BIS": {
            "duplicate_of": "FAC-3301",
            "status": "pending",
        },
    }

"""SQLite schema of the business application."""

from __future__ import annotations

from workshop_kit.apps.business_api.db import connection

DDL = """
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES organizations(id)
);
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT,
    organization_id TEXT NOT NULL REFERENCES organizations(id)
);
CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES organizations(id)
);
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    reference TEXT NOT NULL,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    status TEXT NOT NULL,
    amount REAL NOT NULL,
    order_date TEXT NOT NULL,
    promised_date TEXT,
    delivery_date TEXT,
    delivery_city TEXT,
    deleted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    reference TEXT NOT NULL,
    order_id TEXT REFERENCES orders(id),
    supplier_id TEXT REFERENCES suppliers(id),
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    status TEXT NOT NULL,
    amount REAL NOT NULL,
    invoice_date TEXT NOT NULL,
    duplicate_of TEXT
);
CREATE TABLE IF NOT EXISTS purchase_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    supplier_id TEXT,
    status TEXT NOT NULL,
    subject TEXT NOT NULL,
    amount REAL,
    draft INTEGER NOT NULL DEFAULT 1,
    assigned_to TEXT,
    on_behalf_of TEXT,
    created_at TEXT NOT NULL,
    submitted_at TEXT
);
CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    submitted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    prefer_excl_tax INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    method TEXT NOT NULL,
    route TEXT NOT NULL,
    user_id TEXT,
    organization_id TEXT,
    role TEXT,
    code INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS failures (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    type TEXT,
    active INTEGER NOT NULL DEFAULT 0
);
"""


def init_schema(conn=None) -> None:
    conn = conn or connection()
    conn.executescript(DDL)
    conn.commit()

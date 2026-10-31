import sqlite3
from flask import current_app, g

SCHEMA = '''
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id TEXT UNIQUE NOT NULL,
    student_name TEXT NOT NULL,
    course TEXT NOT NULL,
    institution TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    description TEXT DEFAULT '',
    certificate_hash TEXT NOT NULL,
    signature TEXT NOT NULL,
    created_at TEXT NOT NULL
);
'''

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db(app):
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.executescript(SCHEMA)
        db.close()

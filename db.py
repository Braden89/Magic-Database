# db.py
import sqlite3

DB_PATH = "mtg_commander.db"
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# db.py
import sqlite3
import logging

logger = logging.getLogger(__name__)

from config import DB_PATH

# Conexión global
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

def get_cursor():
    return cursor

def commit():
    conn.commit()

def rollback():
    conn.rollback()


def close_connection():
    conn.close()

import mysql.connector
from config import DB_CONFIG

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def query(sql, params=None, fetch=False, one=False):
    conn = get_conn(); cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    data = cur.fetchone() if fetch and one else (cur.fetchall() if fetch else None)
    conn.commit(); cur.close(); conn.close(); return data

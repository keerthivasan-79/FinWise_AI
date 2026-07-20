import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".runtime_packages")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from db import get_conn


SELECT_SQL = """
SELECT DISTINCT
    t.*,
    source.account_name AS source_account_name,
    source.account_type AS source_account_type,
    target.account_name AS target_account_name,
    target.account_type AS target_account_type
FROM transactions t
JOIN accounts source ON source.id = t.account_id
LEFT JOIN accounts target ON target.id = t.transfer_to_account
WHERE source.account_type = 'Bank' OR target.account_type = 'Bank'
ORDER BY t.id
"""


def serialize_row(row):
    clean = {}
    for key, value in row.items():
        clean[key] = value.isoformat() if hasattr(value, "isoformat") else value
    return clean


def restore_balance(cur, tx):
    amount = float(tx["amount"])
    uid = tx["user_id"]
    if tx["type"] == "Income":
        cur.execute(
            "UPDATE accounts SET current_balance=current_balance-%s WHERE id=%s AND user_id=%s",
            (amount, tx["account_id"], uid),
        )
    elif tx["type"] == "Expense":
        cur.execute(
            "UPDATE accounts SET current_balance=current_balance+%s WHERE id=%s AND user_id=%s",
            (amount, tx["account_id"], uid),
        )
    elif tx["type"] == "Transfer":
        cur.execute(
            "UPDATE accounts SET current_balance=current_balance+%s WHERE id=%s AND user_id=%s",
            (amount, tx["account_id"], uid),
        )
        cur.execute(
            "UPDATE accounts SET current_balance=current_balance-%s WHERE id=%s AND user_id=%s",
            (amount, tx["transfer_to_account"], uid),
        )


def main():
    parser = argparse.ArgumentParser(description="Remove transactions linked to Bank accounts.")
    parser.add_argument("--apply", action="store_true", help="Actually delete matching transactions.")
    args = parser.parse_args()

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(SELECT_SQL)
        matches = cur.fetchall()
        print(f"Matched bank-linked transactions: {len(matches)}")

        by_account = {}
        for tx in matches:
            name = tx["source_account_name"]
            by_account[name] = by_account.get(name, 0) + 1
            if tx.get("target_account_name"):
                by_account[tx["target_account_name"]] = by_account.get(tx["target_account_name"], 0)
        for account, count in sorted(by_account.items()):
            print(f"- {account}: {count}")

        if not args.apply:
            print("Dry run only. Re-run with --apply to delete and restore balances.")
            return

        os.makedirs("transaction_backups", exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join("transaction_backups", f"bank_transactions_{stamp}.json")
        with open(backup_path, "w", encoding="utf-8") as handle:
            json.dump([serialize_row(row) for row in matches], handle, indent=2)

        for tx in matches:
            restore_balance(cur, tx)
            cur.execute("DELETE FROM transactions WHERE id=%s AND user_id=%s", (tx["id"], tx["user_id"]))

        cur.execute("""DELETE s FROM statement_imports s
            LEFT JOIN transactions t ON t.statement_import_id=s.id
            WHERE t.id IS NULL""")
        stale_imports = cur.rowcount
        conn.commit()
        print(f"Deleted transactions: {len(matches)}")
        print(f"Removed stale statement imports: {stale_imports}")
        print(f"Backup saved: {backup_path}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

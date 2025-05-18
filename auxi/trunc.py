#!/usr/bin/env python3
"""
drop_ai_cotations.py
────────────────────
IRREVERSIBLY remove the column `ai_cotations` from the `route` table.

Usage (from your project root):
    docker compose run --rm app python drop_ai_cotations.py
"""

from Databases.ConnectDB import ConnectDB
from Databases.DbParams  import postgresql_config


def main() -> None:
    db   = ConnectDB(**postgresql_config)
    conn = db.connect()

    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE route DROP COLUMN IF EXISTS ai_cotations")
        conn.commit()
        print("[drop] Column ai_cotations has been removed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
check_ai_cotations_type.py
───────────────────────────
Query and print the data type of the `ai_cotations` column in the `route` table.

Usage (from your project root):
    docker compose run --rm app python check_ai_cotations_type.py
"""

from Databases.ConnectDB import ConnectDB
from Databases.DbParams import postgresql_config


def main() -> None:
    db = ConnectDB(**postgresql_config)
    conn = db.connect()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    data_type,
                    udt_name,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name   = 'route'
                  AND column_name  = 'ai_cotations';
            """)
            result = cur.fetchone()

            if result:
                data_type, udt_name, char_len = result
                info = f"Column 'ai_cotations' type: {data_type}"
                info += f" (internal type: {udt_name})"
                if char_len is not None:
                    info += f", max length: {char_len}"
                print(info)
            else:
                print("Column 'ai_cotations' not found in table 'route'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

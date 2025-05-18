# Databases/DbOps.py
# ======================================================================
# CSV ↔ DB utilities for ai_cotations (jsonb arrays, schema now handled
# by official migrations – no local ALTER / TRIGGER code here).
# ======================================================================

import csv
import json
from pathlib import Path

from dotenv import load_dotenv

from Databases.ConnectDB import ConnectDB
from Databases.DbParams  import postgresql_config
from Utils.grade_sort    import sort_cotations


# ──────────────────────────────────────────────────────────────────────
def ExportRoutes(csv_filename: str | Path) -> None:
    """Dump the whole «route» table to a CSV file."""
    load_dotenv()
    db   = ConnectDB(**postgresql_config)
    conn = db.connect()
    try:
        with conn.cursor() as cur, open(csv_filename, "w", encoding="utf-8", newline="") as fout:
            cur.copy_expert(
                """
                COPY route
                  TO STDOUT
                  WITH CSV HEADER
                  DELIMITER ';'
                  QUOTE '"'
                  ESCAPE '"'
                  ENCODING 'UTF8'
                """,
                fout,
            )
        print(f"[ExportRoutes] exported → {csv_filename}")
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────
def produceRoutesCotationsInBulk(
    csv_path: str | Path,
    *,
    skip: bool = True,
    limit: int | None = None,
    dry_run: bool = False,
) -> None:
    """Bulk-import JSONB cotations from a CSV (id ; cotations)."""
    load_dotenv()
    db   = ConnectDB(**postgresql_config)
    conn = db.connect()

    dry_log: list[tuple[int, list[dict[str, int]]]] = []
    processed = updated = 0

    try:
        with open(csv_path, "r", encoding="utf-8") as fin:
            reader = csv.DictReader(fin, delimiter=";")
            for row in reader:
                if limit is not None and processed >= limit:
                    break
                processed += 1

                rid_str = (row.get("id") or "").strip()
                if not rid_str.isdigit():
                    continue
                rid = int(rid_str)

                # ── skip routes that already have data ───────────────────────
                if skip:
                    with conn.cursor() as cur:
                        cur.execute("SELECT ai_cotations FROM route WHERE id = %s", (rid,))
                        existing = cur.fetchone()
                    if existing and existing[0] not in (None, [], "[]", ""):
                        continue

                raw = (row.get("cotations") or "").strip().replace('""', '"')
                try:
                    cot_dict = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    continue

                sorted_dict = sort_cotations(cot_dict)
                cot_list    = [{"grade": g, "count": c} for g, c in sorted_dict.items()]

                if dry_run:
                    dry_log.append((rid, cot_list))
                    continue

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE route
                           SET ai_cotations = %s::jsonb
                         WHERE id = %s
                        """,
                        (json.dumps(cot_list, ensure_ascii=False), rid),
                    )
                    if cur.rowcount:
                        updated += 1

        if not dry_run:
            conn.commit()

        # ── summary ─────────────────────────────────────────────────────────
        if dry_run:
            print("[Bulk] DRY-RUN – planned updates:")
            for rid, arr in dry_log:
                print(f"  • id {rid} → {arr}")
        else:
            print(f"[Bulk] processed {processed} rows — updated {updated}")

    except Exception as e:
        conn.rollback()
        print(f"[Bulk] ERROR: {e}")
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────
def produceRouteCotations(
    route_id: int,
    csv_path: str | Path,
    *,
    dry_run: bool = False,
) -> None:
    """Update a **single** route’s ai_cotations from the CSV."""
    load_dotenv()
    db   = ConnectDB(**postgresql_config)
    conn = db.connect()

    found = False
    try:
        with open(csv_path, "r", encoding="utf-8") as fin:
            reader = csv.DictReader(fin, delimiter=";")
            for row in reader:
                if (row.get("id") or "").strip() != str(route_id):
                    continue
                found = True

                raw = (row.get("cotations") or "").strip().replace('""', '"')
                try:
                    cot_dict = json.loads(raw) if raw else {}
                except json.JSONDecodeError as exc:
                    print(f"[Single] bad JSON for {route_id}: {exc}")
                    return

                sorted_dict = sort_cotations(cot_dict)
                cot_list    = [{"grade": g, "count": c} for g, c in sorted_dict.items()]

                if dry_run:
                    print(f"[Single] DRY-RUN — would set {route_id} → {cot_list}")
                    return

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE route
                           SET ai_cotations = %s::jsonb
                         WHERE id = %s
                        """,
                        (json.dumps(cot_list, ensure_ascii=False), route_id),
                    )
                    conn.commit()
                print(f"[Single] route {route_id} updated.")
                return

        if not found:
            print(f"[Single] id {route_id} not found in {csv_path}")

    except Exception as e:
        conn.rollback()
        print(f"[Single] ERROR for {route_id}: {e}")
    finally:
        conn.close()

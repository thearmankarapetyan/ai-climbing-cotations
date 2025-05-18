#!/usr/bin/env python3
# nbCheckerCotations.py — version corrigée pour JSONB description

"""
Compte les itinéraires nécessitant une extraction de cotations par l’AI.

Critères :
  • status = '1'
  • activités ∈ DESIRED_ACTIVITIES
  • ai_cotations est NULL, vide ou '{}'
  • description contient au moins un motif de cotation (ex : 5a, 6b+, 7c, …)

Usage :
  docker compose exec ai-climbing-cotations-app \
    python3 nbCheckerCotations.py [--verbose]
"""

import json
import re
import sys
from argparse import ArgumentParser

import psycopg2.extras
from Databases.ConnectDB import ConnectDB
from Databases.DbParams import postgresql_config

# ─── activités souhaitées ────────────────────────────────────────────
DESIRED_ACTIVITIES = {
    "rock_climbing",
    "bouldering",
    "mountain_climbing",
}

# ─── motifs de cotations ─────────────────────────────────────────────
COT_PATTERNS = [
    re.compile(r"\b\d+[abc]\+?\b", re.I),   # ex. 5a, 6b+
    re.compile(r"\b\d+[ABCD]\+?\b"),       # variantes majuscules
]

def _activity_matches(raw: str | None) -> bool:
    """Vérifie que raw contient au moins une activité de DESIRED_ACTIVITIES."""
    if not raw:
        return False
    s = raw.strip()
    # JSON list ?
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return any(tok in DESIRED_ACTIVITIES for tok in arr)
        except Exception:
            pass
    # séparateurs CSV
    for tok in re.split(r"[;,]", s):
        if tok.strip() in DESIRED_ACTIVITIES:
            return True
    return s in DESIRED_ACTIVITIES

def has_cotation(text: str) -> bool:
    """Retourne True si un motif de cotation apparaît dans text."""
    for pat in COT_PATTERNS:
        if pat.search(text):
            return True
    return False

def has_cotation_in_desc(desc):
    """
    Si desc est un dict (JSONB), teste chaque valeur string.
    Sinon, s’il s’agit d’une string, teste directement.
    """
    if isinstance(desc, dict):
        for v in desc.values():
            if isinstance(v, str) and has_cotation(v):
                return True
        return False
    if isinstance(desc, str):
        return has_cotation(desc)
    return False

def main(verbose: bool = False):
    conn = ConnectDB(**postgresql_config).connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  id,
                  description,
                  ai_cotations,
                  activities::text AS activity_raw
                FROM route
                WHERE status = '1'
                  AND (
                    ai_cotations IS NULL
                    OR ai_cotations::text = '{}'
                    OR ai_cotations::text = ''
                  )
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    pending = []
    for row in rows:
        if not _activity_matches(row["activity_raw"]):
            continue

        desc = row["description"]
        if has_cotation_in_desc(desc):
            pending.append(row["id"])
            if verbose:
                act = row["activity_raw"]
                print(f"[Route {row['id']}] activité={act} → cotation détectée")

    print(f"Itinéraires à traiter pour cotations : {len(pending)}")
    if verbose:
        print("Liste des IDs :", ", ".join(map(str, pending)))

if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument(
        "--verbose", action="store_true",
        help="affiche les IDs et signale les descriptions concernées"
    )
    args = ap.parse_args()
    main(verbose=args.verbose)

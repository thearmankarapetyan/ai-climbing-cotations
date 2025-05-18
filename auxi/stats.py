#!/usr/bin/env python3
# stats.py – Statistiques “Cotations Extractor” directement depuis la base

"""
Répond aux questions suivantes, sans passer par des CSV intermédiaires :

1) XXX routes : combien de descriptions sont passées du Mapper au Reducer ?
2) YYY grades : total de couples (grade, count) extraits après post-process ?
3) ZZ % ambiguïté : % de JSON où ambiguous=true ?
4) Tokens / coût / temps : estimations comme pour le Markdown (ou N/A si pas suivi)
"""

import os
import re
import json
import psycopg2
from dotenv import load_dotenv

# ─── Activités autorisées (mêmes que dans mapper.py) ────────────────
ALLOWED_ACTIVITIES = {
    "bouldering",
    "rock_climbing",
    "mountain_climbing",
}

# ─── Regex de détection de grade (idem mapper.py) ───────────────────
_ARABIC_RE = (
    r"(?:1|2|"
    r"3(?:\+|[abc])?|"
    r"4(?:\+|[ab]|c(?:\+)?)|"
    r"5(?:\+|[abc](?:\+)?)|"
    r"6(?:[abc](?:\+)?)|"
    r"7(?:[abc](?:\+)?)|"
    r"8(?:[abc](?:\+)?)|"
    r"9(?:[abc](?:\+)?)"
    r")"
)
_ROMAN_RE = (
    r"(?:"  
    r"I\+?|II\+?|III\+?|"
    r"IV-?|IV\+?|"
    r"V-?|V\+?|"
    r"VI-?|VI\+?|"
    r"VII-?|VII\+?|"
    r"VIII-?|VIII\+?|"
    r"IX-?|IX\+?|"
    r"X-?|X\+?|"
    r"XI-?|XI"
    r")"
)
_COTATION_REGEX = re.compile(rf"\b(?:{_ARABIC_RE}|{_ROMAN_RE})\b", re.IGNORECASE)

def extract_activities(blob):
    """
    Toujours renvoyer une liste Python pour 'activities'.
    • Si c'est déjà une liste, on renvoie telle quelle.
    • Si c'est une chaîne, on tente json.loads.
    • Sinon on renvoie [].
    """
    if isinstance(blob, list):
        return blob
    if blob is None:
        return []
    if isinstance(blob, str):
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            return []
    return []

def pick_lang(desc_blob):
    """
    Si description est JSON multilingue (dict ou JSON-string), on choisit
    fr>en>it. Sinon on retourne la chaîne brute.
    """
    if not desc_blob:
        return ""
    # déjà un dict Python
    if isinstance(desc_blob, dict):
        return desc_blob.get("fr") or desc_blob.get("en") or desc_blob.get("it") or ""
    # chaîne : peut être JSON, peut être brut
    if isinstance(desc_blob, str):
        try:
            parsed = json.loads(desc_blob)
            if isinstance(parsed, dict):
                return parsed.get("fr") or parsed.get("en") or parsed.get("it") or ""
        except json.JSONDecodeError:
            pass
        return desc_blob
    # tout autre type (rare)
    return str(desc_blob)

def contains_cotation(text: str) -> bool:
    """Détecte la présence d'au moins un grade dans le texte."""
    return bool(_COTATION_REGEX.search(text or ""))

def count_tokens(text: str) -> int:
    """Approxime le nombre de tokens en splittant sur les espaces."""
    return len(text.split())

def main():
    load_dotenv()

    # Connexion à la BDD
    conn = psycopg2.connect(
        host=os.getenv("HNAME"),
        user=os.getenv("HUSER"),
        password=os.getenv("HPASSWORD"),
        dbname=os.getenv("HDATABASE"),
        port=os.getenv("HPORT"),
    )
    cur = conn.cursor()

    # ── 1) Sélection “Mapper” : status=1, activités autorisées, contient un grade
    cur.execute("SELECT id, description, activities FROM route WHERE status = '1'")
    rows = cur.fetchall()

    mapper_ids   = []
    descriptions = []

    for rid, desc_blob, acts_blob in rows:
        acts = extract_activities(acts_blob)
        if not any(a in ALLOWED_ACTIVITIES for a in acts):
            continue

        text = pick_lang(desc_blob).strip()
        if not text:
            continue
        if not contains_cotation(text):
            continue

        mapper_ids.append(rid)
        descriptions.append(text)

    route_count = len(mapper_ids)

    # ── 2 & 3) Pour ces mêmes routes, lire ai_cotations et accumuler stats
    grade_pairs     = 0
    ambiguous_count = 0
    reduced_count   = 0

    if mapper_ids:
        placeholders = ",".join(["%s"] * route_count)
        cur.execute(
            f"SELECT id, ai_cotations FROM route "
            f"WHERE id IN ({placeholders}) AND ai_cotations IS NOT NULL",
            mapper_ids
        )
        for rid, cot_blob in cur.fetchall():
            reduced_count += 1
            # si jsonb, psycopg2 renvoie dict ; sinon on parse
            try:
                data = cot_blob if isinstance(cot_blob, dict) else json.loads(cot_blob)
            except Exception:
                data = {}

            if data.get("ambiguous"):
                ambiguous_count += 1
            for k in data:
                if k != "ambiguous":
                    grade_pairs += 1

    cur.close()
    conn.close()

    # ── 4) Estimation tokens / coût / temps
    COST_PER_1000 = 0.02   # €/1k tokens
    TIME_PER_1000 = 1.5    # sec/1k tokens

    total_tokens = sum(count_tokens(t) for t in descriptions)
    cost_total   = total_tokens / 1000 * COST_PER_1000
    time_total   = total_tokens / 1000 * TIME_PER_1000
    avg_tokens   = total_tokens / route_count if route_count else 0
    avg_time     = time_total / route_count    if route_count else 0
    ambiguous_pct = (ambiguous_count / reduced_count * 100) if reduced_count else 0.0

    # ─── Affichage final ────────────────────────────────────────────────
    print(f"1) {route_count} routes passées du Mapper au Reducer")
    print(f"2) {grade_pairs} couples (grade, count) extraits au total")
    print(f"3) {ambiguous_pct:.1f}% de JSON ambigus ({ambiguous_count}/{reduced_count})")
    print("4) Tokens / coût / temps estimés :")
    print(f"   • Tokens total      : {total_tokens:,}")
    print(f"   • Coût total        : €{cost_total:.2f} (@ €{COST_PER_1000}/1k tokens)")
    print(f"   • Temps total       : {time_total:.1f}s (@ {TIME_PER_1000}s/1k tokens)")
    print(f"   • Moyenne par route : {avg_tokens:.0f} tokens, {avg_time:.2f}s")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Mapper step
───────────
• Reads route.csv
• Keeps rows whose description mentions *any* climbing grade
  (modern French OR Roman/UIAA)
• Writes MapperOutput.csv   id ; description
"""

import csv
import json
import re
import sys
from pathlib import Path

import pandas as pd

# ────────────────────────── config ──────────────────────────────
INPUT_CSV  : Path = Path("/app/data/route.csv")
OUTPUT_CSV : Path = Path("/app/data/MapperOutput.csv")

desired_activities = {
    "rock_climbing",
    "bouldering",
    "mountain_climbing",
}

# ----------------------------------------------------------------
# Arabic / French-style grades (unchanged)
_arabic_re = (
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

# UIAA Roman grades  I … XI including “–” and “+”
_roman_re = (
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

# final pattern (word-boundaries on both sides)
cotations_pattern = rf"\b(?:{_arabic_re}|{_roman_re})\b"

_cotation_regex = re.compile(cotations_pattern, re.IGNORECASE)

# ────────────────────────── helpers ─────────────────────────────
def contains_cotation(text: str) -> bool:
    """
    Detect at least one grade in `text`.
    • Arabic grades are searched case-insensitively in lower-case text
    • Roman grades are searched in UPPER-case text
    """
    if pd.isna(text):
        return False
    txt = str(text)
    return bool(
        _cotation_regex.search(txt.lower())   # Arabic / French
        or _cotation_regex.search(txt.upper())  # Roman UIAA
    )

# ────────────────────────── main mapper ─────────────────────────
def mapper() -> None:
    output_rows: list[dict[str, str]] = []

    with INPUT_CSV.open("r", encoding="utf-8-sig") as fin:
        reader = csv.DictReader(fin, delimiter=";")

        for row in reader:
            # filter by activity -------------------------------------------------
            try:
                acts = json.loads(row.get("activities", "[]"))
            except Exception:
                acts = []

            if not any(a in desired_activities for a in acts):
                continue

            # filter by status ---------------------------------------------------
            if (row.get("status") or "0") != "1":
                continue

            # choose FR > EN > IT description -----------------------------------
            try:
                desc_blob = json.loads(row.get("description", "{}"))
            except Exception:
                desc_blob = {}
            description = (
                desc_blob.get("fr") or desc_blob.get("en") or desc_blob.get("it") or ""
            )
            if not description.strip():
                continue

            # keep only if a grade is present ------------------------------------
            if not contains_cotation(description):
                continue

            route_id = row.get("\ufeffid") or row.get("id") or ""
            output_rows.append({"id": route_id, "description": description})

    # write CSV -----------------------------------------------------------------
    df = pd.DataFrame(output_rows)
    df.to_csv(OUTPUT_CSV, sep=";", index=False)
    print(f"[Mapper] kept {len(df)} rows → {OUTPUT_CSV}")
    df.info()



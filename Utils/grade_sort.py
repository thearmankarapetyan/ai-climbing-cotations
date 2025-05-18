# Utils/grade_sort.py
# =====================================================================
# Canonical ascending-difficulty order for all grades listed in
# AI/AiParams.VALID_SET, interleaving UIAA Roman grades just before the
# French grades they historically correspond to.
#
# Public helper:
#   sort_cotations(dict[str,int]) -> dict[str,int]
# =====================================================================

from __future__ import annotations

# ---------------------------------------------------------------------
_ORDER: list[str] = [
    # very easy -------------------------------------------------------
    "1",
    "I", "I+",
    "2",
    "II", "II+",

    # 3 block ---------------------------------------------------------
    "3",
    "III", "III+",
    "3+", "3a", "3b", "3c",

    # 4 block ---------------------------------------------------------
    "4",
    "IV-", "IV", "IV+",
    "4a", "4b", "4c", "4c+", "4+",

    # 5 block ---------------------------------------------------------
    "V-", "V", "V+",
    "5", "5+", "5a", "5a+", "5b", "5b+", "5c", "5c+",

    # 6 block ---------------------------------------------------------
    "VI-", "VI", "VI+",
    "6", "6a", "6a+", "6b", "6b+",

    # 6c / VII block --------------------------------------------------
    "VII-", "VII", "VII+",
    "6c", "6c+",

    # 7a / VIII block -------------------------------------------------
    "VIII-", "VIII", "VIII+",
    "7a", "7a+", "7b", "7b+",

    # 7c / IX block ---------------------------------------------------
    "IX-", "IX", "IX+",
    "7c", "7c+",

    # 8a / X block ----------------------------------------------------
    "X-", "X", "X+",
    "8a", "8a+", "8b", "8b+",

    # 8c / XI block + French 9's -------------------------------------
    "XI-", "XI",
    "8c", "8c+",
    "9a", "9a+", "9b", "9b+", "9c", "9c+",
]

# O(1) lookup for ranking
_RANK: dict[str, int] = {g.lower(): i for i, g in enumerate(_ORDER)}


# ---------------------------------------------------------------------
def sort_cotations(cotes: dict[str, int]) -> dict[str, int]:
    """
    Return a **new** dict with keys in canonical difficulty order.
    Any grade not in the list is left in place but appended *after*
    all known grades (preserving its original relative order).
    """
    known   = [k for k in cotes if k.lower() in _RANK]
    unknown = [k for k in cotes if k.lower() not in _RANK]

    known_sorted = sorted(known, key=lambda k: _RANK[k.lower()])
    return {k: cotes[k] for k in (*known_sorted, *unknown)}

def sort_and_array(cotes: dict[str, int]) -> list[dict[str, int]]:
    """
    Convert a grade→count dict into an **ordered list** of
    {"grade": <grade>, "count": <int>}.
    """
    ordered = sort_cotations(cotes)
    return [{"grade": g, "count": c} for g, c in ordered.items()]

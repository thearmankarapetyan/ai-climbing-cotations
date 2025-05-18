#!/usr/bin/env  python3
# AI/AiOps.py  – jsonb array version + activity filter
# ====================================================
# gpt-route  &  gpt-bulk  now skip any route whose
# activities  do **not** overlap  DESIRED_ACTIVITIES.
# ====================================================

from __future__ import annotations
import json, os, re
from typing import Any, Dict

import openai
import psycopg2.extras             # type: ignore
from dotenv import load_dotenv

from AI.AiParams          import AiParams
from Databases.ConnectDB  import ConnectDB
from Databases.DbParams   import postgresql_config
from Utils.grade_sort     import sort_cotations
from Parameters.activities import DESIRED_ACTIVITIES      # ← NEW


# ────────── regex helper ─────────────────────────────────────────────
_JSON_RE = re.compile(
    r"""
    \{
        [^\{\}]*?"difficulties"\s*:\s*\{[^{}]*\}
        [^{}]*?"ambiguous"\s*:\s*(?:true|false)
        [^{}]*?
    \}
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


def _extract_json(text: str) -> Dict[str, Any] | None:
    m = _JSON_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ────────── GPT wrapper ──────────────────────────────────────────────
class AiOps:
    def __init__(self) -> None:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY missing")
        openai.api_key = api_key

    def ask_gpt(self, user_text: str) -> str:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                temperature=0.0,
                messages=[
                    {"role": "system", "content": AiParams.SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": AiParams.USER_PROMPT_TEMPLATE.format(
                            user_text=user_text
                        ),
                    },
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            print(f"[AiOps] error while calling GPT: {exc}")
            return ""

    # kept for backward compatibility
    generate_response = ask_gpt


# ────────── main class ───────────────────────────────────────────────
class AiOpsCotationsExtended:
    """Extracts cotations and writes them as a jsonb array."""

    def __init__(self) -> None:
        self.gpt = AiOps()

    # ------------------------------------------------------------------
    @staticmethod
    def _wanted_activity(acts_json: str | list | None) -> bool:
        """Return True iff activities overlap the wanted set."""
        if not acts_json:
            return False
        acts = acts_json if isinstance(acts_json, list) else json.loads(acts_json)
        return any(a in DESIRED_ACTIVITIES for a in acts)

    # ------------------------------------------------------------------
    def _process_text(self, text: str, rid: int) -> Dict[str, int]:
        raw = self.gpt.ask_gpt(text)

        print(f"\n── GPT raw • {rid} ───────────────────────────────")
        print(raw or "(empty)")
        print("─────────────────────────────────────────────────\n")

        data = _extract_json(raw)
        if data is None:
            print(f"[Route {rid}] JSON block not found → ambiguous")
            return {}
        return data.get("difficulties", {})

    # ------------------------------------------------------------------
    @staticmethod
    def _pick_lang(desc_blob: str | dict) -> str:
        if isinstance(desc_blob, dict):
            d = desc_blob
        else:
            try:
                d = json.loads(desc_blob or "{}")
            except json.JSONDecodeError:
                return ""
        return d.get("fr") or d.get("en") or d.get("it") or ""

    # ------------------------------------------------------------------
    def produceCotationsForRoute(self, route_id: int, *, dry_run: bool = False) -> None:
        """Single-route helper (unchanged except for jsonb array)."""
        conn = ConnectDB(**postgresql_config).connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT description FROM route WHERE id = %s", (route_id,)
                )
                row = cur.fetchone()
            if not row:
                print(f"[Route {route_id}] not found")
                return

            desc = self._pick_lang(row["description"])
            if not desc.strip():
                print(f"[Route {route_id}] empty description")
                return

            cotations = sort_cotations(self._process_text(desc, route_id))
            cot_list  = [{"grade": g, "count": c} for g, c in cotations.items()]

            if dry_run:
                print(f"[DRY-RUN] {route_id} → {cot_list}")
                return

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE route SET ai_cotations = %s::jsonb WHERE id = %s",
                    (json.dumps(cot_list, ensure_ascii=False), route_id),
                )
                conn.commit()
            print(f"[Route {route_id}] ai_cotations updated")
        finally:
            conn.close()

    # ------------------------------------------------------------------
    def produceCotationsInBulk(
        self, *, skip: bool = True, limit: int | None = None, dry_run: bool = False
    ) -> None:
        """
        Iterate over live routes, filter by activities, send to GPT.
        """
        conn = ConnectDB(**postgresql_config).connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, description, ai_cotations, activities
                    FROM   route
                    WHERE  status = '1'
                    """
                )
                rows = cur.fetchall()

            processed = updated = 0
            for row in rows:
                if limit is not None and processed >= limit:
                    break
                processed += 1
                rid = row["id"]

                # 1⃣  activity filter  (NEW) -----------------------------
                if not self._wanted_activity(row["activities"]):
                    continue

                # 2⃣  optional skip of already-processed routes ----------
                if skip and row["ai_cotations"] not in (None, [], "[]", ""):
                    continue

                desc = self._pick_lang(row["description"])
                if not desc.strip():
                    continue

                cotations = sort_cotations(self._process_text(desc, rid))
                cot_list  = [{"grade": g, "count": c} for g, c in cotations.items()]

                if dry_run:
                    print(f"[DRY-RUN] {rid} → {cot_list}")
                    continue

                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE route SET ai_cotations = %s::jsonb WHERE id = %s",
                        (json.dumps(cot_list, ensure_ascii=False), rid),
                    )
                    if cur.rowcount:
                        conn.commit()
                        updated += 1
                    else:
                        conn.rollback()

            if not dry_run:
                print(f"[Bulk] processed {processed} — updated {updated}")
        finally:
            conn.close()

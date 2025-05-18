# MapReduce/reducer.py

import json, re
from pathlib import Path
import pandas as pd

from AI.AiOps import AiOps
from AI.ConnectAI import ConnectAI
from Parameters.cotations import valid_difficulties
from Utils.grade_sort    import sort_and_array  # ← NEW import

_JSON_RE = re.compile(
    r"""
    \{                           # opening brace
      [^\{\}]*?"difficulties"\s*:\s*\{[^{}]*\}   # inner object
      [^{}]*?"ambiguous"\s*:\s*(?:true|false)
      [^{}]*?
    \}
    """,
    re.IGNORECASE|re.DOTALL|re.VERBOSE,
)

def _extract_json(text: str) -> dict | None:
    m = _JSON_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

def reducer(
    input_csv_path : str|Path = "/app/data/MapperOutput.csv",
    output_csv_path: str|Path = "/app/data/result.csv",
) -> None:
    ai_ops = AiOps()
    df = pd.read_csv(
        input_csv_path,
        sep=";",
        quotechar='"',
        engine="python",
        on_bad_lines="skip",
    )

    cotations_out:  list[str]  = []
    ambiguous_out:  list[bool] = []

    for _, row in df.iterrows():
        rid  = row["id"]
        text = row.get("description", "") or ""
        raw  = ai_ops.generate_response(text)
        print(f"\n── GPT raw • {rid} ─────────────────────────────\n{raw}\n")

        parsed = _extract_json(raw)
        if parsed is None:
            print(f"[Reducer] route {rid} → JSON block NOT found → ambiguous")
            parsed = {"difficulties": {}, "ambiguous": True}
        else:
            print(f"[Reducer] route {rid} → parsed JSON {parsed}")

        # Normalize & filter into a dict
        clean_dict: dict[str, int] = {}
        for grade, count in parsed["difficulties"].items():
            g = grade.lower().strip()
            if g in valid_difficulties:
                try:
                    clean_dict[g] = int(count)
                except Exception:
                    clean_dict[g] = 0

        # Convert dict → ordered array
        arr = sort_and_array(clean_dict)

        cotations_out.append(json.dumps(arr, ensure_ascii=False))
        ambiguous_out.append(bool(parsed["ambiguous"]))

    # Write final CSV
    df["cotations"]  = cotations_out
    df["ambiguous"] = ambiguous_out
    df[["id","cotations","ambiguous"]].to_csv(
        output_csv_path, sep=";", index=False
    )
    print(f"\n[Reducer] done → {output_csv_path}")

# AI/AiParams.py
# ======================================================================
# Prompt for cotation extraction – now with many illustrative examples
# showing that, **whenever both systems are present, every Roman-numeral
# grade must be listed immediately before its Arabic “equivalent group”.**
# ======================================================================

class AiParams:          # noqa: N801  (keep original camel-case)
    # ------------------------------------------------------------------
    # 1) whitelists used by other modules
    # ------------------------------------------------------------------
    _arabic = [
        "1",
        "2",
        "3",  "3+",  "3a", "3b", "3c",
        "4",  "4+",  "4a", "4b", "4c", "4c+",
        "5",  "5+",  "5a", "5a+", "5b", "5b+", "5c", "5c+",
        "6a", "6a+", "6b", "6b+", "6c", "6c+",
        "7a", "7a+", "7b", "7b+", "7c", "7c+",
        "8a", "8a+", "8b", "8b+", "8c", "8c+",
        "9a", "9a+", "9b", "9b+", "9c", "9c+",
    ]
    _roman = [
        "I", "I+",
        "II", "II+",
        "III", "III+",
        "IV-", "IV", "IV+",
        "V-",  "V",  "V+",
        "VI-", "VI", "VI+",
        "VII-", "VII", "VII+",
        "VIII-", "VIII", "VIII+",
        "IX-", "IX", "IX+",
        "X-", "X", "X+",
        "XI-", "XI"
    ]
    VALID_SET = _arabic + _roman

    # ------------------------------------------------------------------
    SYSTEM_PROMPT = (
        "You are an assistant that extracts *all* climbing grades mentioned in a text.\n"
        "A grade may appear in the modern French system (4c+, 6a …) **or** in the older UIAA\n"
        "Roman-numeral system (II, VII-, X …). **Do not convert Roman numerals** – keep them\n"
        "exactly as written.\n\n"

        "Recognised grades:\n"
        f"{', '.join(VALID_SET)}\n\n"

        "Users can mention grades in several ways:\n"
        "• Directly with a count – e.g. « 6b 3 », « IV+ 2 »\n"
        "• A range with a total – e.g. « 8 voies de 4 à 6 »\n"
        "• A mix of both.\n\n"

        "IMPORTANT RULES\n"
        "1. For a broad range like « 8 voies de 4 à 6 », assign **1** to every sub-grade in the range\n"
        "   and set \"ambiguous\" = true.\n"
        "2. If some grades inside the range also have an explicit count, sum them.\n"
        "3. If a grade is only named (no count), treat its count as 1.\n"
        "4. If anything is unclear, set \"ambiguous\" = true and give each mentioned grade a count of 1.\n\n"

        "OUTPUT FORMAT\n"
        "Return **one** valid JSON object – nothing before or after it – with exactly:\n"
        "  \"difficulties\": { <grade>: <integer>, … }\n"
        "  \"ambiguous\"  : true | false\n\n"
        "The keys inside \"difficulties\" **must follow this canonical order** so downstream graphs\n"
        "display correctly (Arabic ↔ Roman pairs alternating, then normal progression):\n"
        "  1, I, 2, II, 3, III, 3+, III+, 4, IV-, IV, IV+, 4+, V-, V, V+, 5, 5+, 6, 6a, 6a+, 6b, 6b+, …\n"
        "Skip grades that do not appear, but respect the order of those that do.\n\n"

        "EXAMPLE ANSWERS (note the ordering in each):\n"
        "-------------------------------------------\n"
        "Example A – simple mix\n"
        "{\n"
        "  \"difficulties\": {\n"
        "    \"III\": 1,\n"
        "    \"3+\": 2,\n"
        "    \"IV-\": 1,\n"
        "    \"4a\": 3\n"
        "  },\n"
        "  \"ambiguous\": false\n"
        "}\n\n"

        "Example B – explicit counts *and* a broad range\n"
        "{\n"
        "  \"difficulties\": {\n"
        "    \"VI-\": 1,\n"
        "    \"6a\": 4,\n"
        "    \"VI\": 2,\n"
        "    \"6b\": 2,\n"
        "    \"VI+\": 1,\n"
        "    \"6c\": 1\n"
        "  },\n"
        "  \"ambiguous\": true\n"
        "}\n\n"

        "Example C – high-end grades only in Roman\n"
        "{\n"
        "  \"difficulties\": {\n"
        "    \"VIII\": 2,\n"
        "    \"VIII+\": 1,\n"
        "    \"IX-\": 1\n"
        "  },\n"
        "  \"ambiguous\": false\n"
        "}\n\n"

        "Example D – mixed low grades with ambiguity\n"
        "{\n"
        "  \"difficulties\": {\n"
        "    \"I\": 1,\n"
        "    \"2\": 1,\n"
        "    \"II\": 1,\n"
        "    \"3\": 1\n"
        "  },\n"
        "  \"ambiguous\": true\n"
        "}"
    )

    # ------------------------------------------------------------------
    USER_PROMPT_TEMPLATE = (
        "Climbing-route description:\n\n"
        "{user_text}\n\n"
        "Extract every grade that appears, obey *all* the rules above, and output **exactly**\n"
        "ONE JSON object (no Markdown, no commentary)."
    )


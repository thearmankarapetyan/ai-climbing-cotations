# 📚 Cotations Tool – Usage Documentation

---

## 🚀 Getting Started

### Prerequisites

| Requirement         | Purpose                                           |
|---------------------|-------------------------------------------------|
| **Docker & Docker Compose** | Containers for the PostgreSQL DB and the `ai-climbing-cotations-app` image |
| **`.env` file**            | Supplies DB connection and OpenAI credentials   |

`.env` **template**:

# ── PostgreSQL ─────────────────────────────────────
HNAME=db_host
HUSER=db_user
HPASSWORD=db_password
HDATABASE=db_name
HPORT=5432          # or other port you expose

# ── OpenAI ─────────────────────────────────────────
OPENAI_API_KEY=sk-…

# optional – tweak OpenAI endpoint / proxy if needed
# OPENAI_BASE_URL=https://api.openai.com/v1
`

---

### Launching the stack


docker compose up -d          # starts DB + cotations container


> The service used below is assumed to be named **`ai-climbing-cotations-app`** in your `docker-compose.yml`.
> If you used another name, replace it accordingly.

---

## 🖥️ CLI Overview

All functionality is exposed through **one** entry script inside the container:

docker compose exec ai-climbing-cotations-app \
  python3 main.py <sub-command> [options]


### Sub-commands

| Sub-command | Primary role                                                                                                                                                                                    |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `export`    | Dump the whole **`route`** table to `route.csv`.                                                                                                                                                |
| `map`       | *Mapper*: filter routes → keep only those whose description **mentions a grade** and whose activities are in the allowed set (default: rock / boulder / mountain). Produces `MapperOutput.csv`. |
| `reduce`    | *Reducer*: call GPT on every kept description, extract grades, normalize & order them, write `result.csv`.                                                                                      |
| `pipeline`  | One-shot convenience: **export → map → reduce → optional DB insert**.                                                                                                                           |
| `gpt-route` | Run GPT extraction **directly on a single route** (DB «→ GPT → DB»).                                                                                                                            |
| `gpt-bulk`  | Same as above but for **many** routes (status = 1).                                                                                                                                             |
| `csv-route` | Import cotations **for one route** from a prepared CSV into the DB.                                                                                                                             |
| `csv-bulk`  | Bulk-import an entire CSV (`id ; cotations`) into the DB.                                                                                                                                       |

---

## 📂 File locations inside the container

| Purpose           | Path (default)               |
| ----------------- | ---------------------------- |
| Raw dump of table | `/app/data/route.csv`        |
| Mapper result     | `/app/data/MapperOutput.csv` |
| Reducer result    | `/app/data/result.csv`       |

> All paths can be overridden with options (see below).

---

## 🔧 Common Workflows

### 1️⃣ Full Map-Reduce Pipeline (DB → CSV → GPT → CSV → DB)


docker compose exec ai-climbing-cotations-app \
  python3 main.py pipeline --insert-step       # insert back into DB


**Important flags**

| Flag                                 | Default                     | Meaning                                     |
| ------------------------------------ | --------------------------- | ------------------------------------------- |
| `--no-map-step` / `--no-reduce-step` | run only parts of the chain |                                             |
| `--insert-step`                      | *off*                       | actually update `route.ai_cotations`        |
| `--skip / --no-skip`                 | *skip*                      | skip routes having non-empty `ai_cotations` |
| `--limit N`                          | ∞                           | process / insert at most **N** rows         |
| `--dry-run`                          | off                         | simulate inserts (print but don’t commit)   |

Example: run everything but **only** insert 50 routes and **do not** skip existing ones:


docker compose exec ai-climbing-cotations-app \
  python3 main.py pipeline --insert-step --no-skip --limit 50


---

### 2️⃣ Export routes to CSV


docker compose exec ai-climbing-cotations-app \
  python3 main.py export -o /app/data/my_dump.csv


---

### 3️⃣ Run only the Mapper


docker compose exec ai-climbing-cotations-app \
  python3 main.py map \
      -i /app/data/route.csv \
      -o /app/data/MapperOutput.csv


The mapper **drops** routes that:

* are not `rock_climbing / bouldering / mountain_climbing`
* have `status != 1`
* contain **no** UIAA or French grade in the chosen language blob

---

### 4️⃣ Run only the Reducer


docker compose exec ai-climbing-cotations-app \
  python3 main.py reduce \
      -i /app/data/MapperOutput.csv \
      -o /app/data/result.csv


Each GPT call:

* Returns exactly **one** JSON block
* The reducer converts it into the canonical grade order, then stores it as a **json array** of


[
  {"grade": "5c", "count": 3},
  {"grade": "6a", "count": 4},
  …
]


---

### 5️⃣ Bulk import a prepared CSV (id ; cotations) into DB


docker compose exec ai-climbing-cotations-app \
  python3 main.py csv-bulk /app/data/result.csv --insert


Useful flags:

| Flag        | Default | Meaning                           |
| ----------- | ------- | --------------------------------- |
| `--no-skip` | off     | overwrite existing `ai_cotations` |
| `--limit N` | ∞       | insert at most N rows             |
| `--dry-run` | off     | preview SQL updates               |

---

### 6️⃣ Direct GPT → DB (no CSV)

#### Bulk


docker compose exec ai-climbing-cotations-app \
  python3 main.py gpt-bulk --skip      # re-process only empty routes


* Use `--limit N` to cap the run size
* Use `--dry-run` to see the JSON array without touching the DB

#### Single route (debug)


docker compose exec ai-climbing-cotations-app \
  python3 main.py gpt-route 123456 --dry-run


---

## 📑 JSON Schema Stored in DB

*Column*: `route.ai_cotations` (type **`jsonb`**)

*Shape*: **array** of ordered objects


[
  {"grade": "5b", "count": 2},
  {"grade": "5c", "count": 1},
  {"grade": "6a", "count": 12},
  {"grade": "6b", "count": 21},
  …
]


Ordering is canonical (easy → hard) so that front-end charts render correctly.

---

## ⚙️ Options & Flags Cheat-Sheet

| Global flag (position-specific)    | Sub-commands                       | Effect                                        |
| ---------------------------------- | ---------------------------------- | --------------------------------------------- |
| `--skip / --no-skip`               | `pipeline`, `gpt-bulk`, `csv-bulk` | Skip routes that already have `ai_cotations`. |
| `--limit N`                        | same                               | Hard upper-bound on processed rows.           |
| `--dry-run`                        | any that touches DB                | Do everything except the final `UPDATE`.      |
| `--map-step / --no-map-step`       | `pipeline`                         | Toggle mapper stage.                          |
| `--reduce-step / --no-reduce-step` | `pipeline`                         | Toggle reducer stage.                         |
| `--insert-step`                    | `pipeline`                         | Perform DB insert at the end.                 |

---

## 🛡️ Fault Tolerance

* **Per-route commit** – failures on one ID do **not** abort the loop.
* All long-running commands can be **re-run safely** with `--skip` or `--start-id`.
* The code validates GPT JSON and falls back to `{}`, marking ambiguous cases.

---

## 🧩 Advanced Tips

### Filtering activities

The mapper uses a Python set:


desired_activities = {
    "rock_climbing",
    "bouldering",
    "mountain_climbing",
}


Edit `MapReduce/mapper.py` if you need additional activity types.

### Using a different OpenAI model

Change `"gpt-4o"` to `"gpt-4o-mini"` (or any available) in `AI/AiOps.py`.

### Running outside Docker (dev)


python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)      # load env vars
python3 main.py gpt-route 123456 --dry-run


---

## 📌 Example Scenarios

| Scenario                                       | Command                                                         |
| ---------------------------------------------- | --------------------------------------------------------------- |
| **Resume** reducer after network hiccup        | `main.py reduce -i MapperOutput.csv -o result.csv --limit 1000` |
| **Overwrite** existing cotations for 10 routes | `main.py gpt-bulk --no-skip --limit 10`                         |
| Generate & inspect JSON without DB write       | `main.py gpt-route 123456 --dry-run`                            |

---

🟢 **End of Cotations Tool Documentation**

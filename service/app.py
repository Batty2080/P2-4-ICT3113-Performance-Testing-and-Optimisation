import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException


# Configuration supplied through Docker Compose later.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
LOG_DIR = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
MODEL_TIMEOUT = float(os.getenv("MODEL_TIMEOUT", "300"))
RUN_ID = os.getenv("RUN_ID", "development")

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "tickets.db"

PROMPT = (BASE_DIR / "classification_prompt.txt").read_text(
    encoding="utf-8"
)
PROMPT_HASH = hashlib.sha256(PROMPT.encode("utf-8")).hexdigest()

CATEGORIES = (
    "Credit reporting",
    "Debt collection",
    "Mortgage",
    "Credit card",
    "Bank account or service",
    "Consumer loan",
    "Money transfer or service",
)

app = Flask(__name__)


# One JSON object per line, suitable for later analysis.
request_logger = logging.getLogger("ticket_requests")
request_logger.setLevel(logging.INFO)
request_logger.propagate = False

if not request_logger.handlers:
    handler = logging.FileHandler(
        LOG_DIR / "requests.jsonl",
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    request_logger.addHandler(handler)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Create an empty table on first startup.
# Existing tickets are retained across restarts.
with sqlite3.connect(DATABASE_PATH) as db:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            narrative TEXT NOT NULL,
            category TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


@app.before_request
def start_request():
    g.started = time.perf_counter()
    g.request_id = str(uuid.uuid4())

    # The load generator can supply this ID for reconciliation.
    g.client_request_id = request.headers.get("X-Request-ID", "")[:128]

    g.started_at = utc_now()
    g.model_ms = None
    g.category = None
    g.ticket_id = None
    g.error = None
    g.narrative_hash = None
    g.narrative_chars = None


@app.after_request
def log_request(response):
    elapsed_ms = (time.perf_counter() - g.started) * 1000

    record = {
        "started_at": g.started_at,
        "finished_at": utc_now(),
        "run_id": RUN_ID,
        "request_id": g.request_id,
        "client_request_id": g.client_request_id,
        "method": request.method,
        "path": request.path,
        "status": response.status_code,
        "duration_ms": round(elapsed_ms, 3),
        "model_ms": g.model_ms,
        "model": OLLAMA_MODEL,
        "prompt_sha256": PROMPT_HASH,
        "ticket_id": g.ticket_id,
        "category": g.category,
        "narrative_sha256": g.narrative_hash,
        "narrative_chars": g.narrative_chars,
        "error": g.error,
    }

    request_logger.info(json.dumps(record, ensure_ascii=False))
    response.headers["X-Request-ID"] = g.request_id
    return response


def error_response(message, status):
    g.error = message
    return jsonify(
        error=message,
        request_id=g.request_id,
    ), status


@app.errorhandler(HTTPException)
def handle_http_error(exception):
    return error_response(exception.description, exception.code)


@app.errorhandler(Exception)
def handle_unexpected_error(exception):
    app.logger.exception("Unhandled request error")
    return error_response("Internal server error", 500)


def classify_ticket(narrative):
    started = time.perf_counter()

    try:
        response = requests.post(
            f"{OLLAMA_URL.rstrip('/')}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": narrative},
                ],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_gpu": 0,
                },
            },
            timeout=(10, MODEL_TIMEOUT),
        )
        response.raise_for_status()

        result = response.json()
        if result.get("done") is not True:
            raise ValueError("Incomplete model response")

        prediction = json.loads(result["message"]["content"])
        category = prediction["category"]

        if category not in CATEGORIES:
            raise ValueError("Unrecognised category")

        return category
    finally:
        g.model_ms = round(
            (time.perf_counter() - started) * 1000,
            3,
        )


@app.post("/tickets")
def create_ticket():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return error_response("Request body must be a JSON object", 400)

    narrative = body.get("narrative")

    if not isinstance(narrative, str) or not narrative.strip():
        return error_response(
            "'narrative' must be a non-empty string",
            400,
        )

    g.narrative_chars = len(narrative)
    g.narrative_hash = hashlib.sha256(
        narrative.encode("utf-8")
    ).hexdigest()

    if not OLLAMA_MODEL:
        return error_response("OLLAMA_MODEL is not configured", 503)

    try:
        category = classify_ticket(narrative)
    except requests.exceptions.Timeout:
        return error_response("Model request timed out", 504)
    except requests.exceptions.RequestException:
        return error_response("Ollama request failed", 502)
    except (ValueError, KeyError, TypeError, AttributeError):
        return error_response("Model returned an invalid classification", 502)

    g.category = category
    created_at = utc_now()

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO tickets (narrative, category, model, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (narrative, category, OLLAMA_MODEL, created_at),
    )
    db.commit()

    g.ticket_id = cursor.lastrowid

    return jsonify(
        id=g.ticket_id,
        category=category,
        model=OLLAMA_MODEL,
        created_at=created_at,
        request_id=g.request_id,
    ), 201


@app.get("/search")
def search_tickets():
    query = request.args.get("q", "").strip()

    if not query:
        return error_response("Provide a non-empty 'q' parameter", 400)

    # Literal substring search; % and _ are not wildcards.
    rows = get_db().execute(
        """
        SELECT id, narrative, category, model, created_at
        FROM tickets
        WHERE instr(lower(narrative), lower(?)) > 0
        ORDER BY id
        """,
        (query,),
    ).fetchall()

    tickets = [dict(row) for row in rows]

    return jsonify(
        query=query,
        count=len(tickets),
        tickets=tickets,
    )


@app.get("/stats")
def ticket_stats():
    counts = {category: 0 for category in CATEGORIES}

    rows = get_db().execute(
        """
        SELECT category, COUNT(*) AS count
        FROM tickets
        GROUP BY category
        """
    ).fetchall()

    for row in rows:
        counts[row["category"]] = row["count"]

    return jsonify(
        total=sum(counts.values()),
        categories=counts,
    )
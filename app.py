from flask import Flask, render_template, request, jsonify
from pathlib import Path
from platformdirs import user_data_path
import sqlite3, uuid, json
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent

# Original database location, used for first-launch migration.
LEGACY_DB_PATH = BASE / "data" / "brain_sprinkles.db"

# Application Support location.
DATA_DIR = user_data_path("BrainSprinkles", appauthor=False)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "brain_sprinkles.db"

app = Flask(__name__)

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def migrate_legacy_database():
    """Copy the old project database into Application Support on first launch."""

    if DB_PATH.exists():
        print(f"Using existing database: {DB_PATH}")
        return

    if LEGACY_DB_PATH.exists():
        print("Migrating existing BrainSprinkles database...")

        with sqlite3.connect(LEGACY_DB_PATH) as source:
            with sqlite3.connect(DB_PATH) as destination:
                source.backup(destination)

        print(f"Database migrated to: {DB_PATH}")

    else:
        print("No existing database found. Creating a new one.")

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL DEFAULT 'Thought',
            tags TEXT NOT NULL DEFAULT '[]',
            is_favorite INTEGER NOT NULL DEFAULT 0,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted INTEGER NOT NULL DEFAULT 0,
            synced_at TEXT
        );
        CREATE TABLE IF NOT EXISTS links (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(source_id, target_id)
        );
        CREATE TABLE IF NOT EXISTS sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            payload TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0
        );
        """)
migrate_legacy_database()
init_db()

def queue(con, entity_type, entity_id, action, payload):
    con.execute(
        "INSERT INTO sync_queue(entity_type,entity_id,action,payload,queued_at) VALUES(?,?,?,?,?)",
        (entity_type, entity_id, action, json.dumps(payload), now())
    )

def entry_dict(row):
    d = dict(row)
    d["tags"] = json.loads(d["tags"] or "[]")
    d["is_favorite"] = bool(d["is_favorite"])
    d["is_archived"] = bool(d["is_archived"])
    return d

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/entries")
def entries():
    q = request.args.get("q", "").strip()
    kind = request.args.get("kind", "").strip()
    with db() as con:
        sql = "SELECT * FROM entries WHERE deleted=0 AND is_archived=0"
        args = []
        if kind and kind != "All":
            sql += " AND kind=?"; args.append(kind)
        if q:
            sql += " AND (title LIKE ? OR body LIKE ? OR tags LIKE ?)"
            args.extend([f"%{q}%"]*3)
        sql += " ORDER BY updated_at DESC"
        rows = con.execute(sql, args).fetchall()
        return jsonify([entry_dict(r) for r in rows])

@app.get("/api/entries/<entry_id>")
def get_entry(entry_id):
    with db() as con:
        row = con.execute("SELECT * FROM entries WHERE id=? AND deleted=0", (entry_id,)).fetchone()
        if not row: return jsonify({"error":"Not found"}), 404
        return jsonify(entry_dict(row))

@app.post("/api/entries")
def create_entry():
    data = request.get_json(force=True)
    entry_id, stamp = str(uuid.uuid4()), now()
    payload = {
        "id": entry_id, "title": data.get("title","").strip(),
        "body": data.get("body",""), "kind": data.get("kind","Thought"),
        "tags": data.get("tags",[]), "is_favorite": False,
        "is_archived": False, "created_at": stamp, "updated_at": stamp
    }
    with db() as con:
        con.execute("""INSERT INTO entries(id,title,body,kind,tags,is_favorite,is_archived,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (entry_id,payload["title"],payload["body"],payload["kind"],
                     json.dumps(payload["tags"]),0,0,stamp,stamp))
        queue(con,"entry",entry_id,"upsert",payload)
    return jsonify(payload), 201

@app.patch("/api/entries/<entry_id>")
def update_entry(entry_id):
    data = request.get_json(force=True)
    with db() as con:
        row = con.execute("SELECT * FROM entries WHERE id=? AND deleted=0",(entry_id,)).fetchone()
        if not row: return jsonify({"error":"Not found"}),404
        current = entry_dict(row)
        for key in ("title","body","kind","tags","is_favorite","is_archived"):
            if key in data: current[key] = data[key]
        current["updated_at"] = now()
        con.execute("""UPDATE entries SET title=?,body=?,kind=?,tags=?,is_favorite=?,is_archived=?,updated_at=?
                       WHERE id=?""",
                    (current["title"],current["body"],current["kind"],json.dumps(current["tags"]),
                     int(current["is_favorite"]),int(current["is_archived"]),current["updated_at"],entry_id))
        queue(con,"entry",entry_id,"upsert",current)
    return jsonify(current)

@app.delete("/api/entries/<entry_id>")
def delete_entry(entry_id):
    with db() as con:
        row = con.execute("SELECT * FROM entries WHERE id=?",(entry_id,)).fetchone()
        if not row: return jsonify({"ok":True})
        stamp = now()
        con.execute("UPDATE entries SET deleted=1,updated_at=? WHERE id=?",(stamp,entry_id))
        queue(con,"entry",entry_id,"delete",{"id":entry_id,"updated_at":stamp})
        con.execute("DELETE FROM links WHERE source_id=? OR target_id=?",(entry_id,entry_id))
    return jsonify({"ok":True})

@app.get("/api/entries/<entry_id>/links")
def get_links(entry_id):
    with db() as con:
        rows = con.execute("""
          SELECT e.* FROM entries e JOIN links l
          ON (e.id=l.target_id AND l.source_id=?) OR (e.id=l.source_id AND l.target_id=?)
          WHERE e.deleted=0 ORDER BY e.updated_at DESC
        """,(entry_id,entry_id)).fetchall()
        return jsonify([entry_dict(r) for r in rows])

@app.post("/api/entries/<entry_id>/links")
def add_link(entry_id):
    data = request.get_json(force=True)
    target = data.get("target_id")
    if not target or target == entry_id: return jsonify({"error":"Choose another entry"}),400
    stamp, link_id = now(), str(uuid.uuid4())
    with db() as con:
        exists = con.execute("SELECT id FROM entries WHERE id=? AND deleted=0",(target,)).fetchone()
        if not exists: return jsonify({"error":"Entry not found"}),404
        con.execute("INSERT OR IGNORE INTO links(id,source_id,target_id,created_at) VALUES(?,?,?,?)",
                    (link_id,entry_id,target,stamp))
        queue(con,"link",link_id,"upsert",{"id":link_id,"source_id":entry_id,"target_id":target,"created_at":stamp})
    return jsonify({"ok":True})

@app.delete("/api/entries/<entry_id>/links/<target_id>")
def remove_link(entry_id,target_id):
    with db() as con:
        con.execute("DELETE FROM links WHERE (source_id=? AND target_id=?) OR (source_id=? AND target_id=?)",
                    (entry_id,target_id,target_id,entry_id))
        queue(con,"link",f"{entry_id}:{target_id}","delete",{"source_id":entry_id,"target_id":target_id})
    return jsonify({"ok":True})

@app.get("/api/sync/status")
def sync_status():
    with db() as con:
        count = con.execute("SELECT COUNT(*) FROM sync_queue").fetchone()[0]
    return jsonify({"pending":count})

@app.post("/api/sync")
def sync_now():
    data = request.get_json(force=True)
    endpoint = (data.get("endpoint") or "").strip()
    if not endpoint:
        return jsonify({"ok":False,"message":"Add your Google Apps Script web app URL in Settings first."}),400
    # Sync transport is intentionally completed in the cloud-sync milestone.
    # This endpoint keeps the local queue intact until a verified response is received.
    return jsonify({"ok":False,"message":"Google Sheets sync is not configured in this starter build. Your entries are safe locally."}),501

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5057, debug=False)

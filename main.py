import os
import time
import random
import binascii
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="RetroHub Matchmaker & Signaling Server",
    description="Microservizio cloud per il coordinamento delle stanze Netplay P2P e Matchmaking di RetroHub a costo zero.",
    version="1.0.0"
)

# Abilita CORS per permettere chiamate da qualsiasi client RetroHub (Webview / Browser)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateRoomRequest(BaseModel):
    game_id: int
    game_title: str
    platform: str
    host_name: str
    host_addr: str
    port: int = 5000
    region: str = "auto"
    ping_ms: int = 20

class JoinRoomRequest(BaseModel):
    token: str
    player_name: str
    guest_addr: Optional[str] = None

class HeartbeatRequest(BaseModel):
    room_id: str

class CloseRoomRequest(BaseModel):
    room_id: str

class LeaderboardSubmission(BaseModel):
    game_id: int
    game_title: str
    platform: str
    player_name: str
    score_raw: int
    score_display: str
    score_type: str = "score"
    session_duration_sec: int = 0
    proof_hash: str = ""
    client_version: str = "0.60.0"

DB_PATH = os.environ.get("RETROHUB_LEADERBOARD_DB", "leaderboard.db")

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            game_title TEXT NOT NULL,
            platform TEXT NOT NULL,
            player_name TEXT NOT NULL,
            score_raw INTEGER NOT NULL,
            score_display TEXT NOT NULL,
            score_type TEXT NOT NULL DEFAULT 'score',
            proof_hash TEXT NOT NULL DEFAULT '',
            client_version TEXT NOT NULL DEFAULT '',
            achieved_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lb_game ON leaderboard_records(game_id, score_raw DESC)")
    conn.commit()
    return conn

try:
    _init_conn = get_db()
    _init_conn.close()
except Exception:
    DB_PATH = "/tmp/leaderboard.db"
    _init_conn = get_db()
    _init_conn.close()

class LobbyRoom(BaseModel):
    id: str
    game_id: int
    game_title: str
    platform: str
    host_name: str
    host_addr: str
    port: int
    player_count: int
    max_players: int
    status: str
    ping_ms: int
    created_at: int
    region: str

# Memoria in-RAM per le stanze attive (ultra-veloce)
rooms: Dict[str, dict] = {}
ROOM_TTL_SECONDS = 1800  # 30 minuti max di inattività

def cleanup_stale_rooms():
    now = int(time.time())
    stale = [rid for rid, r in rooms.items() if now - r["updated_at"] > ROOM_TTL_SECONDS]
    for rid in stale:
        rooms.pop(rid, None)

@app.get("/")
def root():
    cleanup_stale_rooms()
    return {
        "service": "RetroHub Matchmaking Server",
        "version": "1.0.0",
        "status": "online",
        "active_rooms": len(rooms),
        "docs_url": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": int(time.time())}

@app.get("/api/lobby/rooms", response_model=List[LobbyRoom])
def list_rooms():
    cleanup_stale_rooms()
    waiting_rooms = [
        LobbyRoom(**r["data"])
        for r in rooms.values()
        if r["data"]["status"] == "Waiting"
    ]
    return waiting_rooms

@app.post("/api/lobby/create")
def create_room(req: CreateRoomRequest):
    cleanup_stale_rooms()
    now = int(time.time())
    room_num = random.randint(1000, 9999)
    room_id = f"RH-{room_num}"
    
    room_data = {
        "id": room_id,
        "game_id": req.game_id,
        "game_title": req.game_title,
        "platform": req.platform,
        "host_name": req.host_name,
        "host_addr": req.host_addr,
        "port": req.port,
        "player_count": 1,
        "max_players": 2,
        "status": "Waiting",
        "ping_ms": req.ping_ms,
        "created_at": now,
        "region": req.region,
    }
    
    rooms[room_id] = {
        "data": room_data,
        "updated_at": now
    }
    
    # Calcola il connection token compatibile con RetroHub
    raw_token = f"{req.host_addr}:{req.port}:0:{room_id}".encode("utf-8")
    hex_token = "RH" + binascii.hexlify(raw_token).decode("utf-8")
    
    return {
        "room_id": room_id,
        "connection_token": hex_token,
        "room": room_data
    }

@app.post("/api/lobby/join")
def join_room(req: JoinRoomRequest):
    cleanup_stale_rooms()
    room_id = req.token.strip().upper()
    if not room_id.startswith("RH-"):
        room_id = f"RH-{room_id}"
        
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Stanza non trovata o scaduta")
        
    room_entry = rooms[room_id]
    rdata = room_entry["data"]
    
    if rdata["status"] != "Waiting":
        raise HTTPException(status_code=400, detail="Stanza chiusa o già in gioco")
    if rdata["player_count"] >= rdata["max_players"]:
        raise HTTPException(status_code=400, detail="Stanza piena")
        
    rdata["player_count"] += 1
    rdata["status"] = "Connected"
    room_entry["updated_at"] = int(time.time())
    
    raw_token = f"{rdata['host_addr']}:{rdata['port']}:0:{room_id}".encode("utf-8")
    hex_token = "RH" + binascii.hexlify(raw_token).decode("utf-8")
    
    return {
        "room_id": room_id,
        "connection_token": hex_token,
        "host_addr": rdata["host_addr"],
        "port": rdata["port"],
        "game_id": rdata["game_id"],
        "game_title": rdata["game_title"],
        "platform": rdata["platform"],
        "host_name": rdata["host_name"],
        "peer_name": req.player_name,
        "status": "Connected"
    }

@app.post("/api/lobby/heartbeat")
def heartbeat(req: HeartbeatRequest):
    if req.room_id in rooms:
        rooms[req.room_id]["updated_at"] = int(time.time())
        return {"status": "alive", "room_id": req.room_id}
    raise HTTPException(status_code=404, detail="Stanza non trovata")

@app.post("/api/lobby/close")
def close_room(req: CloseRoomRequest):
    if req.room_id in rooms:
        rooms.pop(req.room_id, None)
        return {"status": "closed", "room_id": req.room_id}
    return {"status": "already_closed"}

@app.post("/api/leaderboard/submit")
def submit_leaderboard(req: LeaderboardSubmission):
    if req.score_raw <= 0 or req.score_raw > 50_000_000_000:
        raise HTTPException(status_code=400, detail="Punteggio non valido")
    p_name = req.player_name.strip()[:24] or "Player"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT id, score_raw FROM leaderboard_records WHERE game_id = ? AND LOWER(player_name) = LOWER(?) ORDER BY score_raw DESC LIMIT 1",
            (req.game_id, p_name),
        )
        row = cur.fetchone()
        if row and row["score_raw"] >= req.score_raw:
            return {"status": "ok", "accepted": True, "is_new_best": False}
        if row:
            conn.execute(
                """UPDATE leaderboard_records
                   SET score_raw = ?, score_display = ?, game_title = ?, platform = ?, proof_hash = ?, client_version = ?, achieved_at = ?
                   WHERE id = ?""",
                (req.score_raw, req.score_display, req.game_title, req.platform, req.proof_hash, req.client_version, now_iso, row["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO leaderboard_records
                   (game_id, game_title, platform, player_name, score_raw, score_display, score_type, proof_hash, client_version, achieved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (req.game_id, req.game_title, req.platform, p_name, req.score_raw, req.score_display, req.score_type, req.proof_hash, req.client_version, now_iso),
            )
        conn.commit()
        return {"status": "ok", "accepted": True, "is_new_best": True}
    finally:
        conn.close()

@app.get("/api/leaderboard/global")
def get_global_leaderboard(limit: int = 25):
    lim = max(1, min(limit, 100))
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT game_id, game_title, platform, player_name, score_raw, score_display, achieved_at
               FROM leaderboard_records
               ORDER BY score_raw DESC
               LIMIT ?""",
            (lim,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.get("/api/leaderboard/{game_id}")
def get_game_leaderboard(game_id: int, limit: int = 25):
    lim = max(1, min(limit, 100))
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT player_name, score_raw, score_display, achieved_at
               FROM leaderboard_records
               WHERE game_id = ?
               ORDER BY score_raw DESC
               LIMIT ?""",
            (game_id, lim),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.get("/api/players/available")
def check_player_available(name: str):
    clean = name.strip()
    if not clean:
        return {"available": False}
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM leaderboard_records WHERE LOWER(player_name) = LOWER(?) LIMIT 1",
            (clean,),
        ).fetchone()
        return {"available": row is None, "name": clean}
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

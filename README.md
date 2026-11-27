# 🕹️ RetroHub Netplay Matchmaker & Cloud Leaderboard Server

Microservizio cloud ultra-leggero (FastAPI + SQLite) per il matchmaking P2P, la bacheca stanze pubbliche e la **classifica globale persistente** di **RetroHub** (`https://retrohub-matchmaker.onrender.com`).

## 🚀 Caratteristiche
- **Zero Costo (0,00 €/mese):** Progettato per girare 24/7 su **Render.com Free Tier** (750 ore/mese incluse) con workflow keep-alive automatico su GitHub Actions.
- **Stanze Netplay in RAM:** Bacheca pubblica veloce (`< 5 ms` a server caldo) con auto-cleanup delle stanze inattive dopo 30 minuti.
- **Classifiche Cloud Persistenti (SQLite):** Tabella `leaderboard_records` con indice `(game_id, score_raw DESC)` e deduplicazione automatica del miglior punteggio per `(game_id, player_name)`.
- **REST & Swagger Documentato:** Interfaccia API interattiva su `/docs`.

## 📡 API Endpoints

### Lobby & Matchmaking
- `GET /` — Stato del server e conteggio stanze attive.
- `GET /health` — Endpoint uptime & keep-alive anti-sleep.
- `GET /api/lobby/rooms` — Lista stanze pubbliche in attesa (`Waiting`).
- `POST /api/lobby/create` — Creazione stanza host e generazione token `RH...`.
- `POST /api/lobby/join` — Unione a una stanza tramite codice invito.
- `POST /api/lobby/heartbeat` — Rinnovo TTL della stanza (30 min).
- `POST /api/lobby/close` — Chiusura stanza.

### Classifiche Cloud & Giocatori
- `POST /api/leaderboard/submit` — Invia/aggiorna il record di un giocatore per `game_id` (mantiene il miglior `score_raw` per `(game_id, player_name)`).
- `GET /api/leaderboard/global?limit=25` — Classifica globale multi-gioco ordinata per punteggio.
- `GET /api/leaderboard/{game_id}?limit=25` — Classifica Cloud per singolo titolo.
- `GET /api/players/available?name=...` — Verifica se un nickname ha già record registrati sul server.

## ⏰ Keep-Alive 24/24 a Costo Zero (`.github/workflows/keepalive.yml`)
Sui piani gratuiti Render.com, l'istanza va in *sleep* dopo 15 minuti di inattività (provocando 30–50s di *cold start* e ricreazione del container).
Per mantenerlo operativo 24/24 a costo zero:
1. Il workflow [`.github/workflows/keepalive.yml`](.github/workflows/keepalive.yml) esegue `GET https://retrohub-matchmaker.onrender.com/health` ogni **10 minuti** (`cron: '*/10 * * * *'`), ed è anche avviabile manualmente via `workflow_dispatch`.
2. Lato client, RetroHub chiama inoltre `prewarm_matchmaker()` (`src/lobby.rs`) all'avvio per svegliare subito l'istanza in caso di ripartenza.
3. *Nota operativa:* se `schedule` di GitHub Actions dovesse subire ritardi nelle ore di punta, è possibile affiancare un monitor gratuito su **UptimeRobot** sullo stesso endpoint `/health`.



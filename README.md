# 🕹️ RetroHub Netplay Matchmaker & Signaling Server

Microservizio cloud ultra-leggero per il matchmaking, la bacheca stanze pubbliche e il coordinamento peer-to-peer (P2P) di RetroHub Launcher.

## 🚀 Caratteristiche
- **Zero Costo:** Progettato specificamente per girare 24/7 su **Koyeb Free Tier** o **Oracle Always Free** a 0,00€.
- **Latenza Minima:** Architettura asincrona in memoria (RAM) con risposta < 5ms.
- **Auto-Cleanup:** Rimozione automatica delle stanze abbandonate o inattive dopo 30 minuti.
- **REST & Swagger Documentato:** Interfaccia API completa visibile su `/docs`.

## 📡 API Endpoints
- `GET /` - Stato del server e conteggio stanze attive.
- `GET /health` - Endpoint di monitoraggio uptime.
- `GET /api/lobby/rooms` - Lista stanze pubbliche in attesa di sfidante.
- `POST /api/lobby/create` - Creazione di una nuova stanza host.
- `POST /api/lobby/join` - Unione a una stanza esistente.
- `POST /api/lobby/heartbeat` - Rinnovo del timer della stanza.
- `POST /api/lobby/close` - Chiusura della stanza.

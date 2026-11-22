# 🕹️ RetroHub Netplay Matchmaker & Signaling Server

Microservizio cloud ultra-leggero per il matchmaking, la bacheca stanze pubbliche e il coordinamento peer-to-peer (P2P) di RetroHub Launcher.

## 🚀 Caratteristiche
- **Zero Costo:** Progettato specificamente per girare 24/7 su **Koyeb Free Tier** o **Oracle Always Free** a 0,00€.
- **Latenza Minima:** Architettura asincrona in memoria (RAM) con risposta < 5ms.
- **Auto-Cleanup:** Rimozione automatica delle stanze abbandonate o inattive dopo 30 minuti.
- **REST & Swagger Documentato:** Interfaccia API completa visibile su `/docs`.

## 📡 API Endpoints
- `GET /` - Stato del server e conteggio stanze attive.
- `GET /health` - Endpoint di monitoraggio uptime e heartbeat anti-sleep.
- `GET /api/lobby/rooms` - Lista stanze pubbliche in attesa di sfidante.
- `POST /api/lobby/create` - Creazione di una nuova stanza host.
- `POST /api/lobby/join` - Unione a una stanza esistente.
- `POST /api/lobby/heartbeat` - Rinnovo del timer della stanza.
- `POST /api/lobby/close` - Chiusura della stanza.

## ⏰ Keep-Alive Strategy (Anti-Sleep a Costo Zero)
Sulle piattaforme PaaS gratuite (come Render.com Free Tier), l'istanza va in idle spin-down dopo 15 minuti di inattività, provocando un ritardo di cold-start di circa 40-50 secondi al primo risveglio.
Per azzerare questo ritardo e garantire un matchmaker attivo 24/7 a 0 millisecondi di latenza a costo zero:
1. Viene configurato un monitoraggio HTTP esterno gratuito (tramite cron-job.org, UptimeRobot o cronjob locale di Hermes).
2. Viene inviata una richiesta periodica `GET /health` ogni 10 minuti.
3. Il server rimane permanentemente attivo in memoria senza consumare crediti.


# EstateWise — PRD (Product Requirements Document)

## Original Problem Statement
Costruire un gestionale immobiliare completo per gestione affitti con:
- Multi-immobile, multi-unità, multi-contratto, multi-soggetto
- Notifiche automatiche (rate scadute, contratti in scadenza, APE, documenti)
- Generazione PDF (contratti, verbali, report)
- Mappa interattiva immobili
- Dashboard con KPI
- Audit log completo
- Sistema notifiche con escalation (Celery + Redis + Beat)
- **Modulo APE** (Attestato Prestazione Energetica) per ogni unità con scadenza modificabile, sostituzione file, classe energetica
- **Integrazione AI** (Ollama locale + provider esterni: OpenAI/Claude/Gemini via LiteLLM) configurabile dall'utente
- **Autoinstaller Proxmox LXC** (`install.sh` one-shot, container privilegiato, nesting Docker)

## Stack Tecnico
- **Frontend**: React + Vite + TailwindCSS + shadcn/ui + Zustand + React-Leaflet
- **Backend**: FastAPI + MongoDB (motor) + Pydantic v2
- **Async**: Celery + Redis (Beat per cron escalation notifiche)
- **AI**: Ollama locale + provider esterni (OpenAI/Anthropic/Gemini via LiteLLM)
- **Deploy**: Docker Compose stack su Proxmox LXC privilegiato (nesting, keyctl, apparmor unconfined)

## Implementato (Cronologia)

### 2026-05 — P0 Core MVP (Completato)
- Auth JWT, RBAC (supervisore/gestore/lettura)
- CRUD Immobili, Unità, Soggetti, Contratti, Rate, Verbali, Documenti, Interventi
- Dashboard KPI + Mappa interattiva
- Audit log su tutte le mutazioni
- Wizard contratto multi-step con generazione rate
- Notifiche Celery+Redis con escalation idempotente
- Pagine: Dashboard, Immobili (lista/detail), Unità, Soggetti, Contratti (wizard), Notifiche, Mappa

### 2026-05 — P0 Deploy + AI + APE (Completato)
- **install.sh / uninstall.sh** Proxmox LXC autoinstaller (792 righe), include nesting=1, keyctl=1, apparmor unconfined, bind mount `/srv/estatewise/{mongo,uploads,ollama}`, deploy stack Docker (mongo+api+worker+beat+redis+frontend+ollama), self-test finale, pull modello Ollama default `llama3.2:3b`
- **Modulo APE completo**: 12 endpoint REST, modello con classe A4-G + zona climatica + EPgl,nren + certificatore + storico modifiche, upload PDF/immagine, rimando scadenza tracciato, sostituzione file, statistiche dashboard, marcatura "sostituito" su nuovo APE
- **Integrazione AI**: 9 endpoint REST, switch Ollama/OpenAI/Anthropic/Gemini in DB (collection `config` key=`ai_config`), chat conversazionale con sessioni e cronologia, contesto app (immobili/contratti/rate/APE), generazione testo (email sollecito, clausola, disdetta, report), suggerimenti proattivi, analisi documento PDF (estrazione testo via pypdf + LLM), test connessione
- **Frontend nuove pagine**: ApePage (CRUD+filtri+dialog rimando/sostituzione/storico+analisi AI), AiAssistantPage (sidebar sessioni+chat+genera testo), ImpostazioniPage (tab AI con provider+modello+temperature+test connessione)
- **Routing**: ImmobileDetailPage e VerbaleFormPage collegati alle route, /ape, /ai, /impostazioni, /verbali/nuovo/:contrattoId

### 2026-05 — P1 Reports + Notifiche + Pagine secondarie (Completato)
- **WeasyPrint reale**: rimosso fallback try/except in `routers/reports.py`, librerie OS già nel Dockerfile, PDF reports ora generati realmente (contratti, verbali, rate, dashboard)
- **Task Celery APE**: `check_ape_scadenza` con escalation 90/30/7gg + notifica APE scaduti idempotente (max 1 anno post-scadenza), schedulato giornalmente alle 8:45, marca automaticamente stato `scaduto`. Nuovi tipi `ape_scadenza` e `ape_scaduto` aggiunti a `TipoNotifica` enum
- **Pagine UI nuove**: 
  - **VerbaliListPage** (lista verbali con filtro consegna/riconsegna + download PDF)
  - **DocumentiPage** (lista + upload con tipo/scadenza + filtro in scadenza + analisi AI con dialog risultato)
  - **ManutenzionePage** (lista interventi + crea con cascading immobile→unità + cambio stato)
- **Fix bug** SoggettiPage: rimosso `<SelectItem value="">` (non ammesso da Radix Select)
- **UX miglioramento**: sostituiti `alert()` con Dialog componente per visualizzare risultati AI in DocumentiPage e ApePage
- **Test**: backend P1 100% (reports + Celery APE + sync fallback), frontend ~95% (3 pagine + regressione)

### 2026-05 — P2 Pagine finali + Profilo (Completato)
- **Backend**: nuovo endpoint `PUT /api/v1/auth/me` (aggiorna nome/email utente loggato, valida email duplicate)
- **Frontend nuove pagine** (sostituito `<PlaceholderPage />` in `App.js` per tutte le route):
  - **ReportPage** (`/report`) — Tab Pagamenti con export PDF/CSV/Excel via blob download + Tab Executive con KPI patrimonio/finanze/profit-loss mensile (solo supervisore)
  - **AuditLogPage** (`/audit`) — viewer log con filtri tabella/azione, paginazione (25 per pagina), dialog dettaglio con JSON formattato old/new values (solo supervisore)
  - **ProfiloPage** (`/profilo`) — visualizzazione + modifica nome/email, info ruolo/stato/last_login, link a cambio password
  - **CambioPasswordPage** (`/cambio-password`) — form 3 campi con validazione live (8+ caratteri/maiuscola/numero/speciale), toggle visibilità password
  - **ContrattoDetailPage** (`/contratti/:id`) — dati contratto enriched, KPI rate, tab Anagrafica/Rate/Verbali, download PDF, chiudi contratto, nuovo verbale
  - **SoggettoDetailPage** (`/soggetti/:id`) — dati anagrafici + rating stelle, tab contratti come affittuario+locatore con badge ruolo
  - **SoggettoFormPage** (`/soggetti/nuovo` e `/soggetti/:id/modifica`) — form persona/azienda con validazione CF/P.IVA condizionale
- **VerbaleFormPage**: aggiunto **selettore contratto** quando `contrattoId` non passato in URL (combobox con codice+affittuario+immobile/unità), bottone Salva disabled finché non si seleziona
- **Bug fix backend**: `services/audit.py` ora sanitizza ricorsivamente `old_values`/`new_values` al WRITE time (rimuove `_id` e converte `ObjectId`→str e `datetime`→ISO) — risolve definitivamente errore 500 su `GET /api/v1/audit` causato da MongoDB ObjectId non JSON-serializzabile
- **Test**: backend 100% (12/12 + nuovo PUT /auth/me + change-password full cycle), frontend ~98% (8 nuove pagine, tutte funzionali)

### 2026-05 — Brief AI mattutino via email (Completato)
- **Backend**:
  - `models/brief.py`: `BriefConfig`, `BriefConfigUpdate`, `BriefPreview` (Pydantic v2, EmailStr validation)
  - `services/brief.py`: `aggregate_brief_data` (raccoglie rate in ritardo, APE in scadenza 90gg, contratti in scadenza 30gg, interventi aperti enriched con immobile/unità/affittuario), `generate_ai_summary` (chiama `services/ai_provider.send_chat_message` con prompt strutturato in italiano + fallback statico se AI non disponibile), `render_brief_html` (email template responsive con sezioni colorate), `render_brief_text` (versione plain), `build_brief` (combina tutto)
  - `routers/brief.py`: 4 endpoint — `GET /api/v1/brief/config`, `PUT /api/v1/brief/config` (solo supervisore), `POST /api/v1/brief/preview` (anteprima HTML+stats), `POST /api/v1/brief/send-now` (invia subito ai destinatari, persiste `last_sent_at`/`last_status`/`last_error`)
  - `tasks/brief.py`: Celery task `send_morning_brief` con event-loop async (`asyncio.run`+`AsyncIOMotorClient`), idempotenza giornaliera (non rinvia se già inviato lo stesso giorno con status success/partial), check `(hour, minute) == (cron_hour, cron_minute)` in TZ Europe/Rome, `force=True` skip dei check
  - `celery_app.py`: schedule `send-morning-brief-check` con `crontab(minute='*')` — gira ogni minuto, il task stesso filtra in base alla configurazione (cron_hour, cron_minute, enabled)
  - `server.py`: registrato `brief_router`
- **Frontend**: nuova tab **Brief AI** in `ImpostazioniPage` con componente `BriefSettings` — toggle abilitato, input ora/minuti, gestione lista email destinatari (add/remove con validazione), 4 checkbox sezioni (rate/APE/contratti/interventi), bottoni Salva/Anteprima (dialog con HTML preview + 4 stats badge)/Invia ora, pannello "Ultimo invio" con stato success/partial/error
- **SMTP**: nessun cambiamento richiesto, `utils/email.py` con `aiosmtplib` già pronto. In dev senza `SMTP_HOST` configurato l'invio restituisce status='error' con messaggio chiaro (no crash). In produzione configurare `SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM/SMTP_PORT/SMTP_USE_TLS` nel `.env` backend.
- **Default**: brief disabilitato di default, l'utente lo abilita esplicitamente da Impostazioni → Brief AI
- **Test (iteration_6)**: 100% backend (15/15 pytest tests), 100% frontend (validazione email, preview dialog, salva, invia ora con error handling, pannello last_status)

## Architettura

```
/app/
├── backend/
│   ├── models/
│   │   ├── ape.py (NUOVO - APE + storico modifiche)
│   │   ├── ai_chat.py (NUOVO - AiConfig, ChatSession, ChatMessage)
│   │   ├── notifica.py (idempotency_key)
│   │   └── ... (immobile, unita, contratto, soggetto, rata, verbale, documento, intervento, audit, user)
│   ├── routers/
│   │   ├── ape.py (NUOVO - 12 endpoint)
│   │   ├── ai.py (NUOVO - 9 endpoint)
│   │   └── ... (auth, immobili, unita, contratti, soggetti, rate, verbali, documenti, interventi, notifiche, dashboard, audit, reports)
│   ├── services/
│   │   ├── ai_provider.py (NUOVO - Ollama + LiteLLM switch)
│   │   ├── audit.py
│   │   └── notifications/
│   ├── tasks/notifications.py
│   ├── celery_app.py
│   ├── server.py
│   ├── Dockerfile (con WeasyPrint deps)
│   └── requirements.txt (con pypdf + litellm)
├── frontend/
│   ├── src/pages/
│   │   ├── ApePage.jsx (NUOVO)
│   │   ├── AiAssistantPage.jsx (NUOVO)
│   │   ├── ImpostazioniPage.jsx (NUOVO)
│   │   ├── ImmobileDetailPage.jsx, VerbaleFormPage.jsx (collegate)
│   │   └── ... (Dashboard, Login, Immobili, Unità, Soggetti, Contratti, Notifiche, Mappa)
│   ├── components/Layout.jsx (con nav APE + Assistente AI)
│   └── Dockerfile + nginx.conf
├── docker-compose.yml
├── install.sh (Proxmox LXC autoinstaller con Ollama + APE persistent storage)
└── uninstall.sh
```

## Endpoint Principali

### APE
- `GET /api/v1/ape` — lista filtrabile
- `POST /api/v1/ape` — crea (no file)
- `POST /api/v1/ape/upload` — crea con file (multipart)
- `GET /api/v1/ape/{id}` / `PUT /api/v1/ape/{id}` / `DELETE /api/v1/ape/{id}`
- `PUT /api/v1/ape/{id}/scadenza` — rimanda scadenza (motivazione tracciata)
- `PUT /api/v1/ape/{id}/file` — sostituisce file
- `GET /api/v1/ape/in-scadenza?giorni=90`
- `GET /api/v1/ape/scaduti`
- `GET /api/v1/ape/by-unita/{unita_id}`
- `GET /api/v1/ape/stats/dashboard`

### AI
- `GET/PUT /api/v1/ai/config` — config provider
- `POST /api/v1/ai/chat` — chat con session
- `GET /api/v1/ai/sessions` — lista sessioni utente
- `GET /api/v1/ai/sessions/{id}/messages`
- `DELETE /api/v1/ai/sessions/{id}`
- `POST /api/v1/ai/test-connection`
- `POST /api/v1/ai/generate` — testi predefiniti
- `POST /api/v1/ai/suggest` — suggerimenti proattivi
- `POST /api/v1/ai/analyze-document` — analisi PDF (ape_id o documento_id)

## Roadmap (Backlog)

### P2
- Cron import/export multi-formato
- Multi-tenancy (azienda)
- Mobile-first verbali (PWA + camera per foto in checklist)
- Integrazione bancaria per riconciliazione rate
- AI Vision per leggere foto verbali e classificare automaticamente lo stato degli ambienti
- A11y: aggiungere `DialogDescription` ai componenti `<DialogContent>` per evitare warning console
- Brief AI: ottimizzare `aggregate_brief_data` con `$lookup` o batch `$in` per evitare N+1 query MongoDB su grossi volumi

## Credenziali Admin (seed automatico)
- Email: `r.disante@impresacingoli.it`
- Password: `Cingoli26!!`
- Ruolo: supervisore

## File chiavi env
- `/app/backend/.env`: MONGO_URL, DB_NAME, EXTERNAL_AI_KEY, OLLAMA_URL
- `/app/frontend/.env`: REACT_APP_BACKEND_URL

## Note tecniche
- AI: provider default in DB è `ollama` ma se Ollama non raggiungibile → fallisce 503. In dev senza Ollama, switch a `openai` via PUT /ai/config
- Storage uploads: `/data/uploads/{ape,documenti,foto_verbali}` → bind mount LXC `/srv/estatewise/uploads`
- Ollama in produzione gira come servizio Docker `estatewise-ollama:11434` con volume `/srv/estatewise/ollama` per modelli

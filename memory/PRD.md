# EstateWise - PRD (Product Requirements Document)

## Versione: 1.1.0
## Data ultimo aggiornamento: 2026-01-21

---

## 📋 Descrizione Prodotto

**EstateWise** è una web app enterprise per la gestione completa degli affitti immobiliari. Permette di gestire contratti, incassi, notifiche automatiche, documenti e molto altro.

---

## 🏗️ Stack Tecnologico

### Frontend
- **Framework:** React 18 + Vite
- **Styling:** Tailwind CSS + shadcn/ui
- **State Management:** Zustand
- **Forms:** React Hook Form + Zod
- **Mappe:** React-Leaflet (OSM)
- **Grafici:** Recharts

### Backend
- **Framework:** FastAPI (Python 3.11)
- **Database:** MongoDB
- **Task Asincroni:** Celery + Redis + Beat
- **PDF:** WeasyPrint (opzionale - richiede librerie di sistema)
- **Auth:** JWT (passlib + bcrypt)

### Deploy
- **Container:** Docker Compose
- **Reverse Proxy:** Nginx
- **Servizi:** mongodb, redis, api, celery-worker, celery-beat, frontend, nginx

---

## ✅ Funzionalità Implementate

### P0 - Critiche (COMPLETATE 2026-01-21)

#### P0-1: Sistema Notifiche con Celery+Redis+Beat ✅
- Task schedulati per controllo scadenze
- Escalation: rate ritardo (1, 7, 15 gg), scadenze contratto (365, 30, 1 gg), documenti (30, 7 gg)
- Deduplicazione con idempotency_key
- Email SMTP con graceful degradation
- Pagina frontend /notifiche con stats e azioni
- Trigger manuale per supervisori

#### P0-2: Mappa con fitBounds ✅
- React-Leaflet con OpenStreetMap
- fitBounds automatico su tutti i marker
- Padding 40px, maxZoom 16
- Gestione 1 marker (setView zoom 15)
- Gestione 0 marker (placeholder)
- Legenda con stati: Critico, Attenzione, OK, Non locato

#### P0-3: Wizard Contratto Multi-step ✅
- 6 step: Unità, Locatore, Affittuario, Termini, Reminder, Conferma
- Generazione rate automatiche (mensile/trimestrale/annuale)
- Aggiornamento stato unità a "locata"
- Preview rating affittuario
- Upload documento firmato
- Navigazione avanti/indietro con validazione

### Funzionalità Core Implementate
- **Autenticazione:** Login JWT con ruoli (supervisore, gestore, lettura)
- **Immobili:** CRUD completo con geolocalizzazione
- **Unità:** CRUD con stati (libera, locata, manutenzione)
- **Contratti:** CRUD con stati e rate automatiche
- **Soggetti:** CRUD locatori e affittuari
- **Pagamenti/Rate:** Lista, filtri, funzione Incassa
- **Dashboard:** KPI cards, scadenze, problemi
- **Audit Log:** Tracciamento modifiche

---

## 🔜 Backlog (P1/P2)

### P1 - Importanti
- [ ] Verbali consegna/riconsegna con checklist e foto
- [ ] Report PDF con WeasyPrint (fascicolo contratto, scheda immobile, report pagamenti)
- [ ] Pagine dettaglio complete (Immobile, Contratto, Soggetto)
- [ ] Sistema valutazione affittuari

### P2 - Prossimi
- [ ] docker-compose.yml aggiornato con tutti i servizi
- [ ] README.md con documentazione completa
- [ ] Dashboard Executive per Supervisore
- [ ] Audit Log Viewer
- [ ] Template email personalizzabili
- [ ] Import/Export Excel

### Future
- [ ] Webhook per integrazioni esterne
- [ ] Permessi per portafoglio
- [ ] Connessioni DB esterne
- [ ] Multi-tenancy

---

## 🧪 Test

### Backend Tests (22/22 passed)
- Health check, Auth, Notifiche, Mappa, Contratti, Rate, Dashboard, Immobili, Unità
- File: `/app/tests/test_estatewise_p0.py`

### Frontend Tests
- Tutte le pagine P0 testate via Playwright
- Login, Notifiche, Mappa, Wizard Contratto, Pagamenti

---

## 🔐 Credenziali Test

```
Email: admin@estatewise.it
Password: admin123
Ruolo: supervisore
```

---

## 📂 Struttura File

```
/app/
├── backend/
│   ├── celery_app.py          # Configurazione Celery+Beat
│   ├── server.py              # FastAPI app principale
│   ├── models/                # Modelli Pydantic
│   ├── routers/               # API endpoints
│   ├── tasks/                 # Celery tasks
│   │   └── notifications.py   # Task notifiche con escalation
│   ├── templates/pdf/         # Template HTML per WeasyPrint
│   └── utils/                 # Utilities (auth, email, geocoding)
├── frontend/
│   ├── src/
│   │   ├── pages/             # Pagine React
│   │   │   ├── NotifichePage.jsx
│   │   │   ├── MappaPage.jsx
│   │   │   ├── ContrattoWizardPage.jsx
│   │   │   └── PagamentiPage.jsx
│   │   ├── components/ui/     # shadcn/ui components
│   │   └── stores/            # Zustand stores
│   └── package.json
├── docker-compose.yml         # Stack completo
├── nginx/nginx.conf           # Reverse proxy config
└── test_reports/              # Report test automatici
```

---

## ⚠️ Note Tecniche

1. **SMTP:** Se non configurato, le notifiche email vengono marcate "failed" senza crash
2. **WeasyPrint:** Richiede librerie di sistema (libpangoft2). Se assenti, PDF non disponibili
3. **Redis/Celery:** Se non disponibili, task notifiche eseguiti in modo sincrono
4. **Select shadcn/ui:** Non usare `value=""` vuoto, usare `value="all"` o simile

---

## 📈 Metriche Chiave

- **4 Immobili** con coordinate per test mappa
- **1 Unità** (stato: locata)
- **2 Soggetti** (1 azienda locatore, 1 persona affittuario)
- **1 Contratto attivo** con 12 rate mensili
- **4 Notifiche** generate per test

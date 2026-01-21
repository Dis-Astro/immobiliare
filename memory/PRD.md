# EstateWise - PRD (Product Requirements Document)

## Problema Originale
Webapp enterprise completa per gestione affitti immobiliari aziendali che superi i limiti dei software esistenti, combinando:
- Gestione contrattuale avanzata
- UX intuitiva e fluida (problemi-first)
- Valutazione reputazionale affittuari (feature unica)
- Vista mappa interattiva con geolocalizzazione (marker colorati per criticità)
- Reportistica avanzata con grafici, KPI e export PDF/Excel
- Notifiche intelligenti multi-canale (email + notifiche interne)

## Stack Tecnologico
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui + Zustand + React-Leaflet
- **Backend**: FastAPI (Python 3.11+) + MongoDB + JWT Auth
- **Infrastruttura**: Docker-ready, SMTP configurabile

## User Personas
1. **Supervisore**: Accesso completo, gestione utenti, report executive, audit log
2. **Gestore**: CRUD operativo su immobili/contratti/pagamenti/documenti
3. **Solo-lettura**: Consultazione dati senza modifiche

## Core Requirements (Implementati)
- [x] Autenticazione JWT con refresh token
- [x] RBAC (Role-Based Access Control)
- [x] Dashboard problemi-first con KPI
- [x] Mappa interattiva con marker colorati (rosso/giallo/verde/grigio)
- [x] Gestione Immobili con geocodifica Nominatim
- [x] Gestione Unità immobiliari
- [x] Gestione Contratti con generazione rate automatica
- [x] Gestione Soggetti (locatori/affittuari)
- [x] Sistema Pagamenti/Rate con tracking ritardi
- [x] Valutazione reputazionale affittuari
- [x] Eventi critici
- [x] Sistema notifiche (in-memory scheduler)
- [x] Audit logging
- [x] API RESTful completa (/api/v1/*)
- [x] UI completamente in Italiano

## Cosa è Stato Implementato (Gen 2026)

### Backend (17 modelli MongoDB)
- users, soggetti, immobili, unita, contratti, rate
- documenti, valutazioni_affittuari, eventi_critici
- verbali, variazioni, spese, interventi
- notifiche, audit_log, recessi

### Frontend Pages
- Login Page
- Dashboard (KPI + problemi-first)
- Mappa Interattiva (React-Leaflet + OpenStreetMap)
- Immobili List + Form creazione
- Contratti List
- Soggetti List
- Pagamenti con azione rapida incasso

### API Endpoints
- /api/v1/auth/* (login, refresh, me, change-password)
- /api/v1/users/* (CRUD utenti)
- /api/v1/soggetti/* (CRUD soggetti)
- /api/v1/immobili/* (CRUD + geocoding)
- /api/v1/unita/* (CRUD unità)
- /api/v1/contratti/* (CRUD + generazione rate)
- /api/v1/rate/* (pagamenti + incasso)
- /api/v1/documenti/* (upload + metadata)
- /api/v1/valutazioni/* (rating affittuari)
- /api/v1/mappa/markers (marker colorati)
- /api/v1/dashboard/* (KPI + liste)
- /api/v1/reports/* (export CSV/Excel)
- /api/v1/health (status check)

## Prioritized Backlog

### P0 (Immediato)
- [x] MVP funzionante completato

### P1 (Alta priorità)
- [ ] Wizard creazione contratto multi-step
- [ ] Verbali consegna/riconsegna con checklist foto
- [ ] Report PDF con WeasyPrint
- [ ] Pagina dettaglio immobile
- [ ] Pagina dettaglio contratto
- [ ] Pagina dettaglio soggetto con rating completo

### P2 (Media priorità)
- [ ] Variazioni contratto con diff
- [ ] Executive Dashboard (solo supervisore)
- [ ] Import Excel template
- [ ] Gestione documenti scadenza
- [ ] Interventi manutenzione

### P3 (Bassa priorità)
- [ ] Webhook eventi per ERP
- [ ] Full-text search avanzato
- [ ] Permessi portafoglio per gestore
- [ ] PWA con notifiche push

## Credenziali Default
- Email: admin@estatewise.it
- Password: admin123
- Ruolo: Supervisore
- Nota: Al primo accesso richiede cambio password

## Next Steps
1. Implementare wizard contratto multi-step
2. Aggiungere verbali consegna/riconsegna
3. Generazione PDF report con WeasyPrint
4. Completare pagine dettaglio

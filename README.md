# EstateWise

Gestionale immobiliare per affitti, contratti, rate, documenti, APE, notifiche, report, AI assistant, modelli compilabili e parser incassi.

## Installazione Proxmox LXC

Esegui da host Proxmox VE come `root`:

```bash
bash install.sh
```

Variabili utili:

```bash
CT_ID=210 \
CT_HOSTNAME=estatewise \
CT_STORAGE=local-lvm \
CT_IP=dhcp \
GITHUB_REPO=https://github.com/tuo-utente/tuo-repo.git \
GITHUB_BRANCH=main \
bash install.sh
```

Lo script crea un container LXC privilegiato con nesting Docker, storage persistente in `/srv/estatewise`, installa Docker, clona il repo, genera `.env`, builda e avvia:

- MongoDB
- Redis
- FastAPI backend
- Celery worker
- Celery beat
- React frontend
- Ollama locale

URL finali stampati a fine installazione:

- Frontend: `http://IP_CONTAINER:3000`
- Backend API: `http://IP_CONTAINER:8001/api/v1`
- Health: `http://IP_CONTAINER:8001/api/v1/health`

## Sviluppo locale

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

Docker locale:

```bash
docker compose up --build
```

## Modelli compilabili

I modelli documento possono essere caricati come:

- `.docx`: compilabili automaticamente con placeholder `{{campo}}`
- `.pdf`: caricati come modello guida/riferimento

Esempi placeholder DOCX:

- `{{codice_contratto}}`
- `{{data_inizio}}`
- `{{data_scadenza}}`
- `{{canone_importo}}`
- `{{locatore_nome}}`
- `{{affittuario_nome}}`
- `{{immobile_indirizzo}}`
- `{{unita_codice}}`

Endpoint:

- `POST /api/v1/modelli/upload`
- `GET /api/v1/modelli`
- `POST /api/v1/modelli/{id}/compila`

## Parser incassi

Supporta preview da CSV/XLSX di movimenti bancari e propone match con rate da incassare/in ritardo.

Endpoint:

- `POST /api/v1/incassi/import-preview`
- `POST /api/v1/incassi/conferma`

## Note produzione

L'installer genera automaticamente `JWT_SECRET_KEY`. SMTP, provider AI esterni e repository privati possono essere configurati con variabili ambiente prima dell'installazione.
